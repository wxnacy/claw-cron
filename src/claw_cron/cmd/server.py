# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""server command — start the cron scheduler."""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from pathlib import Path

import click
from rich.console import Console

from claw_cron.executor import LOGS_DIR
from claw_cron.scheduler import SYSTEM_LOG, run_scheduler

PID_FILE = Path.home() / ".config" / "claw-cron" / "claw-cron.pid"

console = Console()


def _daemonize() -> None:
    """Double-fork to detach from terminal and become a daemon process."""
    # Close any existing asyncio event loop before fork to avoid
    # "I/O operation on closed kqueue object" errors on macOS
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()
    except Exception:
        pass
    try:
        asyncio.set_event_loop(None)
    except Exception:
        pass

    # First fork: detach from parent
    pid = os.fork()
    if pid > 0:
        # Parent exits immediately without cleanup to avoid event loop __del__ errors
        os._exit(0)

    os.setsid()  # New session, no controlling terminal

    # Second fork: prevent re-acquiring a terminal
    pid = os.fork()
    if pid > 0:
        # Intermediate child exits immediately without cleanup
        os._exit(0)

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


def _get_daemon_pid() -> int | None:
    """Read PID from PID file if it exists and process is alive."""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)  # Check if process exists
        return pid
    except (ValueError, OSError, ProcessLookupError):
        PID_FILE.unlink(missing_ok=True)
        return None


def _stop_daemon() -> bool:
    """Stop the daemon process. Returns True if stopped successfully."""
    pid = _get_daemon_pid()
    if pid is None:
        console.print("[yellow]Daemon is not running.[/yellow]")
        return False
    console.print(f"[yellow]Stopping daemon (PID={pid})...[/yellow]")
    try:
        os.kill(pid, signal.SIGTERM)
        # Wait up to 5 seconds for process to exit
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except (OSError, ProcessLookupError):
                break
            time.sleep(0.1)
        else:
            console.print(f"[red]Daemon did not stop gracefully, sending SIGKILL (PID={pid})...[/red]")
            try:
                os.kill(pid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        PID_FILE.unlink(missing_ok=True)
        console.print("[green]Daemon stopped.[/green]")
        return True
    except (OSError, ProcessLookupError) as e:
        console.print(f"[red]Failed to stop daemon: {e}[/red]")
        PID_FILE.unlink(missing_ok=True)
        return False


@click.command()
@click.option("--daemon", is_flag=True, default=False, help="Run as background daemon process.")
@click.option("--stop", is_flag=True, default=False, help="Stop the running daemon process.")
@click.option("--restart", is_flag=True, default=False, help="Restart the daemon process (stop then start).")
def server(daemon: bool, stop: bool, restart: bool) -> None:
    """Start the cron scheduler server.

    Runs in foreground by default, printing schedule logs to stdout.
    Use --daemon to run as a background process.
    Use --stop to stop a running daemon.
    Use --restart to restart the daemon.
    """
    if stop:
        _stop_daemon()
        return

    if restart:
        _stop_daemon()
        daemon = True

    if daemon:
        # Check if already running
        existing_pid = _get_daemon_pid()
        if existing_pid is not None:
            console.print(f"[yellow]Daemon already running (PID={existing_pid}). Use --restart to restart.[/yellow]")
            return
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
