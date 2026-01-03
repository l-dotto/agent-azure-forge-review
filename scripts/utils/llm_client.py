#!/usr/bin/env python3
"""
LLM Client Abstraction Layer

Supports multiple LLM providers: Anthropic, OpenAI, Google Gemini, Azure OpenAI
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    GEMINI = "gemini"


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    usage: Dict[str, int]
    provider: str


class BaseLLMClient(ABC):
    """Base class for LLM clients"""

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.extra_params = kwargs

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model for this provider"""
        pass


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client"""

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            from anthropic import Anthropic  # type: ignore[import-not-found]
            self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 0.0,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Claude"""
        model = model or self.extra_params.get('model', self.DEFAULT_MODEL)

        messages = [{"role": "user", "content": prompt}]

        # Add system prompt if provided
        api_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
            **kwargs
        }

        if system_prompt:
            api_kwargs["system"] = system_prompt

        response = self.client.messages.create(**api_kwargs)

        return LLMResponse(
            content=response.content[0].text,
            model=model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            provider=LLMProvider.ANTHROPIC.value
        )

    def get_default_model(self) -> str:
        return self.DEFAULT_MODEL


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT client"""

    DEFAULT_MODEL = "gpt-4-turbo-preview"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            from openai import OpenAI  # type: ignore[import-not-found]
            self.client = OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 0.0,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using GPT"""
        model = model or self.extra_params.get('model', self.DEFAULT_MODEL)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            provider=LLMProvider.OPENAI.value
        )

    def get_default_model(self) -> str:
        return self.DEFAULT_MODEL


class AzureOpenAIClient(BaseLLMClient):
    """Azure OpenAI client"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, **kwargs)
        try:
            from openai import AzureOpenAI  # type: ignore[import-not-found]
            self.client = AzureOpenAI(
                api_key=api_key or os.getenv('AZURE_OPENAI_API_KEY'),
                api_version=kwargs.get('api_version', '2024-02-01'),
                azure_endpoint=endpoint or os.getenv('AZURE_OPENAI_ENDPOINT')
            )
            self.deployment_name = deployment_name or os.getenv('AZURE_OPENAI_DEPLOYMENT')
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Azure OpenAI"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.deployment_name,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            },
            provider=LLMProvider.AZURE_OPENAI.value
        )

    def get_default_model(self) -> str:
        return self.deployment_name


class GeminiClient(BaseLLMClient):
    """Google Gemini client"""

    DEFAULT_MODEL = "gemini-pro"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            import google.generativeai as genai  # type: ignore[import-not-found]
            genai.configure(api_key=api_key or os.getenv('GOOGLE_API_KEY'))
            self.genai = genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 0.0,
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini"""
        model_name = model or self.extra_params.get('model', self.DEFAULT_MODEL)

        # Combine system prompt and user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        gemini_model = self.genai.GenerativeModel(model_name)

        generation_config = {
            'temperature': temperature,
            'max_output_tokens': max_tokens,
        }

        response = gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config
        )

        return LLMResponse(
            content=response.text,
            model=model_name,
            usage={
                "input_tokens": 0,  # Gemini doesn't expose token counts
                "output_tokens": 0
            },
            provider=LLMProvider.GEMINI.value
        )

    def get_default_model(self) -> str:
        return self.DEFAULT_MODEL


def create_llm_client(
    provider: str = "anthropic",
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLLMClient:
    """
    Factory function to create LLM client

    Args:
        provider: LLM provider name (anthropic, openai, azure_openai, gemini)
        api_key: API key for the provider
        **kwargs: Additional provider-specific parameters

    Returns:
        BaseLLMClient instance

    Environment variables (fallback if api_key not provided):
        - ANTHROPIC_API_KEY
        - OPENAI_API_KEY
        - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT
        - GOOGLE_API_KEY

    Examples:
        # Anthropic Claude
        client = create_llm_client('anthropic', model='claude-sonnet-4-5-20250929')

        # OpenAI GPT
        client = create_llm_client('openai', model='gpt-4-turbo-preview')

        # Azure OpenAI
        client = create_llm_client(
            'azure_openai',
            endpoint='https://your-endpoint.openai.azure.com',
            deployment_name='gpt-4'
        )

        # Google Gemini
        client = create_llm_client('gemini', model='gemini-pro')
    """
    provider = provider.lower()

    if provider == LLMProvider.ANTHROPIC.value:
        return AnthropicClient(api_key=api_key, **kwargs)
    elif provider == LLMProvider.OPENAI.value:
        return OpenAIClient(api_key=api_key, **kwargs)
    elif provider == LLMProvider.AZURE_OPENAI.value:
        return AzureOpenAIClient(api_key=api_key, **kwargs)
    elif provider == LLMProvider.GEMINI.value:
        return GeminiClient(api_key=api_key, **kwargs)
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported: {', '.join([p.value for p in LLMProvider])}"
        )


def get_provider_from_env() -> str:
    """
    Detect LLM provider from environment variables

    Returns:
        Provider name (defaults to 'anthropic')
    """
    if os.getenv('LLM_PROVIDER'):
        return os.getenv('LLM_PROVIDER').lower()
    elif os.getenv('OPENAI_API_KEY'):
        return LLMProvider.OPENAI.value
    elif os.getenv('AZURE_OPENAI_API_KEY'):
        return LLMProvider.AZURE_OPENAI.value
    elif os.getenv('GOOGLE_API_KEY'):
        return LLMProvider.GEMINI.value
    else:
        # Default to Anthropic
        return LLMProvider.ANTHROPIC.value


if __name__ == "__main__":
    """CLI test interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Test LLM client')
    parser.add_argument(
        '--provider',
        choices=['anthropic', 'openai', 'azure_openai', 'gemini'],
        help='LLM provider (auto-detected from env if not specified)'
    )
    parser.add_argument(
        '--prompt',
        default='Hello, how are you?',
        help='Test prompt'
    )

    args = parser.parse_args()

    provider = args.provider or get_provider_from_env()
    print(f"Using provider: {provider}")

    try:
        client = create_llm_client(provider)
        print(f"Default model: {client.get_default_model()}")

        response = client.generate(args.prompt, max_tokens=100)
        print(f"\nResponse from {response.provider} ({response.model}):")
        print(response.content)
        print(f"\nTokens used: {response.usage}")
    except Exception as e:
        print(f"Error: {e}")
