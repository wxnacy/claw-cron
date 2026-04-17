# Stack Research

**Domain:** WeChat Channel & Capture Enhancement
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

WeChat integration research reveals three distinct approaches with clear trade-offs. **企业微信机器人 Webhook** is the recommended solution for claw-cron due to its simplicity, no authentication requirements, and alignment with the project's notification-only use case. 企业微信应用 provides richer features but requires complex OAuth2 and user ID management. 个人微信 solutions (itchat/WeChatBot) carry high封号 risk and are NOT recommended.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **企业微信机器人 Webhook** | N/A (HTTP API) | Send notifications to WeChat Work groups | Simplest integration: no auth tokens, no user ID management, just POST to webhook URL. Supports text/markdown/images. Rate limit: 20 msgs/min per webhook. |
| **httpx** | ^0.28.0 | Async HTTP client for webhook calls | Already used in QQBotChannel, proven pattern in codebase. Supports async, retries, timeout. Consistent with existing channel implementations. |
| **tenacity** | ^9.0.0 | Retry logic for API calls | Already used in qqbot.py and feishu.py for rate limit handling. Proven pattern for resilience. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pydantic** | ^2.0.0 | Config validation (WebhookConfig) | All channels use pydantic-settings for config. Pattern: `class WechatWorkConfig(BaseSettings, ChannelConfig)` |
| **pydantic-settings** | ^2.0.0 | Environment variable config loading | Environment variable prefix pattern: `CLAW_CRON_WECHAT_WORK_` |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **企业微信管理后台** | Create webhook, get webhook URL | Group settings → Group robots → Add robot. Webhook URL format: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX` |
| **curl / httpie** | Test webhook manually | `curl -X POST $WEBHOOK_URL -H 'Content-Type: application/json' -d '{"msgtype":"text","text":{"content":"test"}}'` |

## Installation

```bash
# Core dependencies (already in project)
# httpx, tenacity, pydantic, pydantic-settings already installed

# No additional packages needed for WeChat Work Webhook
```

## WeChat Channel Comparison

### Option 1: 企业微信机器人 Webhook ✅ RECOMMENDED

**API Endpoint:**
```
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=WEBHOOK_KEY
```

**Features:**
- ✅ **No authentication required** - Webhook URL contains key
- ✅ **Simple HTTP POST** - No OAuth2, no token management
- ✅ **Rich message types** - text, markdown, markdown_v2, image, news, file, voice, template_card
- ✅ **Rate limit: 20 msgs/min** - Sufficient for notification use case
- ✅ **No user ID management** - Send to group, all members receive
- ✅ **Markdown support** - Bold, links, code, quotes, colors (info/comment/warning)

**Limitations:**
- ❌ Group-only (no private chat)
- ❌ Need to create webhook in group settings
- ❌ Webhook URL must be kept secret

**Message Types:**

| Type | msgtype | Max Size | Features |
|------|---------|----------|----------|
| Text | `text` | 2048 bytes | @members by userid or phone |
| Markdown | `markdown` | 4096 bytes | Headers, bold, links, code, quotes, colors |
| Image | `image` | 2MB (base64) | JPG/PNG, send via base64 + md5 |
| News | `news` | 1-8 articles | Title, desc, url, picurl |

**Integration Points:**

1. **Channel Implementation:**
```python
# src/claw_cron/channels/wechat_work.py
class WechatWorkChannel(MessageChannel):
    """WeChat Work group robot webhook channel."""

    @property
    def channel_id(self) -> str:
        return "wechat_work"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        # recipient is webhook_key (extract from webhook URL)
        # POST to https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={recipient}
        ...
```

2. **Configuration:**
```yaml
# ~/.config/claw-cron/config.yaml
channels:
  wechat_work:
    enabled: true
    # Store webhook_key or full URL
    webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXXXXX"
```

3. **Recipient Format:**
```
# Option 1: Full webhook URL
recipients: ["https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX"]

# Option 2: Just the key
recipients: ["webhook:XXX"]
```

---

### Option 2: 企业微信应用 ⚠️ NOT RECOMMENDED

**API Endpoint:**
```
POST https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=ACCESS_TOKEN
```

**Features:**
- ✅ Private chat to individual users (touser)
- ✅ Send to departments (toparty) and tags (totag)
- ✅ Send to "@all" (all visible users)
- ✅ Rich message types (11 types including template cards)
- ✅ ID translation ($userName=USERID$ → "张三")

**Why NOT Recommended:**

| Issue | Impact |
|-------|--------|
| **OAuth2 required** | Need access_token management (refresh every 2 hours) |
| **User ID required** | Must know userid to send private messages |
| **UserID获取复杂** | 需要：手机号查询API / 邮箱查询API / 网页授权 / 通讯录同步 |
| **可见范围限制** | 用户必须在应用的可见范围内才能收到消息 |
| **频率限制严格** | 单成员: 30次/分钟, 1000次/小时; 企业: 2万人次/分钟 |
| **需要创建应用** | 企业微信管理后台 → 应用管理 → 创建自建应用 |
| **需要三个凭证** | corp_id, agent_id, secret (vs webhook只需URL) |

**Complex Integration Points:**

1. **Token Management:**
```python
# Need to implement token cache with refresh
async def get_access_token(self) -> str:
    if self._token and not self._token.is_expired():
        return self._token.access_token

    # POST to https://qyapi.weixin.qq.com/cgi-bin/gettoken
    response = await self._http_client.post(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": self.config.corp_id, "corpsecret": self.config.secret}
    )
    # Cache token, expires in 7200s
```

2. **User ID Acquisition:**
```python
# Option 1: By phone number
POST https://qyapi.weixin.qq.com/cgi-bin/user/getuserid?access_token=ACCESS_TOKEN
{"mobile": "13800138000"}

# Option 2: By email
POST https://qyapi.weixin.qq.com/cgi-bin/user/get_userid_by_email?access_token=ACCESS_TOKEN
{"email": "user@example.com"}

# Option 3: Web OAuth (complex)
# Redirect user to OAuth URL, get code, exchange for userinfo
```

3. **Configuration Complexity:**
```yaml
channels:
  wechat_work_app:
    enabled: true
    corp_id: "wwXXXXXX"           # 企业ID
    agent_id: 1000001             # 应用AgentId
    secret: "XXXXXX"              # 应用Secret
    # Optional: how to map phone/email to userid for capture?
```

**When This Might Be Worth It:**
- Need private notifications to specific users (not groups)
- Already have user ID mapping from external system
- Sending >1000 notifications per hour (need higher limits)

---

### Option 3: 个人微信 (itchat/WeChatBot) ❌ NOT RECOMMENDED

**Libraries:**
- **itchat**: Last maintained ~2019, frequent封号 reports
- **itchat-uos**: Fork for UOS system, still has封号 risk
- **WeChatBot**: PC client hook, requires running WeChat desktop

**Why NOT Recommended:**

| Issue | Severity |
|-------|----------|
| **封号风险极高** | 腾讯严厉打击非官方客户端，频繁封号 |
| **稳定性差** | 需要保持微信登录状态，掉线需重新扫码 |
| **需要扫码登录** | 不适合服务器环境，需要图形界面或长期session |
| **违反用户协议** | 非官方API，违反微信服务条款 |
| **无官方支持** | 问题无法通过官方渠道解决 |

**Risk Assessment:**
- 2026年3月文章指出："任何自动化操作都有风险"
- 封号主要原因：频繁操作、异常行为、非官方客户端
- 即使使用稳定方案（PC客户端HOOK），风险仍存在

**Alternatives Mentioned (but still risky):**
- ChatWave: 99.8%账号安全率（商业方案）
- ClawBot: 开源桥接工具，仍有风险
- 微信 iLink: 官方Bot API（2026年3月发布，申请条件未知）

---

## Integration Points with Existing Architecture

### 1. Follow QQBotChannel Pattern

**Similarities:**
- Both use httpx for async HTTP calls
- Both use tenacity for retry logic
- Both parse recipient to determine send target
- Both support text and markdown

**Key Differences:**

| Aspect | QQ Bot | WeChat Work Webhook |
|--------|--------|---------------------|
| Auth | OAuth2 (app_id + client_secret) | None (webhook key in URL) |
| Recipient | `c2c:OPENID` or `group:GROUP_OPENID` | Webhook key or full URL |
| Token management | Required (cache + refresh) | Not needed |
| Rate limit | Complex (multiple codes) | Simple: 20/min per webhook |

### 2. File Structure

```
src/claw_cron/channels/
├── wechat_work.py          # New: WechatWorkChannel
├── __init__.py             # Register: CHANNEL_REGISTRY["wechat_work"] = WechatWorkChannel
├── base.py                 # No changes
└── qqbot.py                # Reference pattern
```

### 3. Configuration Pattern

```python
# src/claw_cron/channels/wechat_work.py
from pydantic import Field
from pydantic_settings import BaseSettings

class WechatWorkConfig(BaseSettings, ChannelConfig):
    """Configuration for WeChat Work webhook channel."""

    webhook_url: str | None = Field(
        default=None,
        description="WeChat Work webhook URL or key"
    )

    class Config:
        env_prefix = "CLAW_CRON_WECHAT_WORK_"
        env_file = ".env"
        extra = "ignore"
```

### 4. Channel Status Check

Update `get_channel_status()` in `__init__.py`:

```python
elif channel_id == "wechat_work":
    if "webhook_url" not in channel_cfg:
        return "⚠", "配置不完整"
```

### 5. Capture Flow Integration

**For WeChat Work Webhook:**
- **No capture needed** - Webhook URL is static, configured in config.yaml
- Unlike QQ/Feishu which need openid (capture from WebSocket events)

**Simplified flow:**
```
channels add wechat_work
  → Prompt for webhook_url
  → Validate by sending test message
  → Save to config.yaml
  → Done (no capture needed)
```

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **itchat** | 封号风险高，维护停滞（2019年后），违反微信协议 | 企业微信机器人 Webhook |
| **WeChatBot / ClawBot** | PC hook方案风险高，需要图形环境，封号案例多 | 企业微信机器人 Webhook |
| **企业微信应用** | 集成复杂（OAuth2 + userID获取），不适合通知场景 | 企业微信机器人 Webhook（除非需要私聊） |
| **wework PyPI包 (0.1.4)** | 最后更新2019年，版本过旧，不支持新API | 直接使用httpx调用API，或使用官方weworkapi_python |

---

## Decision Matrix

| Criterion | WeChat Work Webhook | WeChat Work App | Personal WeChat |
|-----------|---------------------|-----------------|-----------------|
| **Integration complexity** | ✅ LOW | ❌ HIGH | ❌ VERY HIGH |
| **Authentication** | ✅ None | ❌ OAuth2 + token mgmt | ❌ Login session |
| **User ID management** | ✅ Not needed | ❌ Required | ❌ Implicit |
| **Private chat support** | ❌ No | ✅ Yes | ✅ Yes |
| **Rate limits** | ✅ 20/min | ⚠️ Complex | ❌ Variable |
| **Account safety** | ✅ Official API | ✅ Official API | ❌ High封号 risk |
| **Server deployment** | ✅ Easy | ✅ Easy | ❌ Need session |
| **Fit for notifications** | ✅ Perfect | ⚠️ Overkill | ❌ Risky |

---

## Recommendation

**Use 企业微信机器人 Webhook** for claw-cron WeChat channel implementation.

**Rationale:**
1. **Simplicity** - No auth, no user ID, just POST to webhook URL
2. **Alignment** - claw-cron only sends notifications (no need for private chat)
3. **Safety** - Official API, no封号 risk
4. **Pattern consistency** - Similar to QQBotChannel implementation
5. **No capture needed** - Webhook URL is static config (vs QQ/Feishu need openid capture)

**Defer 企业微信应用** unless:
- Private notifications to specific users become a requirement
- User ID mapping infrastructure already exists

**Never use 个人微信 solutions**:
- 封号风险 unacceptable for production use
- Violates WeChat terms of service
- Stability issues in server environments

---

## Sources

### High Confidence (Official Documentation)

- **企业微信开发者中心 - 消息推送配置说明** (https://developer.work.weixin.qq.com/document/path/91770) — Webhook API specification, message types, rate limits. Last updated: 2025-08-07.
- **企业微信开发者中心 - 发送应用消息** (https://developer.work.weixin.qq.com/document/path/90236) — Application message API, touser format, userid acquisition methods. Last updated: 2025-09-24.
- **企业微信开发者中心 - 专区程序SDK下载** (https://developer.work.weixin.qq.com/document/path/100250) — Official Python SDK version 1.2.3 (2025-02-10), example code 2.1.1 (2025-07-17).

### Medium Confidence (Community Sources)

- **weworkapi_python GitHub** (https://github.com/sbzhu/weworkapi_python) — Official Python lib, last updated 2026-04-17, 608 stars. Actively maintained.
- **Python 企业微信机器人 Webhook 自动化消息推送实战** (https://blog.csdn.net/weixin_29032337/article/details/158753068) — Webhook implementation examples, 2026-03-07.
- **企业微信API接口发消息实战** (https://cloud.tencent.com/developer/article/2550910) — Application message flow with Java examples, 2025-08-02.

### Low Confidence (Flagged for Validation)

- **2026 年微信机器人开发指南：官方 iLink 协议详解** (https://zhuanlan.zhihu.com/p/2019677743126704371) — Mentions official WeChat Bot API (iLink) released 2026-03. **Needs verification**: Application process, feature set, production availability.
- **微信接入AI避坑实战：ClawBot核心能力与封号风险解析** (https://blog.csdn.net/aidoudoulong/article/details/159430136) — 封号 risk analysis for personal WeChat solutions, 2026-03-24.

---

## Open Questions

1. **微信 iLink Official Bot API** - 2026年3月文章提到官方开放个人号Bot API，需要验证：
   - 申请条件和流程
   - 是否支持私聊消息发送
   - 是否适合claw-cron的通知场景
   - 如适用，可能成为未来私聊通知的解决方案

2. **Webhook URL管理** - 当前设计中webhook_url存储在config.yaml，需要确认：
   - 是否支持多个webhook（多个群）
   - recipients数组格式：`["webhook:KEY1", "webhook:KEY2"]` vs full URLs

3. **Markdown V2支持** - 文档提到markdown_v2（4096字节，不支持@和颜色），需要确认：
   - 是否需要支持markdown_v2（vs markdown）
   - 客户端版本兼容性要求

---

*Stack research for: WeChat Channel & Capture Enhancement*
*Researched: 2026-04-17*
