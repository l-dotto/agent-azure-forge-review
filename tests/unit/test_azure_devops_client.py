"""
Unit tests for Azure DevOps client.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "utils"))

from azure_devops_client import AzureDevOpsClient, PRComment, create_client_from_env


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock Azure Pipelines environment variables."""
    monkeypatch.setenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI", "https://dev.azure.com/test-org/")
    monkeypatch.setenv("SYSTEM_TEAMPROJECT", "test-project")
    monkeypatch.setenv("BUILD_REPOSITORY_ID", "test-repo-id")
    monkeypatch.setenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "123")
    monkeypatch.setenv("SYSTEM_ACCESSTOKEN", "test-token")


@pytest.fixture
def client(mock_env_vars):
    """Create test client."""
    return AzureDevOpsClient(
        organization_url="https://dev.azure.com/test-org/",
        project="test-project",
        repository_id="test-repo-id",
        pr_id=123,
        access_token="test-token"
    )


class TestAzureDevOpsClient:
    """Test Azure DevOps client."""

    def test_initialization_with_explicit_params(self):
        """Test client initialization with explicit parameters."""
        client = AzureDevOpsClient(
            organization_url="https://dev.azure.com/test-org/",
            project="test-project",
            repository_id="test-repo-id",
            pr_id=123,
            access_token="test-token"
        )

        assert client.organization_url == "https://dev.azure.com/test-org/"
        assert client.project == "test-project"
        assert client.repository_id == "test-repo-id"
        assert client.pr_id == 123
        assert client.access_token == "test-token"

    def test_initialization_from_environment(self, mock_env_vars):
        """Test client auto-detects configuration from environment."""
        client = create_client_from_env()

        assert client.organization_url == "https://dev.azure.com/test-org/"
        assert client.project == "test-project"
        assert client.repository_id == "test-repo-id"
        assert client.pr_id == 123
        assert client.access_token == "test-token"

    def test_missing_configuration_raises_error(self, monkeypatch):
        """Test missing environment variables raise ValueError."""
        # Clear all environment variables
        monkeypatch.delenv("SYSTEM_TEAMFOUNDATIONCOLLECTIONURI", raising=False)
        monkeypatch.delenv("SYSTEM_TEAMPROJECT", raising=False)
        monkeypatch.delenv("BUILD_REPOSITORY_ID", raising=False)
        monkeypatch.delenv("SYSTEM_PULLREQUEST_PULLREQUESTID", raising=False)
        monkeypatch.delenv("SYSTEM_ACCESSTOKEN", raising=False)

        with pytest.raises(ValueError, match="Missing required Azure DevOps configuration"):
            AzureDevOpsClient()

    def test_parse_pr_id_valid(self, monkeypatch):
        """Test PR ID parsing from string."""
        monkeypatch.setenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "456")

        client = AzureDevOpsClient(
            organization_url="https://dev.azure.com/test/",
            project="test",
            repository_id="test",
            access_token="test"
        )

        assert client.pr_id == 456

    def test_parse_pr_id_invalid(self, monkeypatch):
        """Test PR ID parsing handles invalid values."""
        monkeypatch.setenv("SYSTEM_PULLREQUEST_PULLREQUESTID", "not-a-number")

        # Invalid PR ID should raise ValueError during validation
        with pytest.raises(ValueError, match="Missing required Azure DevOps configuration"):
            AzureDevOpsClient(
                organization_url="https://dev.azure.com/test/",
                project="test",
                repository_id="test",
                access_token="test"
            )

    def test_build_api_url(self, client):
        """Test API URL construction."""
        url = client._build_api_url("git/repositories/test/pullRequests/123/threads")

        expected = (
            "https://dev.azure.com/test-org/test-project/_apis/"
            "git/repositories/test/pullRequests/123/threads?api-version=7.1"
        )
        assert url == expected

    def test_session_has_auth_header(self, client):
        """Test session includes authorization header."""
        assert "Authorization" in client.session.headers
        assert client.session.headers["Authorization"] == "Bearer test-token"

    def test_session_has_content_type(self, client):
        """Test session includes content-type header."""
        assert "Content-Type" in client.session.headers
        assert client.session.headers["Content-Type"] == "application/json"

    @patch('requests.Session.post')
    def test_create_thread_success(self, mock_post, client):
        """Test creating a comment thread."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 789, "status": "active"}
        mock_post.return_value = mock_response

        comment = PRComment(content="Test comment", comment_type="text")
        result = client.create_thread([comment])

        assert result["id"] == 789
        assert mock_post.called

        # Verify payload structure
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert "comments" in payload
        assert len(payload["comments"]) == 1
        assert payload["comments"][0]["content"] == "Test comment"
        assert payload["status"] == "active"

    @patch('requests.Session.post')
    def test_create_summary_comment(self, mock_post, client):
        """Test creating a summary comment."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 999}
        mock_post.return_value = mock_response

        result = client.create_summary_comment("Summary content")

        assert result["id"] == 999
        assert mock_post.called

        # Verify it's a closed thread (summary threads should be closed)
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]
        assert payload["status"] == "closed"

    @patch('requests.Session.post')
    def test_create_inline_comment(self, mock_post, client):
        """Test creating an inline comment."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 888}
        mock_post.return_value = mock_response

        result = client.create_inline_comment(
            content="Inline comment",
            file_path="src/main.py",
            line_number=42,
            thread_status="active"
        )

        assert result["id"] == 888
        assert mock_post.called

        # Verify thread context is set correctly
        call_args = mock_post.call_args
        payload = call_args.kwargs["json"]

        assert "threadContext" in payload
        assert payload["threadContext"]["filePath"] == "/src/main.py"
        assert payload["threadContext"]["rightFileStart"]["line"] == 42

    @patch('requests.Session.post')
    def test_create_thread_handles_api_error(self, mock_post, client):
        """Test error handling when API returns error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized")
        mock_response.text = "Authentication failed"
        mock_post.return_value = mock_response

        comment = PRComment(content="Test")

        with pytest.raises(requests.exceptions.HTTPError):
            client.create_thread([comment])

    @patch('requests.Session.get')
    def test_get_existing_threads(self, mock_get, client):
        """Test retrieving existing threads."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {"id": 1, "status": "active"},
                {"id": 2, "status": "closed"}
            ]
        }
        mock_get.return_value = mock_response

        threads = client.get_existing_threads()

        assert len(threads) == 2
        assert threads[0]["id"] == 1
        assert threads[1]["id"] == 2

    @patch('requests.Session.patch')
    def test_update_thread_status(self, mock_patch, client):
        """Test updating thread status."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "status": "fixed"}
        mock_patch.return_value = mock_response

        result = client.update_thread_status(thread_id=123, status="fixed")

        assert result["status"] == "fixed"
        assert mock_patch.called

        # Verify payload
        call_args = mock_patch.call_args
        payload = call_args.kwargs["json"]
        assert payload["status"] == "fixed"

    def test_mask_url(self, client):
        """Test URL masking for logging."""
        masked = client._mask_url("https://dev.azure.com/my-org/my-project")
        assert "https://dev.azure.com/***" in masked
        assert "my-org" not in masked
        assert "my-project" not in masked


class TestPRComment:
    """Test PRComment dataclass."""

    def test_pr_comment_creation(self):
        """Test creating a PR comment."""
        comment = PRComment(
            content="Test content",
            comment_type="text"
        )

        assert comment.content == "Test content"
        assert comment.comment_type == "text"
        assert comment.thread_context is None
        assert comment.parent_comment_id is None

    def test_pr_comment_with_thread_context(self):
        """Test creating inline comment with thread context."""
        thread_context = {
            "filePath": "/src/main.py",
            "rightFileStart": {"line": 10, "offset": 1}
        }

        comment = PRComment(
            content="Inline comment",
            thread_context=thread_context
        )

        assert comment.thread_context == thread_context
