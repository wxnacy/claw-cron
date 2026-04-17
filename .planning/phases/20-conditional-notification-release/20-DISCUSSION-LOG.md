# Phase 20: Conditional Notification & Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 20-conditional-notification-release
**Areas discussed:** When 表达式求值, 通知拦截位置, 求值失败与日志

---

## When 表达式求值

| Option | Description | Selected |
|--------|-------------|----------|
| 自动类型推断 | true/false 解析为布尔值，数字解析为数字，其余为字符串。简单直观 | ✓ |
| 纯字符串比较 | 所有值都作为字符串比较。简单一致但布尔值需加引号 | |
| JSON 类型语法 | 支持布尔值、数字、字符串自动推断。更强大但超出 v3.0 范围 | |

**User's choice:** 自动类型推断
**Notes:** 与 context.json 中的值比较时进行类型匹配

| Option | Description | Selected |
|--------|-------------|----------|
| 仅 == 和 != | 符合 REQUIREMENTS.md 和 ROADMAP.md，覆盖核心场景 | ✓ |
| 也支持数值比较 | 额外支持 >, <, >=, <=，但 PROJECT.md Out of Scope 排除了 | |

**User's choice:** 仅 == 和 !=
**Notes:** 复合条件和数值比较留给未来 ACOND-01/02

| Option | Description | Selected |
|--------|-------------|----------|
| 简单字符串拆分 | str.split() 拆分 key == value，简单直接 | |
| 正则表达式解析 | 用正则提取 key、operator、value 三部分，更严谨 | ✓ |

**User's choice:** 正则表达式解析
**Notes:** 比简单拆分更严谨

| Option | Description | Selected |
|--------|-------------|----------|
| 仅单条件 | when 字段只支持单个条件表达式，多条件需多个 notify 配置 | ✓ |
| 支持 and/or 组合 | 支持多条件连接，但 PROJECT.md 标注为 Out of Scope | |

**User's choice:** 仅单条件

---

## 通知拦截位置

| Option | Description | Selected |
|--------|-------------|----------|
| executor.py 通知前 | 在 if task.notify: 块内、调用 notify_task_result() 之前检查。merged context 可直接使用，无需修改 Notifier 签名 | ✓ |
| notifier.py 内部 | 在 notify_task_result() 内部检查。需要把 context 传入 Notifier，修改函数签名 | |

**User's choice:** executor.py 通知前
**Notes:** 不修改 Notifier 函数签名

---

## 求值失败与日志

| Option | Description | Selected |
|--------|-------------|----------|
| 日志记录 | when 条件不满足时输出 logger.info 日志，用户可了解通知被抑制原因 | ✓ |
| 静默跳过 | 完全静默跳过，不输出任何日志。简单但调试困难 | |

**User's choice:** 日志记录

| Option | Description | Selected |
|--------|-------------|----------|
| 警告并发送通知 | 求值失败时记录 logger.warning 并发送通知。宁多发不漏发 | ✓ |
| 错误并抑制通知 | 求值失败时记录错误日志并抑制通知。不发送可能不应发的通知 | |
| 抛出异常 | 求值失败时抛出异常让上层处理。但表达式错误不应中断任务执行 | |

**User's choice:** 警告并发送通知
**Notes:** 保守策略——宁多发不漏发

---

## Claude's Discretion

- when 表达式正则的具体实现模式
- 评估函数的模块名和函数签名
- 求值失败时日志的详细格式和内容
- 版本号升级的具体文件修改

## Deferred Ideas

None
