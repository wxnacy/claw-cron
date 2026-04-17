---
phase: 20
status: passed
verified: 2026-04-18
verifier: inline
---

# Verification: Phase 20 — Conditional Notification & Release

## Goal

通知仅在条件满足时发送，版本升级到 0.3.0

## Must-Haves Check

| # | Requirement | Check | Status |
|---|-------------|-------|--------|
| 1 | condition.py 存在且 evaluate_when 可导入 | `from claw_cron.condition import evaluate_when` | ✓ PASS |
| 2 | when=None 时通知正常发送（COND-03） | `evaluate_when(None, {}) == True` | ✓ PASS |
| 3 | when 条件满足时发送，不满足时抑制（COND-02） | `evaluate_when('signed_in == false', {'signed_in': True}) == False` | ✓ PASS |
| 4 | 求值失败保守策略（D-08） | parse error / missing key → True | ✓ PASS |
| 5 | 版本号 0.3.0（VER-01） | `__about__.__version__ == "0.3.0"` | ✓ PASS |

## Requirements Traceability

| Requirement | Description | Status |
|-------------|-------------|--------|
| COND-02 | == 和 != 运算符，字符串/布尔值比较 | ✓ Complete |
| COND-03 | when 为空时默认发送，向后兼容 | ✓ Complete |
| VER-01 | 版本号升级到 0.3.0 | ✓ Complete |

## Automated Checks

```
COND-02: PASSED (== and != operators, type coercion)
COND-03: PASSED (None and empty string both return True)
VER-01:  PASSED (__version__ == "0.3.0")
executor integration: line 206 — if task.notify and evaluate_when(task.notify.when, merged)
```

## Summary

Phase 20 完整实现了条件通知功能：
- `condition.py` 提供 `evaluate_when()` 求值器，支持 `==` / `!=` 运算符和类型强制转换
- `executor.py` 在通知前插入 when 条件检查，向后兼容（when=None 时行为不变）
- 版本号升级至 0.3.0
- v3.0 里程碑全部 10 个需求均已完成
