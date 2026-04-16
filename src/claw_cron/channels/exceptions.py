# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Exception hierarchy for message channels."""

from __future__ import annotations


class ChannelError(Exception):
    """Base exception for all channel-related errors."""

    def __init__(self, message: str, channel_id: str | None = None) -> None:
        self.channel_id = channel_id
        super().__init__(message)


class ChannelAuthError(ChannelError):
    """Authentication failure (invalid credentials, expired token)."""

    pass


class ChannelSendError(ChannelError):
    """Message send failure (network error, rate limit, invalid recipient)."""

    def __init__(
        self,
        message: str,
        channel_id: str | None = None,
        recipient: str | None = None,
    ) -> None:
        self.recipient = recipient
        super().__init__(message, channel_id)


class ChannelConfigError(ChannelError):
    """Configuration error (missing required fields, invalid format)."""

    pass


class ChannelNotAvailableError(ChannelError):
    """Channel not available on this platform (e.g., iMessage on Linux)."""

    pass
