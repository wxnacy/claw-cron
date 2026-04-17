# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Task execution engine — supports command, agent, and reminder task types."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path

from claw_cron.config import get_client_cmd
from claw_cron.context import load_context, save_context
from claw_cron.notifier import Notifier, render_message
from claw_cron.storage import Task
from claw_cron.template import render as render_template

# Configure logger
logger = logging.getLogger(__name__)

LOGS_DIR = Path.home() / ".config" / "claw-cron" / "logs"


def _task_log_path(name: str) -> Path:
    """Return the log file path for a task."""
    return LOGS_DIR / f"{name}.log"


def _write_log(log_path: Path, content: str) -> None:
    """Append content to a log file, creating parent dirs if needed."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(content)


CONTEXT_INPUT_DIR = Path.home() / ".config" / "claw-cron" / "context"


def _build_env(task: Task, context: dict) -> dict[str, str]:
    """Build environment variables dict for subprocess.

    Merges: current process env + system CLAW_ vars + user CLAW_CONTEXT_ vars.

    Args:
        task: Task being executed.
        context: Current task context dict (loaded from context.json).

    Returns:
        Full environment dict for subprocess.
    """
    last_output = context.get("last_output", "")
    if isinstance(last_output, str) and len(last_output) > 4096:
        last_output = last_output[:4096]

    system_vars: dict[str, str] = {
        "CLAW_TASK_NAME": task.name,
        "CLAW_TASK_TYPE": task.type,
        "CLAW_LAST_EXIT_CODE": str(context.get("last_exit_code", "")),
        "CLAW_LAST_OUTPUT": str(last_output),
        "CLAW_EXECUTION_TIME": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "CLAW_TASK_CRON": task.cron,
        "CLAW_EXECUTION_COUNT": str(context.get("execution_count", 0)),
        "CLAW_LAST_EXECUTION_TIME": str(context.get("last_execution_time", "")),
    }

    user_vars: dict[str, str] = {}
    if task.env:
        for k, v in task.env.items():
            user_vars[f"CLAW_CONTEXT_{k}"] = str(v)

    return {**os.environ, **system_vars, **user_vars}


def _write_context_file(task_name: str, context: dict) -> Path:
    """Write context JSON to fixed path file and return the path.

    Args:
        task_name: Task name used in filename.
        context: Context dict to write.

    Returns:
        Path to the written context file.
    """
    path = CONTEXT_INPUT_DIR / f"{task_name}_input.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2))
    return path


def _parse_stdout_json(stdout: str) -> dict | None:
    """Parse the last line of stdout as JSON.

    Args:
        stdout: Full stdout string from subprocess.

    Returns:
        Parsed dict if last line is valid JSON, None otherwise.
    """
    if not stdout:
        return None
    last_line = stdout.rstrip("\n").rsplit("\n", 1)[-1].strip()
    try:
        parsed = json.loads(last_line)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def execute_task(task: Task) -> tuple[int, str, dict | None]:
    """Execute a task and return (exit_code, output, feedback).

    Args:
        task: Task to execute.

    Returns:
        Tuple of (exit_code, output, feedback).
        exit_code 0 = success.
        For reminder type, exit_code is always 0, feedback is None.
        feedback is parsed from last stdout line JSON (command type only).

    Raises:
        ValueError: If task type is unknown.
    """
    log_path = _task_log_path(task.name)
    ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if task.type == "reminder":
        message = render_message(task.message or "")
        log_content = (
            f"[{ts_start}] REMINDER: {task.name}\n"
            f"任务: {task.name}\n"
            f"状态: 成功\n"
            f"结果:\n{message}\n\n"
        )
        _write_log(log_path, log_content)
        return 0, message, None

    if task.type == "command":
        context = load_context(task.name)
        env = _build_env(task, context)
        ctx_file = _write_context_file(task.name, context)
        env["CLAW_CONTEXT_FILE"] = str(ctx_file)
        raw_script = task.script or ""
        cmd = render_template(raw_script, context=context)
    elif task.type == "agent":
        env = None
        if task.client_cmd:
            template = task.client_cmd
        else:
            template = get_client_cmd(task.client or "kiro-cli")
        cmd = template.replace("{prompt}", task.prompt or "")
    else:
        raise ValueError(f"Unknown task type: {task.type!r}")

    _write_log(log_path, f"[{ts_start}] START: {task.name}\n")

    if task.type == "command":
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    else:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    ts_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output = ""
    if result.stdout:
        output += result.stdout
    if result.stderr:
        output += result.stderr
    _write_log(log_path, f"{output}[{ts_end}] END (exit_code={result.returncode})\n\n")

    feedback = _parse_stdout_json(result.stdout or "") if task.type == "command" else None
    return result.returncode, output, feedback


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
    exit_code, output, feedback = execute_task(task)

    # Save context tracking fields (always) and merge feedback (if any)
    existing = load_context(task.name)
    merged = {**existing, **(feedback or {})}
    merged["last_exit_code"] = exit_code
    merged["last_output"] = output[:4096] if output else ""
    merged["last_execution_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    merged["execution_count"] = existing.get("execution_count", 0) + 1
    save_context(task.name, merged)

    if task.notify:
        try:
            notifier = Notifier()
            results = await notifier.notify_task_result(task, exit_code, output)

            # Log notification results
            if results:
                failed_count = sum(1 for r in results if not r.success)
                success_count = len(results) - failed_count

                if success_count > 0:
                    logger.info(
                        f"Notification sent successfully to {success_count} recipient(s) "
                        f"via {task.notify.channel}"
                    )

                if failed_count > 0:
                    for result in results:
                        if not result.success:
                            logger.error(
                                f"Notification failed for task '{task.name}' "
                                f"via {task.notify.channel}: {result.error}"
                            )
        except Exception as e:
            logger.error(
                f"Notification error for task '{task.name}': {type(e).__name__}: {e}"
            )

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
