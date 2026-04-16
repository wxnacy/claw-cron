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
from datetime import datetime
from typing import TYPE_CHECKING, Any

from claw_cron.channels import MessageResult, get_channel
from claw_cron.config import load_config

if TYPE_CHECKING:
    from claw_cron.storage import Task


@dataclass
class NotifyConfig:
    """Notification configuration for a task.

    Attributes:
        channel: Channel identifier ('imessage', 'qqbot', etc.).
            Must match a registered channel in CHANNEL_REGISTRY.
        recipients: List of recipient identifiers.
            Format depends on channel:
            - iMessage: Phone numbers with country code ('+8613812345678')
            - QQ Bot: C2C ('c2c:OPENID') or group ('group:GROUP_ID')

    Example:
        >>> config = NotifyConfig(
        ...     channel="imessage",
        ...     recipients=["+8613812345678", "+8613987654321"]
        ... )
    """

    channel: str
    recipients: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotifyConfig:
        """Create NotifyConfig from a dictionary.

        Args:
            data: Dictionary with 'channel' and 'recipients' keys.

        Returns:
            NotifyConfig instance.

        Example:
            >>> config = NotifyConfig.from_dict({
            ...     "channel": "qqbot",
            ...     "recipients": ["c2c:ABC123"]
            ... })
        """
        return cls(
            channel=data.get("channel", ""),
            recipients=data.get("recipients", []),
        )


def render_message(template: str) -> str:
    """Render message template with variables.

    Supported variables:
        {{ date }} -> Current date in YYYY-MM-DD format
        {{ time }} -> Current time in HH:MM:SS format

    Args:
        template: Message template string.

    Returns:
        Rendered message with variables replaced.

    Example:
        >>> msg = render_message("Today is {{ date }}, time is {{ time }}")
        >>> "{{ date }}" not in msg
        True
    """
    now = datetime.now()
    return (
        template.replace("{{ date }}", now.strftime("%Y-%m-%d")).replace(
            "{{ time }}", now.strftime("%H:%M:%S")
        )
    )


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

        Args:
            task: Task that was executed.
            exit_code: Exit code from task execution (0 = success).
            output: Optional output from task execution.

        Returns:
            List of MessageResult for each recipient.
            Empty list if task has no notify config.
        """
        if not task.notify:
            return []

        # Load channel config from config.yaml
        config = load_config()
        channel_config = config.get("channels", {}).get(task.notify.channel, {})

        try:
            channel = get_channel(task.notify.channel, config=channel_config if channel_config else None)
        except (ValueError, Exception) as e:
            # Channel not available or misconfigured
            return [
                MessageResult(
                    success=False,
                    error=f"Failed to get channel '{task.notify.channel}': {e}",
                )
            ]

        message = self._format_message(task, exit_code, output)

        results: list[MessageResult] = []
        for recipient in task.notify.recipients:
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
