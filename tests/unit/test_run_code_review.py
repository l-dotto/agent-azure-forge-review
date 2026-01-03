#!/usr/bin/env python3
"""
Unit tests for Code Review Runner
"""

from unittest.mock import Mock, patch, mock_open

from scripts.agents.run_code_review import CodeReviewRunner
from scripts.utils.git_diff_parser import DiffResult
from scripts.utils.markdown_parser import Finding
from scripts.utils.llm_client import LLMResponse


class TestCodeReviewRunner:
    """Test CodeReviewRunner class"""

    @patch('scripts.agents.run_code_review.create_llm_client')
    def test_initialization_default(self, mock_create_client):
        """Test runner initialization with defaults"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "claude-opus-4-5-20251101"
        mock_create_client.return_value = mock_client

        runner = CodeReviewRunner()

        mock_create_client.assert_called_once()
        assert runner.provider == "anthropic"
        assert runner.model == "claude-opus-4-5-20251101"

    @patch('scripts.agents.run_code_review.create_llm_client')
    def test_initialization_custom_provider(self, mock_create_client):
        """Test initialization with custom provider"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "gpt-4-turbo-preview"
        mock_create_client.return_value = mock_client

        runner = CodeReviewRunner(
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

    @patch('scripts.agents.run_code_review.create_llm_client')
    def test_load_agent_prompt(self, mock_create_client):
        """Test loading agent prompt template"""
        mock_client = Mock()
        mock_client.get_default_model.return_value = "test-model"
        mock_create_client.return_value = mock_client

        runner = CodeReviewRunner()

        # Mock the file read
        prompt_content = """---
name: Forge
---
# Code Review Agent

Analyze the code for quality and maintainability.
"""

        with patch('builtins.open', mock_open(read_data=prompt_content)):
            prompt = runner._load_agent_prompt()

            assert "# Code Review Agent" in prompt
            assert "---" not in prompt  # Frontmatter should be removed

    @patch('scripts.agents.run_code_review.create_llm_client')
    @patch('scripts.agents.run_code_review.GitDiffParser')
    def test_run_with_no_changes(self, mock_parser_class, mock_create_client):
        """Test running when no changes detected"""
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

        runner = CodeReviewRunner()

        result = runner.run()

        assert len(result["findings"]) == 0
        assert result["metadata"]["files_changed"] == 0

    @patch('scripts.agents.run_code_review.create_llm_client')
    def test_default_models(self, mock_create_client):
        """Test default models for each provider"""
        assert CodeReviewRunner.DEFAULT_MODELS['anthropic'] == 'claude-opus-4-5-20251101'
        assert CodeReviewRunner.DEFAULT_MODELS['openai'] == 'gpt-4-turbo-preview'
        assert CodeReviewRunner.DEFAULT_MODELS['azure_openai'] == 'gpt-4'
        assert CodeReviewRunner.DEFAULT_MODELS['gemini'] == 'gemini-pro'

    @patch('scripts.agents.run_code_review.create_llm_client')
    def test_default_parameters(self, mock_create_client):
        """Test default max_tokens and temperature"""
        assert CodeReviewRunner.DEFAULT_MAX_TOKENS == 16000
        assert abs(CodeReviewRunner.DEFAULT_TEMPERATURE - 0.0) < 0.001
