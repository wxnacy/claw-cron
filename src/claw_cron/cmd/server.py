# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""server command — start the cron scheduler."""

from __future__ import annotations

import os
import signal
import sys
import threading
from pathlib import Path

import click
from rich.console import Console

from claw_cron.executor import LOGS_DIR
from claw_cron.scheduler import SYSTEM_LOG, run_scheduler

PID_FILE = Path.home() / ".config" / "claw-cron" / "claw-cron.pid"

console = Console()


def _daemonize() -> None:
    """Double-fork to detach from terminal and become a daemon process."""
    # First fork: detach from parent
    if os.fork() > 0:
        sys.exit(0)

    os.setsid()  # New session, no controlling terminal

    # Second fork: prevent re-acquiring a terminal
    if os.fork() > 0:
        sys.exit(0)

    # Redirect stdin to /dev/null, stdout/stderr to system log
    sys.stdout.flush()
    sys.stderr.flush()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    devnull_fd = os.open(os.devnull, os.O_RDONLY)
    log_fd = os.open(str(SYSTEM_LOG), os.O_WRONLY | os.O_CREAT | os.O_APPEND)

    os.dup2(devnull_fd, sys.stdin.fileno())
    os.dup2(log_fd, sys.stdout.fileno())
    os.dup2(log_fd, sys.stderr.fileno())

    os.close(devnull_fd)
    os.close(log_fd)

    # Write PID file
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


@click.command()
@click.option("--daemon", is_flag=True, default=False, help="Run as background daemon process.")
def server(daemon: bool) -> None:
    """Start the cron scheduler server.

    Runs in foreground by default, printing schedule logs to stdout.
    Use --daemon to run as a background process.
    """
    if daemon:
        console.print("[cyan]Starting scheduler as daemon...[/cyan]")
        console.print(f"[dim]Log: {SYSTEM_LOG}[/dim]")
        console.print(f"[dim]PID file: {PID_FILE}[/dim]")
        _daemonize()
        # After daemonize: we are the daemon process
        stop_event = threading.Event()
        signal.signal(signal.SIGTERM, lambda s, f: stop_event.set())
        run_scheduler(stop_event, foreground=False)
        PID_FILE.unlink(missing_ok=True)
    else:
        console.print("[cyan]Scheduler starting...[/cyan]")
        console.print(f"[dim]System log: {SYSTEM_LOG}[/dim]")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")

        stop_event = threading.Event()

        def _handle_signal(signum: int, frame: object) -> None:
            console.print("\n[yellow]Stopping scheduler...[/yellow]")
            stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        run_scheduler(stop_event, foreground=True)
        console.print("[green]Scheduler stopped.[/green]")
