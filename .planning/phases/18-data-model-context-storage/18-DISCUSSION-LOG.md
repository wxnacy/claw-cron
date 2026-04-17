# Phase 18: Data Model & Context Storage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 18-data-model-context-storage
**Areas discussed:** env 字段设计, 上下文存储设计, when 条件字段设计

---

## env 字段设计

| Option | Description | Selected |
|--------|-------------|----------|
| 字典格式 | YAML 字典 `env: {API_KEY: xxx}`，直观易读 | ✓ |
| 列表格式 | YAML 列表 `env: [{key: API_KEY, value: xxx}]`，冗长但顺序可保证 | |

**User's choice:** 字典格式
**Notes:** 字典格式更直观，env 变量本身不需要顺序保证

| Option | Description | Selected |
|--------|-------------|----------|
| 自动加前缀 | 用户写 `API_KEY`，系统注入 `CLAW_CONTEXT_API_KEY` | ✓ |
| 原样注入 | 用户写什么就注入什么，更灵活但污染环境变量空间 | |
| 混合模式 | 自动加前缀，但 CLAW_ 开头的变量原样注入 | |

**User's choice:** 自动加前缀
**Notes:** 遵循 CTX-02 规范，避免命名冲突

| Option | Description | Selected |
|--------|-------------|----------|
| 支持模板 | env 值支持 `{{ context.xxx }}` 语法，Phase 19 实现渲染 | ✓ |
| 纯字符串 | env 值为纯字符串，不支持变量替换 | |

**User's choice:** 支持模板
**Notes:** 数据模型在 Phase 18 定义，模板渲染在 Phase 19 实现

---

## 上下文存储设计

| Option | Description | Selected |
|--------|-------------|----------|
| Task 字段 + 独立文件 | Task 加 context 字段（只读快照）+ 独立 JSON 文件 | |
| 独立文件 only | 仅独立 JSON 文件，Task 上无 context 字段，配置与状态完全分离 | ✓ |

**User's choice:** 独立文件 only
**Notes:** 配置与运行时状态分离，tasks.yaml 只存用户配置

| Option | Description | Selected |
|--------|-------------|----------|
| 单文件/任务 | `~/.config/claw-cron/context/{task_name}.json`，简单清晰 | ✓ |
| 单文件全局 | `~/.config/claw-cron/context.json`，文件更少但并发风险高 | |

**User's choice:** 单文件/任务
**Notes:** 确认 REQUIREMENTS.md CTX-06 已指定的路径

| Option | Description | Selected |
|--------|-------------|----------|
| 纯输出上下文 | 只存 script stdout 解析出的 JSON 对象 | |
| 合并上下文 | 包含系统变量（如 last_exit_code）+ script 回传数据 | ✓ |

**User's choice:** 合并上下文
**Notes:** 系统环境变量是运行时注入的，不持久化；但 last_exit_code 等执行结果需要持久化

| Option | Description | Selected |
|--------|-------------|----------|
| 执行前读+执行后写 | 完整闭环，script 可基于上次结果做判断 | ✓ |
| 仅写回 | 简单但 script 无法访问上次执行结果 | |

**User's choice:** 执行前读+执行后写

| Option | Description | Selected |
|--------|-------------|----------|
| storage.py 函数 | 与现有 load_tasks/save_tasks 风格一致 | |
| 独立 context.py | 专门处理上下文存储逻辑 | ✓ |

**User's choice:** 独立 context.py

---

## when 条件字段设计

| Option | Description | Selected |
|--------|-------------|----------|
| 单字符串 | `when: signed_in == false`，简单直接 | ✓ |
| 结构化对象 | `when: {field: signed_in, op: ==, value: false}`，类型安全但冗长 | |
| 表达式列表 | 允许多个表达式，Phase 20 实现复合逻辑 | |

**User's choice:** 单字符串

| Option | Description | Selected |
|--------|-------------|----------|
| 字符串字段 | `when: str \| None = None`，解析留给 Phase 20 | ✓ |
| WhenExpr 对象 | `when: WhenExpr \| None = None`，类型安全但需提前定义结构 | |

**User's choice:** 字符串字段

| Option | Description | Selected |
|--------|-------------|----------|
| 任务上下文 | when 表达式引用 context.json 中的键值 | ✓ |
| 上下文 + 执行结果 | when 也可引用 exit_code、output 等执行状态 | |

**User's choice:** 任务上下文
**Notes:** 保持 when 与 context.json 绑定，执行结果可通过 context.json 间接访问

---

## Claude's Discretion

- Task dataclass 中 env 字段默认值和序列化细节
- context.json 的具体 JSON 结构
- 向后兼容处理策略
- context.py 函数签名
- context 目录自动创建策略

## Deferred Ideas

None — discussion stayed within phase scope
