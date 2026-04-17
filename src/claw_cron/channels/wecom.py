# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""WeChat Work (企业微信) channel implementation for claw-cron."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelConfigError, ChannelError, ChannelSendError


class WeComConfig(BaseSettings, ChannelConfig):
    """Configuration for WeChat Work channel."""

    corp_id: str | None = Field(default=None)
    agent_id: int | None = Field(default=None)
    secret: str | None = Field(default=None)

    class Config:
        env_prefix = "CLAW_CRON_WECOM_"
        env_file = ".env"
        extra = "ignore"


@dataclass
class TokenInfo:
    """Cached access token."""

    access_token: str
    expires_at: float
    buffer_seconds: int = 60

    def is_expired(self) -> bool:
        return time.time() >= (self.expires_at - self.buffer_seconds)


class WeComAPIError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class WeComRateLimitError(WeComAPIError):
    pass


class WeComChannel(MessageChannel):
    """WeChat Work application message channel."""

    def __init__(self, config: WeComConfig | dict | None = None) -> None:
        if config is None:
            config_obj = WeComConfig()
        elif isinstance(config, dict):
            config_obj = WeComConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)
        self._token: TokenInfo | None = None
        self._http_client = httpx.AsyncClient(timeout=30.0)

    @property
    def channel_id(self) -> str:
        return "wecom"

    def _validate_config(self) -> None:
        if not self.config.corp_id or not self.config.agent_id or not self.config.secret:
            raise ChannelConfigError(
                "WeChat Work requires corp_id, agent_id, and secret.",
                channel_id=self.channel_id,
            )

    async def _get_access_token(self) -> str:
        self._validate_config()
        if self._token and not self._token.is_expired():
            return self._token.access_token
        try:
            response = await self._http_client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": self.config.corp_id, "corpsecret": self.config.secret},
            )
            data = response.json()
            if data.get("errcode", 0) != 0:
                raise ChannelConfigError(
                    f"WeChat Work token error: {data.get('errmsg')} (errcode={data.get('errcode')})",
                    channel_id=self.channel_id,
                )
            self._token = TokenInfo(
                access_token=data["access_token"],
                expires_at=time.time() + int(data.get("expires_in", 7200)),
            )
            return self._token.access_token
        except httpx.RequestError as e:
            raise ChannelConfigError(f"WeChat Work token request failed: {e}", channel_id=self.channel_id) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(WeComRateLimitError),
        reraise=True,
    )
    async def _send_with_retry(self, payload: dict) -> dict:
        token = await self._get_access_token()
        try:
            response = await self._http_client.post(
                "https://qyapi.weixin.qq.com/cgi-bin/message/send",
                params={"access_token": token},
                json=payload,
            )
            data = response.json()
            errcode = data.get("errcode", 0)
            if errcode == 0:
                return data
            if errcode == 45009:
                raise WeComRateLimitError(errcode, data.get("errmsg", "rate limit"))
            raise ChannelSendError(
                f"WeChat Work send failed: {data.get('errmsg')} (errcode={errcode})",
                channel_id=self.channel_id,
            )
        except httpx.RequestError as e:
            raise ChannelSendError(f"WeChat Work request failed: {e}", channel_id=self.channel_id) from e

    def _parse_userid(self, recipient: str) -> str:
        return recipient.split(":", 1)[1] if ":" in recipient else recipient

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        userid = self._parse_userid(recipient)
        payload = {
            "touser": userid,
            "msgtype": "text",
            "agentid": self.config.agent_id,
            "text": {"content": content},
        }
        try:
            data = await self._send_with_retry(payload)
            return MessageResult(success=True, raw_response=data)
        except (WeComRateLimitError, ChannelSendError) as e:
            return MessageResult(success=False, error=str(e))

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        userid = self._parse_userid(recipient)
        payload = {
            "touser": userid,
            "msgtype": "markdown",
            "agentid": self.config.agent_id,
            "markdown": {"content": content},
        }
        try:
            data = await self._send_with_retry(payload)
            return MessageResult(success=True, raw_response=data)
        except ChannelSendError as e:
            err_str = str(e)
            if any(code in err_str for code in ("50001", "50002", "50003")) or "not support" in err_str.lower():
                return await self.send_text(recipient, content)
            return MessageResult(success=False, error=err_str)
        except WeComRateLimitError as e:
            return MessageResult(success=False, error=str(e))

    @property
    def supports_capture(self) -> bool:
        return True

    async def capture_openid(self, timeout: int = 300) -> str:
        print("请输入你的企业微信 userid")
        print("（可在企业微信管理后台 → 通讯录 中查看）")
        userid = input("UserID: ").strip()
        if not userid:
            raise ChannelError("userid 不能为空", channel_id=self.channel_id)
        return userid

    async def close(self) -> None:
        await self._http_client.aclose()
