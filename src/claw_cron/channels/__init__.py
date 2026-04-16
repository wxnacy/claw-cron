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

# Will be populated after base.py is created
__all__: list[str] = []

# Channel registry - populated by channel implementations
CHANNEL_REGISTRY: dict[str, type] = {}
