# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""QQ Bot event types and parsing utilities.

This module defines event types received from QQ Bot Gateway
and provides parsing functions for different event types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OpCode(Enum):
    """QQ Bot Gateway opcode types."""

    DISPATCH = 0           # Event dispatch
    HEARTBEAT = 1          # Heartbeat
    IDENTIFY = 2           # Authentication
    HELLO = 10             # Server hello
    HEARTBEAT_ACK = 11     # Heartbeat ACK
    RESUME = 6             # Resume session


class EventType(Enum):
    """QQ Bot event types."""

    READY = "READY"
    RESUMED = "RESUMED"
    C2C_MESSAGE_CREATE = "C2C_MESSAGE_CREATE"
    GROUP_AT_MESSAGE_CREATE = "GROUP_AT_MESSAGE_CREATE"


@dataclass
class C2CMessage:
    """C2C (private chat) message event data.

    Attributes:
        openid: Bot-specific user OpenID.
        union_openid: Cross-bot user identifier (optional).
        content: Message text content.
        message_id: Platform message ID.
        timestamp: Message timestamp.
    """

    openid: str
    union_openid: str | None
    content: str
    message_id: str
    timestamp: datetime


def parse_c2c_message(event_data: dict) -> C2CMessage:
    """Parse C2C_MESSAGE_CREATE event data.

    Args:
        event_data: Raw event data from Gateway.

    Returns:
        Parsed C2CMessage instance.

    Raises:
        KeyError: If required fields are missing.

    Event structure (from QQ Bot API docs):
        {
            "author": {
                "user_openid": "E4F4AEA33253A2797FB897C50B81D7ED",
                "union_openid": "..."  // optional
            },
            "content": "hello",
            "id": "ROBOT1.0_.b6nx.CVryAO0nR58RXuU6SC...",
            "timestamp": "2023-11-06T13:37:18+08:00"
        }
    """
    author = event_data["author"]
    return C2CMessage(
        openid=author["user_openid"],
        union_openid=author.get("union_openid"),
        content=event_data.get("content", ""),
        message_id=event_data["id"],
        timestamp=datetime.fromisoformat(event_data["timestamp"]),
    )
