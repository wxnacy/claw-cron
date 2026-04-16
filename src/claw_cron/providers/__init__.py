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

Usage (after Plan 02):
    from claw_cron.providers import get_provider, ToolDefinition

    provider = get_provider("claude", api_key="...", model="claude-3-5-haiku-20241022")
    result = provider.chat_with_tools(messages, system_prompt, tools)
"""

from .base import BaseProvider, ProviderResult
from .exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderModelNotFoundError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from .tools import ToolCall, ToolDefinition, to_anthropic_tool, to_openai_tool

__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderResult",
    # Tool abstraction
    "ToolDefinition",
    "ToolCall",
    "to_anthropic_tool",
    "to_openai_tool",
    # Exceptions
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderModelNotFoundError",
    "ProviderResponseError",
]
