# claw-cron

## What This Is

claw-cron 是一个结合 AI Agent 的智能定时任务系统。用户可以通过自然语言描述任务，由 Anthropic Agent 解析意图并生成 cron 配置；简单命令直接 subprocess 执行，复杂任务通过 AI 客户端（kiro-cli/codebuddy/opencode）的无交互模式执行。项目自带调度服务，不依赖系统 crontab。

## Core Value

用自然语言描述定时任务，AI 帮你配置并按时执行。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 用户可以通过 AI 对话添加定时任务（Anthropic Agent 解析意图，生成 cron 表达式 + 配置）
- [ ] 任务执行支持两种模式：简单命令直接 subprocess 执行，复杂任务走 AI 客户端无交互模式
- [ ] 支持 kiro-cli、codebuddy、opencode 三种 AI 客户端，默认 kiro-cli，添加任务时可指定
- [ ] 任务配置存储为 YAML 文件，项目自管理
- [ ] CLI 提供 list、delete 命令，也支持通过 AI 对话完成增删查
- [ ] add 命令支持直接模式：提供完整参数（cron 表达式、执行类型、脚本/提示词、AI 客户端）时跳过 AI 交互直接生成任务，供其他 Agent 作为 skill 调用
- [ ] server 命令启动调度服务，默认前台运行，--daemon 参数支持守护进程模式
- [ ] 遵循 python-cli-project-design 规范（Click + Rich + hatch + uv）

### Out of Scope

- 系统 crontab 集成 — 项目自管理调度，不依赖 crontab
- Web UI — CLI 优先
- 多用户/权限管理 — 单用户本地工具

## Context

- 技术栈：Python 3.12，Click，Rich，PyYAML，anthropic SDK
- 项目结构遵循 python-cli-project-design skill 规范
- AI 客户端无交互模式示例：`kiro-cli -a --no-interactive "prompt"`
- 调度器自实现，基于 cron 表达式解析，不依赖系统 crontab

## Constraints

- **Tech**: Python >= 3.12，Click，Rich，anthropic
- **Build**: hatch 构建，uv 管理依赖
- **AI**: Anthropic API（添加任务时的交互解析），默认 AI 执行客户端为 kiro-cli

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 自管理调度，不依赖 crontab | 可存储额外元数据（名称、描述、客户端类型），跨平台一致 | — Pending |
| Anthropic Agent 处理任务添加交互 | 自然语言 → cron 配置，降低用户使用门槛 | — Pending |
| server 默认前台，--daemon 可选 | 开发调试友好，生产可守护进程 | — Pending |
| 任务配置 YAML 存储 | 人类可读，易于手动编辑和版本控制 | — Pending |

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
*Last updated: 2026-04-16 after initialization*
