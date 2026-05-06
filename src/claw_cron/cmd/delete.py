# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""delete command — remove a scheduled task by name."""

from __future__ import annotations

import click
from rich.console import Console

from claw_cron.cmd.info import render_task_info
from claw_cron.prompt import prompt_confirm, prompt_fuzzy_select
from claw_cron.storage import delete_task, get_task, load_tasks

console = Console()


@click.command()
@click.argument("name", required=False)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt")
def delete(name: str | None, yes: bool) -> None:
    """Delete a scheduled task by NAME.

    If NAME is omitted, an interactive fuzzy selector is shown.
    Use -y to skip confirmation.
    """
    if name is None:
        tasks = load_tasks()
        if not tasks:
            console.print("[yellow]No tasks found.[/yellow]")
            raise SystemExit(0)

        choices = [t.name for t in tasks]
        name = prompt_fuzzy_select("选择要删除的任务:", choices)
        if not name:
            console.print("[dim]Cancelled.[/dim]")
            raise SystemExit(0)

    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    console.print(render_task_info(task))
    console.print()

    if not yes and not prompt_confirm(f"Delete task '{name}'?"):
        console.print("[dim]Cancelled.[/dim]")
        raise SystemExit(0)
    delete_task(name)
    console.print(f"[green]Task '{name}' deleted.[/green]")
