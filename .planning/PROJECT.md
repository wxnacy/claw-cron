# claw-cron

## What This Is

claw-cron 是一个结合 AI Agent 的智能定时任务系统。用户可以通过自然语言描述任务，由 AI 解析意图并生成 cron 配置；简单命令直接 subprocess 执行，复杂任务通过 AI 客户端（kiro-cli/codebuddy/opencode）的无交互模式执行。项目自带调度服务，不依赖系统 crontab。v2 新增消息通道支持，任务执行后可通过 iMessage、QQ 等通道通知用户。

## Core Value

用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## Current Milestone: v3.1 Update 命令

**Goal:** 增加 update 命令，支持修改已有任务的字段，版本升级到 0.3.1

**Target features:**
- 增加 `update` 子命令，必传 `name` 参数定位任务
- 支持修改字段：cron、enabled、message、script、prompt
- 版本号升级到 0.3.1

## Requirements

### Validated

- ✅ **v1.0 里程碑已完成** (2026-04-16)
  - 项目基础架构 (Phase 1)
  - 任务管理命令 (Phase 2)
  - 执行引擎 & Chat (Phase 3)
  - 调度服务 (Phase 4)

- ✅ **v2.1 里程碑已完成** (2026-04-17)
  - 通道管理命令 (Phase 9)
  - WebSocket & OpenID 捕获

- ✅ **v2.3 里程碑已完成** (2026-04-17)
  - UX 改进 (Phase 11)
  - 飞书通道 (Phase 12)
  - 邮件通道 (Phase 13)

- ✅ **v2.4 里程碑已完成** (2026-04-17)
  - 微信通道 & Capture 增强 (Phase 14-17)

- ✅ **v3.0 里程碑已完成** (2026-04-18)
  - Command 上下文机制 (Phase 18-20)

### Active (v3.1)

- [ ] update 子命令，必传 name 参数
- [ ] 支持修改 cron 字段
- [ ] 支持修改 enabled 字段
- [ ] 支持修改 message 字段
- [ ] 支持修改 script 字段
- [ ] 支持修改 prompt 字段
- [ ] 版本升级到 0.3.1

### Out of Scope

- 系统 crontab 集成 — 项目自管理调度，不依赖 crontab
- Web UI — CLI 优先
- 多用户/权限管理 — 单用户本地工具
- 消息接收/远程控制 — 仅支持发送通知
- 钉钉通道 — 后续扩展
- Telegram 通道 — 后续扩展
- 跨任务上下文共享 — v3.0 仅支持同一任务内上下文传递，跨任务为未来扩展
- 复杂条件表达式 — 仅支持 == / != 简单判断，不支持 and/or/函数调用

## Context

- 技术栈：Python 3.12，Click，Rich，PyYAML，anthropic，openai
- 项目结构遵循 python-cli-project-design skill 规范
- AI 客户端无交互模式示例：`kiro-cli -a --no-interactive "prompt"`
- 调度器自实现，基于 cron 表达式解析，不依赖系统 crontab
- 消息通道：iMessage 使用 macpymessenger，QQ 使用开放平台 API

## Constraints

- **Tech**: Python >= 3.12，Click，Rich，anthropic，openai
- **Build**: hatch 构建，uv 管理依赖
- **AI**: 支持 Anthropic 和 OpenAI，默认 Anthropic
- **Channels**: iMessage (macOS only)，QQ (开放平台)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 自管理调度，不依赖 crontab | 可存储额外元数据（名称、描述、客户端类型），跨平台一致 | ✅ Validated v1.0 |
| AI 解析处理任务添加交互 | 自然语言 → cron 配置，降低用户使用门槛 | ✅ Validated v1.0 |
| Provider 模式重构 AI 调用 | 支持 OpenAI 和 Anthropic 双提供商，统一 Tool Use 接口 | — Pending |
| MessageChannel 抽象层 | 可扩展支持更多消息通道，统一发送接口 | — Pending |
| iMessage 使用 macpymessenger | 现代、类型安全、无需禁用 SIP | — Pending |
| QQ 使用开放平台 API | 官方支持，稳定性高 | — Pending |
| 邮件通道使用 aiosmtplib | 异步 SMTP，与项目现有异步架构一致 | — Pending |
| 飞书通道使用 lark-oapi | 官方 SDK，自动 token 管理，类型安全 | — Pending |
| 飞书私聊通知 | 类似 QQ Bot 的 open_id 机制，用户需先与机器人交互 | — Pending |
| 内联模式条件通知 | 检查+通知在同一任务，notify when 字段控制是否发送 | — Pending |
| JSON stdout 上下文回传 | script 输出 JSON 到 stdout，系统解析并持久化，简单可靠 | — Pending |
| 三路上下文注入 | 环境变量 + 模板变量 + 上下文文件，覆盖不同脚本使用习惯 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition:**
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone:**
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-18 for v3.1 milestone start*
