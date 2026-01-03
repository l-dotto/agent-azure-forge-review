"""
Azure DevOps API Client for PR comments.

Automatic authentication using Azure Pipelines system variables.
Zero configuration required - works out of the box in pipelines.
"""

import os
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class PRComment:
    """Represents a PR comment to be published."""
    content: str
    thread_context: Optional[Dict[str, Any]] = None  # For inline comments
    parent_comment_id: Optional[int] = None
    comment_type: str = "text"  # text, system, unknown


class AzureDevOpsClient:
    """
    Azure DevOps REST API client with automatic authentication.

    Auto-detects credentials from Azure Pipelines system variables:
    - SYSTEM_ACCESSTOKEN (auto-injected by pipeline)
    - SYSTEM_TEAMFOUNDATIONCOLLECTIONURI
    - SYSTEM_TEAMPROJECT
    - BUILD_REPOSITORY_ID
    - SYSTEM_PULLREQUEST_PULLREQUESTID

    No manual configuration needed!
    """

    API_VERSION = "7.1"

    def __init__(
        self,
        organization_url: Optional[str] = None,
        project: Optional[str] = None,
        repository_id: Optional[str] = None,
        pr_id: Optional[int] = None,
        access_token: Optional[str] = None
    ):
        """
        Initialize client with auto-detection from environment.

        Args:
            organization_url: Azure DevOps org URL (auto-detected if None)
            project: Project name (auto-detected if None)
            repository_id: Repository ID (auto-detected if None)
            pr_id: Pull Request ID (auto-detected if None)
            access_token: PAT or System.AccessToken (auto-detected if None)
        """
        # Auto-detect from Azure Pipelines environment
        self.organization_url = organization_url or os.getenv(
            "SYSTEM_TEAMFOUNDATIONCOLLECTIONURI"
        )
        self.project = project or os.getenv("SYSTEM_TEAMPROJECT")
        self.repository_id = repository_id or os.getenv("BUILD_REPOSITORY_ID")
        self.pr_id = pr_id or self._parse_pr_id()
        self.access_token = access_token or os.getenv("SYSTEM_ACCESSTOKEN")

        # Validate required fields
        self._validate_config()

        # Setup session with retry logic
        self.session = self._create_session()

        logger.info(
            f"Azure DevOps client initialized: "
            f"org={self._mask_url(self.organization_url)}, "
            f"project={self.project}, pr_id={self.pr_id}"
        )

    def _parse_pr_id(self) -> Optional[int]:
        """Parse PR ID from environment variable."""
        pr_id_str = os.getenv("SYSTEM_PULLREQUEST_PULLREQUESTID")
        if pr_id_str:
            try:
                return int(pr_id_str)
            except ValueError:
                logger.warning(f"Invalid PR ID format: {pr_id_str}")
        return None

    def _validate_config(self):
        """Validate all required configuration is present."""
        missing = []

        if not self.organization_url:
            missing.append("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI")
        if not self.project:
            missing.append("SYSTEM_TEAMPROJECT")
        if not self.repository_id:
            missing.append("BUILD_REPOSITORY_ID")
        if not self.pr_id:
            missing.append("SYSTEM_PULLREQUEST_PULLREQUESTID")
        if not self.access_token:
            missing.append("SYSTEM_ACCESSTOKEN")

        if missing:
            raise ValueError(
                f"Missing required Azure DevOps configuration. "
                f"Ensure these environment variables are set: {', '.join(missing)}. "
                f"In azure-pipelines.yml, add 'SYSTEM_ACCESSTOKEN: $(System.AccessToken)' "
                f"to the environment section."
            )

    def _create_session(self) -> requests.Session:
        """Create requests session with automatic retry and authentication."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        })

        return session

    def _mask_url(self, url: str) -> str:
        """Mask organization URL for logging."""
        if not url:
            return "None"
        # Show only domain
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/***"

    def _build_api_url(self, endpoint: str) -> str:
        """Build complete API URL."""
        base = f"{self.organization_url.rstrip('/')}/{self.project}/_apis"
        return f"{base}/{endpoint}?api-version={self.API_VERSION}"

    def create_thread(
        self,
        comments: List[PRComment],
        thread_status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create a new comment thread on the PR.

        Args:
            comments: List of comments to add to the thread
            thread_status: Thread status (active, fixed, closed)

        Returns:
            API response with thread details
        """
        url = self._build_api_url(
            f"git/repositories/{self.repository_id}/pullRequests/{self.pr_id}/threads"
        )

        payload = {
            "comments": [
                {
                    "parentCommentId": 0,
                    "content": comment.content,
                    "commentType": comment.comment_type
                }
                for comment in comments
            ],
            "status": thread_status
        }

        # Add thread context for inline comments
        if comments and comments[0].thread_context:
            payload["threadContext"] = comments[0].thread_context

        logger.debug(f"Creating thread with {len(comments)} comment(s)")

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Thread created successfully: id={result.get('id')}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create thread: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def create_summary_comment(self, content: str) -> Dict[str, Any]:
        """
        Create a top-level summary comment on the PR.

        Args:
            content: Markdown content for the summary

        Returns:
            API response with thread details
        """
        comment = PRComment(
            content=content,
            comment_type="text"
        )
        return self.create_thread([comment], thread_status="closed")

    def create_inline_comment(
        self,
        content: str,
        file_path: str,
        line_number: int,
        thread_status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create an inline comment on a specific file and line.

        Args:
            content: Markdown content for the comment
            file_path: Path to the file (e.g., "src/main.py")
            line_number: Line number to comment on
            thread_status: Thread status (active, fixed, closed)

        Returns:
            API response with thread details
        """
        comment = PRComment(
            content=content,
            thread_context={
                "filePath": f"/{file_path.lstrip('/')}",
                "rightFileStart": {"line": line_number, "offset": 1},
                "rightFileEnd": {"line": line_number, "offset": 1}
            },
            comment_type="text"
        )
        return self.create_thread([comment], thread_status=thread_status)

    def get_existing_threads(self) -> List[Dict[str, Any]]:
        """
        Get all existing threads on the PR.

        Returns:
            List of thread objects
        """
        url = self._build_api_url(
            f"git/repositories/{self.repository_id}/pullRequests/{self.pr_id}/threads"
        )

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            result = response.json()
            threads = result.get("value", [])
            logger.info(f"Retrieved {len(threads)} existing thread(s)")
            return threads

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get existing threads: {e}")
            return []

    def update_thread_status(
        self,
        thread_id: int,
        status: str
    ) -> Dict[str, Any]:
        """
        Update thread status (e.g., mark as fixed/closed).

        Args:
            thread_id: Thread ID to update
            status: New status (active, fixed, closed)

        Returns:
            API response with updated thread
        """
        url = self._build_api_url(
            f"git/repositories/{self.repository_id}/pullRequests/{self.pr_id}/threads/{thread_id}"
        )

        payload = {"status": status}

        try:
            response = self.session.patch(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Thread {thread_id} status updated to '{status}'")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update thread status: {e}")
            raise


def create_client_from_env() -> AzureDevOpsClient:
    """
    Factory function to create client with auto-detected configuration.

    This is the simplest way to use the client in Azure Pipelines:

    Example:
        client = create_client_from_env()
        client.create_summary_comment("## Review Complete!")

    Returns:
        Configured AzureDevOpsClient instance
    """
    return AzureDevOpsClient()
