# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""chat command — natural language task management via Anthropic tool_use."""

from __future__ import annotations

import anthropic
import click
from rich.console import Console

from claw_cron.cmd.add import _add_direct
from claw_cron.executor import execute_task
from claw_cron.prompt import prompt_text
from claw_cron.storage import delete_task, get_task, load_tasks, update_task

console = Console()

_MODEL = "claude-3-5-haiku-20241022"

_SYSTEM_PROMPT = """\
You are a cron task management assistant. Help the user manage their scheduled tasks.
Supported operations: list tasks, add a task, delete a task, run a task immediately,
enable or disable a task. Call the appropriate tool based on the user's intent.
Be concise in your responses.\
"""

_TOOLS: list[anthropic.types.ToolParam] = [
    {
        "name": "list_tasks",
        "description": "List all scheduled tasks",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_task",
        "description": "Add a new scheduled task",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Unique task name (snake_case)"},
                "cron": {"type": "string", "description": "5-field cron expression"},
                "type": {"type": "string", "enum": ["command", "agent"]},
                "script": {"type": "string", "description": "Shell command (command type)"},
                "prompt": {"type": "string", "description": "AI prompt (agent type)"},
                "client": {"type": "string", "enum": ["kiro-cli", "codebuddy", "opencode"]},
            },
            "required": ["name", "cron", "type"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task by name",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Task name to delete"}},
            "required": ["name"],
        },
    },
    {
        "name": "run_task",
        "description": "Execute a task immediately",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Task name to run"}},
            "required": ["name"],
        },
    },
    {
        "name": "enable_task",
        "description": "Enable a disabled task",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Task name to enable"}},
            "required": ["name"],
        },
    },
    {
        "name": "disable_task",
        "description": "Disable a task without deleting it",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Task name to disable"}},
            "required": ["name"],
        },
    },
]


def _handle_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return a result string."""
    if tool_name == "list_tasks":
        tasks = load_tasks()
        if not tasks:
            return "No tasks found."
        lines = [f"- {t.name} ({t.cron}, {t.type}, {'enabled' if t.enabled else 'disabled'})" for t in tasks]
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


def _chat_once(user_input: str, api_client: anthropic.Anthropic) -> None:
    """Process a single user message: call AI, execute tool, print response."""
    messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": user_input}]

    response = api_client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=_TOOLS,
        messages=messages,
    )

    if response.stop_reason == "tool_use":
        tool_block = next(b for b in response.content if b.type == "tool_use")
        tool_result = _handle_tool(tool_block.name, tool_block.input)  # type: ignore[arg-type]

        messages.append({"role": "assistant", "content": response.content})  # type: ignore[arg-type]
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_block.id, "content": tool_result}],
        })

        final = api_client.messages.create(
            model=_MODEL,
            max_tokens=512,
            system=_SYSTEM_PROMPT,
            tools=_TOOLS,
            messages=messages,
        )
        text_blocks = [b for b in final.content if b.type == "text"]
        if text_blocks:
            console.print(f"\n[bold]Assistant:[/bold] {text_blocks[0].text}")
    else:
        text_blocks = [b for b in response.content if b.type == "text"]
        if text_blocks:
            console.print(f"\n[bold]Assistant:[/bold] {text_blocks[0].text}")


@click.command()
def chat() -> None:
    """Start AI chat for natural language task management.

    Supports: list, add, delete, run, enable, disable tasks.
    Each message is processed independently (no conversation history).
    Type 'exit' or 'quit' to stop.
    """
    api_client = anthropic.Anthropic()

    console.print("[bold cyan]claw-cron chat[/bold cyan]")
    console.print("[dim]Manage tasks with natural language. Type 'exit' to quit.[/dim]\n")

    while True:
        try:
            user_input = prompt_text("You")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            console.print("[dim]Bye.[/dim]")
            break

        _chat_once(user_input, api_client)
        console.print()
