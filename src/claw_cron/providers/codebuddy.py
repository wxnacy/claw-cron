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

    @staticmethod
    def _execute_tool(tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a claw-cron tool call and return the result.

        This is used by the MCP server handlers so that tool results
        are sent back to the model inside the SDK, preventing the
        infinite tool-call loop caused by placeholder responses.

        Args:
            tool_name: Name of the claw-cron tool to execute.
            tool_input: Arguments passed by the model.

        Returns:
            Dictionary with a "result" key containing the execution outcome.
        """
        from claw_cron.executor import execute_task
        from claw_cron.storage import Task, add_task, delete_task, get_task, load_tasks, update_task

        try:
            if tool_name == "list_tasks":
                tasks = load_tasks()
                if not tasks:
                    return {"result": "No tasks found."}
                lines = [
                    f"- {t.name} ({t.cron}, {t.type}, {'enabled' if t.enabled else 'disabled'})"
                    for t in tasks
                ]
                return {"result": "\n".join(lines)}

            if tool_name == "add_task":
                name = tool_input["name"]
                cron = tool_input["cron"]
                task_type = tool_input["type"]
                script = tool_input.get("script")
                prompt = tool_input.get("prompt")
                client = tool_input.get("client")

                if task_type == "command" and not script:
                    return {"result": "Error: script is required for command type tasks"}
                if task_type == "agent" and not prompt:
                    return {"result": "Error: prompt is required for agent type tasks"}

                task = Task(
                    name=name,
                    cron=cron,
                    type=task_type,
                    script=script,
                    prompt=prompt,
                    client=client,
                )
                add_task(task)
                return {"result": f"Task '{name}' added successfully."}

            if tool_name == "delete_task":
                name = tool_input["name"]
                if delete_task(name):
                    return {"result": f"Task '{name}' deleted."}
                return {"result": f"Task '{name}' not found."}

            if tool_name == "run_task":
                name = tool_input["name"]
                task = get_task(name)
                if task is None:
                    return {"result": f"Task '{name}' not found."}
                exit_code, _output, _feedback = execute_task(task)
                return {"result": f"Task '{name}' executed (exit_code={exit_code})."}

            if tool_name == "enable_task":
                name = tool_input["name"]
                if update_task(name, enabled=True):
                    return {"result": f"Task '{name}' enabled."}
                return {"result": f"Task '{name}' not found."}

            if tool_name == "disable_task":
                name = tool_input["name"]
                if update_task(name, enabled=False):
                    return {"result": f"Task '{name}' disabled."}
                return {"result": f"Task '{name}' not found."}

            return {"result": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"result": f"Failed to execute {tool_name}: {e}"}

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

                # Use a factory to avoid the late-binding closure trap
                def _make_handler(name: str) -> Any:
                    async def _handler(args: dict[str, Any]) -> dict[str, Any]:
                        return self._execute_tool(name, args)
                    return _handler

                handler = _make_handler(t.name)
                decorated = tool(
                    cb_tool["name"],
                    cb_tool["description"],
                    cb_tool["parameters"],
                )(handler)
                tool_handlers.append(decorated)

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
            from codebuddy_agent_sdk import query, CodeBuddyAgentOptions
            from codebuddy_agent_sdk.types import (
                AssistantMessage,
                PermissionResultAllow,
                PermissionResultDeny,
                TextBlock,
            )

            async def _allow_claw_cron_tools(
                tool_name: str,
                _input_data: dict[str, Any],
                _options: Any,
            ) -> Any:
                """Allow only claw-cron MCP tools, deny built-in tools."""
                if tool_name.startswith("mcp__claw_cron_tools__"):
                    return PermissionResultAllow()
                return PermissionResultDeny(
                    message=f"Tool {tool_name} is not allowed"
                )

            options = CodeBuddyAgentOptions(
                model=model,
                mcp_servers={
                    "claw-cron-tools": mcp_server,
                },
                system_prompt=system_prompt,
                can_use_tool=_allow_claw_cron_tools,
            )

            result = query(
                prompt=prompt,
                options=options,
            )

            text_content = ""

            async def _consume() -> str:
                content = ""
                async for message in result:
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                content += block.text
                return content

            try:
                text_content = await asyncio.wait_for(_consume(), timeout=45.0)
            except asyncio.TimeoutError:
                text_content = "Request timed out. Please try again."

            if not text_content.strip():
                text_content = "Done."

            return ProviderResult(
                content=text_content,
                tool_calls=[],
                stop_reason="end_turn",
                raw_response=None,
            )

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(_async_query())
