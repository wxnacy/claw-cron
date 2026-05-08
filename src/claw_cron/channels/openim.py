# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""OpenIM-based message channel for claw-cron.

Provides a unified channel that routes messages through the OpenIM server
via WebSocket. Supports any platform that OpenIM supports (qq, feishu,
dingtalk, etc.) by passing the platform name at construction time.

Usage:
    from claw_cron.channels.openim import OpenIMBaseChannel

    channel = OpenIMBaseChannel("dingtalk")
    result = await channel.send_text("group:GROUP_OPENID", "Hello!")
"""

from __future__ import annotations

from claw_cron.channels.base import ChannelConfig, MessageChannel, MessageResult
from claw_cron.config import load_config
from claw_cron.openim_manager import OpenIMProcessManager


class OpenIMBaseChannel(MessageChannel):
    """Message channel that sends via OpenIM WebSocket gateway.

    The platform (qq, feishu, dingtalk, etc.) is determined at construction
    time, making it easy to add new platforms without code changes.
    """

    def __init__(self, platform: str, config: ChannelConfig | None = None) -> None:
        self._platform = platform
        super().__init__(config)

    @property
    def channel_id(self) -> str:
        return self._platform

    def _get_openim_uri(self) -> str:
        """Resolve openim WebSocket URI from config.yaml."""
        cfg = load_config()
        openim_cfg = cfg.get("openim", {})
        return openim_cfg.get("uri", "ws://127.0.0.1:12702/ws")

    def _resolve_recipient(self, recipient: str) -> tuple[str, bool]:
        """Parse recipient string into (group_id, is_c2c).

        Supported formats:
            - c2c:OPENID   -> (OPENID, True)
            - group:OPENID -> (OPENID, False)
            - OPENID       -> (OPENID, False)
        """
        if recipient.startswith("c2c:"):
            return recipient[4:], True
        if recipient.startswith("group:"):
            return recipient[6:], False
        return recipient, False

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a text message via OpenIM.

        Ensures the openim server is running (starts it on demand if needed),
        sends the message, and stops the server only if this call started it.
        """
        we_started = OpenIMProcessManager.ensure_running()
        try:
            from openim_sdk import OpenIMClient

            uri = self._get_openim_uri()
            group_id, is_c2c = self._resolve_recipient(recipient)

            client = OpenIMClient(uri)
            await client.connect()
            try:
                await client.send_text(
                    platform=self._platform,
                    group_id=group_id,
                    content=content,
                    is_c2c=is_c2c,
                )
                return MessageResult(success=True)
            finally:
                await client.close()
        except Exception as e:
            return MessageResult(success=False, error=str(e))
        finally:
            if we_started:
                OpenIMProcessManager.stop()

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Fallback to plain text — OpenIM handles formatting per platform."""
        return await self.send_text(recipient, content)

    async def health_check(self) -> bool:
        """Check if openim server is reachable."""
        return OpenIMProcessManager.is_running()
