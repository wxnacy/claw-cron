# Phase 3: Execution Engine & Chat - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

实现两个能力：
1. **执行引擎** — command 类型用 subprocess 执行，agent 类型通过 AI 客户端无交互模式执行
2. **chat 命令** — 用自然语言完成任务的增删查、立即执行、启用/禁用

不包括：调度服务（Phase 4）、执行历史记录（v2）。

</domain>

<decisions>
## Implementation Decisions

### 日志系统

- **D-01:** 双日志分离
  - **系统日志**：服务启动状态、任务开始/结束/耗时等简要信息 → stdout/stderr；守护进程模式时写入 `logs/claw-cron.log`
  - **任务日志**：任务详细输出（启动信息 + 命令本身的 stdout/stderr）→ `logs/<name>.log`
  - 日志目录：`~/.config/claw-cron/logs/`（与 tasks.yaml 同目录）
- **D-02:** 新增 `log` 命令，用 `tail -f` 方式实时输出日志
  - `claw-cron log` → 系统日志（`logs/claw-cron.log`）
  - `claw-cron log <name>` → 指定任务日志（`logs/<name>.log`）
- **D-03:** `server` 启动时打印日志文件位置提示（系统日志路径 + 说明）

### Agent 客户端命令

- **D-04:** 内置默认命令模板（`{prompt}` 为占位符）：
  - `kiro-cli`: `kiro-cli -a --no-interactive "{prompt}"`
  - `codebuddy`: `codebuddy -y -p "{prompt}"`
  - `opencode`: `opencode run --dangerously-skip-permissions "{prompt}"`
- **D-05:** 全局配置文件 `~/.config/claw-cron/config.yaml`，可覆盖内置默认：
  ```yaml
  clients:
    kiro-cli: "kiro-cli -a --no-interactive {prompt}"
    codebuddy: "codebuddy -y -p {prompt}"
    opencode: "opencode run --dangerously-skip-permissions {prompt}"
  ```
- **D-06:** 任务级覆盖：`tasks.yaml` 每个任务可配置 `client_cmd` 字段，优先级最高
- **D-07:** 执行时优先级：任务级 `client_cmd` > 全局 `config.yaml` > 内置默认

### chat 命令能力

- **D-08:** chat 支持的操作：list / add / delete / 立即执行某任务 / enable / disable
- **D-09:** 单轮 intent 识别 — 每条消息独立，AI 识别意图后执行，不保留会话历史
- **D-10:** storage 层需新增 `update_task` 函数，用于修改 `Task.enabled` 字段（enable/disable）

### Claude's Discretion

- chat 的 tool_use 工具定义方式（参考 Phase 2 agent.py 的模式）
- 执行引擎的模块结构（`cmd/run.py` 还是 `executor.py`）
- `log` 命令的 tail 实现方式（subprocess tail vs Python watchdog）
- config.yaml 的加载时机（启动时 vs 按需）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/storage.py` — Task dataclass 定义，load_tasks / get_task / add_task / delete_task
- `src/claw_cron/agent.py` — Anthropic tool_use 对话模式参考（chat 命令复用此模式）
- `src/claw_cron/cli.py` — 注册新命令的位置
- `src/claw_cron/cmd/add.py` — _add_direct 函数，chat 的 add 操作可复用

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束、AI 客户端说明
- `.planning/REQUIREMENTS.md` — EXEC-01, EXEC-02, EXEC-03, CHAT-01

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `storage.Task` dataclass — 执行引擎直接用，需新增 `client_cmd: str | None` 字段
- `storage.load_tasks()` — chat list 操作直接调用
- `storage.get_task()` — chat 执行/enable/disable 操作用
- `cmd/add._add_direct()` — chat add 操作可直接调用
- `agent.py` 的 tool_use 循环 — chat 命令的 AI 对话参考实现

### Established Patterns
- Click command + Rich console（所有命令统一风格）
- Anthropic tool_use（agent.py 已有完整实现，chat 复用）
- YAML 存储（storage.py 已封装，新字段直接加到 Task dataclass）

### Integration Points
- `cli.py` — 注册 `run`（或 `exec`）、`log`、`chat` 命令
- `storage.Task` — 需加 `client_cmd` 字段（任务级客户端命令覆盖）
- `storage.py` — 需加 `update_task(name, **kwargs)` 函数

</code_context>

<specifics>
## Specific Ideas

- 日志目录与 tasks.yaml 同目录：`~/.config/claw-cron/`
- `log` 命令用 `tail -f` 语义（实时跟踪），系统日志默认，`log <name>` 看任务日志
- server 启动时输出类似：`System log: ~/.config/claw-cron/logs/claw-cron.log`

</specifics>

<deferred>
## Deferred Ideas

- 执行历史记录和日志查询（V2-01）
- enable/disable 独立 CLI 命令（V2-03）— chat 里支持，但不单独做命令

</deferred>

---

*Phase: 03-execution-engine-chat*
*Context gathered: 2026-04-16*
