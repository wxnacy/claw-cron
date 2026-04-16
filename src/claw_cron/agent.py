# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""AI Agent for interactive task creation using provider pattern."""

from __future__ import annotations

import os

import click
from rich.console import Console

from claw_cron.config import AIConfig, load_ai_config
from claw_cron.prompt import prompt_select, prompt_text
from claw_cron.providers import (
    BaseProvider,
    ToolDefinition,
    get_provider,
)
from claw_cron.storage import Task, add_task

console = Console()

# Provider-agnostic tool definition
_CREATE_TASK_TOOL = ToolDefinition(
    name="create_task",
    description="Create a scheduled task with the parsed configuration from the conversation",
    parameters={
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
)

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
    """Run AI-guided task creation via provider conversation.

    Args:
        name: Pre-filled task name (optional).
        cron: Pre-filled cron expression (optional).
        task_type: Pre-filled task type (optional).
        script: Pre-filled shell command (optional).
        ai_prompt: Pre-filled AI prompt (optional).
        client: Pre-filled AI client (optional).
    """
    # Load configuration and create provider
    ai_config = load_ai_config()
    provider = get_provider(
        provider=ai_config.provider,
        api_key=ai_config.api_key or _get_api_key_from_env(ai_config.provider),
        model=ai_config.get_effective_model(),
        base_url=ai_config.base_url,
    )

    console.print(f"[dim]Using provider: {provider.get_provider_name()}[/dim]")

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
    messages: list[dict] = [{"role": "user", "content": initial_message}]

    console.print("[bold cyan]Starting AI task creation...[/bold cyan]")
    console.print("[dim]Describe what you want to schedule. Type your response when prompted.[/dim]\n")

    while True:
        result = provider.chat_with_tools(
            messages=messages,
            system_prompt=_SYSTEM_PROMPT,
            tools=[_CREATE_TASK_TOOL],
        )

        if result.stop_reason == "tool_use" and result.tool_calls:
            # Handle tool call
            tool_call = result.tool_calls[0]  # Only one tool expected
            task_input = tool_call.arguments

            # Ask for AI client if agent type and not specified
            resolved_client = task_input.get("client") or client
            if task_input.get("type") == "agent" and not resolved_client:
                resolved_client = prompt_select(
                    "Select AI client",
                    choices=["kiro-cli", "codebuddy", "opencode"],
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

        # Text response - continue conversation
        if result.content:
            console.print(f"\n[bold]Assistant:[/bold] {result.content}")

        # Append assistant response to conversation
        messages.append({"role": "assistant", "content": result.content})

        # Get user input
        user_reply = prompt_text("\nYou")
        messages.append({"role": "user", "content": user_reply})


def _get_api_key_from_env(provider: str) -> str:
    """Fallback to provider-specific env var if not in AIConfig.

    Args:
        provider: Provider name ('claude' or 'openai').

    Returns:
        API key from environment variable.

    Raises:
        ValueError: If no API key is found for the provider.
    """
    if provider == "claude":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
    elif provider == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
    else:
        key = ""

    if not key:
        raise ValueError(
            f"No API key found for provider {provider!r}. "
            f"Set CLAW_CRON_API_KEY or {provider.upper()}_API_KEY environment variable."
        )

    return key
