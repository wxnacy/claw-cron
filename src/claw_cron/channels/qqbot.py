# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""QQ Bot channel implementation for claw-cron.

This module implements the QQ Bot API integration following the MessageChannel
interface. It supports:
- OAuth2 authentication with automatic token refresh
- C2C private chat messages (c2c:OPENID format)
- Group chat messages (group:GROUP_OPENID format)
- Markdown messages (with fallback to plain text)

Environment Variables:
    CLAW_CRON_QQBOT_APP_ID: QQ Bot App ID from q.qq.com
    CLAW_CRON_QQBOT_CLIENT_SECRET: QQ Bot Client Secret from q.qq.com

Recipient Formats:
    - "c2c:OPENID" - Private chat with user (bot-specific openid)
    - "group:GROUP_OPENID" - Group chat (bot-specific group openid)
    - Plain string - Treated as C2C openid for backward compatibility

Note:
    OpenIDs are unique per bot (AppID). You must receive a message from the user
    or group first (via WebSocket events) to obtain their openid.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelAuthError, ChannelConfigError, ChannelSendError


# =============================================================================
# Configuration
# =============================================================================


class QQBotConfig(BaseSettings, ChannelConfig):
    """Configuration for QQ Bot channel.

    Environment variables use CLAW_CRON_QQBOT_ prefix:
        - CLAW_CRON_QQBOT_APP_ID: QQ Bot App ID
        - CLAW_CRON_QQBOT_CLIENT_SECRET: QQ Bot Client Secret

    Attributes:
        app_id: QQ Bot App ID from open platform (q.qq.com).
        client_secret: QQ Bot Client Secret from open platform.
    """

    app_id: str | None = Field(
        default=None, description="QQ Bot App ID from q.qq.com"
    )
    client_secret: str | None = Field(
        default=None, description="QQ Bot Client Secret from q.qq.com"
    )

    class Config:
        env_prefix = "CLAW_CRON_QQBOT_"
        env_file = ".env"
        extra = "ignore"


# =============================================================================
# Token Management
# =============================================================================


@dataclass
class TokenInfo:
    """Cached token information for QQ Bot API.

    Attributes:
        access_token: OAuth2 access token.
        expires_at: Unix timestamp when token expires.
        buffer_seconds: Seconds before expiration to refresh token.
    """

    access_token: str
    expires_at: float  # Unix timestamp
    buffer_seconds: int = 60  # Refresh 60s before expiration

    def is_expired(self) -> bool:
        """Check if token is expired or near expiration.

        Returns:
            True if token should be refreshed.
        """
        return time.time() >= (self.expires_at - self.buffer_seconds)


# =============================================================================
# Recipient Parsing
# =============================================================================


class RecipientType(Enum):
    """Type of message recipient."""

    C2C = "c2c"  # Private chat
    GROUP = "group"  # Group chat


@dataclass
class RecipientInfo:
    """Parsed recipient information.

    Attributes:
        type: Recipient type (C2C or GROUP).
        openid: Bot-specific user or group openid.
    """

    type: RecipientType
    openid: str


def parse_recipient(recipient: str) -> RecipientInfo:
    """Parse recipient string to determine type and openid.

    Formats:
        - "c2c:OPENID" -> Private chat with user
        - "group:GROUP_OPENID" -> Group chat
        - Plain openid string -> Treat as C2C (backward compatibility)

    Args:
        recipient: Recipient identifier string.

    Returns:
        RecipientInfo with type and openid.

    Raises:
        ValueError: If format is invalid.

    Example:
        >>> parse_recipient("c2c:ABC123")
        RecipientInfo(type=RecipientType.C2C, openid='ABC123')
        >>> parse_recipient("group:XYZ789")
        RecipientInfo(type=RecipientType.GROUP, openid='XYZ789')
    """
    if ":" in recipient:
        parts = recipient.split(":", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError(f"Invalid recipient format: {recipient}")

        type_str, openid = parts
        if type_str == "c2c":
            return RecipientInfo(type=RecipientType.C2C, openid=openid)
        elif type_str == "group":
            return RecipientInfo(type=RecipientType.GROUP, openid=openid)
        else:
            raise ValueError(f"Unknown recipient type: {type_str}")
    else:
        # Treat plain string as C2C openid
        return RecipientInfo(type=RecipientType.C2C, openid=recipient)


# =============================================================================
# API Errors
# =============================================================================


class QQBotAPIError(Exception):
    """QQ Bot API error with code and message.

    Attributes:
        code: QQ Bot API error code.
        message: Error message.
    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class QQBotRateLimitError(QQBotAPIError):
    """Rate limit error that can be retried."""

    pass


# =============================================================================
# QQ Bot Channel
# =============================================================================


class QQBotChannel(MessageChannel):
    """QQ Bot channel implementation.

    This channel sends messages through QQ Bot API. It supports:
    - OAuth2 authentication with automatic token refresh
    - C2C private chat messages
    - Group chat messages
    - Markdown messages (with fallback to plain text)

    Attributes:
        config: QQ Bot configuration.
        _token: Cached OAuth2 token.
        _http_client: Async HTTP client for API calls.

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("qqbot")
        >>> result = await channel.send_text("c2c:ABC123", "Hello!")
        >>> if result.success:
        ...     print(f"Message sent: {result.message_id}")
    """

    # Rate limit error codes that should be retried
    RATE_LIMIT_CODES = frozenset({22009, 20028, 304045, 304046, 304047, 304048, 304049, 304050})
    # Auth error codes that should NOT be retried
    AUTH_ERROR_CODES = frozenset({11241, 11242, 11243, 11251, 11261})
    # Markdown not allowed error code
    MARKDOWN_NOT_ALLOWED_CODE = 50056

    def __init__(self, config: QQBotConfig | None = None) -> None:
        """Initialize QQ Bot channel.

        Args:
            config: QQ Bot configuration. Uses defaults if not provided.
        """
        super().__init__(config or QQBotConfig())
        self._token: TokenInfo | None = None
        self._http_client = httpx.AsyncClient(
            base_url="https://api.sgroup.qq.com",
            timeout=30.0,
        )

    @property
    def channel_id(self) -> str:
        """Return unique channel identifier.

        Returns:
            "qqbot" identifier.
        """
        return "qqbot"

    def _validate_config(self) -> None:
        """Validate configuration has required fields.

        Raises:
            ChannelConfigError: If app_id or client_secret is missing.
        """
        if not self.config.app_id:
            raise ChannelConfigError(
                "QQ Bot app_id is required. Set CLAW_CRON_QQBOT_APP_ID environment variable.",
                channel_id=self.channel_id,
            )
        if not self.config.client_secret:
            raise ChannelConfigError(
                "QQ Bot client_secret is required. Set CLAW_CRON_QQBOT_CLIENT_SECRET environment variable.",
                channel_id=self.channel_id,
            )

    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            ChannelConfigError: If credentials are not configured.
            ChannelAuthError: If authentication fails.
        """
        self._validate_config()

        # Return cached token if still valid
        if self._token and not self._token.is_expired():
            return self._token.access_token

        # Fetch new token from QQ Bot API
        try:
            response = await self._http_client.post(
                "https://bots.qq.com/app/getAppAccessToken",
                json={
                    "appId": self.config.app_id,
                    "clientSecret": self.config.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Check for API error
            if "code" in data and data["code"] != 0:
                raise ChannelAuthError(
                    f"QQ Bot authentication failed: {data.get('message', 'Unknown error')}",
                    channel_id=self.channel_id,
                )

            # Cache the new token
            self._token = TokenInfo(
                access_token=data["access_token"],
                expires_at=time.time() + int(data.get("expires_in", 7200)),
            )
            return self._token.access_token

        except httpx.HTTPStatusError as e:
            raise ChannelAuthError(
                f"QQ Bot authentication failed: HTTP {e.response.status_code}",
                channel_id=self.channel_id,
            ) from e
        except httpx.RequestError as e:
            raise ChannelAuthError(
                f"QQ Bot authentication failed: {e}",
                channel_id=self.channel_id,
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(QQBotRateLimitError),
        reraise=True,
    )
    async def _send_with_retry(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send message with automatic retry on rate limits.

        Args:
            endpoint: API endpoint path.
            payload: Message payload.

        Returns:
            API response data.

        Raises:
            QQBotRateLimitError: If rate limit is exceeded (will be retried).
            ChannelAuthError: If authentication fails.
            ChannelSendError: If message send fails.
        """
        token = await self._get_access_token()

        try:
            response = await self._http_client.post(
                endpoint,
                json=payload,
                headers={"Authorization": f"QQBot {token}"},
            )

            data = response.json()

            # Check for business errors in response
            if "code" in data and data["code"] != 0:
                error_code = data["code"]
                error_message = data.get("message", "Unknown error")

                # Rate limit errors - retry
                if error_code in self.RATE_LIMIT_CODES:
                    raise QQBotRateLimitError(error_code, error_message)

                # Auth errors - do not retry
                if error_code in self.AUTH_ERROR_CODES:
                    raise ChannelAuthError(
                        f"QQ Bot authentication failed: {error_message}",
                        channel_id=self.channel_id,
                    )

                # Other errors
                raise ChannelSendError(
                    f"QQ Bot send failed: [{error_code}] {error_message}",
                    channel_id=self.channel_id,
                )

            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise QQBotRateLimitError(429, "Rate limit exceeded")
            if e.response.status_code >= 500:
                raise QQBotRateLimitError(e.response.status_code, f"Server error: {e.response.status_code}")
            raise ChannelSendError(
                f"QQ Bot send failed: HTTP {e.response.status_code}",
                channel_id=self.channel_id,
            ) from e
        except httpx.RequestError as e:
            raise ChannelSendError(
                f"QQ Bot send failed: {e}",
                channel_id=self.channel_id,
            ) from e

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a plain text message.

        Args:
            recipient: Recipient identifier (c2c:OPENID, group:GROUP_OPENID, or plain openid).
            content: Plain text message content.

        Returns:
            MessageResult indicating success or failure.

        Example:
            >>> result = await channel.send_text("c2c:ABC123", "Hello!")
        """
        info = parse_recipient(recipient)

        # Determine endpoint based on recipient type
        if info.type == RecipientType.C2C:
            endpoint = f"/v2/users/{info.openid}/messages"
        else:
            endpoint = f"/v2/groups/{info.openid}/messages"

        payload = {"content": content, "msg_type": 0}

        try:
            data = await self._send_with_retry(endpoint, payload)
            return MessageResult(
                success=True,
                message_id=data.get("id"),
                timestamp=data.get("timestamp"),
                raw_response=data,
            )
        except (QQBotRateLimitError, ChannelAuthError, ChannelSendError) as e:
            return MessageResult(
                success=False,
                error=str(e),
            )

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send a markdown-formatted message.

        Note:
            Markdown messages (msg_type=2) require internal invitation for production
            environments. Sandbox environments allow free testing. If markdown fails
            with error 50056, this method falls back to plain text.

        Args:
            recipient: Recipient identifier.
            content: Markdown-formatted message content.

        Returns:
            MessageResult indicating success or failure.
        """
        info = parse_recipient(recipient)

        # Determine endpoint
        if info.type == RecipientType.C2C:
            endpoint = f"/v2/users/{info.openid}/messages"
        else:
            endpoint = f"/v2/groups/{info.openid}/messages"

        # Try markdown first
        payload = {"msg_type": 2, "markdown": {"content": content}}

        try:
            data = await self._send_with_retry(endpoint, payload)
            return MessageResult(
                success=True,
                message_id=data.get("id"),
                timestamp=data.get("timestamp"),
                raw_response=data,
            )
        except ChannelSendError as e:
            # Check for markdown not allowed error - fallback to plain text
            if self.MARKDOWN_NOT_ALLOWED_CODE in str(e):
                # Retry with plain text
                payload = {"content": content, "msg_type": 0}
                try:
                    data = await self._send_with_retry(endpoint, payload)
                    return MessageResult(
                        success=True,
                        message_id=data.get("id"),
                        timestamp=data.get("timestamp"),
                        raw_response={"markdown_fallback": True, **data},
                    )
                except (QQBotRateLimitError, ChannelSendError) as fallback_e:
                    return MessageResult(success=False, error=str(fallback_e))
            return MessageResult(success=False, error=str(e))
        except (QQBotRateLimitError, ChannelAuthError) as e:
            return MessageResult(success=False, error=str(e))

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self._http_client.aclose()
