# Phase 12: Feishu Channel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 12-feishu-channel
**Areas discussed:** OpenID 获取方式, SDK 选择, 频率限制处理, 收件人格式与消息类型

---

## OpenID 获取方式

| Option | Description | Selected |
|--------|-------------|----------|
| 交互式 capture 命令 | 类似 QQ Bot 的 capture 命令，启动事件监听，等待用户给机器人发送消息后自动获取 open_id | ✓ |
| 手动配置 | 用户自己在飞书后台查看 open_id，然后手动配置到 contacts.yaml | |
| 两者都支持 | 在 channels add feishu 后，自动启动 capture 流程 | |

**User's choice:** 交互式 capture 命令（推荐）
**Notes:** 与 QQ Bot 模式一致，启动事件监听，等待用户给机器人发送消息后自动获取 open_id

---

## SDK 选择

| Option | Description | Selected |
|--------|-------------|----------|
| 确认使用 lark-oapi | 官方 SDK，自动 token 管理、类型安全、错误处理，与现有架构一致 | ✓ |
| 纯 HTTP API | 直接 HTTP 调用，更轻量但需要自行处理 token、签名、错误等 | |

**User's choice:** 确认使用 lark-oapi（推荐）
**Notes:** PROJECT.md 已确定使用 lark-oapi 官方 SDK

---

## 频率限制处理

| Option | Description | Selected |
|--------|-------------|----------|
| tenacity 重试 | 与 QQBotChannel 一致，使用 tenacity 在频率限制时自动重试，无需额外队列 | ✓ |
| 本地队列 + 限流 | 实现本地消息队列，按频率限制速率发送，适合高并发场景 | |
| SDK 内置 + 重试兜底 | SDK 内置的限流处理 + tenacity 兜底 | |

**User's choice:** tenacity 重试（推荐）
**Notes:** 与 QQBotChannel 保持一致，stop_after_attempt(3), wait_exponential

---

## 收件人格式与消息类型

### 收件人格式

| Option | Description | Selected |
|--------|-------------|----------|
| c2c:OPENID | 与 QQ Bot 一致，可复用 parse_recipient 函数，代码统一 | ✓ |
| feishu:OPENID | 更明确的通道标识，但需要新增解析逻辑 | |
| 纯 OPENID | 最简单，直接传给 SDK，但缺少类型区分 | |

**User's choice:** c2c:OPENID（推荐）

### 消息类型

| Option | Description | Selected |
|--------|-------------|----------|
| 文本 + Markdown | 实现 send_text 和 send_markdown，Markdown 不支持时回退纯文本 | ✓ |
| 仅文本 | 只实现 send_text，Markdown 延后到后续阶段 | |

**User's choice:** 文本 + Markdown（推荐）

---

## Claude's Discretion

- FeishuChannel 类的具体实现细节
- capture 命令的事件监听实现方式
- 频率限制错误码的识别逻辑
- 配置状态检查 get_channel_status 的飞书特定逻辑

## Deferred Ideas

None — discussion stayed within phase scope
