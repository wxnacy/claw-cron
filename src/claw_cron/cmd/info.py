# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""info command — show detailed information for a single task."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from claw_cron.prompt import prompt_fuzzy_select
from claw_cron.storage import get_notify_list, get_task, load_tasks

console = Console()


def render_task_info(task) -> Table:
    """Render a vertical table with task details.

    Args:
        task: Task object to render.

    Returns:
        Rich Table with field names in the first column and values in the second.
    """
    table = Table(title=f"Task: {task.name}", show_header=True, header_style="bold")
    table.add_column("Field", style="cyan", min_width=12)
    table.add_column("Value", overflow="fold")

    table.add_row("Name", task.name)
    table.add_row("Cron", task.cron)
    table.add_row("Type", task.type)
    table.add_row("Enabled", "✓ Yes" if task.enabled else "✗ No")

    content = task.script or task.prompt or "-"
    content_label = "Script" if task.script else ("Prompt" if task.prompt else "Content")
    table.add_row(content_label, content)

    if task.client:
        table.add_row("Client", task.client)
    if task.client_cmd:
        table.add_row("Client Cmd", task.client_cmd)
    if task.cwd:
        table.add_row("CWD", task.cwd)
    if task.message:
        table.add_row("Message", task.message)

    configs = get_notify_list(task)
    channels = ", ".join(c.channel for c in configs) if configs else "system"
    table.add_row("Channels", channels)

    if task.env:
        env_lines = "\n".join(f"{k}={v}" for k, v in task.env.items())
        table.add_row("Env", env_lines)

    return table


@click.command()
@click.argument("name", required=False)
def info(name: str | None) -> None:
    """Show detailed information for a task.

    If NAME is omitted, an interactive fuzzy selector is shown.
    """
    if name is None:
        tasks = load_tasks()
        if not tasks:
            console.print("[yellow]No tasks found.[/yellow]")
            raise SystemExit(0)

        choices = [t.name for t in tasks]
        name = prompt_fuzzy_select("选择任务:", choices)
        if not name:
            console.print("[dim]Cancelled.[/dim]")
            raise SystemExit(0)

    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    console.print(render_task_info(task))
