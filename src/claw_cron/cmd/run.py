# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""run command — execute a task immediately by name."""

import click
from rich.console import Console

from claw_cron.executor import LOGS_DIR, run_task_with_notify
from claw_cron.storage import get_task

console = Console()


@click.command()
@click.argument("name")
def run(name: str) -> None:
    """Execute a task immediately by name."""
    task = get_task(name)
    if task is None:
        console.print(f"[red]Task '{name}' not found.[/red]")
        raise SystemExit(1)

    log_path = LOGS_DIR / f"{name}.log"
    console.print(f"[cyan]Running task '{name}'...[/cyan]")
    console.print(f"[dim]Log: {log_path}[/dim]")

    exit_code = run_task_with_notify(task)

    if exit_code == 0:
        console.print(f"[green]Task '{name}' completed successfully.[/green]")
    else:
        console.print(f"[red]Task '{name}' failed (exit_code={exit_code}).[/red]")
    raise SystemExit(exit_code)
