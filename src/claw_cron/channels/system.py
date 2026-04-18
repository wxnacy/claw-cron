# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""macOS system notification channel using osascript.

This channel sends desktop notifications via macOS Notification Center
using the built-in osascript command. No signing required.
"""

from __future__ import annotations

import subprocess
from typing import Any

from .base import ChannelConfig, MessageChannel, MessageResult


class SystemConfig(ChannelConfig):
    """Configuration for system notification channel.

    Attributes:
        sound: Notification sound name (e.g., 'default', 'Submarine', 'Ping').
            Set to None to disable sound.
    """

    sound: str | None = "default"

    def __init__(
        self,
        enabled: bool = True,
        sound: str | None = "default",
        **kwargs: Any,
    ) -> None:
        super().__init__(enabled=enabled, **kwargs)
        self.sound = sound


class SystemChannel(MessageChannel):
    """macOS system notification channel.

    Uses osascript to send desktop notifications via Notification Center.
    Works without any signing requirements.

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("system")
        >>> result = await channel.send_text("local", "Task completed!")
    """

    def __init__(self, config: SystemConfig | None = None) -> None:
        super().__init__(config or SystemConfig())

    @property
    def channel_id(self) -> str:
        return "system"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a desktop notification.

        Args:
            recipient: Ignored for system channel (always shows locally).
                Use "local" as convention.
            content: Notification message content.

        Returns:
            MessageResult indicating success or failure.
        """
        # Extract title from content if it contains newlines
        # First line is title, rest is message
        lines = content.split("\n", 1)
        title = "claw-cron"
        message = content

        if len(lines) > 1:
            title = lines[0]
            message = lines[1]
        elif ":" in lines[0] and len(lines[0]) < 50:
            # Heuristic: short text with colon might be a title
            parts = lines[0].split(":", 1)
            if len(parts[0]) < 20:
                title = parts[0].strip()
                message = parts[1].strip() if len(parts) > 1 else ""

        # Build osascript command
        script = f'display notification "{_escape_quotes(message)}" with title "{_escape_quotes(title)}"'

        # Add sound if configured
        config = self.config
        if isinstance(config, SystemConfig) and config.sound:
            script += f' sound name "{config.sound}"'

        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
            )
            return MessageResult(success=True)
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return MessageResult(success=False, error=error_msg)
        except Exception as e:
            return MessageResult(success=False, error=str(e))

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send a markdown message as plain text.

        macOS notifications don't support markdown, so this falls back
        to plain text.

        Args:
            recipient: Ignored for system channel.
            content: Markdown content (rendered as plain text).

        Returns:
            MessageResult indicating success or failure.
        """
        # Strip markdown formatting for plain text display
        import re

        # Remove markdown bold/italic
        text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", content)
        # Remove markdown links, keep text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove markdown headers
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)

        return await self.send_text(recipient, text)

    async def health_check(self) -> bool:
        """Check if osascript is available.

        Returns:
            True if osascript is available, False otherwise.
        """
        try:
            subprocess.run(
                ["osascript", "-e", 'return "ok"'],
                check=True,
                capture_output=True,
            )
            return True
        except Exception:
            return False


def _escape_quotes(text: str) -> str:
    """Escape quotes for osascript.

    Args:
        text: Text to escape.

    Returns:
        Text with escaped quotes.
    """
    return text.replace('"', '\\"')
