# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Task execution engine — supports command, agent, and reminder task types."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from claw_cron.config import get_client_cmd
from claw_cron.notifier import Notifier, render_message
from claw_cron.storage import Task

LOGS_DIR = Path.home() / ".config" / "claw-cron" / "logs"


def _task_log_path(name: str) -> Path:
    """Return the log file path for a task."""
    return LOGS_DIR / f"{name}.log"


def _write_log(log_path: Path, content: str) -> None:
    """Append content to a log file, creating parent dirs if needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(content)


def execute_task(task: Task) -> tuple[int, str]:
    """Execute a task and return (exit_code, output).

    Args:
        task: Task to execute.

    Returns:
        Tuple of (exit_code, output). exit_code 0 = success.
        For reminder type, exit_code is always 0 and output is the rendered message.

    Raises:
        ValueError: If task type is unknown.
    """
    log_path = _task_log_path(task.name)
    ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if task.type == "reminder":
        # Reminder type: just return the rendered message
        message = render_message(task.message or "")
        _write_log(log_path, f"[{ts_start}] REMINDER: {task.name}\n{message}\n\n")
        return 0, message

    if task.type == "command":
        cmd = task.script or ""
    elif task.type == "agent":
        # Priority: task.client_cmd > config.yaml > built-in defaults
        if task.client_cmd:
            template = task.client_cmd
        else:
            template = get_client_cmd(task.client or "kiro-cli")
        cmd = template.replace("{prompt}", task.prompt or "")
    else:
        raise ValueError(f"Unknown task type: {task.type!r}")

    _write_log(log_path, f"[{ts_start}] START: {task.name}\n")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    ts_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr
    _write_log(log_path, f"{output}[{ts_end}] END (exit_code={result.returncode})\n\n")

    return result.returncode, output


async def execute_task_with_notify(task: Task) -> int:
    """Execute task and send notification if configured.

    This is an async wrapper around execute_task that handles notification
    after task execution.

    Args:
        task: Task to execute.

    Returns:
        Exit code from task execution.
        Notification errors are logged but do not affect the return value.
    """
    exit_code, output = execute_task(task)

    if task.notify:
        try:
            notifier = Notifier()
            await notifier.notify_task_result(task, exit_code, output)
        except Exception:
            # Log but don't fail the task
            pass

    return exit_code


def run_task_with_notify(task: Task) -> int:
    """Synchronous wrapper for execute_task_with_notify.

    Use this for integrating with synchronous schedulers.

    Args:
        task: Task to execute.

    Returns:
        Exit code from task execution.
    """
    return asyncio.run(execute_task_with_notify(task))
