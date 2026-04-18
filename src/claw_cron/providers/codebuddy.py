# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Codebuddy SDK provider implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console

from .base import BaseProvider, ProviderResult
from .exceptions import ProviderAuthError, ProviderError, ProviderResponseError
from .tools import ToolCall, ToolDefinition, to_codebuddy_tool

console = Console()


class CodebuddyProvider(BaseProvider):
    """Codebuddy SDK provider implementation.

    Uses codebuddy-agent-sdk for AI interactions with MCP tool support.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize Codebuddy provider.

        Args:
            api_key: Codebuddy API key (from CODEBUDDY_API_KEY env var).
            model: Model name (e.g., "minimax-m2.5").
            base_url: Custom API endpoint (optional, not typically used).
        """
        super().__init__(api_key=api_key, model=model, base_url=base_url)

        # Check API key availability early
        if not api_key:
            self._show_api_key_missing_message()
            raise ProviderAuthError(
                "CODEBUDDY_API_KEY not set. "
                "Please set the environment variable and try again."
            )

    @staticmethod
    def _show_api_key_missing_message() -> None:
        """Display friendly message when API key is missing."""
        console.print("\n[bold red]Error: CODEBUDDY_API_KEY not found[/bold red]\n")
        console.print("To use Codebuddy provider, please set your API key:\n")
        console.print("  [cyan]export CODEBUDDY_API_KEY=your-api-key[/cyan]\n")
        console.print("Or add it to your shell profile (~/.zshrc or ~/.bashrc):\n")
        console.print("  [dim]export CODEBUDDY_API_KEY=your-api-key[/dim]\n")
        console.print("Get your API key from: [link]https://codebuddy.cn[/link]\n")

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[ToolDefinition],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        """Send chat request via Codebuddy SDK.

        Args:
            messages: Conversation history (only last message used in this impl).
            system_prompt: System instructions for the model.
            tools: Available tools for the model to call.
            max_tokens: Maximum tokens in the response.

        Returns:
            ProviderResult containing text response or tool calls.

        Raises:
            ProviderAuthError: Authentication failure.
            ProviderError: API error.
            ProviderResponseError: Unexpected response format.
        """
        try:
            # Import here to allow module to load without SDK installed
            from codebuddy_agent_sdk import create_sdk_mcp_server, query, tool

            # Convert tools to Codebuddy format and create handlers
            tool_handlers = []
            for t in tools:
                cb_tool = to_codebuddy_tool(t)

                # Create async handler for each tool
                @tool(
                    cb_tool["name"],
                    cb_tool["description"],
                    cb_tool["parameters"],
                )
                async def _handler(args: dict[str, Any]) -> dict[str, Any]:
                    # Placeholder - actual tool execution happens elsewhere
                    return {"status": "tool_call_requested", "args": args}

                tool_handlers.append(_handler)

            # Create MCP server with tools
            mcp_server = create_sdk_mcp_server(
                name="claw-cron-tools",
                tools=tool_handlers,
            )

            # Get last user message as prompt
            user_message = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, str):
                        user_message = content
                    break

            if not user_message:
                user_message = messages[-1].get("content", "") if messages else ""

            # Run async query in sync context
            result = self._run_query(
                prompt=user_message,
                system_prompt=system_prompt,
                mcp_server=mcp_server,
                model=self.model,
                max_tokens=max_tokens,
            )

            return result

        except ImportError as e:
            raise ProviderError(
                f"Codebuddy SDK not installed: {e}. "
                "Install with: pip install codebuddy-agent-sdk"
            ) from e
        except Exception as e:
            raise ProviderResponseError(
                f"Unexpected error from Codebuddy: {e}"
            ) from e

    def _run_query(
        self,
        prompt: str,
        system_prompt: str,
        mcp_server: Any,
        model: str,
        max_tokens: int,
    ) -> ProviderResult:
        """Execute async query and parse result."""

        async def _async_query() -> ProviderResult:
            from codebuddy_agent_sdk import query

            result = query(
                prompt=f"{system_prompt}\n\nUser: {prompt}",
                options={
                    "model": model,
                    "max_tokens": max_tokens,
                    "mcp_servers": {
                        "claw-cron-tools": mcp_server,
                    },
                },
            )

            text_content = ""
            tool_calls: list[ToolCall] = []
            stop_reason = "end_turn"

            async for message in result:
                # Parse message types from SDK
                msg_type = message.get("type", "")

                if msg_type == "text":
                    text_content += message.get("content", "")
                elif msg_type == "tool_use":
                    tool_calls.append(
                        ToolCall(
                            id=message.get("id", ""),
                            name=message.get("name", ""),
                            arguments=message.get("input", {}),
                        )
                    )
                    stop_reason = "tool_use"
                elif msg_type == "stop":
                    stop_reason = message.get("reason", "end_turn")

            return ProviderResult(
                content=text_content,
                tool_calls=tool_calls,
                stop_reason=stop_reason,
                raw_response=None,
            )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(_async_query())
