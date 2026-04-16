# Phase 3: Execution Engine & Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 03-execution-engine-chat
**Areas discussed:** 命令执行输出, Agent 客户端调用方式, chat 能力边界, chat 对话上下文

---

## 命令执行输出

| Option | Description | Selected |
|--------|-------------|----------|
| 实时打印 | stdout/stderr 直接流到终端 | |
| 静默 + 退出码 | 只记录成功/失败 | |
| 捕获 + 记录到日志文件 | 输出写入 logs/<name>.log | |
| 双日志分离（自定义） | 系统日志 + 任务日志，新增 log 命令 | ✓ |

**User's choice:** 双日志分离 — 系统日志（stdout/守护进程时写文件）+ 任务日志（logs/<name>.log）。新增 `log` 命令用 tail -f 方式查看。server 启动时打印日志文件位置。

---

## Agent 客户端调用方式

| Option | Description | Selected |
|--------|-------------|----------|
| 硬编码 | 三个客户端命令写死 | |
| 可配置 | 全局 config.yaml + 任务级覆盖 | ✓ |

**User's choice:** 需要自定义配置。全局 `config.yaml` 设默认，`tasks.yaml` 每个任务可独立配置 `client_cmd`。

**客户端命令确认：**
- kiro-cli: `kiro-cli -a --no-interactive "{prompt}"`
- codebuddy: `codebuddy -y -p "{prompt}"`
- opencode: `opencode run --dangerously-skip-permissions "{prompt}"`

---

## chat 能力边界

| Option | Description | Selected |
|--------|-------------|----------|
| 增删查 | list / add / delete | |
| 增删查 + 立即执行 | 额外支持手动触发任务 | |
| 增删查 + 立即执行 + enable/disable | 完整操作集 | ✓ |

**User's choice:** 选项 3 — 支持 list / add / delete / 立即执行 / enable / disable。

---

## chat 对话上下文

| Option | Description | Selected |
|--------|-------------|----------|
| 单轮 intent 识别 | 每条消息独立，无历史 | ✓ |
| 保持会话历史 | messages 累积，支持上下文引用 | |

**User's choice:** 先单轮，简单点。

---

## Claude's Discretion

- chat tool_use 工具定义方式
- 执行引擎模块结构
- log 命令的 tail 实现
- config.yaml 加载时机
