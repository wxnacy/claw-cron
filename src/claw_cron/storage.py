# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""YAML-based task storage for claw-cron."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

TASKS_FILE = Path.home() / ".config" / "claw-cron" / "tasks.yaml"


@dataclass
class Task:
    """A scheduled task configuration.

    Attributes:
        name: Unique task identifier.
        cron: Standard 5-field cron expression (min hour day month weekday).
        type: Execution type — "command" or "agent".
        script: Shell command to run (command type).
        prompt: AI prompt to send (agent type).
        client: AI client to use — "kiro-cli", "codebuddy", or "opencode" (agent type).
        client_cmd: Full command template override for this task (highest priority, overrides config.yaml and built-in defaults). Use {prompt} as placeholder.
        enabled: Whether the task is active. Defaults to True.
    """

    name: str
    cron: str
    type: str
    script: str | None = None
    prompt: str | None = None
    client: str | None = None
    client_cmd: str | None = None
    enabled: bool = field(default=True)


def _load_raw(path: Path = TASKS_FILE) -> list[dict[str, Any]]:
    """Load raw task dicts from YAML file."""
    if not path.exists():
        return []
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    return data.get("tasks", [])


def load_tasks(path: Path = TASKS_FILE) -> list[Task]:
    """Load all tasks from the YAML file.

    Args:
        path: Path to the tasks YAML file.

    Returns:
        List of Task objects. Empty list if file doesn't exist.
    """
    return [Task(**raw) for raw in _load_raw(path)]


def save_tasks(tasks: list[Task], path: Path = TASKS_FILE) -> None:
    """Save tasks to the YAML file.

    Creates parent directories if they don't exist.

    Args:
        tasks: List of Task objects to persist.
        path: Path to the tasks YAML file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump({"tasks": [asdict(t) for t in tasks]}, f, default_flow_style=False, allow_unicode=True)


def get_task(name: str, path: Path = TASKS_FILE) -> Task | None:
    """Find a task by name.

    Args:
        name: Task name to search for.
        path: Path to the tasks YAML file.

    Returns:
        Task if found, None otherwise.
    """
    return next((t for t in load_tasks(path) if t.name == name), None)


def add_task(task: Task, path: Path = TASKS_FILE) -> None:
    """Add a new task, replacing any existing task with the same name.

    Args:
        task: Task to add or update.
        path: Path to the tasks YAML file.
    """
    tasks = [t for t in load_tasks(path) if t.name != task.name]
    tasks.append(task)
    save_tasks(tasks, path)


def delete_task(name: str, path: Path = TASKS_FILE) -> bool:
    """Delete a task by name.

    Args:
        name: Name of the task to delete.
        path: Path to the tasks YAML file.

    Returns:
        True if task was found and deleted, False if not found.
    """
    tasks = load_tasks(path)
    filtered = [t for t in tasks if t.name != name]
    if len(filtered) == len(tasks):
        return False
    save_tasks(filtered, path)
    return True


def update_task(name: str, path: Path = TASKS_FILE, **kwargs: Any) -> bool:
    """Update fields of an existing task by name.

    Args:
        name: Name of the task to update.
        path: Path to the tasks YAML file.
        **kwargs: Fields to update (e.g., enabled=True, client_cmd="...").

    Returns:
        True if task was found and updated, False if not found.
    """
    tasks = load_tasks(path)
    for task in tasks:
        if task.name == name:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            save_tasks(tasks, path)
            return True
    return False