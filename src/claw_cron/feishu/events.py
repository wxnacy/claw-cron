# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Feishu event types and parsing utilities.

This module defines event types received from Feishu WebSocket
and provides parsing functions for different event types.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class FeishuMessage:
    """Feishu private chat message event data.

    Attributes:
        openid: Bot-specific user OpenID (starts with "ou_").
        content: Message text content.
        message_id: Platform message ID.
        chat_id: Chat ID.
        timestamp: Message timestamp.
    """

    openid: str
    content: str
    message_id: str
    chat_id: str
    timestamp: datetime


def parse_feishu_message(event_data: dict) -> FeishuMessage:
    """Parse im.message.receive_v1 event data.

    Args:
        event_data: Raw event from lark.ws.Client handler.

    Returns:
        Parsed FeishuMessage instance.

    Raises:
        KeyError: If required fields are missing.

    Event structure (from Feishu API docs):
        {
            "sender": {
                "sender_id": {
                    "open_id": "ou_xxx"
                }
            },
            "message": {
                "content": "...",
                "message_id": "...",
                "chat_id": "...",
                "create_time": "..."
            }
        }
    """
    sender_id = event_data["sender"]["sender_id"]
    message = event_data["message"]

    return FeishuMessage(
        openid=sender_id["open_id"],
        content=message.get("content", ""),
        message_id=message["message_id"],
        chat_id=message["chat_id"],
        timestamp=datetime.fromtimestamp(int(message["create_time"]) / 1000),
    )
