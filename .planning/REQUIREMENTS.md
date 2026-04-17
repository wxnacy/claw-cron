# Requirements: claw-cron v3.0

**Defined:** 2026-04-17
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## v3.0 Requirements

为 command 类型任务增加双向上下文机制，让脚本可获取系统状态并回传执行结果，实现条件化通知。

### Context Injection (系统 → script)

- [ ] **CTX-01**: 系统环境变量注入 — 执行 command 任务时自动注入 CLAW_TASK_NAME, CLAW_TASK_TYPE, CLAW_LAST_EXIT_CODE, CLAW_LAST_OUTPUT 等系统环境变量到子进程
- [ ] **CTX-02**: 自定义环境变量注入 — 任务配置中的 `env` 字段（key-value 列表）以 CLAW_CONTEXT_ 前缀注入为环境变量
- [ ] **CTX-03**: 模板变量注入 — 扩展 `{{ }}` 语法，支持 `{{ context.last_output }}`, `{{ context.signed_in }}` 等上下文变量渲染到 script 字段
- [ ] **CTX-04**: 上下文文件注入 — 将任务上下文以 JSON 格式写入临时文件，通过 CLAW_CONTEXT_FILE 环境变量传递文件路径给脚本

### Context Feedback (script → 系统)

- [ ] **CTX-05**: JSON stdout 解析 — 解析 command 任务 stdout 中的 JSON 对象，提取为上下文字典（非 JSON 输出按原逻辑处理）
- [ ] **CTX-06**: 上下文状态持久化 — 将解析后的上下文保存到独立 JSON 文件（`~/.config/claw-cron/context/{task_name}.json`），与 tasks.yaml 分离（用户配置 vs 运行时状态），下次执行时可读取

### Conditional Notification (条件通知)

- [ ] **COND-01**: notify when 条件字段 — NotifyConfig 增加 `when` 字段，支持简单表达式如 `signed_in == false`，仅在条件为真时发送通知
- [ ] **COND-02**: 条件表达式求值 — 支持 `==` 和 `!=` 运算符，对上下文字典中的键值进行判断，支持字符串和布尔值比较
- [ ] **COND-03**: 无 when 字段时默认行为 — when 为空时保持现有逻辑（始终发送通知），确保向后兼容

### Version (版本)

- [ ] **VER-01**: 版本号升级到 0.3.0

## Future Requirements

### Cross-task Context

- **XCTX-01**: 任务间上下文共享 — 不同任务可读取其他任务的上下文状态
- **XCTX-02**: 上下文引用语法 — 类似 `{{ tasks.check_signin.context.signed_in }}` 跨任务引用

### Advanced Conditions

- **ACOND-01**: 复合条件表达式 — 支持 and / or / not 逻辑运算
- **ACOND-02**: 数值比较 — 支持 >, <, >=, <= 运算符
- **ACOND-03**: 条件模板 — when 中引用其他任务的上下文

## Out of Scope

| Feature | Reason |
|---------|--------|
| 跨任务上下文共享 | v3.0 仅支持同一任务内上下文传递，跨任务需要调度时序保证，复杂度高 |
| 复合条件表达式 | and/or/函数调用增加解析复杂度和安全风险，简单 == / != 已覆盖核心场景 |
| 数值比较运算符 | 核心场景是布尔/字符串判断，数值比较为未来扩展 |
| 上下文加密 | 单用户本地工具，YAML 文件存储，安全由文件系统权限保证 |
| 上下文过期机制 | 当前任务量小，无需自动过期清理 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CTX-01 | Phase 19 | Pending |
| CTX-02 | Phase 18 | ✓ Complete |
| CTX-03 | Phase 19 | Pending |
| CTX-04 | Phase 19 | Pending |
| CTX-05 | Phase 19 | Pending |
| CTX-06 | Phase 18 | ✓ Complete |
| COND-01 | Phase 18 | ✓ Complete |
| COND-02 | Phase 20 | Pending |
| COND-03 | Phase 20 | Pending |
| VER-01 | Phase 20 | Pending |

**Coverage:**
- v3.0 requirements: 10 total
- Mapped to phases: 10 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-17*
*Last updated: 2026-04-17 after initial definition*
