# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Task execution engine — supports command and agent task types."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from claw_cron.config import get_client_cmd
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


def execute_task(task: Task) -> int:
    """Execute a task and write output to its log file.

    Args:
        task: Task to execute.

    Returns:
        Exit code of the executed command (0 = success).
    """
    log_path = _task_log_path(task.name)
    ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    return result.returncode
