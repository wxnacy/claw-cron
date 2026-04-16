# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Abstract base class for AI providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .tools import ToolCall, ToolDefinition


@dataclass
class ProviderResult:
    """Result from a provider chat call.

    This dataclass standardizes the response format across different
    AI providers, abstracting away provider-specific response structures.

    Attributes:
        content: Text content from the assistant (empty if tool_use).
        tool_calls: List of tool calls requested by the model (empty if text response).
        stop_reason: Why the model stopped generating. One of:
            - "end_turn": Normal completion, no tool use
            - "tool_use": Model requested tool execution
            - "max_tokens": Token limit reached
        raw_response: Provider-specific raw response object (for debugging).
    """

    content: str
    tool_calls: list[ToolCall]
    stop_reason: str  # "end_turn" | "tool_use" | "max_tokens"
    raw_response: Any  # Provider-specific raw response (for debugging)


class BaseProvider(ABC):
    """Abstract base class for AI providers.

    This class defines the interface that all AI providers must implement.
    It provides a unified API for chat interactions with tool support,
    allowing the application to switch between providers without code changes.

    Subclasses must implement:
        - chat_with_tools(): Core chat method with tool support

    Attributes:
        api_key: API key for authentication.
        model: Model identifier (provider-specific).
        base_url: Custom API endpoint (optional, for proxies or local models).
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            api_key: API key for authentication.
            model: Model identifier (e.g., "claude-3-5-haiku-20241022", "gpt-4o-mini").
            base_url: Custom API endpoint (optional, for proxies or local models).
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[ToolDefinition],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        """Send a chat request with tool support.

        This method sends a conversation to the AI model with available tools
        and returns the model's response. If the model decides to use a tool,
        the tool calls will be included in the result.

        Args:
            messages: Conversation history in format:
                [{"role": "user" | "assistant", "content": str}]
            system_prompt: System instructions for the model.
            tools: Available tools for the model to call.
            max_tokens: Maximum tokens in the response.

        Returns:
            ProviderResult containing:
                - content: Text response (empty if tool_use)
                - tool_calls: Tool call requests (empty if text response)
                - stop_reason: Why generation stopped
                - raw_response: Provider-specific response object

        Example:
            >>> provider = AnthropicProvider(api_key="...", model="claude-3-5-haiku")
            >>> result = provider.chat_with_tools(
            ...     messages=[{"role": "user", "content": "Create a task"}],
            ...     system_prompt="You are a helpful assistant.",
            ...     tools=[ToolDefinition(name="create_task", ...)]
            ... )
            >>> if result.stop_reason == "tool_use":
            ...     for call in result.tool_calls:
            ...         print(f"Tool: {call.name}, Args: {call.arguments}")
        """
        ...

    def get_provider_name(self) -> str:
        """Return provider name for logging/debugging.

        Extracts the provider name from the class name by removing
        the "Provider" suffix and converting to lowercase.

        Returns:
            Provider name (e.g., "anthropic", "openai").
        """
        return self.__class__.__name__.replace("Provider", "").lower()
