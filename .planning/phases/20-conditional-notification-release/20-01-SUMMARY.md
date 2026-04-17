---
plan: 20-01
phase: 20
status: complete
completed: 2026-04-18
commit: a56fcca
---

# Summary: Plan 20-01 — Conditional Notification & Release

## What Was Built

实现了 when 条件表达式求值器，并集成到通知流程中，同时升级版本号到 0.3.0。

## Key Files

### Created
- `src/claw_cron/condition.py` — when 表达式求值模块，包含 `evaluate_when()` 和 `_coerce()` 函数

### Modified
- `src/claw_cron/executor.py` — 导入 `evaluate_when`，在 `if task.notify` 条件中插入 when 检查
- `src/claw_cron/__about__.py` — 版本号从 0.2.1 升级到 0.3.0

## Decisions

- 保守策略：when 解析失败或 key 缺失时发送通知（不静默丢弃）
- `evaluate_when` 接收 `merged` context（包含 feedback + 系统字段），向后兼容 when=None 场景

## Self-Check: PASSED

- [x] condition.py 存在且可正常导入
- [x] evaluate_when(None, {}) == True（向后兼容）
- [x] when 条件满足时发送，不满足时抑制
- [x] 解析失败保守策略验证通过（6 个断言全部通过）
- [x] 版本号更新为 0.3.0
- [x] COND-02, COND-03, VER-01 全部覆盖
