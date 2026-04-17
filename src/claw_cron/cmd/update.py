# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""update command — modify fields of an existing scheduled task."""

import click
from rich.console import Console

from claw_cron.storage import get_task, update_task

console = Console()


@click.command()
@click.argument("name")
@click.option("--cron", default=None, help="New cron expression (5 fields, e.g. '0 8 * * *')")
@click.option("--enabled", default=None, type=bool, help="Enable or disable the task (true/false)")
@click.option("--message", default=None, help="New notification message template")
@click.option("--script", default=None, help="New shell script content (command type)")
@click.option("--prompt", default=None, help="New AI prompt content (chat type)")
def update(
    name: str,
    cron: str | None,
    enabled: bool | None,
    message: str | None,
    script: str | None,
    prompt: str | None,
) -> None:
    """Update fields of an existing task by NAME."""
    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    updates: dict = {}
    if cron is not None:
        updates["cron"] = cron
    if enabled is not None:
        updates["enabled"] = enabled
    if message is not None:
        updates["message"] = message
    if script is not None:
        updates["script"] = script
    if prompt is not None:
        updates["prompt"] = prompt

    if not updates:
        console.print("[yellow]No fields specified to update. Use --cron, --enabled, --message, --script, or --prompt.[/yellow]")
        raise SystemExit(0)

    update_task(name, **updates)
    console.print(f"[green]Task '{name}' updated.[/green]")
    for key, value in updates.items():
        console.print(f"  [dim]{key}[/dim] = {value}")
