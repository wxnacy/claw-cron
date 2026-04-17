# Phase 19: Context Injection & Feedback - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 19-context-injection-feedback
**Areas discussed:** 环境变量注入方式, 模板变量渲染, 上下文文件注入, JSON stdout 解析, 上下文命令

---

## 环境变量注入方式

| Option | Description | Selected |
|--------|-------------|----------|
| 干净环境 | 仅注入 CLAW_ 前缀变量，不继承当前进程环境 | |
| 继承当前环境 | 继承当前进程所有环境变量，再叠加上 CLAW_ 变量 | ✓ |

**User's choice:** 继承当前环境
**Notes:** executor.py 目前用 subprocess.run 默认继承环境，保持现有行为更安全

---

| Option | Description | Selected |
|--------|-------------|----------|
| 截断存储 (1024) | 截断到 1024 字符，环境变量安全 | |
| 截断存储 (4096) | 允许更长输出，接近系统限制 | ✓ |
| 截断存储 (2048) | 中间方案 | |
| 不注入 last_output | 仅通过 CLAW_CONTEXT_FILE 传递 | |

**User's choice:** 截断存储 (4096)
**Notes:** 4096 字符覆盖更多场景

---

| Option | Description | Selected |
|--------|-------------|----------|
| 四个核心变量 | CLAW_TASK_NAME, CLAW_TASK_TYPE, CLAW_LAST_EXIT_CODE, CLAW_LAST_OUTPUT | |
| 扩展变量集 | 额外增加 CLAW_EXECUTION_TIME, CLAW_TASK_CRON, CLAW_EXECUTION_COUNT, CLAW_LAST_EXECUTION_TIME | ✓ |

**User's choice:** 扩展变量集
**Notes:** 全部四个扩展变量均选中

---

| Option | Description | Selected |
|--------|-------------|----------|
| 用户 env 覆盖系统 | 用户自定义优先级最高 | ✓ |
| 系统变量优先 | 系统变量不可覆盖 | |

**User's choice:** 用户 env 覆盖系统

---

## 模板变量渲染

| Option | Description | Selected |
|--------|-------------|----------|
| 复用 render_message | 在 notifier.py 基础上扩展 | |
| 新建模板模块 | 创建 template.py 统一处理 | ✓ |
| 引入模板库 | 使用 Jinja2 等成熟引擎 | |

**User's choice:** 新建模板模块
**Notes:** 复用会耦合模板逻辑和通知逻辑，独立模块更清晰

---

| Option | Description | Selected |
|--------|-------------|----------|
| context.xxx | 如 {{ context.signed_in }}，明确区分 | ✓ |
| 直接引用键名 | 如 {{ signed_in }}，简洁但可能冲突 | |

**User's choice:** context.xxx
**Notes:** 遵循 REQUIREMENTS.md CTX-03 规范

---

## 上下文文件注入

| Option | Description | Selected |
|--------|-------------|----------|
| tempfile | 系统临时目录，进程结束后自动清理 | |
| 固定路径文件 | ~/.config/claw-cron/context/{task_name}_input.json | ✓ |

**User's choice:** 固定路径文件
**Notes:** 固定路径更可靠，AI agent 也可直接读取

---

| Option | Description | Selected |
|--------|-------------|----------|
| 完整 context.json | 包含系统变量和 script 回传数据 | ✓ |
| 仅系统变量 | 不含上次 script 回传的数据 | |
| 结构化分组 | {system: {...}, feedback: {...}} | |

**User's choice:** 完整 context.json

---

## JSON stdout 解析

| Option | Description | Selected |
|--------|-------------|----------|
| 整体解析 | 尝试将整个 stdout 解析为 JSON | |
| 提取 JSON 行 | 从混合输出中提取 JSON 行 | |
| 最后一行解析 | 只解析最后一行，如果是 JSON 则提取 | ✓ |

**User's choice:** 最后一行解析
**Notes:** 允许脚本先输出日志再输出 JSON

---

| Option | Description | Selected |
|--------|-------------|----------|
| 替换模式 | script 回传的 JSON 完全替换 feedback 部分 | |
| 合并模式 | 新 JSON 合并到现有 context，保留未覆盖的旧字段 | ✓ |

**User's choice:** 合并模式

---

## 上下文命令

| Option | Description | Selected |
|--------|-------------|----------|
| context 命令 | claw-cron context <task_name> 读取 | |
| context set 命令 | 支持命令行设置上下文 | |
| context get + set | 同时支持读取和设置 | ✓ |

**User's choice:** context get + set
**Notes:** AI agent 需要读写上下文能力

---

## Claude's Discretion

- template.py 的具体渲染实现
- context set 命令的参数设计
- 执行流程中的调用顺序
- CLAW_EXECUTION_COUNT 的计数来源
- 上下文文件写入时机

## Deferred Ideas

None — discussion stayed within phase scope
