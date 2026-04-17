# Feature Research

**Domain:** Message notification channels (邮件通道 & 飞书通道)
**Researched:** 2026-04-17
**Confidence:** HIGH (Official docs verified, multiple sources)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

#### Email Channel

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SMTP configuration | Standard email requirement | LOW | Host, port, credentials (username/password or app password) |
| Text message sending | Basic functionality | LOW | Plain text content support |
| HTML message sending | Rich formatting expected | LOW | HTML content for better presentation |
| Multiple recipients | Bulk notifications common | LOW | Support `to` list, CC, BCC |
| Attachment support | Log files, reports common | MEDIUM | File attachments for task outputs |
| Subject line | Email standard | LOW | Required for email messages |
| Error handling | Delivery failures happen | MEDIUM | SMTP errors, bounced emails |

#### Feishu Channel

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| App authentication | Required by platform | MEDIUM | App ID + App Secret, tenant_access_token |
| Text message sending | Basic functionality | LOW | Plain text content support |
| Private chat (C2C) | Direct notifications | MEDIUM | Send to user via open_id |
| Message acknowledgment | Know if sent successfully | LOW | Success/failure response |
| Rate limit handling | Platform requires it | MEDIUM | 5 QPS per user, automatic retry |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

#### Email Channel

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Template support | Consistent branding | MEDIUM | Pre-defined email templates for task notifications |
| Inline images | Better visual presentation | MEDIUM | Embed images in HTML content |
| Markdown rendering | Modern formatting | LOW | Convert task markdown to HTML email |
| Delivery tracking | Know if email arrived | HIGH | Delivery receipts, read receipts (optional) |
| Multiple SMTP providers | Flexibility | LOW | Support Gmail, Outlook, custom SMTP |

#### Feishu Channel

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Rich text (Post) messages | Better formatting | MEDIUM | Structured content with headings, lists |
| Interactive cards | Actionable notifications | HIGH | Buttons, forms for quick responses |
| File attachments | Share outputs | MEDIUM | Upload files before sending |
| Image attachments | Visual outputs | MEDIUM | Screenshot, chart sharing |
| Markdown support | Developer-friendly | MEDIUM | Send markdown formatted messages |
| Message cards | Professional look | HIGH | Structured notifications with cards |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

#### Email Channel

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Complex HTML templates | Beautiful emails | Maintenance burden, rendering issues across clients | Simple, responsive HTML templates |
| Email scheduling | Delayed send | Adds complexity, cron already handles timing | Let cron scheduler handle timing |
| Read receipts | Know when opened | Privacy concerns, unreliable | Send receipts only (delivery confirmation) |
| Email threading | Conversation view | Complex implementation, ID management | Simple subject line grouping |
| Marketing automation features | Campaigns | Out of scope for notifications | Keep it simple: send notifications only |

#### Feishu Channel

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Receiving messages | Two-way communication | PROJECT.md out of scope, requires WebSocket/events | Notification-only channel (单向通知) |
| Complex card builders | Rich UI | High complexity, maintenance burden | Simple card templates |
| Message reactions | User feedback | Requires event subscription, WebSocket | Keep notification-only |
| Group management | Multi-user | Complex permission handling | Focus on private chat (C2C) first |
| Real-time status | Typing indicators | Requires persistent connection | Fire-and-forget notifications |

## Feature Dependencies

```
[Email Channel]
    └──requires──> [SMTP Configuration]
                       └──requires──> [Credentials (username/password)]

[Feishu Channel]
    └──requires──> [App Registration]
                       └──requires──> [App ID + App Secret]
    └──requires──> [Permission: im:message + im:message:send_as_bot]
    └──requires──> [User open_id] (recipient identifier)

[Rich Text Support]
    └──requires──> [Content conversion logic]
                       └──for Feishu──> [Post message type]
                       └──for Email──> [HTML rendering]

[Attachment Support]
    └──requires──> [File upload]
                       └──for Feishu──> [Upload API + file_key]
                       └──for Email──> [MIME multipart]
```

### Dependency Notes

- **Feishu Channel requires App Registration:** Must create enterprise app in Feishu Open Platform, get App ID and Secret
- **Feishu Channel requires permissions:** `im:message` and `im:message:send_as_bot` permissions must be granted and published
- **Feishu requires open_id:** Recipient identifier is bot-specific open_id (user must interact with bot first to obtain it)
- **Email Channel requires SMTP credentials:** Username/password or app-specific password (Gmail, Outlook)
- **Attachment Support for Feishu requires upload:** Files must be uploaded first via API to get file_key before attaching to message
- **Rich Text diverges by channel:** Email uses HTML, Feishu uses "post" message type with structured JSON

## MVP Definition

### Launch With (v2.3)

Minimum viable product — what's needed to validate the concept.

**Email Channel:**
- [x] SMTP configuration (host, port, username, password)
- [x] Text message sending (plain text content)
- [x] HTML message sending (basic HTML support)
- [x] Subject line support
- [x] Basic error handling (SMTP errors)
- [x] Configuration via environment variables (CLAW_CRON_EMAIL_*)

**Feishu Channel:**
- [x] App authentication (App ID + App Secret)
- [x] Tenant access token management (auto-refresh)
- [x] Text message sending (plain text content)
- [x] Private chat support (send to open_id)
- [x] Basic error handling (API errors, rate limits)
- [x] Configuration via environment variables (CLAW_CRON_FEISHU_*)

### Add After Validation (v2.x)

Features to add once core is working.

**Email Channel:**
- [ ] Attachment support — Task outputs with file attachments
- [ ] Markdown to HTML conversion — Better formatting for task notifications
- [ ] Template support — Consistent notification branding

**Feishu Channel:**
- [ ] Rich text (Post) messages — Better formatting with headings, lists
- [ ] Markdown message support — Developer-friendly formatting
- [ ] File/image attachments — Share task outputs (requires upload API)

### Future Consideration (v3+)

Features to defer until product-market fit is established.

**Email Channel:**
- [ ] Inline images — Embed images in HTML content
- [ ] Delivery/read tracking — Know if notifications arrived
- [ ] Multiple SMTP provider presets — Easy config for Gmail, Outlook

**Feishu Channel:**
- [ ] Interactive cards — Actionable notifications with buttons
- [ ] Message cards — Professional structured notifications
- [ ] Group chat support — Send to groups (group:GROUP_OPENID format)

## Feature Prioritization Matrix

### Email Channel

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SMTP config + text sending | HIGH | LOW | P1 |
| HTML message sending | HIGH | LOW | P1 |
| Subject line support | HIGH | LOW | P1 |
| Error handling | HIGH | MEDIUM | P1 |
| Attachment support | MEDIUM | MEDIUM | P2 |
| Markdown to HTML | MEDIUM | LOW | P2 |
| Template support | LOW | MEDIUM | P3 |

### Feishu Channel

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| App authentication + token | HIGH | MEDIUM | P1 |
| Text message sending | HIGH | LOW | P1 |
| Private chat (C2C) | HIGH | MEDIUM | P1 |
| Error handling + rate limits | HIGH | MEDIUM | P1 |
| Rich text (Post) messages | MEDIUM | MEDIUM | P2 |
| Markdown support | MEDIUM | LOW | P2 |
| File/image attachments | MEDIUM | HIGH | P3 |
| Interactive cards | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

### Email Channels (Python Libraries)

| Feature | smtplib (stdlib) | yagmail | Our Approach |
|---------|------------------|---------|--------------|
| API simplicity | LOW (verbose) | HIGH (clean) | Use yagmail for simplicity |
| HTML support | Manual construction | Native support | Use yagmail HTML support |
| Attachments | Manual MIME | Native support | Use yagmail attachments |
| Connection management | Manual | Automatic | Leverage yagmail auto-connect |
| Password security | Manual | keyring support | Use env vars (simpler) |

**Recommendation:** Use yagmail library instead of raw smtplib for cleaner API and built-in HTML/attachment support.

### Feishu Channels (SDKs)

| Feature | Raw HTTP API | lark-oapi SDK | Our Approach |
|---------|--------------|---------------|--------------|
| Authentication | Manual token management | Auto token refresh | Use lark-oapi SDK |
| Type safety | No | Yes (full type hints) | Leverage SDK types |
| Error handling | Manual parsing | Structured errors | Use SDK error handling |
| Message building | Manual JSON | Builder pattern | Use SDK builders |
| Documentation | API docs only | SDK + API docs | Reference both |

**Recommendation:** Use official lark-oapi Python SDK for type safety, auto token management, and structured errors.

## Implementation Complexity Notes

### Email Channel (LOW-MEDIUM complexity)

**Simple parts:**
- SMTP connection (yagmail handles)
- Text/HTML content sending
- Basic error handling

**Moderate complexity:**
- Attachment support (file paths, MIME types)
- Multiple recipients (list handling)
- SMTP provider variations (Gmail app passwords, port differences)

**Sources of complexity:**
- Different SMTP providers have different requirements
- App passwords vs regular passwords (Gmail, Outlook)
- SSL/TLS configuration varies by provider

### Feishu Channel (MEDIUM complexity)

**Simple parts:**
- App ID/Secret configuration
- Text message sending (simple JSON)
- Token management (SDK handles refresh)

**Moderate complexity:**
- open_id requirement (user must interact with bot first)
- Permission configuration (must be granted + published)
- Rate limit handling (5 QPS per user)
- Error code interpretation

**Sources of complexity:**
- Permission system (must configure in Feishu admin console)
- User must obtain open_id (requires prior interaction)
- Event subscription not needed for sending, but needed for receiving open_id
- Publishing app version required for permissions to take effect

**Common pitfalls (from debugging guides):**
1. **Event subscription missing:** Without `im.message.receive_v1` subscription, won't receive user messages (needed to get open_id)
2. **Permissions not published:** Permissions must be added AND app version published
3. **Config key errors:** Using wrong key names (e.g., `dmAllowFrom` vs `allowFrom`)
4. **User not in scope:** User must be in app's available range
5. **User stopped bot:** User may have blocked bot notifications

## Sources

### Email Channel
- [Python yagmail库教程：轻松发送电子邮件](https://cloud.tencent.com/developer/article/2554931) - HIGH confidence (verified with library docs)
- [Python邮件发送全场景实现](https://blog.csdn.net/dengjianbin/article/details/151931926) - MEDIUM confidence
- [Python SMTP官方文档](https://docs.python.org/3/library/smtplib.html) - HIGH confidence (official)

### Feishu Channel
- [发送消息 - 飞书开放平台](https://open.feishu.cn/document/server-docs/im-v1/message/create?lang=zh-CN) - HIGH confidence (official docs)
- [消息常见问题 - 飞书开放平台](https://open.feishu.cn/document/server-docs/im-v1/faq) - HIGH confidence (official)
- [飞书机器人接入完整调试记录](https://leapvale.com/blog/technique/feishu-bot-setup-guide/) - HIGH confidence (real-world troubleshooting)
- [开发前准备 - 飞书 Python SDK](https://open.feishu.cn/document/server-side-sdk/python--sdk/preparations-before-development?lang=zh-CN) - HIGH confidence (official)
- [lark-oapi PyPI](https://pypi.org/project/lark-oapi/) - HIGH confidence (official SDK)

### Integration Patterns
- [Existing claw-cron channels](src/claw_cron/channels/) - HIGH confidence (project code)
- [MessageChannel abstraction](src/claw_cron/channels/base.py) - HIGH confidence (project code)

---
*Feature research for: Email & Feishu notification channels*
*Researched: 2026-04-17*
