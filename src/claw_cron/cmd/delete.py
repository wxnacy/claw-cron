# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""delete command — remove a scheduled task by name."""

import click
from rich.console import Console

from claw_cron.prompt import prompt_confirm
from claw_cron.storage import delete_task, get_task

console = Console()


@click.command()
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def delete(name: str, yes: bool) -> None:
    """Delete a scheduled task by NAME.

    Use -y to skip confirmation.
    """
    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    if not yes and not prompt_confirm(f"Delete task '{name}'?"):
        console.print("[dim]Cancelled.[/dim]")
        raise SystemExit(0)
    delete_task(name)
    console.print(f"[green]Task '{name}' deleted.[/green]")
