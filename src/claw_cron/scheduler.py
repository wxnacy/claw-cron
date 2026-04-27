# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Cron expression parser and scheduler loop for claw-cron."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from claw_cron.executor import LOGS_DIR, run_task_with_notify
from claw_cron.storage import load_tasks

SYSTEM_LOG = LOGS_DIR / "claw-cron.log"


def cron_matches(expr: str, dt: datetime) -> bool:
    """Check if a 5-field cron expression matches the given datetime.

    Field order: minute hour day month weekday
    Weekday: 0=Sunday, 6=Saturday (cron standard).

    Supports: * (any), */N (step), N-M (range), N,M (list), N (exact).

    Args:
        expr: 5-field cron expression string.
        dt: Datetime to check against.

    Returns:
        True if the expression matches the datetime.

    Raises:
        ValueError: If expr does not have exactly 5 fields.
    """
    fields = expr.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields, got {len(fields)}: {expr!r}")

    minute_f, hour_f, day_f, month_f, weekday_f = fields
    # Convert Python weekday (0=Mon) to cron weekday (0=Sun)
    cron_weekday = (dt.weekday() + 1) % 7

    def _match(field: str, value: int) -> bool:
        if field == "*":
            return True
        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                start = 0 if base == "*" else int(base)
                if value >= start and (value - start) % int(step) == 0:
                    return True
            elif "-" in part:
                lo, hi = part.split("-", 1)
                if int(lo) <= value <= int(hi):
                    return True
            elif int(part) == value:
                return True
        return False

    return (
        _match(minute_f, dt.minute)
        and _match(hour_f, dt.hour)
        and _match(day_f, dt.day)
        and _match(month_f, dt.month)
        and _match(weekday_f, cron_weekday)
    )


def _write_system_log(message: str) -> None:
    """Append a timestamped message to the system log file."""
    SYSTEM_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with SYSTEM_LOG.open("a") as f:
        f.write(f"[{ts}] {message}\n")


def run_scheduler(stop_event: threading.Event, foreground: bool = True) -> None:
    """Run the cron scheduler loop until stop_event is set.

    Checks all enabled tasks every minute. Tasks whose cron expression
    matches the current minute are executed in separate daemon threads.

    Args:
        stop_event: Threading event; set it to stop the scheduler.
        foreground: If True, also print log messages to stdout.
    """
    def log(msg: str) -> None:
        _write_system_log(msg)
        if foreground:
            print(msg, flush=True)

    log(f"Scheduler started (PID={__import__('os').getpid()})")

    tasks = load_tasks()
    log(f"Loaded {len(tasks)} task(s): {', '.join(t.name for t in tasks)}")

    while not stop_event.is_set():
        now = datetime.now().replace(second=0, microsecond=0)
        tasks = load_tasks()
        for task in tasks:
            if not task.enabled:
                continue
            try:
                if cron_matches(task.cron, now):
                    log(f"Triggered: {task.name} ({task.cron})")
                    t = threading.Thread(target=run_task_with_notify, args=(task,), daemon=True)
                    t.start()
            except ValueError as e:
                log(f"Invalid cron for task '{task.name}': {e}")

        # Sleep until the start of the next minute
        next_minute = (time.time() // 60 + 1) * 60
        stop_event.wait(timeout=next_minute - time.time())

    log("Scheduler stopped.")
