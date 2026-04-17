# Project Research Summary

**Project:** claw-cron 邮件和飞书消息通道扩展
**Domain:** 消息通知通道集成
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

claw-cron is adding email and Feishu notification channels to its existing channel ecosystem (iMessage, QQBot). The recommended approach mirrors the existing QQBot architecture: use `aiosmtplib` for async SMTP sending and the official `lark-oapi` SDK for Feishu private messaging. Both channels inherit from the existing `MessageChannel` abstract base class, leveraging the established registry pattern for seamless integration.

The primary risks are security-related (credential storage) and integration complexity (Feishu event subscriptions, token management). These are mitigated by following the QQBot patterns: environment variables for all secrets, token caching with preemptive refresh, and unified error handling via `MessageResult`. The Feishu channel requires more setup (app registration, event subscription, permission publishing) compared to email (SMTP credentials only).

Build order should prioritize EmailChannel first (simpler, independent), then FeishuChannel (depends on Feishu platform configuration). Both channels must implement consistent error handling that distinguishes temporary failures (retry) from permanent failures (no retry, log and alert).

## Key Findings

### Recommended Stack

Email uses `aiosmtplib` (async SMTP, zero dependencies) + Python's built-in `email.message` for MIME construction. Feishu uses the official `lark-oapi` SDK which handles token lifecycle, encryption, and type safety automatically. Both leverage existing project dependencies (`tenacity` for retries, `pydantic-settings` for config, `httpx` for HTTP).

**Core technologies:**
- **aiosmtplib 5.1.0** — async SMTP email sending — matches project's async architecture, zero dependencies
- **lark-oapi SDK** — Feishu API integration — official SDK with auto token refresh, full type hints
- **email.message** — MIME message construction — Python stdlib, supports HTML/attachments

### Expected Features

**Must have (table stakes):**
- SMTP configuration (host, port, credentials) — users expect email basics
- Text and HTML message sending — standard email functionality
- Feishu app authentication — required by platform
- Private chat (C2C) messaging — direct notifications to users
- Rate limit handling — both platforms enforce limits

**Should have (competitive):**
- Attachment support — task outputs, log files
- Rich text (Post) messages for Feishu — better formatting
- Markdown support — developer-friendly formatting

**Defer (v2+):**
- Interactive cards (Feishu) — complex, high maintenance
- Delivery/read tracking — unreliable, privacy concerns
- Template support — not essential for notifications

### Architecture Approach

Both channels follow the existing `MessageChannel` pattern established by `QQBotChannel`. EmailChannel uses async SMTP via `aiosmtplib.send()`. FeishuChannel manages `tenant_access_token` (2-hour expiry) with preemptive refresh, mirroring QQBot's `TokenInfo` caching pattern.

**Major components:**
1. **EmailChannel** (`channels/email.py`) — SMTP sending, TLS support, MIME construction
2. **FeishuChannel** (`channels/feishu.py`) — API client, token management, retry logic
3. **Channel Registry** (`channels/__init__.py`) — register both channels for `get_channel()` factory
4. **CLI Integration** (`cmd/channels.py`) — add/list/delete commands for email and feishu types

### Critical Pitfalls

1. **SMTP credentials in plaintext** — use environment variables (`CLAW_CRON_EMAIL_*`), never hardcode
2. **Ignoring SMTP error code differences** — 4xx = retry with backoff, 5xx = permanent failure, no retry
3. **Feishu event subscription missing** — must subscribe to `im.message.receive_v1` and publish app version
4. **Token expiration without refresh** — cache token with `buffer_seconds` margin, refresh before expiry
5. **Inconsistent error handling across channels** — all channels must return unified `MessageResult` with `permanent_failure` flag

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Channel Infrastructure
**Rationale:** Define base abstractions and registry before implementing concrete channels. Establishes consistent patterns.
**Delivers:** Unified error handling (`ChannelConfigError`, `ChannelAuthError`, `ChannelSendError`), `MessageResult` standard, config patterns
**Addresses:** Pitfall #5 (inconsistent error handling), Pitfall #1 (credential storage)
**Avoids:** Technical debt from divergent error handling patterns

### Phase 2: EmailChannel Implementation
**Rationale:** Simpler, independent of external platform configuration. Validates channel architecture.
**Delivers:** Working email notifications via SMTP
**Uses:** aiosmtplib, email.message, pydantic-settings
**Implements:** EmailChannel class with send_text/send_markdown, CLI integration
**Avoids:** Pitfall #2 (SMTP error codes), Pitfall #6 (rate limits via tenacity retry)

### Phase 3: FeishuChannel Implementation
**Rationale:** More complex — requires app registration, event subscription, token management. Builds on validated patterns.
**Delivers:** Working Feishu private message notifications
**Uses:** lark-oapi SDK, httpx, tenacity
**Implements:** FeishuChannel with token caching, API integration, retry logic
**Avoids:** Pitfall #3 (event subscription), Pitfall #4 (token expiration), Pitfall #5 (user scope)

### Phase 4: Integration Testing & UX Polish
**Rationale:** Validate multi-channel scenarios, improve user experience with config validation
**Delivers:** Tested multi-channel notifications, improved CLI feedback
**Addresses:** Pitfall #7 (UX issues — channels add/list validation)

### Phase Ordering Rationale

- **Dependency-based:** Phase 1 defines abstractions that Phase 2-3 implement
- **Complexity gradient:** Email (simpler) before Feishu (complex) to validate architecture early
- **Pitfall coverage:** Each phase addresses specific pitfalls from research
- **Incremental value:** Email delivers value faster while Feishu setup completes

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** Feishu open_id acquisition — requires API call or WebSocket event capture, needs user flow design

Phases with standard patterns (skip research-phase):
- **Phase 1:** Existing QQBot architecture provides clear patterns
- **Phase 2:** SMTP is well-documented, aiosmtplib API is straightforward

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official SDKs, verified docs, existing patterns in project |
| Features | HIGH | Official Feishu docs, multiple email library comparisons |
| Architecture | HIGH | Existing QQBotChannel provides proven template |
| Pitfalls | HIGH | Official docs + real-world troubleshooting guides |

**Overall confidence:** HIGH

### Gaps to Address

- **Feishu open_id acquisition workflow:** Research indicates users must interact with bot first. Consider adding `channels capture` command (like QQBot) or document API-based lookup method. Handle during Phase 3 planning.
- **SMTP provider variations:** Gmail requires app passwords, Outlook has different defaults. Document common configurations. Handle during Phase 2 documentation.

## Sources

### Primary (HIGH confidence)
- aiosmtplib Documentation — https://aiosmtplib.readthedocs.io/
- Feishu Message API — https://open.feishu.cn/document/server-docs/im-v1/message/create
- Feishu Authentication — https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal
- Python email.message — https://docs.python.org/3/library/email.message.html
- Existing QQBotChannel — `src/claw_cron/channels/qqbot.py`

### Secondary (MEDIUM confidence)
- lark-oapi GitHub — https://github.com/larksuite/oapi-sdk-python
- Feishu Bot Troubleshooting — https://leapvale.com/blog/technique/feishu-bot-setup-guide/
- SMTP Errors Guide — https://www.twilio.com/docs/sendgrid/for-developers/sending-email/smtp-errors-and-troubleshooting

### Tertiary (LOW confidence)
- Chinese blog posts on email sending — general patterns, verified against official docs

---
*Research completed: 2026-04-17*
*Ready for roadmap: yes*
