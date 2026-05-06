# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""add command — create a new scheduled task."""

import click
from rich.console import Console

from claw_cron.storage import Task, add_task

console = Console()


@click.command()
@click.option("--name", default=None, help="Unique task name")
@click.option("--cron", default=None, help="Cron expression (5 fields, e.g. '0 8 * * *')")
@click.option(
    "--type",
    "task_type",
    default=None,
    type=click.Choice(["command", "agent", "reminder"]),
    help="Execution type",
)
@click.option("--script", default=None, help="Shell command to run (command type)")
@click.option("--prompt", "ai_prompt", default=None, help="AI prompt to send (agent type)")
@click.option(
    "--client",
    default=None,
    type=click.Choice(["kiro-cli", "codebuddy", "opencode"]),
    help="AI client to use (agent type)",
)
@click.option("--cwd", default=None, help="Working directory for task execution")
def add(
    name: str | None,
    cron: str | None,
    task_type: str | None,
    script: str | None,
    ai_prompt: str | None,
    client: str | None,
    cwd: str | None,
) -> None:
    """Add a new scheduled task.

    Direct mode: provide --name, --cron, --type (and --script or --prompt) to skip AI interaction.
    Interactive mode: omit required options to start an AI-guided conversation.
    """
    # Direct mode: all required fields provided
    if name and cron and task_type:
        _add_direct(name, cron, task_type, script, ai_prompt, client, cwd)
        return

    # AI interactive mode (Phase 2 Plan 03)
    from claw_cron.agent import run_ai_add  # noqa: PLC0415

    run_ai_add(name=name, cron=cron, task_type=task_type, script=script, ai_prompt=ai_prompt, client=client)


def _add_direct(
    name: str,
    cron: str,
    task_type: str,
    script: str | None,
    ai_prompt: str | None,
    client: str | None,
    cwd: str | None,
) -> None:
    """Create task directly from provided arguments."""
    if task_type == "command" and not script:
        raise click.UsageError("--script is required for command type tasks")
    if task_type == "agent" and not ai_prompt:
        raise click.UsageError("--prompt is required for agent type tasks")
    if task_type == "reminder":
        if not ai_prompt:
            raise click.UsageError(
                "--prompt is required for reminder type tasks (used as message)"
            )
        # Use prompt as message for reminder
        task = Task(
            name=name,
            cron=cron,
            type=task_type,
            message=ai_prompt,
        )
        add_task(task)
        console.print(f"[green]Reminder '{name}' added.[/green]")
        console.print(
            "[yellow]Note: Edit tasks.yaml to add notification config.[/yellow]"
        )
        return

    task = Task(
        name=name,
        cron=cron,
        type=task_type,
        script=script,
        prompt=ai_prompt,
        client=client,
        cwd=cwd,
    )
    add_task(task)
    console.print(f"[green]Task '{name}' added.[/green]")
