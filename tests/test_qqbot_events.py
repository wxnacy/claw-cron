# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Unit tests for QQ Bot event parsing."""

from datetime import datetime

import pytest

from claw_cron.qqbot.events import C2CMessage, EventType, OpCode, parse_c2c_message


class TestOpCode:
    """Tests for OpCode enum."""

    def test_opcodes_have_expected_values(self) -> None:
        """OpCode values match QQ Bot Gateway protocol."""
        assert OpCode.DISPATCH.value == 0
        assert OpCode.HEARTBEAT.value == 1
        assert OpCode.IDENTIFY.value == 2
        assert OpCode.HELLO.value == 10
        assert OpCode.HEARTBEAT_ACK.value == 11
        assert OpCode.RESUME.value == 6


class TestEventType:
    """Tests for EventType enum."""

    def test_event_types_match_gateway_names(self) -> None:
        """EventType values match QQ Bot Gateway event names."""
        assert EventType.READY.value == "READY"
        assert EventType.C2C_MESSAGE_CREATE.value == "C2C_MESSAGE_CREATE"


class TestC2CMessage:
    """Tests for C2CMessage dataclass."""

    def test_dataclass_has_all_fields(self) -> None:
        """C2CMessage has all required fields."""
        message = C2CMessage(
            openid="ABC123",
            union_openid=None,
            content="hello",
            message_id="msg_001",
            timestamp=datetime.now(),
        )
        assert message.openid == "ABC123"
        assert message.content == "hello"


class TestParseC2CMessage:
    """Tests for parse_c2c_message function."""

    def test_extracts_openid_from_valid_event(self) -> None:
        """parse_c2c_message extracts openid from valid event data."""
        event_data = {
            "author": {
                "user_openid": "E4F4AEA33253A2797FB897C50B81D7ED",
            },
            "content": "hello world",
            "id": "ROBOT1.0_.b6nx.CVryAO0nR58RXuU6SC",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        result = parse_c2c_message(event_data)

        assert result.openid == "E4F4AEA33253A2797FB897C50B81D7ED"
        assert result.content == "hello world"
        assert result.message_id == "ROBOT1.0_.b6nx.CVryAO0nR58RXuU6SC"

    def test_handles_missing_optional_fields(self) -> None:
        """parse_c2c_message handles missing optional fields gracefully."""
        event_data = {
            "author": {
                "user_openid": "ABC123",
            },
            "id": "msg_001",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        result = parse_c2c_message(event_data)

        assert result.openid == "ABC123"
        assert result.content == ""  # Default for missing content
        assert result.union_openid is None

    def test_raises_key_error_for_missing_author(self) -> None:
        """parse_c2c_message raises KeyError if author is missing."""
        event_data = {
            "content": "hello",
            "id": "msg_001",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        with pytest.raises(KeyError):
            parse_c2c_message(event_data)

    def test_raises_key_error_for_missing_user_openid(self) -> None:
        """parse_c2c_message raises KeyError if user_openid is missing."""
        event_data = {
            "author": {},  # Missing user_openid
            "content": "hello",
            "id": "msg_001",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        with pytest.raises(KeyError):
            parse_c2c_message(event_data)

    def test_raises_key_error_for_missing_id(self) -> None:
        """parse_c2c_message raises KeyError if id is missing."""
        event_data = {
            "author": {
                "user_openid": "ABC123",
            },
            "content": "hello",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        with pytest.raises(KeyError):
            parse_c2c_message(event_data)

    def test_parses_timestamp_correctly(self) -> None:
        """parse_c2c_message parses ISO timestamp correctly."""
        event_data = {
            "author": {
                "user_openid": "ABC123",
            },
            "id": "msg_001",
            "timestamp": "2023-11-06T13:37:18+08:00",
        }

        result = parse_c2c_message(event_data)

        assert isinstance(result.timestamp, datetime)
        assert result.timestamp.year == 2023
        assert result.timestamp.month == 11
        assert result.timestamp.day == 6
