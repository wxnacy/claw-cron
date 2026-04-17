# Phase 19: Context Injection & Feedback - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

脚本在执行时可接收系统注入的上下文，并可通过 stdout 回传结构化数据。实现三种注入方式（环境变量、模板变量、上下文文件）和一种回传方式（JSON stdout 解析），以及 CLI 上下文命令供 AI agent 调用。

**Requirements:** CTX-01, CTX-03, CTX-04, CTX-05

</domain>

<decisions>
## Implementation Decisions

### 环境变量注入方式
- **D-01:** 子进程继承当前进程环境变量，再叠加上 CLAW_ 前缀变量（`os.environ | claw_env`）
- **D-02:** 系统环境变量包含八个：CLAW_TASK_NAME, CLAW_TASK_TYPE, CLAW_LAST_EXIT_CODE, CLAW_LAST_OUTPUT, CLAW_EXECUTION_TIME, CLAW_TASK_CRON, CLAW_EXECUTION_COUNT, CLAW_LAST_EXECUTION_TIME
- **D-03:** CLAW_LAST_OUTPUT 截断到 4096 字符后注入环境变量，避免系统限制问题
- **D-04:** 用户自定义 env 变量优先级高于系统变量——当 env 中定义的变量与系统变量重名时，用户 env 覆盖系统变量
- **D-05:** 用户 env 变量按 Phase 18 D-02 决定，加 `CLAW_CONTEXT_` 前缀注入到子进程

### 模板变量渲染
- **D-06:** 新建独立模板渲染模块 `template.py`，统一处理所有 `{{ }}` 语法（包括现有的 `{{ date }}`/`{{ time }}` 和新增的 `{{ context.xxx }}`）
- **D-07:** notifier.py 的 `render_message` 改为调用 template.py，消除模板逻辑和通知逻辑的耦合
- **D-08:** 上下文变量使用 `{{ context.xxx }}` 语法，明确区分上下文变量和系统变量（如 `{{ context.signed_in }}`）

### 上下文文件注入
- **D-09:** CLAW_CONTEXT_FILE 使用固定路径文件（`~/.config/claw-cron/context/{task_name}_input.json`），每次执行前覆盖写入，不使用 tempfile
- **D-10:** 上下文文件内容为完整的 context.json 数据，包含系统变量和 script 回传的数据

### JSON stdout 解析
- **D-11:** 解析 stdout 的最后一行——如果是有效 JSON 则提取为上下文，如果不是则视为普通文本不解析。允许脚本先输出日志再输出 JSON
- **D-12:** script 回传的 JSON 采用合并模式——新 JSON 合并到现有 context.json 中，新键覆盖旧键，未涉及的键保留

### 上下文命令
- **D-13:** 新增 `claw-cron context` 子命令组，支持 `get` 和 `set` 操作
- **D-14:** `claw-cron context get <task_name>` — 输出任务上下文 JSON，AI agent 可通过 subprocess 调用获取
- **D-15:** `claw-cron context set <task_name> --key <key> --value <value>` — 命令行设置上下文键值对，AI agent 可回传执行结果

### Claude's Discretion
- template.py 的具体渲染实现（正则替换 vs 递归解析）
- context set 命令的具体参数设计（--key/--value 对 vs --json vs 两者都支持）
- 执行流程中环境变量构建、模板渲染、文件写入的调用顺序
- CLAW_EXECUTION_COUNT 的计数来源（context.json 中维护 vs 从日志计算）
- 上下文文件写入时机（执行前 vs 调度触发时）

</decisions>

<specifics>
## Specific Ideas

- 环境变量注入需修改 `executor.py:execute_task()` 中的 `subprocess.run` 调用，添加 `env` 参数
- 模板渲染影响两个地方：script 字段（执行前渲染）和 message 字段（通知时渲染）
- 最后一行 JSON 解析策略让脚本可以 `echo "logging..." && echo '{"signed_in": true}'` 混合输出
- context 命令让 AI agent 类型的任务也能读写上下文，不仅限于 command 类型

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Design
- `.planning/REQUIREMENTS.md` — CTX-01 (系统环境变量), CTX-03 (模板变量), CTX-04 (上下文文件), CTX-05 (JSON stdout 解析) 的完整需求定义
- `.planning/ROADMAP.md` — Phase 19 目标、依赖、成功标准
- `.planning/phases/18-data-model-context-storage/18-CONTEXT.md` — Phase 18 的决策，特别是 D-01~D-08 关于 env 字段、context 存储和 when 字段的设计

### Existing Code (must read for injection and parsing changes)
- `src/claw_cron/executor.py` — `execute_task()` 函数 (line 37-90), subprocess.run 调用需添加 env 参数
- `src/claw_cron/storage.py` — Task dataclass 定义 (line 22-49), env 字段已定义
- `src/claw_cron/context.py` — `load_context()` / `save_context()` 函数，上下文文件读写
- `src/claw_cron/notifier.py` — `render_message()` (line 90-113), 现有模板变量实现，需重构到 template.py
- `src/claw_cron/cli.py` — Click CLI group entry, 新增 context 子命令需在此注册

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `context.py` 的 `load_context` / `save_context`：可直接用于上下文文件注入的读写
- `notifier.py` 的 `render_message` 中的 `{{ }}` 替换模式：可作为 template.py 的参考实现
- `cli.py` 的 Click group 模式：新增 context 子命令可直接按现有模式注册

### Established Patterns
- subprocess.run 使用 shell=True, capture_output=True, text=True：添加 env 参数时需保持现有行为
- 配置文件统一存储在 `~/.config/claw-cron/` 目录：上下文文件也在此目录下
- cmd/ 目录下子命令模块模式：每个子命令一个文件（如 cmd_add.py, cmd_list.py）

### Integration Points
- `executor.py:execute_task()` — 主要修改点：构建 env、渲染模板、写入上下文文件、解析 stdout JSON
- `executor.py:execute_task_with_notify()` — 执行后需要将解析的上下文保存回 context.json
- `notifier.py:render_message()` — 需重构为调用 template.py
- `cli.py` — 新增 context 子命令组注册

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 19-context-injection-feedback*
*Context gathered: 2026-04-17*
