# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""OpenAI GPT provider implementation."""

from __future__ import annotations

import json
from openai import APIError, AuthenticationError, OpenAI, RateLimitError

from .base import BaseProvider, ProviderResult
from .exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from .tools import ToolCall, ToolDefinition, to_openai_tool


class OpenAIProvider(BaseProvider):
    """OpenAI GPT provider implementation."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            model: Model name (e.g., "gpt-4o-mini", "gpt-4o").
            base_url: Custom API endpoint (optional, for proxies or local models).
        """
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._client = OpenAI(
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
        """Send chat request with OpenAI function calling support.

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
            ProviderResponseError: Unexpected response format or JSON parse error.
        """
        try:
            # Convert tools to OpenAI format
            openai_tools = [to_openai_tool(t) for t in tools]

            # Prepend system message to conversation
            full_messages = [
                {"role": "system", "content": system_prompt},
                *messages,
            ]

            response = self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=full_messages,  # type: ignore[arg-type]
                tools=openai_tools if openai_tools else None,
            )

            choice = response.choices[0]

            # Parse response
            tool_calls: list[ToolCall] = []
            text_content = ""

            if choice.finish_reason == "tool_calls":
                # Extract tool calls
                if choice.message.tool_calls:
                    for tc in choice.message.tool_calls:
                        # OpenAI returns arguments as JSON string
                        args = json.loads(tc.function.arguments)
                        tool_calls.append(ToolCall(
                            id=tc.id,
                            name=tc.function.name,
                            arguments=args,
                        ))
            else:
                # Extract text content
                text_content = choice.message.content or ""

            return ProviderResult(
                content=text_content,
                tool_calls=tool_calls,
                stop_reason=choice.finish_reason or "stop",
                raw_response=response,
            )

        except AuthenticationError as e:
            raise ProviderAuthError(
                f"OpenAI authentication failed: {str(e)}"
            ) from e
        except RateLimitError as e:
            raise ProviderRateLimitError(
                f"OpenAI rate limit exceeded: {str(e)}"
            ) from e
        except APIError as e:
            raise ProviderError(
                f"OpenAI API error: {str(e)}"
            ) from e
        except json.JSONDecodeError as e:
            raise ProviderResponseError(
                f"Failed to parse OpenAI tool arguments: {e}"
            ) from e
        except Exception as e:
            raise ProviderResponseError(
                f"Unexpected error from OpenAI: {e}"
            ) from e
