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
    "get_channel_status",
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


def get_channel_status(channel_id: str) -> tuple[str, str]:
    """Check channel configuration status.

    Returns tuple of (status_icon, status_text) where:
        - "✓", "已配置" — Complete config in config.yaml
        - "⚠", "配置不完整" — Missing required fields
        - "○", "未配置" — No config entry

    Args:
        channel_id: Channel identifier to check.

    Returns:
        Tuple of (icon, text) for display.

    Example:
        >>> icon, text = get_channel_status("qqbot")
        >>> print(f"{icon} {text}")
        ✓ 已配置
    """
    from claw_cron.config import load_config

    config = load_config()
    channels_config = config.get("channels", {})

    # Check if channel has any config
    if channel_id not in channels_config:
        return "○", "未配置"

    channel_cfg = channels_config[channel_id]

    # Check for required fields (app_id/client_secret for qqbot, enabled for all)
    # For now, check if config dict is non-empty and has 'enabled' key
    if not channel_cfg or "enabled" not in channel_cfg:
        return "⚠", "配置不完整"

    # Channel-specific validation
    if channel_id == "qqbot":
        if "app_id" not in channel_cfg or "client_secret" not in channel_cfg:
            return "⚠", "配置不完整"
    elif channel_id == "imessage":
        # iMessage doesn't require credentials, just enabled flag
        pass

    return "✓", "已配置"


# Import and register built-in channels
from .imessage import IMessageChannel
from .qqbot import QQBotChannel

CHANNEL_REGISTRY["imessage"] = IMessageChannel
CHANNEL_REGISTRY["qqbot"] = QQBotChannel
