#!/usr/bin/env python3
"""
Git Diff Parser for Azure Code Reviewer

Extracts and sanitizes git diffs for pull request analysis.
"""

import os
import re
import subprocess
from typing import Tuple
from dataclasses import dataclass


@dataclass
class DiffResult:
    """Result of a git diff operation"""
    content: str
    files_changed: list[str]
    additions: int
    deletions: int
    sanitized: bool


class GitDiffParser:
    """Parser for git diff operations with security sanitization"""

    # Regex patterns for secret detection and sanitization
    SECRET_PATTERNS = [
        (r'api[_-]?key[\s]*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'api_key=***REDACTED***'),
        (r'password[\s]*[=:]\s*["\']?([^\s"\']{8,})["\']?', 'password=***REDACTED***'),
        (r'secret[\s]*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'secret=***REDACTED***'),
        (r'token[\s]*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'token=***REDACTED***'),
        (r'bearer[\s]+([a-zA-Z0-9_\-\.]{20,})', 'bearer ***REDACTED***'),
        # CPF (Brazilian tax ID): 000.000.000-00
        (r'\d{3}\.\d{3}\.\d{3}-\d{2}', '***.***.***-**'),
        # Email addresses
        (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '***@***.***'),
        # Credit card patterns (basic)
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '**** **** **** ****'),
        # AWS Access Key
        (r'AKIA[0-9A-Z]{16}', 'AKIA***REDACTED***'),
        # Generic high-entropy strings (potential secrets)
        (r'["\'][a-zA-Z0-9/+=]{40,}["\']', '"***REDACTED***"'),
    ]

    def __init__(self, repo_path: str = "."):
        """
        Initialize the parser

        Args:
            repo_path: Path to the git repository (default: current directory)
        """
        self.repo_path = repo_path
        self._validate_git_repo()

    def _validate_git_repo(self) -> None:
        """Validate that the path is a git repository"""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError:
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def get_pr_diff(
        self,
        base_branch: str = "origin/main",
        sanitize: bool = True
    ) -> DiffResult:
        """
        Get the diff for a pull request

        Args:
            base_branch: Base branch to diff against (default: origin/main)
            sanitize: Whether to sanitize secrets from the diff (default: True)

        Returns:
            DiffResult object containing diff content and metadata
        """
        # Get the diff using merge-base to find common ancestor
        cmd = [
            "git", "diff",
            "--merge-base", base_branch,
            "--unified=3",  # 3 lines of context
            "--no-color"
        ]

        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        diff_content = result.stdout

        # Parse statistics
        files_changed = self._extract_changed_files(diff_content)
        additions, deletions = self._count_changes(diff_content)

        # Sanitize if requested
        if sanitize:
            diff_content = self._sanitize_secrets(diff_content)

        return DiffResult(
            content=diff_content,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            sanitized=sanitize
        )

    def get_diff_for_files(
        self,
        file_paths: list[str],
        base_branch: str = "origin/main",
        sanitize: bool = True
    ) -> DiffResult:
        """
        Get diff for specific files only

        Args:
            file_paths: List of file paths to include in diff
            base_branch: Base branch to diff against
            sanitize: Whether to sanitize secrets

        Returns:
            DiffResult object
        """
        cmd = [
            "git", "diff",
            "--merge-base", base_branch,
            "--unified=3",
            "--no-color",
            "--"
        ] + file_paths

        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        diff_content = result.stdout
        files_changed = self._extract_changed_files(diff_content)
        additions, deletions = self._count_changes(diff_content)

        if sanitize:
            diff_content = self._sanitize_secrets(diff_content)

        return DiffResult(
            content=diff_content,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            sanitized=sanitize
        )

    def _extract_changed_files(self, diff: str) -> list[str]:
        """Extract list of changed files from diff"""
        files = []
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                # Extract filename from "diff --git a/file.py b/file.py"
                parts = line.split()
                if len(parts) >= 4:
                    # Remove 'a/' or 'b/' prefix
                    file_path = parts[2].lstrip('a/')
                    files.append(file_path)
        return files

    def _count_changes(self, diff: str) -> Tuple[int, int]:
        """Count additions and deletions in diff"""
        additions = 0
        deletions = 0

        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

        return additions, deletions

    def _sanitize_secrets(self, content: str) -> str:
        """
        Sanitize secrets from diff content

        Args:
            content: Raw diff content

        Returns:
            Sanitized diff content with secrets masked
        """
        sanitized = content

        for pattern, replacement in self.SECRET_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

        return sanitized

    def get_changed_files_list(self, base_branch: str = "origin/main") -> list[str]:
        """
        Get list of changed files without full diff

        Args:
            base_branch: Base branch to compare against

        Returns:
            List of changed file paths
        """
        cmd = [
            "git", "diff",
            "--merge-base", base_branch,
            "--name-only"
        ]

        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        return [f for f in result.stdout.strip().split('\n') if f]


def get_pr_diff_from_env() -> DiffResult:
    """
    Convenience function to get PR diff using environment variables

    Expected environment variables:
        - SYSTEM_PULLREQUEST_TARGETBRANCH: Target branch (Azure Pipelines)
        - BUILD_REPOSITORY_LOCALPATH: Repository path (Azure Pipelines)

    Returns:
        DiffResult object
    """
    target_branch = os.getenv('SYSTEM_PULLREQUEST_TARGETBRANCH', 'origin/main')
    repo_path = os.getenv('BUILD_REPOSITORY_LOCALPATH', '.')

    # Azure Pipelines provides branch name without 'origin/' prefix
    if not target_branch.startswith('origin/'):
        target_branch = f'origin/{target_branch}'

    parser = GitDiffParser(repo_path=repo_path)
    return parser.get_pr_diff(base_branch=target_branch)


if __name__ == "__main__":
    """CLI interface for testing"""
    import argparse
    import json

    parser_cli = argparse.ArgumentParser(description='Extract and sanitize git diffs')
    parser_cli.add_argument(
        '--base-branch',
        default='origin/main',
        help='Base branch to diff against (default: origin/main)'
    )
    parser_cli.add_argument(
        '--no-sanitize',
        action='store_true',
        help='Disable secret sanitization (use with caution)'
    )
    parser_cli.add_argument(
        '--output',
        help='Output file path (default: stdout)'
    )
    parser_cli.add_argument(
        '--format',
        choices=['diff', 'json'],
        default='diff',
        help='Output format (default: diff)'
    )

    args = parser_cli.parse_args()

    parser = GitDiffParser()
    result = parser.get_pr_diff(
        base_branch=args.base_branch,
        sanitize=not args.no_sanitize
    )

    if args.format == 'json':
        output = json.dumps({
            'files_changed': result.files_changed,
            'additions': result.additions,
            'deletions': result.deletions,
            'sanitized': result.sanitized,
            'diff': result.content
        }, indent=2)
    else:
        output = result.content

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Diff written to {args.output}")
    else:
        print(output)
