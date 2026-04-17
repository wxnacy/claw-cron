# Stack Research

**Domain:** claw-cron 邮件和飞书消息通道扩展
**Researched:** 2026-04-17
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **aiosmtplib** | 5.1.0 | 异步 SMTP 邮件发送 | 异步架构匹配项目现有模式（httpx.AsyncClient），生产稳定，零依赖，完整类型提示 |
| **lark-oapi** | latest | 飞书开放平台官方 SDK | 官方维护，自动处理 token 管理/加密解密/签名验证，完整类型系统，与 QQ Bot 实现模式一致 |
| **email.message** | built-in (Python 3.12) | 邮件消息构建 | Python 标准库，无需额外依赖，支持 MIME、附件、HTML 邮件 |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | already installed | 重试机制 | SMTP/Feishu API 调用失败时的自动重试（已在 QQ Bot 中使用） |
| **pydantic-settings** | already installed | 配置管理 | EmailConfig 和 FeishuConfig 的环境变量注入（已有模式） |
| **httpx** | 0.28.1 (installed) | HTTP 客户端 | Feishu API 调用（如不使用 SDK 的场景） |

## Installation

```bash
# 新增依赖（邮件）
uv add aiosmtplib

# 新增依赖（飞书）
uv add lark-oapi

# email.message 是 Python 标准库，无需安装
```

## Integration Points

### Email Channel (SMTP)

**配置参数：**
```python
class EmailConfig(BaseSettings, ChannelConfig):
    """邮件通道配置"""
    smtp_host: str           # SMTP 服务器地址
    smtp_port: int = 587     # SMTP 端口（默认 587 for TLS）
    smtp_user: str           # SMTP 用户名
    smtp_password: str       # SMTP 密码
    smtp_use_tls: bool = True  # 是否使用 TLS
    from_email: str          # 发件人邮箱地址
    from_name: str | None = None  # 发件人名称（可选）

    class Config:
        env_prefix = "CLAW_CRON_EMAIL_"
```

**使用示例：**
```python
from email.message import EmailMessage
import aiosmtplib

async def send_email(to: str, subject: str, content: str):
    message = EmailMessage()
    message["From"] = f"{config.from_name} <{config.from_email}>" if config.from_name else config.from_email
    message["To"] = to
    message["Subject"] = subject
    message.set_content(content)

    await aiosmtplib.send(
        message,
        hostname=config.smtp_host,
        port=config.smtp_port,
        username=config.smtp_user,
        password=config.smtp_password,
        start_tls=config.smtp_use_tls,
    )
```

**关键特性：**
- ✅ 异步非阻塞（匹配 MessageChannel 接口）
- ✅ 支持 TLS/SSL 加密
- ✅ 支持 HTML 邮件（通过 EmailMessage.set_type("text/html")）
- ✅ 支持附件（EmailMessage.add_attachment）
- ✅ 无需额外依赖（aiosmtplib 是零依赖库）

### Feishu Channel (Private Chat)

**配置参数：**
```python
class FeishuConfig(BaseSettings, ChannelConfig):
    """飞书通道配置"""
    app_id: str              # 飞书应用 ID
    app_secret: str          # 飞书应用密钥

    class Config:
        env_prefix = "CLAW_CRON_FEISHU_"
```

**认证流程：**
1. 使用 `app_id` + `app_secret` 获取 `tenant_access_token`
2. Token 有效期 2 小时，SDK 自动管理刷新
3. 使用 token 调用消息发送 API

**使用 SDK 发送私聊消息：**
```python
from lark_oapi.api.im.v1 import CreateMessageRequest

# SDK 自动处理 token 管理
request = CreateMessageRequest.builder() \
    .receive_id_type("open_id") \
    .request_body(
        CreateMessageRequestBody.builder()
        .receive_id("ou_xxx")  # 用户的 open_id
        .msg_type("text")
        .content("{\"text\":\"Hello from claw-cron\"}")
        .build()
    ) \
    .build()

response = client.im.v1.message.create(request)
```

**关键特性：**
- ✅ 官方 SDK，自动处理 token 生命周期
- ✅ 完整类型提示（匹配项目 strict 模式）
- ✅ 自动重试和错误处理
- ✅ 支持多种消息类型（文本、富文本、卡片）
- ✅ 用户标识使用 `open_id`（推荐）

**前提条件：**
1. 在飞书开放平台创建应用并获取 `app_id` 和 `app_secret`
2. 开启机器人能力
3. 发布应用版本
4. 用户需在机器人的可用范围内

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| aiosmtplib + email.message | emails library (1.1.1) | 需要高级功能如模板渲染（Jinja2）、DKIM 签名、HTML 清理时。但项目仅需基础邮件发送，标准库足够 |
| aiosmtplib | smtplib (built-in, sync) | 仅在同步代码中使用。项目 MessageChannel 是异步接口，必须使用异步库 |
| lark-oapi SDK | httpx 直接调用 API | 需要更细粒度控制或减少依赖时。但需手动实现 token 管理、加密解密，增加复杂度 |
| lark-oapi SDK | feishu-python-sdk (非官方) | 无官方 SDK 时。官方 SDK 更稳定、有完整文档和社区支持 |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| smtplib (同步版) | MessageChannel 接口是异步的，同步调用会阻塞事件循环 | aiosmtplib（异步版本） |
| 手动构建 HTTP 请求调用飞书 API | 需要手动实现 token 管理、过期刷新、错误重试，增加维护负担 | lark-oapi SDK（自动处理） |
| yagmail, Redmail 等高级邮件库 | 引入额外依赖，而标准库 email.message 已足够，且 aiosmtplib 支持异步 | email.message + aiosmtplib |
| Feishu webhook（群机器人） | 仅支持群聊，不支持私聊 | Feishu Bot API（使用 lark-oapi SDK） |

## Stack Patterns by Variant

**对于简单文本邮件：**
- 使用 EmailMessage + set_content()
- 标准 MIME 类型自动处理
- 无需手动构建 MIME 树

**对于 HTML 邮件：**
```python
message = EmailMessage()
message.set_content(html_content, subtype="html")
```

**对于带附件的邮件：**
```python
message.add_attachment(
    file_data,
    maintype="application",
    subtype="pdf",
    filename="report.pdf"
)
```

**对于飞书消息（使用 SDK）：**
- 文本消息：msg_type="text", content=JSON字符串
- 富文本消息：msg_type="post", content=富文本结构
- 卡片消息：msg_type="interactive", content=卡片JSON

**对于飞书消息（不使用 SDK）：**
- 需要手动调用 `/auth/v3/tenant_access_token/internal` 获取 token
- 需要实现 token 缓存和过期刷新（7200秒 = 2小时）
- 需要调用 `/im/v1/messages?receive_id_type=open_id` 发送消息
- 不推荐，SDK 已封装这些逻辑

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| aiosmtplib | 5.1.0 | Python >= 3.10 | 项目使用 Python 3.12 ✅ |
| lark-oapi | latest | Python >= 3.7 | 项目使用 Python 3.12 ✅ |
| httpx | 0.28.1 | aiosmtplib (无冲突) | 已安装，Feishu SDK 可能也使用 httpx |
| tenacity | installed | aiosmtplib (可选) | 可用于 SMTP 重试逻辑 |
| pydantic-settings | installed | lark-oapi (无冲突) | 配置管理模式保持一致 |

**依赖冲突检查：**
- ✅ aiosmtplib：零依赖，不会引入冲突
- ✅ lark-oapi：官方 SDK，设计良好，与项目现有依赖无冲突
- ✅ email.message：Python 标准库，无依赖问题

## Sources

- **aiosmtplib** — PyPI (2026-01-25), 官方文档 https://aiosmtplib.readthedocs.io/
  - MEDIUM confidence (WebSearch + 官方文档验证)

- **lark-oapi SDK** — GitHub 官方仓库 https://github.com/larksuite/oapi-sdk-python
  - MEDIUM confidence (官方文档 + GitHub 验证)

- **Feishu API 文档** — https://open.feishu.cn/document/server-docs/im-v1/message/create
  - HIGH confidence (官方 API 文档)

- **Feishu 认证文档** — https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
  - HIGH confidence (官方认证文档)

- **Python email 模块** — https://docs.python.org/3/library/email.message.html
  - HIGH confidence (Python 官方标准库文档)

- **emails library (未选用)** — PyPI https://pypi.org/project/emails/
  - MEDIUM confidence (WebSearch 验证，对比后决定不使用)

---
*Stack research for: claw-cron 邮件和飞书通道扩展*
*Researched: 2026-04-17*
