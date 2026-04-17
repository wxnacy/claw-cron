# Phase 16: WeChat Channel - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 16-wechat-channel
**Areas discussed:** Capture 实现方式, 消息类型与格式, Token 管理策略, 频率限制与错误处理

---

## Capture 实现方式

| Option | Description | Selected |
|--------|-------------|----------|
| HTTP 回调服务器 | 用户给应用发消息，本地启动 HTTP 服务器监听回调。需公网 URL 或端口转发 | |
| 手动输入 userid | 用户在 capture 命令中直接输入企业微信 userid，最简单 | |
| 两种方式都支持 | 同时支持回调和手动输入，灵活但复杂度高 | ✓ |

**User's choice:** 两种方式都支持
**Notes:** 后续澄清：回调优先，先支持手动输入，后续再加 HTTP 回调方式。企业微信没有官方 WebSocket 推送服务，因此回调方式需要公网 URL，配置较复杂。

---

## 消息类型与格式

| Option | Description | Selected |
|--------|-------------|----------|
| 文本 + Markdown | 满足 REQUIREMENTS，企业微信 API 原生支持 | ✓ |
| 文本 + Markdown + 卡片 | 额外支持卡片消息，视觉更好但增加复杂度 | |

**User's choice:** 文本 + Markdown
**Notes:** 收件人格式复用 c2c:userid 模式，与其他通道保持一致。Markdown 不支持时回退纯文本。

---

## Token 管理策略

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 TokenInfo 模式 | 在 WeComChannel 内复制 QQBot 的 TokenInfo 模式，独立管理 | ✓ |
| 抽取公共 TokenManager | 抽取公共类，QQBot 和 WeCom 共用，更整洁但增加重构范围 | |

**User's choice:** 复用 TokenInfo 模式
**Notes:** access_token 仅内存缓存，不持久化。与 QQBot 模式一致，提前 60 秒刷新。

---

## 频率限制与错误处理

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 tenacity 模式 | stop_after_attempt(3) + wait_exponential，与 QQBot/Feishu 一致 | ✓ |
| 不重试，直接报错 | 企业微信限流较宽松，直接报错让用户重试 | |

**User's choice:** 复用 tenacity 模式
**Notes:** 凭证验证在 add 时进行，调用 access_token API 验证有效性。配置字段：corp_id, agent_id, secret。

---

## Claude's Discretion

- WeComChannel 类的具体实现细节
- WeComConfig 配置类字段和验证
- 企业微信 API 错误码识别和映射
- capture 手动输入的交互提示语
- 配置状态检查的 wecom 特定逻辑

## Deferred Ideas

- HTTP 回调 capture — 企业微信自动捕获方式，需公网 URL，延后到后续 phase
