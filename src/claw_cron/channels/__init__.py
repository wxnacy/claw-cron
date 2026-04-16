# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Message channel abstraction layer for claw-cron.

This module provides a unified interface for multiple messaging channels
(iMessage, QQ, Telegram, etc.). The channel pattern follows the provider
pattern established in Phase 5.

Channel Pattern:
    - MessageChannel: Abstract base class defining the interface
    - IMessageChannel: iMessage implementation (Plan 02)
    - QQBotChannel: QQ Bot implementation (Phase 7)
    - ChannelConfig: Configuration base class
    - MessageResult: Standardized send result

Usage:
    from claw_cron.channels import get_channel, MessageResult

    channel = get_channel("imessage")
    result = await channel.send_text("+8613812345678", "Hello!")
    if result.success:
        print("Message sent!")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import (
    ChannelAuthError,
    ChannelConfigError,
    ChannelError,
    ChannelNotAvailableError,
    ChannelSendError,
)

__all__ = [
    # Base classes
    "MessageChannel",
    "ChannelConfig",
    "MessageResult",
    # Exceptions
    "ChannelError",
    "ChannelAuthError",
    "ChannelSendError",
    "ChannelConfigError",
    "ChannelNotAvailableError",
    # Factory
    "get_channel",
    "CHANNEL_REGISTRY",
    # Channel implementations
    "IMessageChannel",
    "QQBotChannel",
]


# Channel registry - populated by channel implementations
# Each channel module should add itself: CHANNEL_REGISTRY["imessage"] = IMessageChannel
CHANNEL_REGISTRY: dict[str, type[MessageChannel]] = {}


def get_channel(
    channel_id: str,
    config: ChannelConfig | None = None,
) -> MessageChannel:
    """Factory function to create channel instances.

    Args:
        channel_id: Channel identifier ('imessage', 'qq', etc.)
        config: Optional channel configuration.

    Returns:
        Channel instance implementing MessageChannel.

    Raises:
        ValueError: If channel_id is not registered.
        ChannelNotAvailableError: If channel is not available on this platform.

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("imessage")
        >>> result = await channel.send_text("+8613812345678", "Hello!")
    """
    if channel_id not in CHANNEL_REGISTRY:
        available = list(CHANNEL_REGISTRY.keys())
        raise ValueError(
            f"Unknown channel: {channel_id!r}. "
            f"Available channels: {available if available else 'none registered yet'}"
        )

    channel_class = CHANNEL_REGISTRY[channel_id]
    return channel_class(config=config)


# Import and register built-in channels
from .imessage import IMessageChannel
from .qqbot import QQBotChannel

CHANNEL_REGISTRY["imessage"] = IMessageChannel
CHANNEL_REGISTRY["qqbot"] = QQBotChannel
