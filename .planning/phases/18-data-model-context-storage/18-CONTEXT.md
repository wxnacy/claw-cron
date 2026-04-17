# Phase 18: Data Model & Context Storage - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

扩展任务数据模型，支持环境变量定义（env 字段）、上下文持久化（独立 JSON 文件）、通知条件定义（when 字段）。此阶段定义数据结构和存储机制，注入与求值逻辑在 Phase 19/20 实现。

**Requirements:** CTX-02, CTX-06, COND-01

</domain>

<decisions>
## Implementation Decisions

### env 字段设计
- **D-01:** env 字段使用字典格式 `dict[str, str]`，YAML 中写为 `env: {API_KEY: xxx, MODE: check}`
- **D-02:** 用户定义的 env 变量自动加 `CLAW_CONTEXT_` 前缀注入到子进程（用户写 `API_KEY`，子进程收到 `CLAW_CONTEXT_API_KEY`）
- **D-03:** env 值支持模板变量语法（如 `{{ context.last_output }}`），Phase 18 仅定义数据模型，Phase 19 实现模板渲染

### 上下文存储设计
- **D-04:** Task dataclass 上不保存 context 字段，上下文仅存储在独立 JSON 文件中（配置与运行时状态分离）
- **D-05:** 每个任务一个 context 文件：`~/.config/claw-cron/context/{task_name}.json`
- **D-06:** context JSON 存储合并上下文——包含系统变量（如 last_exit_code）和 script 通过 stdout 回传的数据
- **D-07:** 执行前读取 context.json 注入给脚本，执行后写回 context.json（完整闭环）
- **D-08:** 上下文读写逻辑放在独立 `context.py` 模块，不在 storage.py 中

### when 条件字段设计
- **D-09:** when 字段使用单字符串格式，YAML 中写为 `when: signed_in == false`
- **D-10:** NotifyConfig dataclass 中 when 字段类型为 `when: str | None = None`，Phase 20 实现表达式解析器
- **D-11:** when 表达式引用任务上下文（context.json 中的键值），不直接引用执行结果

### Claude's Discretion
- Task dataclass 中 env 字段的默认值和序列化细节
- context.json 的具体 JSON 结构（如是否包含 metadata/timestamp）
- 向后兼容处理（现有 tasks.yaml 无 env/when 字段的任务如何加载）
- context.py 模块的具体函数签名
- context 目录不存在时的自动创建策略

</decisions>

<specifics>
## Specific Ideas

- 环境变量前缀 `CLAW_CONTEXT_` 遵循 REQUIREMENTS.md CTX-02 规范
- 上下文存储路径 `~/.config/claw-cron/context/{task_name}.json` 遵循 REQUIREMENTS.md CTX-06 规范
- 序列化使用 `dataclasses.asdict()`，新增字段需确保向后兼容（现有 YAML 无 env/when 字段时使用默认值）

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Design
- `.planning/REQUIREMENTS.md` — CTX-02 (env 字段), CTX-06 (上下文持久化), COND-01 (when 条件字段) 的完整需求定义
- `.planning/ROADMAP.md` — Phase 18 目标、依赖、成功标准

### Existing Code (must read for data model changes)
- `src/claw_cron/storage.py` — Task dataclass 定义 (line 22-47), 序列化/反序列化逻辑, YAML 读写
- `src/claw_cron/notifier.py` — NotifyConfig dataclass 定义 (line 42-83), from_dict 反序列化
- `src/claw_cron/executor.py` — execute_task 函数 (line 37-90), subprocess.run 调用方式

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `storage.py` 的 `_task_from_dict` / `save_tasks` 模式：可用于 context.py 的 load/save 函数参考
- `notifier.py` 的 `NotifyConfig.from_dict()` 模式：嵌套对象的反序列化参考
- `contacts.py` 的独立 YAML 存储模式：类似 context.py 的独立存储设计

### Established Patterns
- Dataclass + `dataclasses.asdict()` 序列化：所有数据模型使用此模式，新增字段需兼容
- `_load_raw` → `_task_from_dict` → `load_tasks` 三层加载模式
- 配置文件统一存储在 `~/.config/claw-cron/` 目录

### Integration Points
- `storage.py:_task_from_dict()` — 需要处理新的 `env` 字段反序列化
- `notifier.py:NotifyConfig.from_dict()` — 需要处理新的 `when` 字段反序列化
- `executor.py:execute_task()` — Phase 19 需要在此处注入 env 到 subprocess.run
- `notifier.py:notify_task_result()` — Phase 20 需要在此处求值 when 表达式

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-data-model-context-storage*
*Context gathered: 2026-04-17*
