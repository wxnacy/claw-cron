# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Task context persistence — load and save per-task context JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTEXT_DIR = Path.home() / ".config" / "claw-cron" / "context"


def _context_path(task_name: str) -> Path:
    """Return the context file path for a task."""
    return CONTEXT_DIR / f"{task_name}.json"


def load_context(task_name: str) -> dict[str, Any]:
    """Load task context from JSON file.

    Args:
        task_name: Task name used as the context file key.

    Returns:
        Context dict. Empty dict if file doesn't exist or is invalid JSON.
    """
    path = _context_path(task_name)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_context(task_name: str, context: dict[str, Any]) -> None:
    """Save task context to JSON file.

    Creates parent directories if they don't exist.

    Args:
        task_name: Task name used as the context file key.
        context: Context dict to persist.
    """
    path = _context_path(task_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2))
