#!/usr/bin/env python3
"""
Unit tests for Security Review Runner
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
import json

from scripts.agents.run_security_review import SecurityReviewRunner
from scripts.utils.git_diff_parser import DiffResult
from scripts.utils.markdown_parser import Finding
from scripts.utils.llm_client import LLMResponse


class TestSecurityReviewRunner:
    """Test SecurityReviewRunner class"""

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_initialization_default(self, mock_create_client):
        """Test runner initialization with defaults"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "claude-sonnet-4-5-20250929"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        mock_create_client.assert_called_once()
        assert runner.provider == "anthropic"
        assert runner.model == "claude-sonnet-4-5-20250929"

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_initialization_custom_provider(self, mock_create_client):
        """Test initialization with custom provider"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "gpt-4-turbo-preview"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner(
            provider="openai",
            api_key="test-key",
            model="gpt-4-turbo-preview"
        )

        mock_create_client.assert_called_once_with(
            provider="openai",
            api_key="test-key",
            model="gpt-4-turbo-preview"
        )
        assert runner.provider == "openai"

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_load_agent_prompt(self, mock_create_client):
        """Test loading agent prompt template"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        # Mock the file read
        prompt_content = """---
name: Sentinel
---
# Security Review Agent

Analyze the code for vulnerabilities.
"""

        with patch('builtins.open', mock_open(read_data=prompt_content)):
            prompt = runner._load_agent_prompt()

            assert "# Security Review Agent" in prompt
            assert "---" not in prompt  # Frontmatter should be removed

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.subprocess.run')
    def test_execute_git_command(self, mock_run, mock_create_client):
        """Test executing git commands"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        # Mock successful git command
        mock_run.return_value = Mock(stdout="main", returncode=0)

        result = runner._execute_git_command("git branch --show-current")

        assert result == "main"
        mock_run.assert_called_once()

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.subprocess.run')
    def test_execute_git_command_failure(self, mock_run, mock_create_client):
        """Test handling failed git command"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        # Mock failed git command
        import subprocess
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        result = runner._execute_git_command("git invalid-command")

        assert "command failed" in result

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_substitute_placeholders(self, mock_create_client):
        """Test substituting placeholders in prompt"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        # Mock diff result
        diff_result = DiffResult(
            content="diff content here",
            files_changed=["app.py"],
            additions=5,
            deletions=2,
            sanitized=True
        )

        prompt = """Current branch: !`git branch --show-current`

Diff:
```
git diff --merge-base origin/HEAD
```
"""

        with patch.object(runner, '_execute_git_command', return_value='feature-branch'):
            result = runner._substitute_placeholders(prompt, diff_result)

            assert 'feature-branch' in result
            assert 'diff content here' in result
            assert '!`git' not in result

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_call_llm(self, mock_create_client):
        """Test calling LLM API"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_client.generate.return_value = LLMResponse(
            content="# Vuln 1: XSS: `app.py:42`\n\n* Severity: High\n* Description: XSS\n* Exploit Scenario: Attack\n* Recommendation: Fix",
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 50},
            provider="anthropic"
        )
        mock_create_client.return_value = mock_client

        runner = SecurityReviewRunner()

        response = runner._call_llm("Test prompt")

        assert "Vuln 1" in response
        mock_client.generate.assert_called_once()

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.GitDiffParser')
    @patch('scripts.agents.run_security_review.parse_agent_output')
    def test_run_with_findings(self, mock_parse, mock_parser_class, mock_create_client):
        """Test running security review with findings"""
        # Mock LLM client
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_client.generate.return_value = LLMResponse(
            content="# Vuln 1: XSS: `app.py:42`\n\n* Severity: High\n* Description: XSS\n* Exploit Scenario: Attack\n* Recommendation: Fix",
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 50},
            provider="anthropic"
        )
        mock_create_client.return_value = mock_client

        # Mock git diff parser
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="diff content",
            files_changed=["app.py"],
            additions=10,
            deletions=5,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        # Mock findings parser
        mock_finding = Finding(
            agent="sentinel",
            severity="high",
            category="xss",
            title="XSS: app.py:42",
            file_path="app.py",
            line_number=42,
            description="XSS vulnerability",
            recommendation="Fix it"
        )
        mock_parse.return_value = [mock_finding]

        runner = SecurityReviewRunner()

        # Mock _load_agent_prompt and _substitute_placeholders
        with patch.object(runner, '_load_agent_prompt', return_value="prompt template"):
            with patch.object(runner, '_substitute_placeholders', return_value="full prompt"):
                result = runner.run()

        assert "findings" in result
        assert "metadata" in result
        assert len(result["findings"]) == 1
        assert result["metadata"]["agent"] == "sentinel"
        assert result["metadata"]["total_findings"] == 1
        assert result["metadata"]["findings_by_severity"]["high"] == 1

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.GitDiffParser')
    def test_run_with_no_changes(self, mock_parser_class, mock_create_client):
        """Test running security review with no changes"""
        # Mock LLM client
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        # Mock git diff parser with empty diff
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="",
            files_changed=[],
            additions=0,
            deletions=0,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        runner = SecurityReviewRunner()

        result = runner.run()

        assert len(result["findings"]) == 0
        assert result["metadata"]["files_changed"] == 0

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.GitDiffParser')
    @patch('scripts.agents.run_security_review.parse_agent_output')
    def test_run_with_critical_findings(self, mock_parse, mock_parser_class, mock_create_client):
        """Test running with critical severity findings"""
        # Mock LLM client
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_client.generate.return_value = LLMResponse(
            content="vulnerability output",
            model="test-model",
            usage={"input_tokens": 100, "output_tokens": 50},
            provider="anthropic"
        )
        mock_create_client.return_value = mock_client

        # Mock git diff parser
        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="diff content",
            files_changed=["app.py"],
            additions=10,
            deletions=5,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        # Mock critical finding
        mock_finding = Finding(
            agent="sentinel",
            severity="critical",
            category="sql_injection",
            title="SQL Injection",
            file_path="app.py",
            line_number=10,
            description="SQL injection vulnerability",
            recommendation="Use parameterized queries"
        )
        mock_parse.return_value = [mock_finding]

        runner = SecurityReviewRunner()

        with patch.object(runner, '_load_agent_prompt', return_value="prompt"):
            with patch.object(runner, '_substitute_placeholders', return_value="full prompt"):
                result = runner.run()

        assert result["metadata"]["findings_by_severity"]["critical"] == 1

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_default_models(self, mock_create_client):
        """Test default models for each provider"""
        assert SecurityReviewRunner.DEFAULT_MODELS['anthropic'] == 'claude-sonnet-4-5-20250929'
        assert SecurityReviewRunner.DEFAULT_MODELS['openai'] == 'gpt-4-turbo-preview'
        assert SecurityReviewRunner.DEFAULT_MODELS['azure_openai'] == 'gpt-4'
        assert SecurityReviewRunner.DEFAULT_MODELS['gemini'] == 'gemini-pro'

    @patch('scripts.agents.run_security_review.create_llm_client')
    def test_default_parameters(self, mock_create_client):
        """Test default max_tokens and temperature"""
        assert SecurityReviewRunner.DEFAULT_MAX_TOKENS == 16000
        assert SecurityReviewRunner.DEFAULT_TEMPERATURE == 0.0


class TestSecurityReviewRunnerIntegration:
    """Integration-style tests for SecurityReviewRunner"""

    @patch('scripts.agents.run_security_review.create_llm_client')
    @patch('scripts.agents.run_security_review.GitDiffParser')
    @patch('scripts.agents.run_security_review.parse_agent_output')
    @patch('builtins.open', new_callable=mock_open, read_data="# Security Review\n\nAnalyze code")
    def test_full_run_workflow(self, mock_file, mock_parse, mock_parser_class, mock_create_client):
        """Test complete workflow from diff to findings"""
        # Setup mocks
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_client.generate.return_value = LLMResponse(
            content="security findings",
            model="test-model",
            usage={"input_tokens": 500, "output_tokens": 300},
            provider="anthropic"
        )
        mock_create_client.return_value = mock_client

        mock_parser = Mock()
        mock_parser.get_pr_diff.return_value = DiffResult(
            content="+ new code\n- old code",
            files_changed=["app.py", "test.py"],
            additions=15,
            deletions=8,
            sanitized=True
        )
        mock_parser_class.return_value = mock_parser

        findings = [
            Finding(
                agent="sentinel",
                severity="high",
                category="xss",
                title="XSS",
                file_path="app.py",
                line_number=10,
                description="XSS vuln",
                recommendation="Escape"
            ),
            Finding(
                agent="sentinel",
                severity="medium",
                category="csrf",
                title="CSRF",
                file_path="test.py",
                line_number=20,
                description="CSRF vuln",
                recommendation="Add token"
            )
        ]
        mock_parse.return_value = findings

        runner = SecurityReviewRunner(provider="anthropic")

        with patch.object(runner, '_execute_git_command', return_value='main'):
            result = runner.run()

        # Verify complete result structure
        assert "findings" in result
        assert "metadata" in result
        assert "raw_output" in result

        assert len(result["findings"]) == 2
        assert result["metadata"]["agent"] == "sentinel"
        assert result["metadata"]["files_changed"] == 2
        assert result["metadata"]["total_findings"] == 2
        assert result["metadata"]["findings_by_severity"]["high"] == 1
        assert result["metadata"]["findings_by_severity"]["medium"] == 1
