# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Feishu channel implementation for claw-cron.

This module implements the Feishu (Lark) Bot API integration following the MessageChannel
interface. It supports:
- Automatic tenant_access_token management via lark-oapi SDK
- C2C private chat messages (c2c:OPENID format)
- Markdown messages (with fallback to plain text)

Environment Variables:
    CLAW_CRON_FEISHU_APP_ID: Feishu App ID from open.feishu.cn
    CLAW_CRON_FEISHU_APP_SECRET: Feishu App Secret from open.feishu.cn

Recipient Formats:
    - "c2c:OPENID" - Private chat with user (bot-specific openid)
    - Plain string - Treated as C2C openid for backward compatibility
"""

from __future__ import annotations

import asyncio
import json

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
)
from pydantic import Field
from pydantic_settings import BaseSettings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelAuthError, ChannelConfigError, ChannelError, ChannelSendError
from .qqbot import parse_recipient


class FeishuConfig(BaseSettings, ChannelConfig):
    """Configuration for Feishu channel.

    Environment variables use CLAW_CRON_FEISHU_ prefix:
        - CLAW_CRON_FEISHU_APP_ID: Feishu App ID
        - CLAW_CRON_FEISHU_APP_SECRET: Feishu App Secret

    Attributes:
        app_id: Feishu App ID from open platform (open.feishu.cn).
        app_secret: Feishu App Secret from open platform.
    """

    app_id: str | None = Field(
        default=None, description="Feishu App ID from open.feishu.cn"
    )
    app_secret: str | None = Field(
        default=None, description="Feishu App Secret from open.feishu.cn"
    )

    class Config:
        env_prefix = "CLAW_CRON_FEISHU_"
        env_file = ".env"
        extra = "ignore"


class FeishuRateLimitError(Exception):
    """Feishu rate limit error that can be retried.

    Feishu rate limit error code: 99991400
    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class FeishuChannel(MessageChannel):
    """Feishu channel implementation using lark-oapi SDK.

    This channel sends messages through Feishu Open Platform API. It supports:
    - Automatic tenant_access_token management via SDK
    - C2C private chat messages
    - Markdown messages (with fallback to plain text)

    Attributes:
        config: Feishu configuration.
        _client: lark-oapi SDK client (lazy initialization).

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("feishu")
        >>> result = await channel.send_text("c2c:ou_xxx", "Hello!")
        >>> if result.success:
        ...     print(f"Message sent: {result.message_id}")
    """

    RATE_LIMIT_CODE = 99991400
    AUTH_ERROR_CODES = frozenset({99991661, 99991662, 99991663})

    def __init__(self, config: FeishuConfig | dict | None = None) -> None:
        """Initialize Feishu channel.

        Args:
            config: Feishu configuration. Can be FeishuConfig, dict, or None.
        """
        if config is None:
            config_obj = FeishuConfig()
        elif isinstance(config, dict):
            config_obj = FeishuConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)
        self._client: lark.Client | None = None

    @property
    def channel_id(self) -> str:
        """Return unique channel identifier."""
        return "feishu"

    def _validate_config(self) -> None:
        """Validate configuration has required fields.

        Raises:
            ChannelConfigError: If app_id or app_secret is missing.
        """
        if not self.config.app_id:
            raise ChannelConfigError(
                "Feishu app_id is required. Set CLAW_CRON_FEISHU_APP_ID environment variable.",
                channel_id=self.channel_id,
            )
        if not self.config.app_secret:
            raise ChannelConfigError(
                "Feishu app_secret is required. Set CLAW_CRON_FEISHU_APP_SECRET environment variable.",
                channel_id=self.channel_id,
            )

    def _get_client(self) -> lark.Client:
        """Get or create SDK client (lazy init).

        The SDK handles tenant_access_token lifecycle automatically.

        Returns:
            lark-oapi Client instance.
        """
        if self._client is None:
            self._validate_config()
            self._client = (
                lark.Client.builder()
                .app_id(self.config.app_id)
                .app_secret(self.config.app_secret)
                .log_level(lark.LogLevel.ERROR)
                .build()
            )
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(FeishuRateLimitError),
        reraise=True,
    )
    async def _send_message(
        self,
        receive_id: str,
        msg_type: str,
        content: str,
    ) -> MessageResult:
        """Send message with automatic retry on rate limits.

        Args:
            receive_id: User open_id.
            msg_type: Message type ("text", "post").
            content: JSON-formatted content string.

        Returns:
            MessageResult indicating success or failure.

        Raises:
            FeishuRateLimitError: If rate limit exceeded (will be retried).
            ChannelAuthError: If authentication fails.
            ChannelSendError: If message send fails.
        """
        client = self._get_client()

        request = (
            CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(receive_id)
                .msg_type(msg_type)
                .content(content)
                .build()
            )
            .build()
        )

        try:
            response: CreateMessageResponse = await client.im.v1.message.acreate(request)

            if not response.success():
                error_code = response.code
                error_msg = response.msg

                if error_code == self.RATE_LIMIT_CODE:
                    raise FeishuRateLimitError(error_code, error_msg)

                if error_code in self.AUTH_ERROR_CODES:
                    raise ChannelAuthError(
                        f"Feishu authentication failed: {error_msg}",
                        channel_id=self.channel_id,
                    )

                raise ChannelSendError(
                    f"Feishu send failed: [{error_code}] {error_msg}",
                    channel_id=self.channel_id,
                )

            return MessageResult(
                success=True,
                message_id=response.data.message_id,
                timestamp=response.data.create_time,
                raw_response=response.data,
            )

        except Exception as e:
            if isinstance(e, (FeishuRateLimitError, ChannelAuthError, ChannelSendError)):
                raise
            return MessageResult(success=False, error=str(e))

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a plain text message.

        Args:
            recipient: Recipient identifier (c2c:OPENID or plain openid).
            content: Plain text message content.

        Returns:
            MessageResult indicating success or failure.
        """
        info = parse_recipient(recipient)
        text_content = json.dumps({"text": content})

        try:
            return await self._send_message(info.openid, "text", text_content)
        except (FeishuRateLimitError, ChannelAuthError, ChannelSendError) as e:
            return MessageResult(success=False, error=str(e))

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send a markdown-formatted message.

        Feishu uses "post" msg_type for rich text. Falls back to plain text
        if markdown is not supported.

        Args:
            recipient: Recipient identifier.
            content: Markdown-formatted message content.

        Returns:
            MessageResult indicating success or failure.
        """
        info = parse_recipient(recipient)
        post_content = json.dumps({
            "zh_cn": {
                "title": "",
                "content": [[{"tag": "text", "text": content}]],
            }
        })

        try:
            return await self._send_message(info.openid, "post", post_content)
        except ChannelSendError as e:
            if "50056" in str(e) or "not support" in str(e).lower():
                return await self.send_text(recipient, content)
            return MessageResult(success=False, error=str(e))
        except (FeishuRateLimitError, ChannelAuthError) as e:
            return MessageResult(success=False, error=str(e))

    @property
    def supports_capture(self) -> bool:
        return True

    async def capture_openid(self, timeout: int = 300) -> str:
        """Capture user openid via Feishu WebSocket.

        Args:
            timeout: Timeout in seconds (default: 300).

        Returns:
            Captured open_id string (starts with "ou_").

        Raises:
            ChannelConfigError: If app_id or app_secret is not configured.
            ChannelError: If capture times out or connection fails.
        """
        self._validate_config()

        from claw_cron.feishu.events import parse_feishu_message

        captured_openid: str | None = None

        def on_message_received(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
            nonlocal captured_openid
            event_data = {
                "sender": {"sender_id": {"open_id": data.event.sender.sender_id.open_id}},
                "message": {
                    "content": data.event.message.content,
                    "message_id": data.event.message.message_id,
                    "chat_id": data.event.message.chat_id,
                    "create_time": data.event.message.create_time,
                },
            }
            message = parse_feishu_message(event_data)
            captured_openid = message.openid

        event_handler = (
            lark.EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(on_message_received)
            .build()
        )
        ws_client = lark.ws.Client(
            self.config.app_id,
            self.config.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.ERROR,
        )

        async def _wait_for_capture() -> None:
            while not captured_openid:
                await asyncio.sleep(0.1)

        async def _do_capture() -> str:
            await asyncio.gather(ws_client.start(), _wait_for_capture())
            return captured_openid  # type: ignore[return-value]

        try:
            return await asyncio.wait_for(_do_capture(), timeout=timeout)
        except asyncio.TimeoutError:
            raise ChannelError(
                f"Capture timed out after {timeout}s", channel_id=self.channel_id
            )

    async def close(self) -> None:
        """Close the SDK client."""
        self._client = None
