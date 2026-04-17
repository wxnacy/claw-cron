# Phase 13: Email Channel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 13-email-channel
**Areas discussed:** 收件人格式, 附件处理, Markdown处理, 多收件人, SMTP验证, 配置字段

---

## 收件人格式

| Option | Description | Selected |
|--------|-------------|----------|
| 直接邮箱地址 | recipient 直接是 'user@example.com'，简单直观，符合邮件习惯 | ✓ |
| 复用 c2c: 前缀 | 与 QQ/飞书格式一致 'c2c:user@example.com'，统一 parse_recipient 解析逻辑 | |

**User's choice:** 直接邮箱地址（推荐）
**Notes:** 简单直观，符合邮件使用习惯，不复用 c2c: 前缀模式

---

## 附件处理

| Option | Description | Selected |
|--------|-------------|----------|
| 仅支持文件路径 | attachment 参数为文件路径，简单实用，任务执行后附加日志文件场景 | ✓ |
| 路径和内存数据都支持 | 同时支持文件路径和 bytes 内容，灵活性更高但实现复杂 | |

**User's choice:** 仅支持文件路径（推荐）
**Notes:** 适合任务执行后附加日志文件场景，不支持内存数据（bytes）附件

---

## Markdown处理

| Option | Description | Selected |
|--------|-------------|----------|
| 转换为 HTML 发送 | 使用 markdown 库将 Markdown 转为 HTML，实现 send_markdown 真正意义 | ✓ |
| 直接作为 HTML | 假设用户传入的已是 HTML，不做转换，send_markdown 等同于发送 HTML | |
| 回退纯文本 | 不支持 Markdown，send_markdown 回退到 send_text 发送原始内容 | |

**User's choice:** 转换为 HTML 发送（推荐）
**Notes:** 使用 markdown Python 库进行转换，生成 multipart/alternative 邮件（包含 text 和 HTML 部分）

---

## 多收件人处理

| Option | Description | Selected |
|--------|-------------|----------|
| 逗号分隔字符串 | recipient = 'a@ex.com, b@ex.com'，一次发送多收件人，简单直观 | ✓ |
| 列表参数 | send_text(recipients: list[str], ...) 更类型安全，但接口不一致 | |

**User's choice:** 逗号分隔字符串（推荐）
**Notes:** 一次 SMTP 发送，所有收件人在同一封邮件，保持与 MessageChannel 接口一致

---

## SMTP验证

| Option | Description | Selected |
|--------|-------------|----------|
| 发送测试邮件 | 向配置的发件人地址发送一封验证邮件，验证完整发送流程 | ✓ |
| 仅连接验证 | 仅测试 SMTP 连接和认证，不发送实际邮件，验证快但更保守 | |

**User's choice:** 发送测试邮件（推荐）
**Notes:** 向配置的 from_email 地址发送验证邮件，验证完整的发送流程

---

## 配置字段

| Option | Description | Selected |
|--------|-------------|----------|
| 基础字段 | host, port, username, password, from_email, use_tls, enabled | ✓ |
| 基础 + 显示名 | 额外包含 from_name 用于邮件显示名 | |

**User's choice:** 基础字段（推荐）
**Notes:** 包含 host, port, username, password, from_email, use_tls, enabled

---

## Claude's Discretion

- EmailChannel 类的具体实现细节
- 错误处理和重试逻辑
- 邮件主题格式（默认使用任务名称）
- 配置状态检查 `get_channel_status` 的 email 特定逻辑

## Deferred Ideas

None — discussion stayed within phase scope
