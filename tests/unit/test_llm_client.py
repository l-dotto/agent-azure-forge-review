#!/usr/bin/env python3
"""
Unit tests for LLM Client abstraction layer
"""

import pytest
from unittest.mock import Mock, patch
import os

from scripts.utils.llm_client import (
    LLMProvider,
    LLMResponse,
    AnthropicClient,
    create_llm_client,
    get_provider_from_env
)


class TestLLMProvider:
    """Test LLMProvider enum"""

    def test_provider_values(self):
        """Test provider enum values"""
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
        assert LLMProvider.GEMINI.value == "gemini"


class TestLLMResponse:
    """Test LLMResponse dataclass"""

    def test_response_creation(self):
        """Test creating LLM response"""
        response = LLMResponse(
            content="Hello world",
            model="test-model",
            usage={"input_tokens": 10, "output_tokens": 20},
            provider="test"
        )

        assert response.content == "Hello world"
        assert response.model == "test-model"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20
        assert response.provider == "test"


class TestAnthropicClient:
    """Test AnthropicClient"""

    def test_initialization(self):
        """Test client initialization"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            client = AnthropicClient(api_key="test-key")
            mock_anthropic.assert_called_once_with(api_key="test-key")
            assert client.api_key == "test-key"

    def test_initialization_from_env(self):
        """Test initialization from environment variable"""
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'env-key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                _ = AnthropicClient()
                mock_anthropic.assert_called_once_with(api_key='env-key')

    def test_generate(self):
        """Test generate method"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            # Mock response
            mock_response = Mock()
            mock_response.content = [Mock(text="Generated response")]
            mock_response.usage = Mock(input_tokens=100, output_tokens=50)

            mock_client = Mock()
            mock_client.messages.create.return_value = mock_response
            mock_anthropic.return_value = mock_client

            client = AnthropicClient(api_key="test-key")
            response = client.generate(
                prompt="Test prompt",
                system_prompt="System instructions",
                max_tokens=1000,
                temperature=0.5
            )

            assert response.content == "Generated response"
            assert response.model == "claude-sonnet-4-5-20250929"
            assert response.usage["input_tokens"] == 100
            assert response.usage["output_tokens"] == 50
            assert response.provider == "anthropic"

    def test_get_default_model(self):
        """Test getting default model"""
        with patch('anthropic.Anthropic'):
            client = AnthropicClient(api_key="test-key")
            assert client.get_default_model() == "claude-sonnet-4-5-20250929"


class TestOpenAIClient:
    """Test OpenAIClient"""

    @pytest.mark.skip(reason="OpenAI package not installed (optional dependency)")
    def test_initialization(self):
        """Test client initialization"""
        pass

    @pytest.mark.skip(reason="OpenAI package not installed (optional dependency)")
    def test_generate(self):
        """Test generate method"""
        pass

    @pytest.mark.skip(reason="OpenAI package not installed (optional dependency)")
    def test_get_default_model(self):
        """Test getting default model"""
        pass


class TestAzureOpenAIClient:
    """Test AzureOpenAIClient"""

    @pytest.mark.skip(reason="OpenAI package not installed (optional dependency)")
    def test_initialization(self):
        """Test client initialization"""
        pass

    @pytest.mark.skip(reason="OpenAI package not installed (optional dependency)")
    def test_generate(self):
        """Test generate method"""
        pass


class TestGeminiClient:
    """Test GeminiClient"""

    @pytest.mark.skip(reason="Google Generative AI package not installed (optional dependency)")
    def test_initialization(self):
        """Test client initialization"""
        pass

    @pytest.mark.skip(reason="Google Generative AI package not installed (optional dependency)")
    def test_get_default_model(self):
        """Test getting default model"""
        pass


class TestCreateLLMClient:
    """Test factory function"""

    @patch('scripts.utils.llm_client.AnthropicClient')
    def test_create_anthropic_client(self, mock_client):
        """Test creating Anthropic client"""
        create_llm_client('anthropic', api_key='test-key')
        mock_client.assert_called_once()

    @patch('scripts.utils.llm_client.OpenAIClient')
    def test_create_openai_client(self, mock_client):
        """Test creating OpenAI client"""
        create_llm_client('openai', api_key='test-key')
        mock_client.assert_called_once()

    @patch('scripts.utils.llm_client.AzureOpenAIClient')
    def test_create_azure_client(self, mock_client):
        """Test creating Azure OpenAI client"""
        create_llm_client('azure_openai', api_key='test-key')
        mock_client.assert_called_once()

    @patch('scripts.utils.llm_client.GeminiClient')
    def test_create_gemini_client(self, mock_client):
        """Test creating Gemini client"""
        create_llm_client('gemini', api_key='test-key')
        mock_client.assert_called_once()

    def test_unsupported_provider(self):
        """Test error on unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            create_llm_client('unknown')


class TestGetProviderFromEnv:
    """Test provider detection from environment"""

    def test_explicit_provider_env(self):
        """Test explicit LLM_PROVIDER env var"""
        with patch.dict(os.environ, {'LLM_PROVIDER': 'openai'}):
            assert get_provider_from_env() == 'openai'

    def test_openai_key_detection(self):
        """Test detection from OPENAI_API_KEY"""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'key'}, clear=True):
            assert get_provider_from_env() == 'openai'

    def test_azure_key_detection(self):
        """Test detection from AZURE_OPENAI_API_KEY"""
        with patch.dict(os.environ, {'AZURE_OPENAI_API_KEY': 'key'}, clear=True):
            assert get_provider_from_env() == 'azure_openai'

    def test_google_key_detection(self):
        """Test detection from GOOGLE_API_KEY"""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'key'}, clear=True):
            assert get_provider_from_env() == 'gemini'

    def test_default_to_anthropic(self):
        """Test default to Anthropic when no env vars set"""
        with patch.dict(os.environ, {}, clear=True):
            assert get_provider_from_env() == 'anthropic'
