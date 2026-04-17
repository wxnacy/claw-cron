# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
# SPDX-License-Identifier: MIT
"""Unit tests for channel boundary conditions."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claw_cron.channels import CHANNEL_REGISTRY
from claw_cron.channels.exceptions import ChannelConfigError, ChannelError
from claw_cron.channels.wecom import TokenInfo, WeComChannel, WeComConfig, WeComRateLimitError


class TestSupportsCapture:
    """Verify supports_capture property for each channel."""

    def test_imessage_does_not_support_capture(self) -> None:
        assert CHANNEL_REGISTRY["imessage"]().supports_capture is False

    def test_email_does_not_support_capture(self) -> None:
        assert CHANNEL_REGISTRY["email"]().supports_capture is False

    def test_qqbot_supports_capture(self) -> None:
        assert CHANNEL_REGISTRY["qqbot"]().supports_capture is True

    def test_feishu_supports_capture(self) -> None:
        assert CHANNEL_REGISTRY["feishu"]().supports_capture is True

    def test_wecom_supports_capture(self) -> None:
        assert WeComChannel().supports_capture is True


class TestCaptureUnsupportedChannel:
    """Channels without capture support must raise NotImplementedError."""

    @pytest.mark.asyncio
    async def test_imessage_capture_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="imessage"):
            await CHANNEL_REGISTRY["imessage"]().capture_openid()

    @pytest.mark.asyncio
    async def test_email_capture_raises(self) -> None:
        with pytest.raises(NotImplementedError, match="email"):
            await CHANNEL_REGISTRY["email"]().capture_openid()


class TestTokenInfo:
    """Verify TokenInfo expiry logic without mocks."""

    def test_token_not_expired_when_fresh(self) -> None:
        token = TokenInfo(access_token="t", expires_at=time.time() + 3600)
        assert token.is_expired() is False

    def test_token_expired_when_past_expiry(self) -> None:
        token = TokenInfo(access_token="t", expires_at=time.time() - 1)
        assert token.is_expired() is True

    def test_token_expired_within_buffer(self) -> None:
        # 30s remaining < 60s buffer → expired
        token = TokenInfo(access_token="t", expires_at=time.time() + 30, buffer_seconds=60)
        assert token.is_expired() is True


class TestWeComConfigValidation:
    """Missing config fields must raise ChannelConfigError."""

    @pytest.mark.asyncio
    async def test_missing_corp_id_raises(self) -> None:
        ch = WeComChannel(WeComConfig(agent_id=1, secret="s"))
        with pytest.raises(ChannelConfigError):
            await ch._get_access_token()

    @pytest.mark.asyncio
    async def test_missing_secret_raises(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1))
        with pytest.raises(ChannelConfigError):
            await ch._get_access_token()


class TestWeComTokenCaching:
    """Verify token is cached and refreshed correctly."""

    @pytest.mark.asyncio
    async def test_token_cached_when_valid(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "access_token": "tok1", "expires_in": 7200}
        ch._http_client.get = AsyncMock(return_value=mock_response)

        result1 = await ch._get_access_token()
        result2 = await ch._get_access_token()

        assert result1 == "tok1"
        assert result2 == "tok1"
        ch._http_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_refreshed_when_expired(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._token = TokenInfo(access_token="old", expires_at=time.time() - 1)
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "access_token": "new", "expires_in": 7200}
        ch._http_client.get = AsyncMock(return_value=mock_response)

        result = await ch._get_access_token()
        assert result == "new"


class TestWeComSendText:
    """Verify text message sending behavior."""

    @pytest.mark.asyncio
    async def test_send_text_success(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._get_access_token = AsyncMock(return_value="token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        ch._http_client.post = AsyncMock(return_value=mock_response)

        result = await ch.send_text("userid123", "hello")

        assert result.success is True
        call_kwargs = ch._http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["touser"] == "userid123"
        assert payload["msgtype"] == "text"

    @pytest.mark.asyncio
    async def test_send_text_strips_prefix(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._get_access_token = AsyncMock(return_value="token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        ch._http_client.post = AsyncMock(return_value=mock_response)

        await ch.send_text("c2c:userid123", "hello")

        call_kwargs = ch._http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["touser"] == "userid123"

    @pytest.mark.asyncio
    async def test_send_text_rate_limit_retries(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._get_access_token = AsyncMock(return_value="token")
        rate_limit_resp = MagicMock()
        rate_limit_resp.json.return_value = {"errcode": 45009, "errmsg": "rate limit"}
        success_resp = MagicMock()
        success_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        ch._http_client.post = AsyncMock(
            side_effect=[rate_limit_resp, rate_limit_resp, success_resp]
        )

        result = await ch.send_text("userid123", "hello")
        assert result.success is True


class TestWeComSendMarkdown:
    """Verify markdown message sending and fallback behavior."""

    @pytest.mark.asyncio
    async def test_send_markdown_success(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._get_access_token = AsyncMock(return_value="token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        ch._http_client.post = AsyncMock(return_value=mock_response)

        result = await ch.send_markdown("userid123", "**hello**")

        assert result.success is True
        call_kwargs = ch._http_client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert payload["msgtype"] == "markdown"

    @pytest.mark.asyncio
    async def test_send_markdown_fallback_to_text(self) -> None:
        ch = WeComChannel(WeComConfig(corp_id="c", agent_id=1, secret="s"))
        ch._get_access_token = AsyncMock(return_value="token")
        not_support_resp = MagicMock()
        not_support_resp.json.return_value = {"errcode": 50001, "errmsg": "not support markdown"}
        success_resp = MagicMock()
        success_resp.json.return_value = {"errcode": 0, "errmsg": "ok"}
        ch._http_client.post = AsyncMock(side_effect=[not_support_resp, success_resp])

        result = await ch.send_markdown("userid123", "**hello**")

        assert result.success is True
        # Second call should be text fallback
        second_call_kwargs = ch._http_client.post.call_args_list[1]
        payload = second_call_kwargs.kwargs.get("json") or second_call_kwargs[1].get("json")
        assert payload["msgtype"] == "text"
