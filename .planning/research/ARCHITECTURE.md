# Architecture Research: Email & Feishu Channels

**Domain:** Message channel integration for claw-cron
**Researched:** 2026-04-17
**Confidence:** HIGH

## Integration Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     claw-cron Notification                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ Notifier │  │  Notify  │  │ Contact  │  │    Config    │    │
│  │          │  │  Config  │  │ Resolver │  │   Loader     │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
│       │             │             │                │            │
├───────┴─────────────┴─────────────┴────────────────┴────────────┤
│                    Channel Registry Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  CHANNEL_REGISTRY = {                                            │
│    "imessage": IMessageChannel,                                  │
│    "qqbot": QQBotChannel,                                        │
│    "email": EmailChannel,         ← NEW                          │
│    "feishu": FeishuChannel        ← NEW                          │
│  }                                                               │
├─────────────────────────────────────────────────────────────────┤
│              MessageChannel Abstract Interface                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │ IMessageCh  │  │ QQBotChannel │  │ EmailChannel │ ← NEW      │
│  └─────────────┘  └──────────────┘  └──────────────┘            │
│  ┌──────────────┐                                                │
│  │ FeishuChannel│ ← NEW                                          │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Existing Architecture Components

| Component | Responsibility | Integration Point |
|-----------|----------------|-------------------|
| **MessageChannel** | Abstract base class defining channel interface | EmailChannel & FeishuChannel inherit from this |
| **ChannelConfig** | Base configuration dataclass | EmailConfig & FeishuConfig extend this |
| **MessageResult** | Standardized send result | Used by all channels |
| **CHANNEL_REGISTRY** | Channel class registry | Register new channels here |
| **get_channel()** | Factory function | No changes needed - works automatically |
| **Notifier** | Orchestrates notification sending | No changes needed - works with any registered channel |
| **NotifyConfig** | Task-level notification config | No changes needed |
| **Contact** | Recipient alias management | Works with email addresses & open_ids |
| **channels CLI** | Channel management commands | Add support for "email" and "feishu" types |

## New Components Required

### 1. EmailChannel

**File:** `src/claw_cron/channels/email.py`

```python
"""Email channel implementation using aiosmtplib."""

from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

import aiosmtplib
from pydantic import Field
from pydantic_settings import BaseSettings

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelConfigError, ChannelSendError


@dataclass
class EmailConfig(BaseSettings, ChannelConfig):
    """Email channel configuration.
    
    Environment variables use CLAW_CRON_EMAIL_ prefix:
        - CLAW_CRON_EMAIL_SMTP_HOST: SMTP server hostname
        - CLAW_CRON_EMAIL_SMTP_PORT: SMTP server port
        - CLAW_CRON_EMAIL_USERNAME: SMTP username
        - CLAW_CRON_EMAIL_PASSWORD: SMTP password
        - CLAW_CRON_EMAIL_FROM: From email address
        - CLAW_CRON_EMAIL_USE_TLS: Use TLS (default: True)
    
    Attributes:
        smtp_host: SMTP server hostname.
        smtp_port: SMTP server port (default: 587).
        username: SMTP authentication username.
        password: SMTP authentication password.
        from_email: Default sender email address.
        use_tls: Whether to use TLS encryption.
    """
    
    smtp_host: str | None = Field(default=None, description="SMTP server hostname")
    smtp_port: int = Field(default=587, description="SMTP server port")
    username: str | None = Field(default=None, description="SMTP username")
    password: str | None = Field(default=None, description="SMTP password")
    from_email: str | None = Field(default=None, description="Sender email address")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    
    class Config:
        env_prefix = "CLAW_CRON_EMAIL_"
        env_file = ".env"
        extra = "ignore"


class EmailChannel(MessageChannel):
    """Email channel using aiosmtplib.
    
    This channel sends emails via SMTP. Supports:
    - Plain text and HTML messages
    - TLS/SSL encryption
    - Multiple recipients
    
    Recipient format: email address string (e.g., "user@example.com")
    
    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("email")
        >>> result = await channel.send_text("user@example.com", "Hello!")
    """
    
    def __init__(self, config: EmailConfig | dict | None = None) -> None:
        """Initialize email channel.
        
        Args:
            config: Email configuration. Can be EmailConfig, dict, or None.
        """
        if config is None:
            config_obj = EmailConfig()
        elif isinstance(config, dict):
            config_obj = EmailConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)
    
    @property
    def channel_id(self) -> str:
        """Return unique channel identifier."""
        return "email"
    
    def _validate_config(self) -> None:
        """Validate configuration has required fields."""
        if not self.config.smtp_host:
            raise ChannelConfigError(
                "Email smtp_host is required. Set CLAW_CRON_EMAIL_SMTP_HOST environment variable.",
                channel_id=self.channel_id,
            )
        if not self.config.from_email:
            raise ChannelConfigError(
                "Email from_email is required. Set CLAW_CRON_EMAIL_FROM environment variable.",
                channel_id=self.channel_id,
            )
    
    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send a plain text email.
        
        Args:
            recipient: Recipient email address.
            content: Plain text email content.
        
        Returns:
            MessageResult indicating success or failure.
        """
        self._validate_config()
        
        message = EmailMessage()
        message["From"] = self.config.from_email
        message["To"] = recipient
        message["Subject"] = "claw-cron notification"
        message.set_content(content)
        
        try:
            await aiosmtplib.send(
                message,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                start_tls=self.config.use_tls,
            )
            return MessageResult(success=True)
        except Exception as e:
            return MessageResult(success=False, error=str(e))
    
    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send an HTML email (markdown converted to HTML).
        
        Note: For simplicity, sends as plain text.
        Future enhancement: Use markdown library to convert to HTML.
        
        Args:
            recipient: Recipient email address.
            content: Markdown content (sent as plain text for now).
        
        Returns:
            MessageResult indicating success or failure.
        """
        # For MVP, treat markdown as plain text
        return await self.send_text(recipient, content)
```

**Key Design Decisions:**
- Uses `aiosmtplib` for async SMTP (version 5.1.0+)
- Follows QQBotChannel pattern for configuration
- Recipients are email addresses (no special format needed)
- Supports TLS by default (port 587 + STARTTLS)
- MVP: markdown sent as plain text (future: convert to HTML)

### 2. FeishuChannel

**File:** `src/claw_cron/channels/feishu.py`

```python
"""Feishu (Lark) channel implementation."""

import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import ChannelConfig, MessageChannel, MessageResult
from .exceptions import ChannelAuthError, ChannelConfigError, ChannelSendError


@dataclass
class TokenInfo:
    """Cached tenant access token."""
    access_token: str
    expires_at: float
    buffer_seconds: int = 60
    
    def is_expired(self) -> bool:
        """Check if token needs refresh."""
        return time.time() >= (self.expires_at - self.buffer_seconds)


class FeishuConfig(BaseSettings, ChannelConfig):
    """Feishu channel configuration.
    
    Environment variables use CLAW_CRON_FEISHU_ prefix:
        - CLAW_CRON_FEISHU_APP_ID: Feishu App ID
        - CLAW_CRON_FEISHU_APP_SECRET: Feishu App Secret
    
    Attributes:
        app_id: Feishu application App ID.
        app_secret: Feishu application App Secret.
    """
    
    app_id: str | None = Field(default=None, description="Feishu App ID")
    app_secret: str | None = Field(default=None, description="Feishu App Secret")
    
    class Config:
        env_prefix = "CLAW_CRON_FEISHU_"
        env_file = ".env"
        extra = "ignore"


class FeishuChannel(MessageChannel):
    """Feishu (Lark) channel for private messages.
    
    This channel sends private messages via Feishu Bot API.
    Similar to QQBotChannel, requires app credentials and tenant_access_token.
    
    Recipient format: User open_id (e.g., "ou_7d8a6e6df7621556ce0d21922b676706ccs")
    
    Prerequisites:
        - Application with bot capability enabled
        - User must be in bot's available scope
        - User's open_id obtained via API or events
    
    Example:
        >>> from claw_cron.channels import get_channel
        >>> channel = get_channel("feishu")
        >>> result = await channel.send_text("ou_xxx", "Hello!")
    """
    
    API_BASE = "https://open.feishu.cn/open-apis"
    
    def __init__(self, config: FeishuConfig | dict | None = None) -> None:
        """Initialize Feishu channel."""
        if config is None:
            config_obj = FeishuConfig()
        elif isinstance(config, dict):
            config_obj = FeishuConfig(**config)
        else:
            config_obj = config
        super().__init__(config_obj)
        self._token: TokenInfo | None = None
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    @property
    def channel_id(self) -> str:
        """Return unique channel identifier."""
        return "feishu"
    
    def _validate_config(self) -> None:
        """Validate configuration."""
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
    
    async def _get_tenant_access_token(self) -> str:
        """Get valid tenant access token, refreshing if necessary."""
        self._validate_config()
        
        if self._token and not self._token.is_expired():
            return self._token.access_token
        
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.config.app_id,
                    "app_secret": self.config.app_secret,
                },
            )
            data = response.json()
            
            if data.get("code", 0) != 0:
                raise ChannelAuthError(
                    f"Feishu authentication failed: {data.get('msg', 'Unknown error')}",
                    channel_id=self.channel_id,
                )
            
            self._token = TokenInfo(
                access_token=data["tenant_access_token"],
                expires_at=time.time() + int(data.get("expire", 7200)),
            )
            return self._token.access_token
        
        except httpx.HTTPStatusError as e:
            raise ChannelAuthError(
                f"Feishu authentication failed: HTTP {e.response.status_code}",
                channel_id=self.channel_id,
            ) from e
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def _send_message(
        self,
        receive_id: str,
        msg_type: str,
        content: str,
    ) -> dict[str, Any]:
        """Send message to Feishu API with retry."""
        token = await self._get_tenant_access_token()
        
        try:
            response = await self._http_client.post(
                f"{self.API_BASE}/im/v1/messages",
                params={"receive_id_type": "open_id"},
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "receive_id": receive_id,
                    "msg_type": msg_type,
                    "content": content,
                },
            )
            
            data = response.json()
            
            if data.get("code", 0) != 0:
                raise ChannelSendError(
                    f"Feishu send failed: [{data.get('code')}] {data.get('msg')}",
                    channel_id=self.channel_id,
                )
            
            return data
        
        except httpx.RequestError as e:
            raise ChannelSendError(
                f"Feishu send failed: {e}",
                channel_id=self.channel_id,
            ) from e
    
    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """Send plain text message.
        
        Args:
            recipient: User open_id (e.g., "ou_xxx").
            content: Plain text content.
        
        Returns:
            MessageResult indicating success or failure.
        """
        import json
        
        try:
            data = await self._send_message(
                receive_id=recipient,
                msg_type="text",
                content=json.dumps({"text": content}),
            )
            return MessageResult(
                success=True,
                message_id=data.get("data", {}).get("message_id"),
                raw_response=data,
            )
        except (ChannelAuthError, ChannelSendError) as e:
            return MessageResult(success=False, error=str(e))
    
    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """Send markdown-formatted message.
        
        Args:
            recipient: User open_id.
            content: Markdown content.
        
        Returns:
            MessageResult indicating success or failure.
        """
        import json
        
        # Feishu supports markdown in "post" message type
        # For simplicity, send as text (supports markdown rendering in Feishu)
        return await self.send_text(recipient, content)
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self._http_client.aclose()
```

**Key Design Decisions:**
- Uses official Feishu API (not webhook) for private messages
- Mirrors QQBotChannel architecture (token management, retry logic)
- Recipients are `open_id` strings (similar to QQ Bot)
- Uses `tenant_access_token` for authentication
- Rate limit: 5 QPS per user (same as QQ Bot)
- Supports markdown via text messages (Feishu renders markdown automatically)

### 3. Registry Updates

**File:** `src/claw_cron/channels/__init__.py` (MODIFY)

```python
# ... existing imports ...

# Import and register built-in channels
from .email import EmailChannel
from .feishu import FeishuChannel
from .imessage import IMessageChannel
from .qqbot import QQBotChannel

CHANNEL_REGISTRY["email"] = EmailChannel      # ← NEW
CHANNEL_REGISTRY["feishu"] = FeishuChannel    # ← NEW
CHANNEL_REGISTRY["imessage"] = IMessageChannel
CHANNEL_REGISTRY["qqbot"] = QQBotChannel

__all__ = [
    # ... existing exports ...
    "EmailChannel",     # ← NEW
    "FeishuChannel",    # ← NEW
]
```

### 4. CLI Updates

**File:** `src/claw_cron/cmd/channels.py` (MODIFY)

#### Changes to `add` command:

```python
@channels.command()
@click.option(
    "--channel-type",
    type=click.Choice(["qqbot", "email", "feishu"], case_sensitive=False),  # ← UPDATED
    prompt="Channel type",
    help="Type of channel to configure",
)
@click.option("--app-id", help="App ID (for qqbot/feishu)")
@click.option("--client-secret", help="Client Secret (for qqbot)")
@click.option("--app-secret", help="App Secret (for feishu)")
@click.option("--smtp-host", help="SMTP server hostname (for email)")
@click.option("--smtp-port", type=int, default=587, help="SMTP port (default: 587)")
@click.option("--username", help="SMTP username (for email)")
@click.option("--password", help="SMTP password (for email)")
@click.option("--from-email", help="Sender email address (for email)")
def add(
    channel_type: str,
    app_id: str | None,
    client_secret: str | None,
    app_secret: str | None,
    smtp_host: str | None,
    smtp_port: int,
    username: str | None,
    password: str | None,
    from_email: str | None,
) -> None:
    """Add a new message channel configuration."""
    channel_type = channel_type.lower()
    
    if channel_type == "email":
        # Interactive prompts for email
        if not smtp_host:
            smtp_host = click.prompt("SMTP server hostname")
        if not username:
            username = click.prompt("SMTP username")
        if not password:
            password = click.prompt("SMTP password", hide_input=True)
        if not from_email:
            from_email = click.prompt("Sender email address")
        
        # Validate connection (optional but recommended)
        # ... validation logic ...
        
        config["channels"]["email"] = {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "username": username,
            "password": password,
            "from_email": from_email,
            "use_tls": True,
            "enabled": True,
        }
    
    elif channel_type == "feishu":
        # Interactive prompts for feishu
        if not app_id:
            app_id = click.prompt("Feishu App ID")
        if not app_secret:
            app_secret = click.prompt("Feishu App Secret", hide_input=True)
        
        # Validate credentials
        # ... validation logic ...
        
        config["channels"]["feishu"] = {
            "app_id": app_id,
            "app_secret": app_secret,
            "enabled": True,
        }
    
    # ... existing qqbot logic ...
```

#### Changes to `list` command:

```python
@channels.command("list")
def list_channels() -> None:
    """List configured message channels."""
    config = load_config()
    channels_config = config.get("channels", {})

    if not channels_config:
        console.print("[dim]No channels configured.[/dim]")
        return

    table = Table(title="Configured Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Config", style="dim")
    table.add_column("Contacts", style="yellow")

    contacts_data = load_contacts()

    for channel_id, cfg in channels_config.items():
        status = "[green]enabled[/green]" if cfg.get("enabled", True) else "[red]disabled[/red]"
        
        # Display relevant config for each channel type
        if channel_id == "email":
            config_display = cfg.get("from_email", "N/A")
        elif channel_id in ("qqbot", "feishu"):
            app_id = cfg.get("app_id", "N/A")
            config_display = f"{app_id[:8]}..." if len(str(app_id)) > 8 else str(app_id)
        else:
            config_display = "N/A"
        
        contact_count = sum(1 for c in contacts_data.values() if c.channel == channel_id)
        table.add_row(channel_id, status, config_display, str(contact_count))

    console.print(table)
```

## Data Flow

### Notification Sending Flow

```
Task Execution Complete
    ↓
Notifier.notify_task_result(task, exit_code, output)
    ↓
Load task.notify config (NotifyConfig)
    ├── channel: "email" | "feishu" | "qqbot" | "imessage"
    └── recipients: ["user@example.com"] | ["ou_xxx"] | ["c2c:xxx"]
    ↓
Load channel config from config.yaml
    config["channels"][channel]
    ↓
get_channel(channel_id, config)
    ↓
CHANNEL_REGISTRY[channel_id](config) → Channel instance
    ↓
For each recipient:
    ├── channel.send_text(recipient, message)
    └── Returns MessageResult
    ↓
Return list[MessageResult]
```

### Channel Registration Flow

```
channels add --channel-type email
    ↓
Interactive prompts for config values
    ↓
Validate connection (optional)
    ↓
Save to ~/.config/claw-cron/config.yaml:
    channels:
        email:
            smtp_host: smtp.example.com
            smtp_port: 587
            username: user@example.com
            password: secret
            from_email: user@example.com
            use_tls: true
            enabled: true
```

## Configuration Schema

### config.yaml Structure

```yaml
channels:
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    username: user@gmail.com
    password: app_password
    from_email: user@gmail.com
    use_tls: true
    enabled: true
  
  feishu:
    app_id: cli_a1b2c3d4e5f6
    app_secret: abc123def456
    enabled: true
  
  qqbot:
    app_id: 1234567890
    client_secret: xyz789
    enabled: true
  
  imessage:
    enabled: true

contacts:
  me:
    openid: ou_7d8a6e6df7621556ce0d21922b676706ccs
    channel: feishu
    alias: me
    created: "2026-04-17T00:00:00"
  
  john:
    openid: john@example.com
    channel: email
    alias: john
    created: "2026-04-17T00:00:00"
```

## Integration Points Summary

| Component | Status | Changes Required |
|-----------|--------|------------------|
| **channels/base.py** | NO CHANGES | Abstract interface already supports new channels |
| **channels/__init__.py** | MODIFY | Add imports & registry entries for EmailChannel, FeishuChannel |
| **channels/email.py** | NEW FILE | Implement EmailChannel class |
| **channels/feishu.py** | NEW FILE | Implement FeishuChannel class |
| **notifier.py** | NO CHANGES | Works with any registered channel |
| **contacts.py** | NO CHANGES | Works with email addresses & open_ids |
| **cmd/channels.py** | MODIFY | Add email/feishu to add/delete/list commands |
| **config.yaml** | MODIFY | Add email & feishu config sections |

## Build Order

### Phase 1: EmailChannel (Simpler, Independent)
1. Create `src/claw_cron/channels/email.py`
   - EmailConfig dataclass
   - EmailChannel class with send_text/send_markdown
   - Error handling with ChannelConfigError, ChannelSendError
2. Update `src/claw_cron/channels/__init__.py`
   - Import EmailChannel
   - Register in CHANNEL_REGISTRY
   - Add to __all__
3. Update `src/claw_cron/cmd/channels.py`
   - Add "email" to channel-type choices
   - Implement email-specific prompts in add command
   - Update list command to show email config
4. Add dependencies to pyproject.toml
   - `aiosmtplib>=5.1.0`
5. Test manually:
   - `claw-cron channels add --channel-type email`
   - Add task with email notification
   - Verify email received

### Phase 2: FeishuChannel (More Complex, Dependencies)
1. Create `src/claw_cron/channels/feishu.py`
   - FeishuConfig dataclass
   - TokenInfo for token caching
   - FeishuChannel with token management
   - API integration with retry logic
2. Update `src/claw_cron/channels/__init__.py`
   - Import FeishuChannel
   - Register in CHANNEL_REGISTRY
   - Add to __all__
3. Update `src/claw_cron/cmd/channels.py`
   - Add "feishu" to channel-type choices
   - Implement feishu-specific prompts
   - Update list command
4. Add to pyproject.toml (dependencies already present for QQBot)
   - `httpx` (already exists)
   - `tenacity` (already exists)
   - `pydantic-settings` (already exists)
5. Test manually:
   - `claw-cron channels add --channel-type feishu`
   - Obtain user open_id (manual API call or event)
   - Add task with feishu notification
   - Verify message received in Feishu

### Phase 3: Integration Testing
1. Test multi-channel notification
   - Task with multiple recipients across channels
2. Test contact alias resolution
   - `claw-cron channels contacts add --alias john --openid john@example.com --channel email`
3. Test error handling
   - Invalid credentials
   - Network failures
   - Rate limiting

## Dependencies

### Email Channel
```toml
[project.dependencies]
aiosmtplib = ">=5.1.0"
```

### Feishu Channel
```toml
# Already present for QQBot
httpx = ">=0.27.0"
tenacity = ">=8.2.0"
pydantic-settings = ">=2.0.0"
```

## Key Differences from Existing Channels

| Aspect | QQBotChannel | EmailChannel | FeishuChannel |
|--------|--------------|--------------|---------------|
| **Auth** | App ID + Client Secret | Username + Password | App ID + App Secret |
| **Token** | access_token (2h) | No token | tenant_access_token (2h) |
| **Recipient Format** | `c2c:OPENID` / `group:GROUP_ID` | Email address | `open_id` (ou_xxx) |
| **API Base** | `api.sgroup.qq.com` | SMTP server | `open.feishu.cn` |
| **Rate Limit** | 5 QPS/user | Server-dependent | 5 QPS/user |
| **Markdown Support** | Yes (with fallback) | Via HTML (future) | Yes (auto-render) |
| **Platform** | QQ | Any | Feishu/Lark |
| **Get OpenID** | WebSocket event | N/A | API or event |

## Anti-Patterns to Avoid

### Anti-Pattern 1: Synchronous SMTP
**What people do:** Use Python's built-in `smtplib` which is synchronous
**Why it's wrong:** Blocks the async event loop, affects scheduler performance
**Do this instead:** Use `aiosmtplib` for fully async email sending

### Anti-Pattern 2: Hardcoded Email Templates
**What people do:** Hardcode email subject/body formatting in channel
**Why it's wrong:** Notifier already formats messages, duplicates logic
**Do this instead:** Use message from Notifier._format_message(), add subject configuration if needed

### Anti-Pattern 3: Feishu Webhook for Private Messages
**What people do:** Use webhook approach (only works for group chats)
**Why it's wrong:** Cannot send private messages via webhook
**Do this instead:** Use tenant_access_token API with open_id for private messages

### Anti-Pattern 4: Separate Token for Each Message
**What people do:** Fetch new token for every send_text() call
**Why it's wrong:** Wastes API calls, hits rate limits faster
**Do this instead:** Cache token with expiration (like QQBotChannel), reuse until expired

### Anti-Pattern 5: Ignoring Feishu OpenID Acquisition
**What people do:** Assume open_id is easy to obtain
**Why it's wrong:** Requires API calls or event subscriptions
**Do this instead:** 
- Document how to get open_id (API call with phone/email)
- Consider adding `channels capture` command for Feishu (similar to QQBot)
- Or provide utility command to lookup open_id by email

## Security Considerations

### Email Channel
- **Password Storage:** Stored in plain text in config.yaml (same as QQBot)
  - Mitigation: Recommend using app-specific passwords (Gmail, Outlook)
  - Future: Consider keyring integration
- **TLS:** Enabled by default, prevents MITM attacks
- **From Address:** Must match SMTP account to avoid SPF/DKIM issues

### Feishu Channel
- **App Secret:** Same security model as QQBot (stored in config.yaml)
- **Tenant Token:** 2-hour expiration limits exposure if leaked
- **User Scope:** Only users in bot's available scope can receive messages
- **OpenID Privacy:** OpenIDs are bot-specific, not globally unique

## Scalability Considerations

| Scale | Email Channel | Feishu Channel |
|-------|---------------|----------------|
| **10 notifications/day** | No issues | No issues |
| **100 notifications/day** | No issues | No issues |
| **1000+ notifications/day** | Check SMTP limits | Check Feishu quotas (contact support) |

**Rate Limits:**
- Email: Depends on SMTP provider (Gmail: 500/day, Outlook: 10000/day)
- Feishu: 5 QPS per user, can request increase

## Sources

- **aiosmtplib Documentation:** https://aiosmtplib.readthedocs.io/ (HIGH confidence)
- **Feishu Message API:** https://open.feishu.cn/document/server-docs/im-v1/message/create (HIGH confidence - official docs)
- **Feishu Authentication:** https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token (HIGH confidence - official docs)
- **Feishu OpenID Guide:** https://open.larksuite.com/document/faq/trouble-shooting/how-to-obtain-openid (HIGH confidence - official docs)
- **Python EmailMessage:** https://docs.pythonlang.cn/3/library/email.message.html (HIGH confidence - official docs)
- **Existing QQBotChannel Implementation:** src/claw_cron/channels/qqbot.py (HIGH confidence - project code)

---
*Architecture research for: Email & Feishu channel integration*
*Researched: 2026-04-17*
