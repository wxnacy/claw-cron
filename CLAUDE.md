<!-- GSD:project-start source:PROJECT.md -->
## Project

**claw-cron**

claw-cron 是一个结合 AI Agent 的智能定时任务系统。用户可以通过自然语言描述任务，由 Anthropic Agent 解析意图并生成 cron 配置；简单命令直接 subprocess 执行，复杂任务通过 AI 客户端（kiro-cli/codebuddy/opencode）的无交互模式执行。项目自带调度服务，不依赖系统 crontab。

**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行。

### Constraints

- **Tech**: Python >= 3.12，Click，Rich，anthropic
- **Build**: hatch 构建，uv 管理依赖
- **AI**: Anthropic API（添加任务时的交互解析），默认 AI 执行客户端为 kiro-cli
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
