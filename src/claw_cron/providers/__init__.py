# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""AI Provider abstraction layer for claw-cron.

This module provides a unified interface for multiple AI providers (Anthropic, OpenAI, etc.)
with Tool Use support. The provider pattern allows switching between different AI backends
without modifying application code.

Provider Pattern:
    - BaseProvider: Abstract base class defining the interface
    - AnthropicProvider: Claude implementation (Plan 02)
    - OpenAIProvider: GPT implementation (Plan 02)
    - ToolDefinition: Provider-agnostic tool schema
    - ToolConverter: Transforms tools to provider-specific formats

Usage:
    from claw_cron.providers import get_provider, ToolDefinition

    provider = get_provider("claude", api_key="...", model="claude-3-5-haiku-20241022")
    result = provider.chat_with_tools(messages, system_prompt, tools)
"""

from typing import Literal

from .base import BaseProvider, ProviderResult
from .exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from .tools import ToolCall, ToolDefinition, to_anthropic_tool, to_codebuddy_tool, to_openai_tool
from .anthropic import AnthropicProvider
from .codebuddy import CodebuddyProvider
from .openai import OpenAIProvider

__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderResult",
    # Tool abstraction
    "ToolDefinition",
    "ToolCall",
    "to_anthropic_tool",
    "to_openai_tool",
    "to_codebuddy_tool",
    # Exceptions
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderModelNotFoundError",
    "ProviderResponseError",
    # Providers
    "AnthropicProvider",
    "CodebuddyProvider",
    "OpenAIProvider",
    # Factory
    "get_provider",
    "ProviderType",
]

ProviderType = Literal["claude", "openai", "codebuddy"]


def get_provider(
    provider: ProviderType,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseProvider:
    """Factory function to create provider instances.

    Args:
        provider: Provider name ('claude' or 'openai')
        api_key: API key for the provider
        model: Model name to use
        base_url: Optional custom API endpoint

    Returns:
        Provider instance implementing BaseProvider

    Raises:
        ValueError: If provider name is not recognized
    """
    providers = {
        "claude": AnthropicProvider,
        "openai": OpenAIProvider,
        "codebuddy": CodebuddyProvider,
    }

    if provider not in providers:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            f"Supported: {list(providers.keys())}"
        )

    return providers[provider](
        api_key=api_key,
        model=model,
        base_url=base_url,
    )
