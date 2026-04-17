# Phase 20: Conditional Notification & Release - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

通知仅在 when 条件表达式满足时发送，版本升级到 0.3.0。实现 when 表达式求值器（== / != 运算符），在 executor.py 通知前评估条件，确保向后兼容（无 when 字段时始终发送通知），更新版本号。

**Requirements:** COND-02, COND-03, VER-01

</domain>

<decisions>
## Implementation Decisions

### When 表达式求值
- **D-01:** when 表达式右侧值采用自动类型推断——`true`/`false` 解析为布尔值，数字（如 `123`）解析为数字，其余作为字符串。与 context.json 中的值比较时进行类型匹配
- **D-02:** 仅支持 `==` 和 `!=` 两个运算符，与 REQUIREMENTS.md 和 PROJECT.md Out of Scope 一致。复合条件（and/or）和数值比较（>/</>=/<=）留给未来 ACOND-01/02
- **D-03:** 使用正则表达式解析 when 表达式，提取 key、operator、value 三部分。比简单字符串拆分更严谨
- **D-04:** when 字段仅支持单条件表达式（如 `signed_in == false`）。多条件需要多个 notify 配置项

### 通知拦截位置
- **D-05:** 在 executor.py 的 `if task.notify:` 块内、调用 `notify_task_result()` 之前检查 when 条件。此时 merged context 已保存且可直接使用，无需修改 Notifier 函数签名
- **D-06:** when 评估函数独立放在一个模块中（如 `condition.py` 或 `when_eval.py`），不在 executor.py 或 notifier.py 中内联实现

### 求值失败与日志
- **D-07:** when 条件不满足时记录 `logger.info` 日志（如 "Notification suppressed: when condition 'signed_in == false' not met"），用户可通过日志了解通知被抑制的原因
- **D-08:** when 表达式求值失败时（语法错误、context 中无对应键、类型不匹配），记录 `logger.warning` 日志并发送通知。保守策略：宁多发不漏发，确保用户不会因配置错误而遗漏重要通知

### Claude's Discretion
- when 表达式正则的具体实现模式
- 评估函数的模块名和函数签名
- 求值失败时日志的详细格式和内容
- 版本号升级的具体文件修改（`__about__.py` 中的 `__version__`）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Design
- `.planning/REQUIREMENTS.md` — COND-02 (条件表达式求值), COND-03 (无 when 字段默认行为), VER-01 (版本升级) 的完整需求定义
- `.planning/ROADMAP.md` — Phase 20 目标、依赖、成功标准
- `.planning/phases/18-data-model-context-storage/18-CONTEXT.md` — Phase 18 决策，特别是 D-09~D-11 关于 when 字段的设计
- `.planning/phases/19-context-injection-feedback/19-CONTEXT.md` — Phase 19 决策，特别是 D-11~D-12 关于 context 合并和 JSON stdout 解析

### Existing Code (must read for condition evaluation and notification changes)
- `src/claw_cron/notifier.py` — NotifyConfig dataclass (when 字段已定义), `notify_task_result()` 函数（通知发送逻辑）
- `src/claw_cron/executor.py` — `execute_task_with_notify()` 函数 (line 181), when 条件检查的插入点 (line 205)
- `src/claw_cron/context.py` — `load_context()` / `save_context()` 函数，context 读写
- `src/claw_cron/__about__.py` — 当前版本号 `0.2.1`，需升级到 `0.3.0`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `context.py` 的 `load_context()` — 执行 when 求值时可直接读取 context dict
- `notifier.py` 的 `NotifyConfig.when` — when 字段已在数据模型中定义并支持反序列化
- `template.py` 的正则替换模式 — 可参考正则实现风格

### Established Patterns
- 子进程执行后 merged context 已保存（executor.py line 197-203），when 评估可复用 merged dict
- 配置文件统一存储在 `~/.config/claw-cron/` 目录
- 每个功能模块一个文件（如 `template.py`, `context.py`）

### Integration Points
- `executor.py:execute_task_with_notify()` (line 205) — when 条件检查插入点，在 `if task.notify:` 之后、`notify_task_result()` 之前
- `src/claw_cron/__about__.py` — 版本号从 `0.2.1` 更新到 `0.3.0`

</code_context>

<specifics>
## Specific Ideas

- when 表达式示例：`signed_in == false`（用户已签到时不通知）、`status != "ok"`（状态非 ok 时通知）
- context 中常见值类型：布尔值（true/false）、字符串（如 "ok"、"error"）、数字（如 exit_code）
- 求值失败场景：when 中的 key 在 context 中不存在、表达式语法错误（如缺少运算符）、类型不匹配

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-conditional-notification-release*
*Context gathered: 2026-04-17*
