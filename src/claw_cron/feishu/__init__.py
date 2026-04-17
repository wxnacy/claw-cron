# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Feishu WebSocket client for message event handling.

This module provides WebSocket connectivity to Feishu Gateway
for receiving message events and capturing user OpenIDs.
"""

from __future__ import annotations

from .events import FeishuMessage, parse_feishu_message

__all__ = [
    "FeishuMessage",
    "parse_feishu_message",
]
