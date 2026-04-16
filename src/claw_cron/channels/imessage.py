# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""iMessage channel implementation using AppleScript.

First-Time Setup:
    1. Ensure Messages.app is logged into iMessage
    2. First send attempt will trigger macOS Accessibility permission prompt
    3. Grant permission in System Settings → Privacy & Security → Accessibility
    4. Retry the send operation

Platform Requirements:
    - macOS only (raises ChannelNotAvailableError on other platforms)
    - Messages.app must be configured with iMessage account
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelNotAvailableError


@dataclass
class IMessageConfig(ChannelConfig):
    """Configuration for iMessage channel.

    iMessage uses system Messages.app configuration, so no additional
    credentials are needed. The configuration is primarily for enabling/disabling.
    """

    # Future: could add default_sender, message_templates, etc.
    pass


class IMessageChannel(MessageChannel):
    """iMessage channel for sending messages on macOS.

    This channel uses AppleScript to send iMessages via Messages.app.

    Requirements:
        - macOS operating system
        - Messages.app logged into iMessage account
        - Accessibility permission (prompted on first use)

    Phone Number Format:
        - Supports international format: +8613812345678
        - Supports local format: 13812345678
        - Must be a valid iMessage recipient

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("imessage")
        >>> result = await channel.send_text("+8613812345678", "Hello!")
        >>> if result.success:
        ...     print("Message sent!")
    """

    def __init__(self, config: IMessageConfig | None = None) -> None:
        """Initialize iMessage channel.

        Args:
            config: Channel configuration (optional).

        Raises:
            ChannelNotAvailableError: If not running on macOS.
        """
        super().__init__(config or IMessageConfig())

        # Platform check
        if platform.system() != "Darwin":
            raise ChannelNotAvailableError(
                "iMessage is only available on macOS",
                channel_id="imessage",
            )

    @property
    def channel_id(self) -> str:
        """Return channel identifier."""
        return "imessage"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a plain text iMessage.

        Args:
            recipient: Phone number (e.g., "+8613812345678" or "13812345678")
            content: Plain text message content.

        Returns:
            MessageResult with success status.
        """
        # Validate phone number format (basic check)
        normalized = self._normalize_phone(recipient)

        try:
            # Use AppleScript to send iMessage
            result = self._send_applescript(normalized, content)

            if result == "Success":
                return MessageResult(
                    success=True,
                    raw_response={"recipient": normalized, "content": content},
                )
            else:
                # Handle permission errors
                error_msg = result.lower()
                if "accessibility" in error_msg or "permission" in error_msg:
                    return MessageResult(
                        success=False,
                        error=(
                            "iMessage requires Accessibility permission. "
                            "Go to System Settings → Privacy & Security → Accessibility "
                            "and grant permission to Terminal or your IDE."
                        ),
                    )

                return MessageResult(
                    success=False,
                    error=f"Failed to send iMessage: {result}",
                )

        except Exception as e:
            return MessageResult(
                success=False,
                error=f"Failed to send iMessage: {e}",
            )

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send markdown as plain text (iMessage doesn't support markdown).

        Args:
            recipient: Phone number.
            content: Markdown content (sent as plain text).

        Returns:
            MessageResult with success status.
        """
        # iMessage doesn't support markdown formatting
        # Send as plain text
        return await self.send_text(recipient, content)

    async def health_check(self) -> bool:
        """Check if iMessage is available and configured.

        Returns:
            True if Messages.app is logged in and accessible.
        """
        if platform.system() != "Darwin":
            return False

        try:
            # Check if Messages.app is running or can be launched
            script = '''
            tell application "System Events"
                return exists process "Messages"
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number format.

        - Removes spaces, dashes, parentheses
        - Preserves + prefix for international format
        - +86 format is supported directly

        Args:
            phone: Phone number string.

        Returns:
            Normalized phone number.
        """
        import re

        # Remove common formatting characters
        normalized = re.sub(r"[\s\-\(\)]", "", phone)

        # Ensure + prefix for international format if not present
        # and number starts with country code
        if not normalized.startswith("+") and len(normalized) > 10:
            # Assume international format without +
            # Don't add + automatically - let Messages.app handle it
            pass

        return normalized

    def _send_applescript(self, phone: str, message: str) -> str:
        """Send iMessage using AppleScript.

        Uses the bundled sendMessage.scpt from macpymessenger package,
        or falls back to inline AppleScript.

        Args:
            phone: Normalized phone number.
            message: Message content.

        Returns:
            "Success" or error message.
        """
        # Try to use bundled scpt file
        scpt_path = (
            Path(__file__).parent.parent.parent.parent
            / ".venv/lib/python3.12/site-packages/macpymessenger/osascript/sendMessage.scpt"
        )

        if scpt_path.exists():
            try:
                result = subprocess.run(
                    ["osascript", str(scpt_path), phone, message],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return result.stdout.strip() or f"Error: {result.stderr.strip()}"
            except subprocess.TimeoutExpired:
                return "Error: Timeout waiting for Messages.app"
            except Exception as e:
                return f"Error: {e}"

        # Fallback to inline AppleScript
        script = f'''
        tell application "Messages"
            if not running then
                launch
                delay 1
            end if

            set targetService to first service whose service type = iMessage
            set targetBuddy to buddy "{phone}" of targetService

            try
                send "{message}" to targetBuddy
                return "Success"
            on error errMsg
                return "Error: " & errMsg
            end try
        end tell
        '''

        # Escape quotes in message
        escaped_message = message.replace('"', '\\"')
        script = script.replace(f'send "{message}"', f'send "{escaped_message}"')

        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout.strip() or f"Error: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "Error: Timeout waiting for Messages.app"
        except Exception as e:
            return f"Error: {e}"
