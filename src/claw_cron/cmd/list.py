# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""list command — show all scheduled tasks."""

import click
from rich.console import Console
from rich.table import Table

from claw_cron.storage import get_notify_list, load_tasks

console = Console()


@click.command("list")
def list_tasks() -> None:
    """List all scheduled tasks."""
    tasks = load_tasks()
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(title="Tasks", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Cron", style="green")
    table.add_column("Type")
    table.add_column("Script/Prompt", overflow="fold", max_width=40)
    table.add_column("CWD", overflow="fold", max_width=20)
    table.add_column("Channels")
    table.add_column("Status")

    for t in tasks:
        content = t.script or t.prompt or "-"
        status = "✓ enabled" if t.enabled else "✗ disabled"
        configs = get_notify_list(t)
        channels = ", ".join(c.channel for c in configs) if configs else "system"
        cwd = t.cwd or "-"
        table.add_row(t.name, t.cron, t.type, content, cwd, channels, status)

    console.print(table)
