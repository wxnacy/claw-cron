# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""log command — tail task or system logs in real time."""

import subprocess

import click
from rich.console import Console

from claw_cron.executor import LOGS_DIR

console = Console()

SYSTEM_LOG = LOGS_DIR / "claw-cron.log"


@click.command()
@click.argument("name", required=False, default=None)
def log(name: str | None) -> None:
    """Tail task log or system log in real time.

    Without NAME: tail the system log (logs/claw-cron.log).
    With NAME: tail the named task's log (logs/<name>.log).
    """
    if name:
        log_path = LOGS_DIR / f"{name}.log"
    else:
        log_path = SYSTEM_LOG

    if not log_path.exists():
        console.print(f"[yellow]Log file not found: {log_path}[/yellow]")
        console.print("[dim]Run a task first to generate logs.[/dim]")
        raise SystemExit(1)

    console.print(f"[dim]Tailing: {log_path}[/dim]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")
    try:
        subprocess.run(["tail", "-f", str(log_path)])
    except KeyboardInterrupt:
        pass
