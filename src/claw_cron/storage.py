# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""YAML-based task storage for claw-cron."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from claw_cron.notifier import NotifyConfig

TASKS_FILE = Path.home() / ".config" / "claw-cron" / "tasks.yaml"


@dataclass
class Task:
    """A scheduled task configuration.

    Attributes:
        name: Unique task identifier.
        cron: Standard 5-field cron expression (min hour day month weekday).
        type: Execution type — "command", "agent", or "reminder".
        script: Shell command to run (command type).
        prompt: AI prompt to send (agent type).
        client: AI client to use — "kiro-cli", "codebuddy", or "opencode" (agent type).
        client_cmd: Full command template override for this task (highest priority, overrides config.yaml and built-in defaults). Use {prompt} as placeholder.
        enabled: Whether the task is active. Defaults to True.
        notify: Notification configuration. Can be single NotifyConfig or list for multi-channel support.
        message: Message for reminder type tasks. Optional.
        env: Custom environment variables to inject with CLAW_CONTEXT_ prefix. Optional.
        cwd: Working directory for task execution. Optional.
    """

    name: str
    cron: str
    type: str
    script: str | None = None
    prompt: str | None = None
    client: str | None = None
    client_cmd: str | None = None
    enabled: bool = field(default=True)
    notify: NotifyConfig | list[NotifyConfig] | None = None
    message: str | None = None
    env: dict[str, str] | None = None
    cwd: str | None = None


def _load_raw(path: Path = TASKS_FILE) -> list[dict[str, Any]]:
    """Load raw task dicts from YAML file."""
    if not path.exists():
        return []
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    return data.get("tasks", [])


def _task_from_dict(raw: dict[str, Any]) -> Task:
    """Create Task from raw dict, handling nested NotifyConfig."""
    # Handle notify field conversion (single or list)
    if "notify" in raw and raw["notify"]:
        from claw_cron.notifier import NotifyConfig

        notify_data = raw["notify"]
        if isinstance(notify_data, list):
            raw["notify"] = [NotifyConfig.from_dict(item) for item in notify_data]
        elif isinstance(notify_data, dict):
            raw["notify"] = NotifyConfig.from_dict(notify_data)
    return Task(**raw)


def load_tasks(path: Path = TASKS_FILE) -> list[Task]:
    """Load all tasks from the YAML file.

    Args:
        path: Path to the tasks YAML file.

    Returns:
        List of Task objects. Empty list if file doesn't exist.
    """
    return [_task_from_dict(raw) for raw in _load_raw(path)]


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


def get_notify_list(task: "Task") -> list["NotifyConfig"]:
    """Return task notify as a normalized list (never None)."""
    from claw_cron.notifier import NotifyConfig  # noqa: F401

    if task.notify is None:
        return []
    if isinstance(task.notify, list):
        return list(task.notify)
    return [task.notify]


def notify_add(name: str, channel: str, recipients: list[str], when: str | None = None, path: Path = TASKS_FILE) -> bool:
    """Add a notify channel to a task. Returns False if channel already exists."""
    from claw_cron.notifier import NotifyConfig

    tasks = load_tasks(path)
    for task in tasks:
        if task.name == name:
            configs = get_notify_list(task)
            if any(c.channel == channel for c in configs):
                return False
            configs.append(NotifyConfig(channel=channel, recipients=recipients, when=when or None))
            task.notify = configs
            save_tasks(tasks, path)
            return True
    return False


def notify_remove(name: str, channel: str, path: Path = TASKS_FILE) -> bool:
    """Remove a notify channel from a task. Returns False if channel not found."""
    tasks = load_tasks(path)
    for task in tasks:
        if task.name == name:
            configs = get_notify_list(task)
            new_configs = [c for c in configs if c.channel != channel]
            if len(new_configs) == len(configs):
                return False
            task.notify = new_configs or None
            save_tasks(tasks, path)
            return True
    return False


def notify_update(name: str, channel: str, recipients: list[str] | None = None, when: str | None = None, clear_when: bool = False, path: Path = TASKS_FILE) -> bool:
    """Update recipients or when condition of an existing notify channel."""
    tasks = load_tasks(path)
    for task in tasks:
        if task.name == name:
            configs = get_notify_list(task)
            for cfg in configs:
                if cfg.channel == channel:
                    if recipients is not None:
                        cfg.recipients = recipients
                    if clear_when:
                        cfg.when = None
                    elif when is not None:
                        cfg.when = when
                    task.notify = configs
                    save_tasks(tasks, path)
                    return True
            return False
    return False


def notify_clear(name: str, path: Path = TASKS_FILE) -> bool:
    """Remove all notify configs from a task."""
    tasks = load_tasks(path)
    for task in tasks:
        if task.name == name:
            task.notify = None
            save_tasks(tasks, path)
            return True
    return False


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