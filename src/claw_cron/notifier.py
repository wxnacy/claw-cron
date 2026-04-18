# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Notification system for task execution results.

This module provides notification capabilities for claw-cron tasks,
allowing users to receive alerts via multiple messaging channels
(iMessage, QQ Bot, etc.) when tasks complete.

Classes:
    NotifyConfig: Configuration for task notifications.
    Notifier: Sends task execution notifications.

Usage:
    from claw_cron.notifier import NotifyConfig, Notifier
    from claw_cron.storage import Task

    # Create a task with notification
    notify = NotifyConfig(channel="imessage", recipients=["+8613812345678"])
    task = Task(name="backup", cron="0 2 * * *", type="command",
                script="backup.sh", notify=notify)

    # Send notification after execution
    notifier = Notifier()
    await notifier.notify_task_result(task, exit_code=0, output="Done!")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from claw_cron.channels import MessageResult, get_channel
from claw_cron.config import load_config
from claw_cron.template import render as render_template

if TYPE_CHECKING:
    from claw_cron.storage import Task


@dataclass
class NotifyConfig:
    """Notification configuration for a task.

    Attributes:
        channel: Channel identifier ('imessage', 'qqbot', 'system', etc.).
            Must match a registered channel in CHANNEL_REGISTRY.
        recipients: List of recipient identifiers.
            Format depends on channel:
            - iMessage: Phone numbers with country code ('+8613812345678')
            - QQ Bot: C2C ('c2c:OPENID') or group ('group:GROUP_ID')
            - System: Use 'local' (ignored, notification shows locally)
        when: Condition expression for notification delivery (e.g. 'signed_in == false').
            When None, notification is always sent. Evaluated in Phase 20.

    Example:
        >>> config = NotifyConfig(
        ...     channel="imessage",
        ...     recipients=["+8613812345678", "+8613987654321"]
        ... )
    """

    channel: str
    recipients: list[str] = field(default_factory=list)
    when: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotifyConfig | list[NotifyConfig]:
        """Create NotifyConfig from a dictionary.

        Supports both single notify config and list of configs.

        Args:
            data: Dictionary with 'channel' and 'recipients' keys,
                or a list of such dictionaries.

        Returns:
            NotifyConfig instance or list of NotifyConfig instances.

        Example:
            >>> config = NotifyConfig.from_dict({
            ...     "channel": "qqbot",
            ...     "recipients": ["c2c:ABC123"]
            ... })
        """
        return cls(
            channel=data.get("channel", ""),
            recipients=data.get("recipients", []),
            when=data.get("when"),
        )

    @classmethod
    def from_dict_list(cls, data: dict[str, Any] | list[dict[str, Any]]) -> list[NotifyConfig]:
        """Create list of NotifyConfig from dict or list of dicts.

        Args:
            data: Single notify dict or list of notify dicts.

        Returns:
            List of NotifyConfig instances.

        Example:
            >>> configs = NotifyConfig.from_dict_list([
            ...     {"channel": "qqbot", "recipients": ["c2c:ABC123"]},
            ...     {"channel": "system", "recipients": ["local"]}
            ... ])
        """
        if isinstance(data, list):
            return [cls.from_dict(item) for item in data]
        else:
            return [cls.from_dict(data)]


def render_message(template: str, context: dict | None = None) -> str:
    """Render message template with variables.

    Supported variables:
        {{ date }} -> Current date in YYYY-MM-DD format
        {{ time }} -> Current time in HH:MM:SS format
        {{ context.KEY }} -> Value from context dict under key KEY

    Args:
        template: Message template string.
        context: Optional context dict for {{ context.xxx }} variables.

    Returns:
        Rendered message with variables replaced.

    Example:
        >>> msg = render_message("Today is {{ date }}, time is {{ time }}")
        >>> "{{ date }}" not in msg
        True
    """
    return render_template(template, context=context)


class Notifier:
    """Send task execution notifications via configured channels.

    This class handles the notification logic after task execution,
    formatting messages and sending them through the appropriate
    messaging channel.

    Example:
        >>> from claw_cron.notifier import Notifier, NotifyConfig
        >>> from claw_cron.storage import Task
        >>> notify = NotifyConfig(channel="imessage", recipients=["+86138"])
        >>> task = Task(name="test", cron="* * * * *", type="command",
        ...             script="echo hi", notify=notify)
        >>> notifier = Notifier()
        >>> results = await notifier.notify_task_result(task, 0, "hi")
    """

    async def notify_task_result(
        self,
        task: Task,
        exit_code: int,
        output: str | None = None,
    ) -> list[MessageResult]:
        """Send notification after task execution.

        Supports multiple notification channels (notify can be a list).

        Args:
            task: Task that was executed.
            exit_code: Exit code from task execution (0 = success).
            output: Optional output from task execution.

        Returns:
            List of MessageResult for each recipient across all channels.
            Empty list if task has no notify config.
        """
        if not task.notify:
            return []

        # Normalize to list
        notify_configs: list[NotifyConfig] = []
        if isinstance(task.notify, list):
            notify_configs = task.notify
        else:
            notify_configs = [task.notify]

        config = load_config()
        results: list[MessageResult] = []
        message = self._format_message(task, exit_code, output)

        for notify_config in notify_configs:
            channel_config = config.get("channels", {}).get(notify_config.channel, {})

            try:
                channel = get_channel(notify_config.channel, config=channel_config if channel_config else None)
            except (ValueError, Exception) as e:
                results.append(
                    MessageResult(
                        success=False,
                        error=f"Failed to get channel '{notify_config.channel}': {e}",
                    )
                )
                continue

            for recipient in notify_config.recipients:
                try:
                    result = await channel.send_text(recipient, message)
                    results.append(result)
                except Exception as e:
                    results.append(
                        MessageResult(
                            success=False,
                            error=str(e),
                        )
                    )

        return results

    def _format_message(
        self,
        task: Task,
        exit_code: int,
        output: str | None,
    ) -> str:
        """Format notification message.

        Args:
            task: Task that was executed.
            exit_code: Exit code from task execution.
            output: Optional output from task execution.

        Returns:
            Formatted notification message.
        """
        # Reminder type: send only the message content, no task metadata
        if task.type == "reminder":
            return output or render_message(task.message or "")

        status = "成功" if exit_code == 0 else "失败"
        lines = [
            f"任务: {task.name}",
            f"状态: {status}",
        ]
        if exit_code != 0:
            lines.append(f"退出码: {exit_code}")
        if output:
            # Truncate long output
            truncated = output[:500] + "..." if len(output) > 500 else output
            lines.append(f"结果:\n{truncated}")
        return "\n".join(lines)
