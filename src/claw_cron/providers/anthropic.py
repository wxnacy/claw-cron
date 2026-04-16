# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Anthropic Claude provider implementation."""

from __future__ import annotations

import anthropic
from anthropic import APIError, AuthenticationError, RateLimitError

from .base import BaseProvider, ProviderResult
from .exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from .tools import ToolCall, ToolDefinition, to_anthropic_tool


class AnthropicProvider(BaseProvider):
    """Anthropic Claude provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key.
            model: Model name (e.g., "claude-3-5-haiku-20241022").
            base_url: Custom API endpoint (optional).
        """
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
        )

    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[ToolDefinition],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        """Send chat request with Anthropic tool support.

        Args:
            messages: Conversation history in format:
                [{"role": "user" | "assistant", "content": str}]
            system_prompt: System instructions for the model.
            tools: Available tools for the model to call.
            max_tokens: Maximum tokens in the response.

        Returns:
            ProviderResult containing text response or tool calls.

        Raises:
            ProviderAuthError: Authentication failure.
            ProviderRateLimitError: Rate limit exceeded.
            ProviderError: API error.
            ProviderResponseError: Unexpected response format.
        """
        try:
            # Convert tools to Anthropic format
            anthropic_tools = [to_anthropic_tool(t) for t in tools]

            # Build message params
            # Note: Anthropic uses separate 'system' param, not a message
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=anthropic_tools,
                messages=messages,  # type: ignore[arg-type]
            )

            # Parse response
            tool_calls: list[ToolCall] = []
            text_content = ""

            if response.stop_reason == "tool_use":
                # Extract tool calls
                for block in response.content:
                    if block.type == "tool_use":
                        tool_calls.append(ToolCall(
                            id=block.id,
                            name=block.name,
                            arguments=block.input,  # type: ignore[union-attr]
                        ))
            else:
                # Extract text content
                for block in response.content:
                    if block.type == "text":
                        text_content += block.text

            return ProviderResult(
                content=text_content,
                tool_calls=tool_calls,
                stop_reason=response.stop_reason or "end_turn",
                raw_response=response,
            )

        except AuthenticationError as e:
            raise ProviderAuthError(
                f"Anthropic authentication failed: {e.message}"
            ) from e
        except RateLimitError as e:
            raise ProviderRateLimitError(
                f"Anthropic rate limit exceeded: {e.message}"
            ) from e
        except APIError as e:
            raise ProviderError(
                f"Anthropic API error: {e.message}"
            ) from e
        except Exception as e:
            raise ProviderResponseError(
                f"Unexpected error from Anthropic: {e}"
            ) from e
