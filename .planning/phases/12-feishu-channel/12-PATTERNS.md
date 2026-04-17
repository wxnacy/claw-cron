# Phase 12: Feishu Channel - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 2 new files, 3 modified files
**Analogs found:** 5 / 5

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/claw_cron/channels/feishu.py` | channel | request-response | `src/claw_cron/channels/qqbot.py` | exact |
| `src/claw_cron/feishu/__init__.py` | module | — | `src/claw_cron/qqbot/__init__.py` | exact |
| `src/claw_cron/feishu/events.py` | dataclass | event-driven | `src/claw_cron/qqbot/events.py` | exact |
| `src/claw_cron/channels/__init__.py` | registry | — | (existing file to modify) | — |
| `src/claw_cron/cmd/channels.py` | controller | request-response | (existing file to modify) | — |

## Pattern Assignments

### `src/claw_cron/channels/feishu.py` (channel, request-response)

**Analog:** `src/claw_cron/channels/qqbot.py`

**Imports pattern** (lines 1-47):
```python
# SPDX-FileCopyrightText: 2026-present wxnacy <371032668@qq.com>
#
# SPDX-License-Identifier: MIT

"""Feishu channel implementation for claw-cron.

This module implements the Feishu (Lark) Bot API integration following the MessageChannel
interface. It supports:
- Automatic tenant_access_token management via lark-oapi SDK
- C2C private chat messages (c2c:OPENID format)
- Markdown messages (with fallback to plain text)

Environment Variables:
    CLAW_CRON_FEISHU_APP_ID: Feishu App ID from open.feishu.cn
    CLAW_CRON_FEISHU_APP_SECRET: Feishu App Secret from open.feishu.cn

Recipient Formats:
    - "c2c:OPENID" - Private chat with user (bot-specific openid)
    - Plain string - Treated as C2C openid for backward compatibility
"""

from __future__ import annotations

import json
from typing import Any

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    CreateMessageResponse,
)
from pydantic import Field
from pydantic_settings import BaseSettings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelAuthError, ChannelConfigError, ChannelSendError
```

**Config class pattern** (lines 54-77):
```python
class FeishuConfig(BaseSettings, ChannelConfig):
    """Configuration for Feishu channel.

    Environment variables use CLAW_CRON_FEISHU_ prefix:
        - CLAW_CRON_FEISHU_APP_ID: Feishu App ID
        - CLAW_CRON_FEISHU_APP_SECRET: Feishu App Secret

    Attributes:
        app_id: Feishu App ID from open platform (open.feishu.cn).
        app_secret: Feishu App Secret from open platform.
    """

    app_id: str | None = Field(
        default=None, description="Feishu App ID from open.feishu.cn"
    )
    app_secret: str | None = Field(
        default=None, description="Feishu App Secret from open.feishu.cn"
    )

    class Config:
        env_prefix = "CLAW_CRON_FEISHU_"
        env_file = ".env"
        extra = "ignore"
```

**Recipient parsing pattern** (lines 112-170):
```python
# Reuse the existing parse_recipient from qqbot.py
# For feishu, we only need c2c type (no group support in this phase)
from .qqbot import parse_recipient, RecipientInfo, RecipientType
```

**Rate limit error pattern** (lines 176-195):
```python
class FeishuRateLimitError(Exception):
    """Feishu rate limit error that can be retried.

    Feishu rate limit error code: 99991400
    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
```

**Channel class pattern** (lines 202-250):
```python
class FeishuChannel(MessageChannel):
    """Feishu channel implementation using lark-oapi SDK.

    This channel sends messages through Feishu Open Platform API. It supports:
    - Automatic tenant_access_token management via SDK
    - C2C private chat messages
    - Markdown messages (with fallback to plain text)

    Attributes:
        config: Feishu configuration.
        _client: lark-oapi SDK client (lazy initialization).

    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("feishu")
        >>> result = await channel.send_text("c2c:ou_xxx", "Hello!")
        >>> if result.success:
        ...     print(f"Message sent: {result.message_id}")
    """

    # Rate limit error code
    RATE_LIMIT_CODE = 99991400
    # Auth error codes
    AUTH_ERROR_CODES = frozenset({99991661, 99991662, 99991663})

    def __init__(self, config: FeishuConfig | dict | None = None) -> None:
        """Initialize Feishu channel.

        Args:
            config: Feishu configuration. Can be FeishuConfig, dict, or None.
        """
        if config is None:
            config_obj = FeishuConfig()
        elif isinstance(config, dict):
            config_obj = FeishuConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)

        # SDK client (lazy init)
        self._client: lark.Client | None = None

    @property
    def channel_id(self) -> str:
        """Return unique channel identifier."""
        return "feishu"
```

**Config validation pattern** (lines 260-276):
```python
def _validate_config(self) -> None:
    """Validate configuration has required fields.

    Raises:
        ChannelConfigError: If app_id or app_secret is missing.
    """
    if not self.config.app_id:
        raise ChannelConfigError(
            "Feishu app_id is required. Set CLAW_CRON_FEISHU_APP_ID environment variable.",
            channel_id=self.channel_id,
        )
    if not self.config.app_secret:
        raise ChannelConfigError(
            "Feishu app_secret is required. Set CLAW_CRON_FEISHU_APP_SECRET environment variable.",
            channel_id=self.channel_id,
        )
```

**SDK client initialization pattern** (lines 277-297):
```python
def _get_client(self) -> lark.Client:
    """Get or create SDK client.

    The SDK handles tenant_access_token lifecycle automatically.

    Returns:
        lark-oapi Client instance.
    """
    if self._client is None:
        self._validate_config()
        self._client = (
            lark.Client.builder()
            .app_id(self.config.app_id)
            .app_secret(self.config.app_secret)
            .log_level(lark.LogLevel.ERROR)
            .build()
        )
    return self._client
```

**Send with retry pattern** (lines 330-404):
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(FeishuRateLimitError),
    reraise=True,
)
async def _send_message(
    self,
    receive_id: str,
    msg_type: str,
    content: str,
) -> MessageResult:
    """Send message with automatic retry on rate limits.

    Args:
        receive_id: User open_id.
        msg_type: Message type ("text", "post").
        content: JSON-formatted content string.

    Returns:
        MessageResult indicating success or failure.

    Raises:
        FeishuRateLimitError: If rate limit exceeded (will be retried).
        ChannelAuthError: If authentication fails.
        ChannelSendError: If message send fails.
    """
    client = self._get_client()

    # Build request using SDK
    request = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type(msg_type)
            .content(content)
            .build()
        )
        .build()
    )

    try:
        # Use async API
        response: CreateMessageResponse = await client.im.v1.message.acreate(request)

        if not response.success():
            error_code = response.code
            error_msg = response.msg

            # Check for rate limit
            if error_code == self.RATE_LIMIT_CODE:
                raise FeishuRateLimitError(error_code, error_msg)

            # Auth errors
            if error_code in self.AUTH_ERROR_CODES:
                raise ChannelAuthError(
                    f"Feishu authentication failed: {error_msg}",
                    channel_id=self.channel_id,
                )

            # Other errors
            raise ChannelSendError(
                f"Feishu send failed: [{error_code}] {error_msg}",
                channel_id=self.channel_id,
            )

        return MessageResult(
            success=True,
            message_id=response.data.message_id,
            timestamp=response.data.create_time,
            raw_response=response.data,
        )

    except Exception as e:
        if isinstance(e, (FeishuRateLimitError, ChannelAuthError, ChannelSendError)):
            raise
        return MessageResult(success=False, error=str(e))
```

**send_text implementation** (lines 405-441):
```python
async def send_text(self, recipient: str, content: str) -> MessageResult:
    """Send a plain text message.

    Args:
        recipient: Recipient identifier (c2c:OPENID or plain openid).
        content: Plain text message content.

    Returns:
        MessageResult indicating success or failure.

    Example:
        >>> result = await channel.send_text("c2c:ou_xxx", "Hello!")
    """
    # Parse recipient format
    info = parse_recipient(recipient)

    # Build text content JSON
    text_content = json.dumps({"text": content})

    try:
        return await self._send_message(info.openid, "text", text_content)
    except (FeishuRateLimitError, ChannelAuthError, ChannelSendError) as e:
        return MessageResult(success=False, error=str(e))
```

**send_markdown implementation** (lines 442-493):
```python
async def send_markdown(self, recipient: str, content: str) -> MessageResult:
    """Send a markdown-formatted message.

    Feishu uses "post" msg_type for rich text. If markdown fails,
    falls back to plain text.

    Args:
        recipient: Recipient identifier.
        content: Markdown-formatted message content.

    Returns:
        MessageResult indicating success or failure.
    """
    info = parse_recipient(recipient)

    # Build post content (Feishu's rich text format)
    post_content = json.dumps({
        "zh_cn": {
            "title": "",
            "content": [[{"tag": "text", "text": content}]]
        }
    })

    try:
        result = await self._send_message(info.openid, "post", post_content)
        return result
    except ChannelSendError as e:
        # Fallback to plain text if markdown not supported
        if "50056" in str(e) or "not support" in str(e).lower():
            return await self.send_text(recipient, content)
        return MessageResult(success=False, error=str(e))
    except (FeishuRateLimitError, ChannelAuthError) as e:
        return MessageResult(success=False, error=str(e))
```

**close implementation** (lines 495-498):
```python
async def close(self) -> None:
    """Close the SDK client.

    lark-oapi SDK doesn't require explicit cleanup.
    """
    self._client = None
```

---

### `src/claw_cron/feishu/__init__.py` (module init)

**Analog:** `src/claw_cron/qqbot/__init__.py`

**Module init pattern** (lines 1-24):
```python
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
```

---

### `src/claw_cron/feishu/events.py` (dataclass, event-driven)

**Analog:** `src/claw_cron/qqbot/events.py`

**Imports pattern** (lines 1-17):
```python
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
```

**Event dataclass pattern** (lines 38-55):
```python
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
```

**Event parsing pattern** (lines 57-88):
```python
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
```

---

### `src/claw_cron/channels/__init__.py` (registry modification)

**Analog:** (existing file to modify)

**Registry addition pattern** (add at line 150):
```python
# Import and register built-in channels
from .feishu import FeishuChannel
from .imessage import IMessageChannel
from .qqbot import QQBotChannel

CHANNEL_REGISTRY["feishu"] = FeishuChannel
CHANNEL_REGISTRY["imessage"] = IMessageChannel
CHANNEL_REGISTRY["qqbot"] = QQBotChannel
```

**__all__ addition** (add at line 58):
```python
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
    "FeishuChannel",  # NEW
    "IMessageChannel",
    "QQBotChannel",
]
```

---

### `src/claw_cron/cmd/channels.py` (controller modification)

**Analog:** (existing file to modify)

**add() command feishu branch** (add after line 117):
```python
    elif channel_type == "feishu":
        app_id = click.prompt("App ID", type=str)
        app_secret = click.prompt("App Secret", type=str, hide_input=True)

        # Validate credentials before saving
        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                    timeout=10.0,
                )
                data = response.json()
                if data.get("code", 0) != 0:
                    raise click.ClickException(
                        f"验证失败: {data.get('message', '未知错误')}"
                    )
                console.print("[green]✓ 凭证验证成功[/green]")
            except httpx.RequestError as e:
                raise click.ClickException(f"连接失败: {e}") from e

        # Save to config.yaml
        if "channels" not in config:
            config["channels"] = {}
        config["channels"][channel_type] = {
            "app_id": app_id,
            "app_secret": app_secret,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
        }
        save_config(config)
        console.print(f"[green]✓ 通道 '{channel_type}' 配置完成[/green]")

        # Handle capture_openid flag
        if capture_openid:
            console.print("\n[bold]步骤 2: 获取用户 OpenID[/bold]\n")
            asyncio.run(_capture_feishu_openid(alias="me"))
```

**verify() command feishu branch** (add after line 278):
```python
    elif channel_type == "feishu":
        feishu_config = channels_config["feishu"]
        app_id = feishu_config.get("app_id")
        app_secret = feishu_config.get("app_secret")

        if not app_id or not app_secret:
            console.print("[red]✗ 配置不完整：缺少 app_id 或 app_secret[/red]")
            raise SystemExit(1)

        with console.status("[bold green]正在验证凭证..."):
            try:
                response = httpx.post(
                    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret},
                    timeout=10.0,
                )
                data = response.json()

                if data.get("code", 0) != 0:
                    console.print(f"[red]✗ 验证失败: {data.get('message', '未知错误')}[/red]")
                    console.print(f"[dim]错误码: {data.get('code')}[/dim]")
                    raise SystemExit(1)

                console.print("[green]✓ 凭证验证成功[/green]")
                console.print(f"[dim]App ID: {app_id}[/dim]")

                # Show token info
                access_token = data.get("tenant_access_token", "")
                if access_token:
                    console.print(f"[dim]Tenant Access Token: {access_token[:20]}...[/dim]")

            except httpx.RequestError as e:
                console.print(f"[red]✗ 连接失败: {e}[/red]")
                raise SystemExit(1)
```

**capture() command feishu support** (modify lines 283-309):
```python
@channels.command()
@click.option(
    "--channel-type",
    type=click.Choice(["qqbot", "feishu"], case_sensitive=False),
    default="qqbot",
    help="Channel to capture openid from",
)
@click.option(
    "--alias",
    prompt="Save as contact alias",
    default="me",
    help="Alias name for the captured contact",
)
def capture(channel_type: str, alias: str) -> None:
    """Connect to channel and capture user openid.

    This command starts a WebSocket connection and waits for you
    to send a message to the bot. When received, your openid is
    captured and saved as a contact alias.

    Example:
        claw-cron channels capture --channel-type feishu --alias my_friend
        # Then send any message to your Feishu Bot
    """
    if channel_type == "qqbot":
        asyncio.run(_capture_qqbot_openid(alias))
    elif channel_type == "feishu":
        asyncio.run(_capture_feishu_openid(alias))
```

**_capture_feishu_openid() function** (add after line 386):
```python
async def _capture_feishu_openid(alias: str) -> None:
    """Capture OpenID from Feishu WebSocket."""
    import lark_oapi as lark

    from claw_cron.channels.feishu import FeishuChannel
    from claw_cron.feishu.events import parse_feishu_message

    # Load config
    config = load_config()
    feishu_config = config.get("channels", {}).get("feishu", {})
    app_id = feishu_config.get("app_id")
    app_secret = feishu_config.get("app_secret")

    if not app_id or not app_secret:
        console.print("[red]Error: Feishu not configured.[/red]")
        console.print("[dim]Run 'claw-cron channels add' first.[/dim]")
        raise SystemExit(1)

    captured_openid: str | None = None

    def on_message_received(data: lark.im.v1.P2ImMessageReceiveV1) -> None:
        nonlocal captured_openid
        # Extract open_id from event
        # v2.0 event structure: data.event.sender.sender_id.open_id
        event_data = {
            "sender": {
                "sender_id": {
                    "open_id": data.event.sender.sender_id.open_id
                }
            },
            "message": {
                "content": data.event.message.content,
                "message_id": data.event.message.message_id,
                "chat_id": data.event.message.chat_id,
                "create_time": data.event.message.create_time
            }
        }
        message = parse_feishu_message(event_data)
        captured_openid = message.openid
        console.print(f"\n[green]✓ OpenID captured: [bold]{message.openid}[/bold][/green]")
        console.print(f"[dim]Message content: {message.content}[/dim]")

    # Build event handler
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(on_message_received)
        .build()
    )

    # Create WebSocket client
    ws_client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO
    )

    console.print("\n[bold]Waiting for message...[/bold]")
    console.print("[dim]Send any message to your Feishu bot to capture your openid.[/dim]")
    console.print("[dim]Press Ctrl+C to cancel.[/dim]\n")

    try:
        async def wait_for_capture() -> None:
            while not captured_openid:
                await asyncio.sleep(0.5)

        # Start WebSocket connection
        await asyncio.gather(
            ws_client.start(),  # This blocks
            wait_for_capture()
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return

    # Save contact
    if captured_openid:
        contact = Contact(
            openid=captured_openid,
            channel="feishu",
            alias=alias,
            created=datetime.now().isoformat(),
        )
        save_contact(contact)
        console.print(f"\n[green]✓ Contact saved as '[bold]{alias}[/bold]'[/green]")
        console.print(f"[dim]You can now use 'claw-cron remind --recipient {alias}'[/dim]")
```

**list_channels() feishu display** (modify lines 154-162):
```python
        # Get config display value
        channel_cfg = channels_config.get(channel_id, {})
        if channel_id == "qqbot":
            app_id = channel_cfg.get("app_id", "")
            config_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id) or "-"
        elif channel_id == "feishu":
            app_id = channel_cfg.get("app_id", "")
            config_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id) or "-"
        elif channel_id == "imessage":
            config_display = "[dim]无需凭证[/dim]"
        else:
            config_display = "-"
```

**get_channel_status() in channels/__init__.py** (modify lines 135-142):
```python
    # Channel-specific validation
    if channel_id == "qqbot":
        if "app_id" not in channel_cfg or "client_secret" not in channel_cfg:
            return "⚠", "配置不完整"
    elif channel_id == "feishu":
        if "app_id" not in channel_cfg or "app_secret" not in channel_cfg:
            return "⚠", "配置不完整"
    elif channel_id == "imessage":
        # iMessage doesn't require credentials, just enabled flag
        pass
```

---

## Shared Patterns

### Configuration Class Pattern
**Source:** `src/claw_cron/channels/qqbot.py`
**Apply to:** All channel config classes
```python
class ChannelConfig(BaseSettings, ChannelConfig):
    """Configuration for [channel] channel.

    Environment variables use [PREFIX]_ prefix:
        - [PREFIX]_APP_ID: [Channel] App ID
        - [PREFIX]_APP_SECRET: [Channel] App Secret
    """

    app_id: str | None = Field(
        default=None, description="[Channel] App ID from [platform]"
    )
    app_secret: str | None = Field(
        default=None, description="[Channel] App Secret from [platform]"
    )

    class Config:
        env_prefix = "[PREFIX]_"
        env_file = ".env"
        extra = "ignore"
```

### Retry Pattern
**Source:** `src/claw_cron/channels/qqbot.py`
**Apply to:** All channel send methods with rate limits
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True,
)
async def _send_with_retry(...) -> dict[str, Any]:
    """Send message with automatic retry on rate limits."""
    # Implementation
```

### Error Classification Pattern
**Source:** `src/claw_cron/channels/qqbot.py`
**Apply to:** All channel implementations
```python
# In class definition:
RATE_LIMIT_CODES = frozenset({22009, 20028, ...})
AUTH_ERROR_CODES = frozenset({11241, 11242, ...})

# In send method:
if error_code in self.RATE_LIMIT_CODES:
    raise RateLimitError(error_code, error_message)
if error_code in self.AUTH_ERROR_CODES:
    raise ChannelAuthError(f"Authentication failed: {error_message}", channel_id=self.channel_id)
raise ChannelSendError(f"Send failed: [{error_code}] {error_message}", channel_id=self.channel_id)
```

### Recipient Format Pattern
**Source:** `src/claw_cron/channels/qqbot.py`
**Apply to:** All channel implementations
```python
# Reuse parse_recipient from qqbot module
from claw_cron.channels.qqbot import parse_recipient

# In send methods:
info = parse_recipient(recipient)  # Returns RecipientInfo with type and openid
# Use info.openid for API calls
```

### Credential Verification Pattern
**Source:** `src/claw_cron/cmd/channels.py`
**Apply to:** All channel add/verify commands
```python
# Validate credentials before saving
with console.status("[bold green]正在验证凭证..."):
    try:
        response = httpx.post(
            "[TOKEN_ENDPOINT]",
            json={"app_id": app_id, "app_secret": app_secret},
            timeout=10.0,
        )
        data = response.json()
        if data.get("code", 0) != 0:
            raise click.ClickException(
                f"验证失败: {data.get('message', '未知错误')}"
            )
        console.print("[green]✓ 凭证验证成功[/green]")
    except httpx.RequestError as e:
        raise click.ClickException(f"连接失败: {e}") from e
```

### Capture Command Pattern
**Source:** `src/claw_cron/cmd/channels.py`
**Apply to:** All channel capture implementations
```python
async def _capture_[channel]_openid(alias: str) -> None:
    """Capture OpenID from [channel] WebSocket."""
    # 1. Load config
    config = load_config()
    channel_config = config.get("channels", {}).get("[channel]", {})
    # Check required fields...

    # 2. Setup callback
    captured_openid: str | None = None

    async def on_message(message) -> None:
        nonlocal captured_openid
        captured_openid = message.openid
        console.print(f"[green]✓ OpenID captured: {message.openid}[/green]")

    # 3. Setup WebSocket client
    ws_client = WebSocketClient(config, on_message)

    # 4. Wait for capture
    console.print("[bold]Waiting for message...[/bold]")
    try:
        async def wait_for_capture() -> None:
            while not captured_openid:
                await asyncio.sleep(0.5)

        await asyncio.gather(
            ws_client.connect(),
            wait_for_capture()
        )
    except KeyboardInterrupt:
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # 5. Save contact
    if captured_openid:
        contact = Contact(
            openid=captured_openid,
            channel="[channel]",
            alias=alias,
            created=datetime.now().isoformat(),
        )
        save_contact(contact)
        console.print(f"[green]✓ Contact saved as '{alias}'[/green]")
```

---

## No Analog Found

None — All files have close matches in the existing codebase.

---

## Metadata

**Analog search scope:**
- `src/claw_cron/channels/` — Channel implementations
- `src/claw_cron/cmd/` — CLI command implementations
- `src/claw_cron/qqbot/` — WebSocket event handling

**Files scanned:** 10
**Pattern extraction date:** 2026-04-17

**Key pattern sources:**
- `qqbot.py` — Full channel implementation pattern (config, token, retry, send)
- `qqbot/events.py` — Event dataclass and parsing pattern
- `cmd/channels.py` — CLI command patterns (add, verify, capture)
- `channels/__init__.py` — Registry and status check patterns
