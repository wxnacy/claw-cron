# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""chat command — natural language task management via AI providers."""

from __future__ import annotations

import os
from typing import Any

import click
from rich.console import Console

from claw_cron.cmd.add import _add_direct
from claw_cron.executor import execute_task
from claw_cron.prompt import prompt_text
from claw_cron.providers import ToolDefinition, get_provider
from claw_cron.storage import delete_task, get_task, load_tasks, update_task

console = Console()

_SYSTEM_PROMPT = """\
You are a cron task management assistant. Help the user manage their scheduled tasks.
Supported operations: list tasks, add a task, delete a task, run a task immediately,
enable or disable a task. Call the appropriate tool based on the user's intent.
Be concise in your responses.\
"""

# Default models for each provider
_MODEL_DEFAULTS = {
    "claude": "claude-3-5-haiku-20241022",
    "openai": "gpt-4o-mini",
    "codebuddy": "minimax-m2.5",
}

# API key environment variable mapping
_API_KEYS = {
    "claude": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "codebuddy": "CODEBUDDY_API_KEY",
}


def _get_tools() -> list[ToolDefinition]:
    """Get available tool definitions."""
    return [
        ToolDefinition(
            name="list_tasks",
            description="List all scheduled tasks",
            parameters={"type": "object", "properties": {}, "required": []},
        ),
        ToolDefinition(
            name="add_task",
            description="Add a new scheduled task",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Unique task name"},
                    "cron": {"type": "string", "description": "5-field cron expression"},
                    "type": {"type": "string", "enum": ["command", "agent"]},
                    "script": {"type": "string", "description": "Shell command"},
                    "prompt": {"type": "string", "description": "AI prompt"},
                    "client": {"type": "string", "enum": ["kiro-cli", "codebuddy", "opencode"]},
                },
                "required": ["name", "cron", "type"],
            },
        ),
        ToolDefinition(
            name="delete_task",
            description="Delete a task by name",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Task name"}},
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="run_task",
            description="Execute a task immediately",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Task name"}},
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="enable_task",
            description="Enable a disabled task",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Task name"}},
                "required": ["name"],
            },
        ),
        ToolDefinition(
            name="disable_task",
            description="Disable a task without deleting",
            parameters={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Task name"}},
                "required": ["name"],
            },
        ),
    ]


def _handle_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute a tool call and return a result string."""
    if tool_name == "list_tasks":
        tasks = load_tasks()
        if not tasks:
            return "No tasks found."
        lines = [
            f"- {t.name} ({t.cron}, {t.type}, {'enabled' if t.enabled else 'disabled'})"
            for t in tasks
        ]
        return "\n".join(lines)

    elif tool_name == "add_task":
        try:
            _add_direct(
                name=tool_input["name"],
                cron=tool_input["cron"],
                task_type=tool_input["type"],
                script=tool_input.get("script"),
                ai_prompt=tool_input.get("prompt"),
                client=tool_input.get("client"),
            )
            return f"Task '{tool_input['name']}' added successfully."
        except Exception as e:
            return f"Failed to add task: {e}"

    elif tool_name == "delete_task":
        name = tool_input["name"]
        if delete_task(name):
            return f"Task '{name}' deleted."
        return f"Task '{name}' not found."

    elif tool_name == "run_task":
        name = tool_input["name"]
        task = get_task(name)
        if task is None:
            return f"Task '{name}' not found."
        exit_code = execute_task(task)
        return f"Task '{name}' executed (exit_code={exit_code})."

    elif tool_name == "enable_task":
        name = tool_input["name"]
        if update_task(name, enabled=True):
            return f"Task '{name}' enabled."
        return f"Task '{name}' not found."

    elif tool_name == "disable_task":
        name = tool_input["name"]
        if update_task(name, enabled=False):
            return f"Task '{name}' disabled."
        return f"Task '{name}' not found."

    return f"Unknown tool: {tool_name}"


def _chat_with_provider(user_input: str, ai_provider: Any) -> None:
    """Process a single user message using the provider abstraction."""
    tools = _get_tools()
    messages = [{"role": "user", "content": user_input}]

    try:
        result = ai_provider.chat_with_tools(
            messages=messages,
            system_prompt=_SYSTEM_PROMPT,
            tools=tools,
        )

        if result.stop_reason == "tool_use" and result.tool_calls:
            for call in result.tool_calls:
                tool_result = _handle_tool(call.name, call.arguments)
                console.print(f"\n[bold]Assistant:[/bold] {tool_result}")
        else:
            console.print(f"\n[bold]Assistant:[/bold] {result.content}")

    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")


@click.command()
@click.option(
    "--agent",
    "-a",
    "provider",
    default="claude",
    type=click.Choice(["claude", "openai", "codebuddy"]),
    help="AI provider to use (default: claude)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name (provider-specific, e.g., minimax-m2.5 for codebuddy)",
)
def chat(provider: str, model: str | None) -> None:
    """Start AI chat for natural language task management.

    Supports: list, add, delete, run, enable, disable tasks.
    Each message is processed independently (no conversation history).
    Type 'exit' or 'quit' to stop.

    \b
    Examples:
        claw-cron chat
        claw-cron chat --agent codebuddy
        claw-cron chat -a openai -m gpt-4o-mini
    """
    # Determine model based on provider
    if model is None:
        model = _MODEL_DEFAULTS.get(provider, "claude-3-5-haiku-20241022")

    # Get API key based on provider
    api_key_env = _API_KEYS.get(provider, "")
    api_key = os.environ.get(api_key_env, "")

    # Handle missing API key
    if not api_key:
        console.print(
            f"[bold red]Error: API key not found for provider '{provider}'[/bold red]"
        )
        console.print(f"Set environment variable: {api_key_env}=your-key")
        return

    # Create provider instance
    try:
        ai_provider = get_provider(
            provider=provider,  # type: ignore[arg-type]
            api_key=api_key,
            model=model,
        )
    except Exception as e:
        console.print(f"[bold red]Failed to initialize provider: {e}[/bold red]")
        return

    console.print(
        f"[bold cyan]claw-cron chat[/bold cyan] (provider: {provider}, model: {model})"
    )
    console.print(
        "[dim]Manage tasks with natural language. Type 'exit' to quit.[/dim]\n"
    )

    while True:
        try:
            user_input = prompt_text("You")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            console.print("[dim]Bye.[/dim]")
            break

        _chat_with_provider(user_input, ai_provider)
        console.print()
