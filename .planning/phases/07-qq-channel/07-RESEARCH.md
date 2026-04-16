# Phase 7: QQ Bot Channel - Research

**Researched:** 2026-04-16
**Domain:** QQ Bot API, OAuth2 Authentication, Message Channels
**Confidence:** HIGH

## Summary

QQ Bot Channel 实现需要集成 QQ 开放平台机器人 API。API 使用 OAuth2 认证，通过 App ID + Client Secret 获取 access_token（有效期 7200 秒）。消息发送支持 C2C 私聊和群聊两种场景，需要使用不同的 API 端点和 openid 格式。Markdown 消息（msg_type=2）在正式环境需要内邀开通，沙箱环境可自由调试。项目已安装 httpx (v0.28.1)，可直接用于 HTTP 请求。需要实现 token 缓存和自动刷新机制，以及针对频率限制（429, 22009）的指数退避重试策略。

**Primary recommendation:** 使用 httpx 作为 HTTP 客户端，实现 QQBotChannel 类继承 MessageChannel，采用 pydantic-settings 管理 app_id/client_secret 配置，实现 token 缓存和自动刷新，以及针对常见错误的统一处理。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1 | Async HTTP client | Already installed, supports async/await, connection pooling |
| pydantic-settings | latest | Configuration management | Project pattern from AIConfig, supports env vars and YAML |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | latest | Retry with exponential backoff | For rate limit (429, 22009) and transient errors |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp | httpx already installed, similar functionality |
| tenacity | manual retry logic | tenacity provides battle-tested exponential backoff |

**Installation:**
```bash
# tenacity is not yet installed
pip install tenacity
```

**Version verification:** 
- httpx: 0.28.1 (verified via python3 import)
- pydantic-settings: Already in dependencies
- tenacity: Not installed (need to add to pyproject.toml)

## Architecture Patterns

### Recommended Project Structure
```
src/claw_cron/channels/
├── __init__.py          # Channel registry
├── base.py              # MessageChannel abstract base
├── exceptions.py        # Channel exceptions
├── imessage.py          # iMessage implementation (reference)
└── qqbot.py             # QQ Bot implementation (NEW)
```

### Pattern 1: Configuration with pydantic-settings
**What:** Use pydantic-settings for QQ Bot configuration, following AIConfig pattern
**When to use:** For all configuration that supports environment variables and YAML file
**Example:**
```python
from pydantic import Field
from pydantic_settings import BaseSettings
from claw_cron.channels.base import ChannelConfig

class QQBotConfig(ChannelConfig):
    """Configuration for QQ Bot channel.
    
    Environment variables use CLAW_CRON_QQBOT_ prefix:
        - CLAW_CRON_QQBOT_APP_ID: QQ Bot App ID
        - CLAW_CRON_QQBOT_CLIENT_SECRET: QQ Bot Client Secret
    
    Attributes:
        app_id: QQ Bot App ID from open platform
        client_secret: QQ Bot Client Secret from open platform
    """
    app_id: str | None = Field(
        default=None,
        description="QQ Bot App ID from q.qq.com"
    )
    client_secret: str | None = Field(
        default=None,
        description="QQ Bot Client Secret from q.qq.com"
    )
    
    class Config:
        env_prefix = "CLAW_CRON_QQBOT_"
        env_file = ".env"
        extra = "ignore"
```

### Pattern 2: Token Management
**What:** Implement token caching with automatic refresh before expiration
**When to use:** All QQ Bot API calls require valid access_token
**Example:**
```python
import time
from dataclasses import dataclass

@dataclass
class TokenInfo:
    """Cached token information."""
    access_token: str
    expires_at: float  # Unix timestamp
    buffer_seconds: int = 60  # Refresh 60s before expiration
    
    def is_expired(self) -> bool:
        """Check if token is expired or near expiration."""
        return time.time() >= (self.expires_at - self.buffer_seconds)

class QQBotChannel(MessageChannel):
    def __init__(self, config: QQBotConfig | None = None):
        super().__init__(config or QQBotConfig())
        self._token: TokenInfo | None = None
        self._http_client = httpx.AsyncClient(
            base_url="https://api.sgroup.qq.com",
            timeout=30.0
        )
    
    async def _get_access_token(self) -> str:
        """Get valid access token, refreshing if necessary."""
        if self._token and not self._token.is_expired():
            return self._token.access_token
        
        # Fetch new token
        response = await self._http_client.post(
            "https://bots.qq.com/app/getAppAccessToken",
            json={
                "appId": self.config.app_id,
                "clientSecret": self.config.client_secret
            }
        )
        data = response.json()
        
        self._token = TokenInfo(
            access_token=data["access_token"],
            expires_at=time.time() + int(data["expires_in"])
        )
        return self._token.access_token
```

### Pattern 3: Recipient Format Parsing
**What:** Parse recipient string to determine message type and extract openid
**When to use:** When user provides recipient in different formats
**Example:**
```python
import re
from dataclasses import dataclass
from enum import Enum

class RecipientType(Enum):
    C2C = "c2c"      # Private chat
    GROUP = "group"  # Group chat

@dataclass
class RecipientInfo:
    """Parsed recipient information."""
    type: RecipientType
    openid: str

def parse_recipient(recipient: str) -> RecipientInfo:
    """Parse recipient string to determine type and openid.
    
    Formats:
        - "c2c:OPENID" -> Private chat with user
        - "group:GROUP_OPENID" -> Group chat
        - Plain openid string -> Treat as C2C (backward compatibility)
    
    Args:
        recipient: Recipient identifier string.
    
    Returns:
        RecipientInfo with type and openid.
    
    Raises:
        ValueError: If format is invalid.
    """
    if ":" in recipient:
        parts = recipient.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid recipient format: {recipient}")
        
        type_str, openid = parts
        if type_str == "c2c":
            return RecipientInfo(type=RecipientType.C2C, openid=openid)
        elif type_str == "group":
            return RecipientInfo(type=RecipientType.GROUP, openid=openid)
        else:
            raise ValueError(f"Unknown recipient type: {type_str}")
    else:
        # Treat plain string as C2C openid
        return RecipientInfo(type=RecipientType.C2C, openid=recipient)
```

### Pattern 4: Error Handling with Retry
**What:** Use tenacity for automatic retry on transient errors
**When to use:** For rate limits (429, 22009) and server errors (500, 504)
**Example:**
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class QQBotAPIError(Exception):
    """QQ Bot API error with code and message."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

# Retry on rate limit (429) and server errors (500, 504)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((RateLimitError, ServerError)),
    reraise=True
)
async def _send_message_with_retry(
    self,
    endpoint: str,
    payload: dict
) -> dict:
    """Send message with automatic retry on transient errors."""
    token = await self._get_access_token()
    
    response = await self._http_client.post(
        endpoint,
        json=payload,
        headers={"Authorization": f"QQBot {token}"}
    )
    
    if response.status_code == 429:
        raise RateLimitError("Rate limit exceeded")
    
    if response.status_code >= 500:
        raise ServerError(f"Server error: {response.status_code}")
    
    data = response.json()
    
    # Check for business errors
    if "code" in data and data["code"] != 0:
        error_code = data["code"]
        
        # Rate limit errors
        if error_code in (22009, 20028, 304045, 304046, 304047, 304048, 304049, 304050):
            raise RateLimitError(data.get("message", "Rate limit exceeded"))
        
        # Auth errors
        if error_code in (11241, 11242, 11243, 11251, 11261):
            raise ChannelAuthError(
                f"Authentication failed: {data.get('message')}",
                channel_id=self.channel_id
            )
        
        # Other errors
        raise QQBotAPIError(error_code, data.get("message", "Unknown error"))
    
    return data
```

### Anti-Patterns to Avoid
- **Hardcoding tokens:** Never store access_token in code or config files
- **Ignoring token expiration:** Always check expiration before API calls
- **Missing error codes:** Don't only check HTTP status, also check platform error codes in response body
- **Retrying auth errors:** Don't retry on 11241-11261 auth errors (will always fail)
- **Sending Markdown in production:** msg_type=2 requires internal invitation for production use

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP client | Manual requests with aiohttp | httpx | Already installed, connection pooling, async support |
| Configuration | Custom env var parsing | pydantic-settings | Project pattern, type-safe, supports YAML and env vars |
| Retry logic | Manual retry loops | tenacity | Exponential backoff, declarative, well-tested |
| Token caching | Custom cache with dict | TokenInfo dataclass + time.time() | Simple, testable, thread-safe |

**Key insight:** QQ Bot API has complex error codes (200+ types) and rate limits. Using tenacity for retry and pydantic-settings for config reduces boilerplate and improves reliability.

## Runtime State Inventory

> This section is not applicable for greenfield implementation phases.

**N/A** — Phase 7 is a new feature implementation, not a rename/refactor/migration.

## Common Pitfalls

### Pitfall 1: Token Expiration During Long-Running Operations
**What goes wrong:** Token expires in the middle of sending multiple messages
**Why it happens:** Access token expires after 7200 seconds (2 hours)
**How to avoid:** Always check `is_expired()` before each API call, refresh proactively
**Warning signs:** HTTP 401 errors, error codes 11242, 11243

### Pitfall 2: Rate Limit Exceeded
**What goes wrong:** Sending too many messages too quickly triggers rate limit
**Why it happens:** 
- C2C: 4 messages per user per month (active), 5 replies per message in 60min (passive)
- Group: 4 messages per group per month (active), 5 replies per message in 5min (passive)
**How to avoid:** 
- Implement message queue with rate limiting
- Use passive reply (msg_id/event_id) instead of active send when possible
- Monitor error codes 22009, 20028, 304045-304050
**Warning signs:** Error code 22009, HTTP 429

### Pitfall 3: Markdown Not Working in Production
**What goes wrong:** Markdown messages work in sandbox but fail in production
**Why it happens:** Markdown requires internal invitation for production environments
**How to avoid:** 
- Check if markdown is enabled before sending
- Implement fallback to plain text (msg_type=0)
- Document markdown limitation clearly
**Warning signs:** Error code 50056 "不允许发送 markdown content"

### Pitfall 4: Invalid Recipient Format
**What goes wrong:** Using wrong openid format or mixing bot openid with user openid
**Why it happens:** OpenIDs are unique per bot (AppID), can't reuse across bots
**How to avoid:** 
- Always get openid from bot events (C2C_MSG_RECEIVE, GROUP_MSG_RECEIVE)
- Document that openid is bot-specific
- Validate recipient format before sending
**Warning signs:** Error 10003, 10004, 11264

### Pitfall 5: Not Handling WebSocket Events
**What goes wrong:** Can't get user openid without receiving events
**Why it happens:** QQ Bot requires WebSocket connection to receive user events
**How to avoid:** 
- Document that bot must be added to user's friend list or group
- User must interact with bot first (send message or add friend)
- Store openid from events for future use
**Warning signs:** No openid available, can't send messages

## Code Examples

Verified patterns from official QQ Bot documentation:

### OAuth2 Token Request
```python
# Source: https://bot.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/api-use.html
import httpx

async def get_access_token(app_id: str, client_secret: str) -> dict:
    """Get QQ Bot access token.
    
    Returns:
        {
            "access_token": "ACCESS_TOKEN",
            "expires_in": "7200"
        }
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://bots.qq.com/app/getAppAccessToken",
            json={
                "appId": app_id,
                "clientSecret": client_secret
            }
        )
        return response.json()
```

### C2C Private Chat Message
```python
# Source: https://bot.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/send.html
async def send_c2c_message(
    client: httpx.AsyncClient,
    access_token: str,
    user_openid: str,
    content: str,
    msg_type: int = 0
) -> dict:
    """Send C2C private chat message.
    
    Args:
        user_openid: User's openid (bot-specific)
        msg_type: 0=text, 2=markdown, 3=ark, 4=embed, 7=media
    
    Returns:
        {"id": "message_id", "timestamp": 1234567890}
    """
    response = await client.post(
        f"/v2/users/{user_openid}/messages",
        json={
            "content": content,
            "msg_type": msg_type
        },
        headers={"Authorization": f"QQBot {access_token}"}
    )
    return response.json()
```

### Group Chat Message
```python
# Source: https://bot.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/send.html
async def send_group_message(
    client: httpx.AsyncClient,
    access_token: str,
    group_openid: str,
    content: str,
    msg_type: int = 0
) -> dict:
    """Send group chat message.
    
    Args:
        group_openid: Group's openid (bot-specific)
        msg_type: 0=text, 2=markdown, 3=ark, 4=embed, 7=media
    
    Returns:
        {"id": "message_id", "timestamp": 1234567890}
    """
    response = await client.post(
        f"/v2/groups/{group_openid}/messages",
        json={
            "content": content,
            "msg_type": msg_type
        },
        headers={"Authorization": f"QQBot {access_token}"}
    )
    return response.json()
```

### Markdown Message
```python
# Source: https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/type/markdown.html
async def send_markdown_message(
    client: httpx.AsyncClient,
    access_token: str,
    user_openid: str,
    markdown_content: str
) -> dict:
    """Send markdown message (requires internal invitation in production).
    
    Args:
        markdown_content: Markdown formatted content
    
    Returns:
        {"id": "message_id", "timestamp": 1234567890}
    """
    response = await client.post(
        f"/v2/users/{user_openid}/messages",
        json={
            "msg_type": 2,
            "markdown": {
                "content": markdown_content
            }
        },
        headers={"Authorization": f"QQBot {access_token}"}
    )
    return response.json()
```

### Passive Reply (Recommended)
```python
# Source: https://bot.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/send.html
async def reply_to_message(
    client: httpx.AsyncClient,
    access_token: str,
    user_openid: str,
    content: str,
    msg_id: str,
    msg_seq: int = 1
) -> dict:
    """Reply to a received message (passive reply).
    
    Passive replies have higher limits:
    - C2C: 5 replies per message within 60 minutes
    - Group: 5 replies per message within 5 minutes
    
    Args:
        msg_id: ID of the message to reply to
        msg_seq: Reply sequence number (default: 1)
    """
    response = await client.post(
        f"/v2/users/{user_openid}/messages",
        json={
            "content": content,
            "msg_type": 0,
            "msg_id": msg_id,
            "msg_seq": msg_seq
        },
        headers={"Authorization": f"QQBot {access_token}"}
    )
    return response.json()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bot Token authentication | App ID + Client Secret OAuth2 | 2024-03 (botpy v1.1.5) | More secure, supports granular permissions |
| Active message push (unlimited) | Active messages limited to 4/month | 2025-04-21 | Must use passive replies when possible |
| WebSocket-only | REST API + WebSocket events | Current | Can send messages without WebSocket, but need events for openid |

**Deprecated/outdated:**
- Bot Token authentication: Use App ID + Client Secret instead
- Unlimited active messages: Now limited to 4 per user/group per month
- qq-bot package (old): Use qq-botpy v1.2.1 instead

## Open Questions

1. **How to get user openid without WebSocket?**
   - What we know: OpenID comes from bot events (C2C_MSG_RECEIVE, FRIEND_ADD, GROUP_ADD_ROBOT)
   - What's unclear: Can we use REST API to query user openid?
   - Recommendation: Document that user must interact with bot first, then store openid for future use. Consider implementing WebSocket listener as a future enhancement.

2. **Should we use the official botpy SDK?**
   - What we know: botpy v1.2.1 is official SDK with full API support
   - What's unclear: Does it fit our MessageChannel abstraction? Is it too heavyweight?
   - Recommendation: For Phase 7, implement our own QQBotChannel using httpx directly. This gives us full control and matches our MessageChannel pattern. Consider botpy integration as a future optimization if needed.

3. **How to handle markdown template approval?**
   - What we know: Markdown templates require separate approval process
   - What's unclear: How long does approval take? What are the criteria?
   - Recommendation: For Phase 7, use plain text messages (msg_type=0) as primary. Implement markdown support with fallback to plain text. Document that custom markdown requires internal invitation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | HTTP client for QQ Bot API | ✓ | 0.28.1 | — |
| pydantic-settings | Configuration management | ✓ | latest | — |
| tenacity | Retry with exponential backoff | ✗ | — | Manual retry logic (less robust) |
| Python | Runtime | ✓ | 3.12+ | — |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- tenacity: Can implement manual retry logic, but less robust and more code

## Validation Architecture

> nyquist_validation is set to false in .planning/config.json — skipping this section.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QQ-01 | 实现 `QQBotChannel` 类，支持 QQ 开放平台 API | Pattern 2 (Token Management), Pattern 3 (Recipient Parsing), Pattern 4 (Error Handling) |
| QQ-02 | 实现 `QQBotConfig` 配置类，包含 `app_id`、`client_secret` | Pattern 1 (Configuration with pydantic-settings) |
| QQ-03 | 支持 OAuth2 认证获取 access_token | Code Example: OAuth2 Token Request, Pattern 2 (Token Management) |
| QQ-04 | 支持私聊消息发送 (`c2c:OPENID` 格式) | Code Example: C2C Private Chat Message, Pattern 3 (Recipient Format Parsing) |
| QQ-05 | 支持群聊消息发送 (`group:GROUP_OPENID` 格式) | Code Example: Group Chat Message, Pattern 3 (Recipient Format Parsing) |
| QQ-06 | 支持 Markdown 消息格式 (msg_type=2) | Code Example: Markdown Message, Pitfall 3 (Markdown limitations) |

## Sources

### Primary (HIGH confidence)
- [QQ Bot Official Docs - API Authentication](https://bot.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/api-use.html) - OAuth2 flow, token management
- [QQ Bot Official Docs - Message Sending](https://bot.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/send.html) - C2C and Group message APIs
- [QQ Bot Official Docs - Unique ID Mechanism](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/unique-id.html) - OpenID format and constraints
- [QQ Bot Official Docs - Error Codes](https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/error-trace/openapi.html) - Complete error code reference

### Secondary (MEDIUM confidence)
- [QQ Bot Official Docs - Markdown Messages](https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/type/markdown.html) - Markdown format support and limitations
- [botpy GitHub Repository](https://github.com/tencent-connect/botpy) - Official Python SDK reference
- [qq-botpy PyPI](https://pypi.org/project/qq-botpy/) - Package version and installation

### Tertiary (LOW confidence)
- N/A - All core information comes from official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - httpx already installed, pydantic-settings is project pattern, tenacity is well-known library
- Architecture: HIGH - Patterns derived from official docs and existing codebase (iMessage channel, AI config)
- Pitfalls: HIGH - All pitfalls documented in official error code reference

**Research date:** 2026-04-16
**Valid until:** 2026-07-16 (3 months - QQ Bot API is stable but rate limits and features may change)
