# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Anthropic Agent for interactive task creation (ADD-01, ADD-04)."""

from __future__ import annotations

import click
import anthropic
from rich.console import Console

from claw_cron.storage import Task, add_task

console = Console()

_MODEL = "claude-3-5-haiku-20241022"

_CREATE_TASK_TOOL: anthropic.types.ToolParam = {
    "name": "create_task",
    "description": "Create a scheduled task with the parsed configuration from the conversation",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique task name (snake_case)"},
            "cron": {"type": "string", "description": "Standard 5-field cron expression (min hour day month weekday)"},
            "type": {"type": "string", "enum": ["command", "agent"], "description": "Execution type"},
            "script": {"type": "string", "description": "Shell command to run (required for command type)"},
            "prompt": {"type": "string", "description": "AI prompt to send (required for agent type)"},
            "client": {
                "type": "string",
                "enum": ["kiro-cli", "codebuddy", "opencode"],
                "description": "AI client to use (agent type only)",
            },
        },
        "required": ["name", "cron", "type"],
    },
}

_SYSTEM_PROMPT = """\
You are a cron task configuration assistant. Help the user create a scheduled task.

Ask for:
1. What the task should do (derive type: command for shell scripts, agent for AI tasks)
2. When it should run (convert natural language to a 5-field cron expression)
3. The specific command or prompt

Once you have enough information, call the create_task tool with the complete configuration.
Be concise. Ask one question at a time if information is missing.\
"""


def run_ai_add(
    name: str | None = None,
    cron: str | None = None,
    task_type: str | None = None,
    script: str | None = None,
    ai_prompt: str | None = None,
    client: str | None = None,
) -> None:
    """Run AI-guided task creation via Anthropic conversation.

    Args:
        name: Pre-filled task name (optional).
        cron: Pre-filled cron expression (optional).
        task_type: Pre-filled task type (optional).
        script: Pre-filled shell command (optional).
        ai_prompt: Pre-filled AI prompt (optional).
        client: Pre-filled AI client (optional).
    """
    api_client = anthropic.Anthropic()

    # Build initial user message with any pre-filled context
    parts = ["I want to create a new scheduled task."]
    if name:
        parts.append(f"Task name: {name}")
    if cron:
        parts.append(f"Cron schedule: {cron}")
    if task_type:
        parts.append(f"Type: {task_type}")
    if script:
        parts.append(f"Script: {script}")
    if ai_prompt:
        parts.append(f"Prompt: {ai_prompt}")
    if client:
        parts.append(f"AI client: {client}")

    initial_message = " ".join(parts)
    messages: list[anthropic.types.MessageParam] = [{"role": "user", "content": initial_message}]

    console.print("[bold cyan]Starting AI task creation...[/bold cyan]")
    console.print("[dim]Describe what you want to schedule. Type your response when prompted.[/dim]\n")

    while True:
        response = api_client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            tools=[_CREATE_TASK_TOOL],
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_block = next(b for b in response.content if b.type == "tool_use")
            task_input = tool_block.input  # type: ignore[union-attr]

            # Ask for AI client if agent type and not specified
            resolved_client = task_input.get("client") or client
            if task_input.get("type") == "agent" and not resolved_client:
                resolved_client = click.prompt(
                    "Select AI client",
                    type=click.Choice(["kiro-cli", "codebuddy", "opencode"]),
                    default="kiro-cli",
                )

            task = Task(
                name=task_input["name"],
                cron=task_input["cron"],
                type=task_input["type"],
                script=task_input.get("script"),
                prompt=task_input.get("prompt"),
                client=resolved_client,
            )
            add_task(task)
            console.print(f"\n[green]Task '{task.name}' created.[/green]")
            console.print(f"  Cron: {task.cron}")
            console.print(f"  Type: {task.type}")
            if task.script:
                console.print(f"  Script: {task.script}")
            if task.prompt:
                console.print(f"  Prompt: {task.prompt}")
            return

        # Extract assistant text and continue conversation
        text_blocks = [b for b in response.content if b.type == "text"]
        if text_blocks:
            assistant_text = text_blocks[0].text
            console.print(f"\n[bold]Assistant:[/bold] {assistant_text}")

        messages.append({"role": "assistant", "content": response.content})  # type: ignore[arg-type]
        user_reply = click.prompt("\nYou")
        messages.append({"role": "user", "content": user_reply})
