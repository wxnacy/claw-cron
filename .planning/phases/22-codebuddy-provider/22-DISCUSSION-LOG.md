# Phase 22: Codebuddy Provider - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 22-codebuddy-provider
**Areas discussed:** SDK 集成方式, 参数设计, API Key 缺失处理, Tool 格式适配

---

## SDK 集成方式

| Option | Description | Selected |
|--------|-------------|----------|
| Python SDK | 有官方 Python SDK，可以直接 import 使用 | ✓ |
| CLI 封装 | 通过 subprocess 调用 CLI，解析输出 | |
| HTTP API | 需要调用 HTTP API，无 SDK | |

**User's choice:** Python SDK
**Notes:** 使用 `codebuddy_agent_sdk` 包，工具调用基于 MCP 协议

---

## Tool Use 格式

| Option | Description | Selected |
|--------|-------------|----------|
| OpenAI 格式 | 与 OpenAI 兼容，可以直接复用现有工具定义 | |
| Anthropic 格式 | 与 Anthropic 兼容，可以直接复用现有工具定义 | |
| 自定义格式 | 有自己独特的工具调用格式，需要专门适配 | ✓ |

**User's choice:** 不确定，需查阅文档
**Notes:** 调研后发现使用 MCP 协议，需要新的转换器

---

## 参数设计

### 默认 Provider

| Option | Description | Selected |
|--------|-------------|----------|
| codebuddy | 与 REQUIREMENTS 中描述一致，新用户默认使用 Codebuddy | ✓ |
| claude | 保持向后兼容，现有用户不受影响 | |

**User's choice:** codebuddy (推荐)

### 配置支持

| Option | Description | Selected |
|--------|-------------|----------|
| 支持配置文件 | 用户可以配置默认 agent/model，命令行参数覆盖配置 | ✓ |
| 仅命令行参数 | 只支持命令行参数，简单直接 | |

**User's choice:** 支持配置文件 (推荐)

---

## API Key 缺失处理

### 提示内容

| Option | Description | Selected |
|--------|-------------|----------|
| 简单提示 | 仅显示错误信息，告知用户需要设置 CODEBUDDY_API_KEY | |
| 详细指引 | 显示错误信息和配置方法，如 export 或创建配置文件 | ✓ |

**User's choice:** 详细指引 (推荐)

### 退出行为

| Option | Description | Selected |
|--------|-------------|----------|
| 友好退出 | 显示提示后正常退出，exit code 为 0 | ✓ |
| 错误退出 | 显示提示后退出，exit code 为 1（表示错误） | |

**User's choice:** 友好退出 (推荐)

---

## Claude's Discretion

- 具体的错误提示文案
- 配置文件的具体格式和字段名

## Deferred Ideas

None — discussion stayed within phase scope
