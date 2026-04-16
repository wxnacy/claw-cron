# claw-cron

## What This Is

claw-cron 是一个结合 AI Agent 的智能定时任务系统。用户可以通过自然语言描述任务，由 AI 解析意图并生成 cron 配置；简单命令直接 subprocess 执行，复杂任务通过 AI 客户端（kiro-cli/codebuddy/opencode）的无交互模式执行。项目自带调度服务，不依赖系统 crontab。v2 新增消息通道支持，任务执行后可通过 iMessage、QQ 等通道通知用户。

## Core Value

用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## Requirements

### Validated

- ✅ **v1.0 里程碑已完成** (2026-04-16)
  - 项目基础架构 (Phase 1)
  - 任务管理命令 (Phase 2)
  - 执行引擎 & Chat (Phase 3)
  - 调度服务 (Phase 4)

### Validated

- ✅ **v2.1 里程碑已完成** (2026-04-17)
  - 通道管理命令 (Phase 9)
  - WebSocket & OpenID 捕获

### Active (v2.2)

- [ ] InquirerPy 集成：统一交互式 CLI 体验
- [ ] remind 交互式模式：无参数进入交互引导
- [ ] command 命令：新增专门创建 command 类型任务
- [ ] Cron 预设选择：降低 cron 语法学习门槛

### Validated

- ✅ **v2.0 里程碑已完成** (2026-04-16)
  - AI Provider 重构 (Phase 5)
  - 消息通道基础 + iMessage (Phase 6)
  - QQ 通道 (Phase 7)
  - 任务通知 + 定时提醒 (Phase 8)

### Out of Scope

- 系统 crontab 集成 — 项目自管理调度，不依赖 crontab
- Web UI — CLI 优先
- 多用户/权限管理 — 单用户本地工具
- 微信/飞书通道 — v2 不包含，后续扩展
- 消息接收/远程控制 — v2 仅支持发送通知

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
*Last updated: 2026-04-16 for v2.0 milestone start*
