#!/usr/bin/env python3
"""
Unit tests for Git Diff Parser
"""

import pytest
from unittest.mock import Mock, patch
import subprocess
import os

from scripts.utils.git_diff_parser import (
    DiffResult,
    GitDiffParser,
    get_pr_diff_from_env
)


class TestDiffResult:
    """Test DiffResult dataclass"""

    def test_diff_result_creation(self):
        """Test creating DiffResult"""
        result = DiffResult(
            content="diff content",
            files_changed=["file1.py", "file2.py"],
            additions=10,
            deletions=5,
            sanitized=True
        )

        assert result.content == "diff content"
        assert len(result.files_changed) == 2
        assert result.additions == 10
        assert result.deletions == 5
        assert result.sanitized is True


class TestGitDiffParser:
    """Test GitDiffParser class"""

    @patch('subprocess.run')
    def test_initialization_valid_repo(self, mock_run):
        """Test initialization with valid git repository"""
        mock_run.return_value = Mock(returncode=0)

        parser = GitDiffParser(repo_path="/test/repo")

        mock_run.assert_called_once()
        assert parser.repo_path == "/test/repo"

    @patch('subprocess.run')
    def test_initialization_invalid_repo(self, mock_run):
        """Test initialization with invalid repository"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        with pytest.raises(ValueError, match="Not a git repository"):
            GitDiffParser(repo_path="/invalid/repo")

    @patch('subprocess.run')
    def test_get_pr_diff(self, mock_run):
        """Test getting PR diff"""
        # Mock validation
        mock_run.return_value = Mock(returncode=0, stdout="")

        parser = GitDiffParser()

        # Mock diff command
        diff_output = """diff --git a/file1.py b/file1.py
index abc123..def456 100644
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
 def hello():
+    print("new line")
     pass
-    old_line()
"""

        mock_run.return_value = Mock(returncode=0, stdout=diff_output)

        result = parser.get_pr_diff(base_branch="origin/main", sanitize=False)

        assert isinstance(result, DiffResult)
        assert "file1.py" in result.files_changed
        assert result.additions == 1
        assert result.deletions == 1
        assert result.sanitized is False

    @patch('subprocess.run')
    def test_get_pr_diff_with_sanitization(self, mock_run):
        """Test diff with secret sanitization"""
        # Mock validation
        mock_run.return_value = Mock(returncode=0, stdout="")

        parser = GitDiffParser()

        # Mock diff with secrets
        diff_with_secrets = """diff --git a/config.py b/config.py
+api_key = "sk_live_abc123def456"
+password = "secret123"
"""

        mock_run.return_value = Mock(returncode=0, stdout=diff_with_secrets)

        result = parser.get_pr_diff(sanitize=True)

        assert "sk_live_abc123def456" not in result.content
        assert "secret123" not in result.content
        assert "***REDACTED***" in result.content
        assert result.sanitized is True

    def test_extract_changed_files(self):
        """Test extracting changed files from diff"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        diff = """diff --git a/file1.py b/file1.py
diff --git a/src/file2.js b/src/file2.js
diff --git a/tests/test_file.py b/tests/test_file.py
"""

        files = parser._extract_changed_files(diff)

        assert len(files) == 3
        assert "file1.py" in files
        assert "src/file2.js" in files
        assert "tests/test_file.py" in files

    def test_count_changes(self):
        """Test counting additions and deletions"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        diff = """@@ -1,3 +1,4 @@
 unchanged line
+added line 1
+added line 2
-deleted line 1
 another unchanged
"""

        additions, deletions = parser._count_changes(diff)

        assert additions == 2
        assert deletions == 1

    def test_sanitize_secrets_api_key(self):
        """Test sanitizing API keys"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = 'api_key = "sk_live_1234567890abcdefghij"'
        sanitized = parser._sanitize_secrets(content)

        assert "sk_live_" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_secrets_password(self):
        """Test sanitizing passwords"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = 'password="mySecretPass123"'
        sanitized = parser._sanitize_secrets(content)

        assert "mySecretPass123" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_sanitize_secrets_cpf(self):
        """Test sanitizing CPF (Brazilian tax ID)"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = "CPF: 123.456.789-00"
        sanitized = parser._sanitize_secrets(content)

        assert "123.456.789-00" not in sanitized
        assert "***.***.***-**" in sanitized

    def test_sanitize_secrets_email(self):
        """Test sanitizing email addresses"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = "user@example.com"
        sanitized = parser._sanitize_secrets(content)

        assert "user@example.com" not in sanitized
        assert "***@***.***" in sanitized

    def test_sanitize_secrets_credit_card(self):
        """Test sanitizing credit card numbers"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = "Card: 1234 5678 9012 3456"
        sanitized = parser._sanitize_secrets(content)

        assert "1234 5678 9012 3456" not in sanitized
        assert "**** **** **** ****" in sanitized

    def test_sanitize_secrets_aws_key(self):
        """Test sanitizing AWS access keys"""
        parser = GitDiffParser.__new__(GitDiffParser)
        parser.repo_path = "."

        content = "AWS_KEY=AKIAIOSFODNN7EXAMPLE"
        sanitized = parser._sanitize_secrets(content)

        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "AKIA***REDACTED***" in sanitized

    @patch('subprocess.run')
    def test_get_changed_files_list(self, mock_run):
        """Test getting list of changed files"""
        # Mock validation
        mock_run.return_value = Mock(returncode=0, stdout="")

        parser = GitDiffParser()

        # Mock git diff --name-only
        file_list = "file1.py\nfile2.js\nfile3.md"
        mock_run.return_value = Mock(returncode=0, stdout=file_list)

        files = parser.get_changed_files_list(base_branch="origin/main")

        assert len(files) == 3
        assert "file1.py" in files
        assert "file2.js" in files
        assert "file3.md" in files

    @patch('subprocess.run')
    def test_get_diff_for_files(self, mock_run):
        """Test getting diff for specific files"""
        # Mock validation
        mock_run.return_value = Mock(returncode=0, stdout="")

        parser = GitDiffParser()

        # Mock diff for specific files
        diff_output = """diff --git a/file1.py b/file1.py
+new line
"""

        mock_run.return_value = Mock(returncode=0, stdout=diff_output)

        result = parser.get_diff_for_files(
            file_paths=["file1.py"],
            base_branch="origin/main",
            sanitize=False
        )

        assert isinstance(result, DiffResult)
        assert "file1.py" in result.files_changed


class TestGetPRDiffFromEnv:
    """Test convenience function for Azure Pipelines"""

    @patch('scripts.utils.git_diff_parser.GitDiffParser')
    def test_get_pr_diff_from_env_defaults(self, mock_parser_class):
        """Test with default environment"""
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="diff",
            files_changed=[],
            additions=0,
            deletions=0,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        with patch.dict(os.environ, {}, clear=True):
            _ = get_pr_diff_from_env()

            mock_parser_class.assert_called_once_with(repo_path='.')
            mock_parser.get_pr_diff.assert_called_once_with(base_branch='origin/main')

    @patch('scripts.utils.git_diff_parser.GitDiffParser')
    def test_get_pr_diff_from_env_azure(self, mock_parser_class):
        """Test with Azure Pipelines environment variables"""
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="diff",
            files_changed=[],
            additions=0,
            deletions=0,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        with patch.dict(os.environ, {
            'SYSTEM_PULLREQUEST_TARGETBRANCH': 'develop',
            'BUILD_REPOSITORY_LOCALPATH': '/repo/path'
        }):
            _ = get_pr_diff_from_env()

            mock_parser_class.assert_called_once_with(repo_path='/repo/path')
            mock_parser.get_pr_diff.assert_called_once_with(base_branch='origin/develop')

    @patch('scripts.utils.git_diff_parser.GitDiffParser')
    def test_get_pr_diff_from_env_with_origin_prefix(self, mock_parser_class):
        """Test when target branch already has origin/ prefix"""
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="diff",
            files_changed=[],
            additions=0,
            deletions=0,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        with patch.dict(os.environ, {
            'SYSTEM_PULLREQUEST_TARGETBRANCH': 'origin/feature-branch'
        }):
            _ = get_pr_diff_from_env()

            mock_parser.get_pr_diff.assert_called_once_with(base_branch='origin/feature-branch')
