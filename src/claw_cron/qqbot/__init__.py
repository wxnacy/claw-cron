# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""QQ Bot WebSocket client for message event handling.

This module provides WebSocket connectivity to QQ Bot Gateway
for receiving message events and capturing user OpenIDs.
"""

from __future__ import annotations

from .events import C2CMessage, EventType, OpCode, parse_c2c_message
from .websocket import GatewayConfig, QQBotWebSocket

__all__ = [
    "GatewayConfig",
    "QQBotWebSocket",
    "C2CMessage",
    "OpCode",
    "EventType",
    "parse_c2c_message",
]
