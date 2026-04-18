# Requirements: claw-cron v3.2

**Defined:** 2026-04-19
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## v1 Requirements (Current Milestone)

### Provider Integration

- [ ] **PROV-01**: 用户可以通过 `--agent` / `-a` 参数选择 AI 后端，默认 codebuddy
- [ ] **PROV-02**: 用户可以通过 `--model` / `-m` 参数选择模型，默认 minimax-m2.5
- [ ] **PROV-03**: 新增 CodebuddyProvider 实现 BaseProvider 接口，支持 Codebuddy SDK 调用

### Custom Tools

- [ ] **TOOL-01**: 将 list_tasks 方法集成为 Agent 自定义工具
- [ ] **TOOL-02**: 将 add_task 方法集成为 Agent 自定义工具
- [ ] **TOOL-03**: 将 update_task 方法集成为 Agent 自定义工具
- [ ] **TOOL-04**: 将 delete_task 方法集成为 Agent 自定义工具
- [ ] **TOOL-05**: 将 run_task 方法集成为 Agent 自定义工具
- [ ] **TOOL-06**: 内置工具使用渐进式批量模式（系统提示词给名称描述，agent 按需获取详情）

### Session Management

- [ ] **SESS-01**: Agent 对话日志按 session 单独保存到 `~/.config/claw-cron/sessions/{session_id}.jsonl`
- [ ] **SESS-02**: 支持从历史 session 恢复对话

### UX

- [ ] **UX-01**: Chat 对话显示每轮 tokens 消耗（输入、输出、缓存）
- [ ] **UX-02**: CODEBUDDY_API_KEY 缺失时友好提示，不抛异常
- [ ] **UX-03**: 版本升级到 0.3.3

## v2 Requirements (Deferred)

### Advanced Features

- **ADV-01**: 支持提醒任务（remind_task）工具
- **ADV-02**: 支持上下文命令（context）工具
- **ADV-03**: 支持 tool calling 失败时的降级策略

### Integration

- **INT-01**: 支持从现有 chat.py 历史导入对话
- **INT-02**: 支持配置默认 agent 和 model

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web UI | CLI 优先 |
| 多用户/权限管理 | 单用户本地工具 |
| 外部 MCP 服务器 | Custom Tools 已足够，无需额外进程 |
| 完全替代现有 Provider 层 | 保持向后兼容，逐步迁移 |
| 系统 crontab 集成 | 项目自管理调度 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 22 | Pending |
| PROV-02 | Phase 22 | Pending |
| PROV-03 | Phase 22 | Pending |
| TOOL-01 | Phase 23 | Pending |
| TOOL-02 | Phase 23 | Pending |
| TOOL-03 | Phase 23 | Pending |
| TOOL-04 | Phase 23 | Pending |
| TOOL-05 | Phase 23 | Pending |
| TOOL-06 | Phase 25 | Pending |
| SESS-01 | Phase 24 | Pending |
| SESS-02 | Phase 24 | Pending |
| UX-01 | Phase 24 | Pending |
| UX-02 | Phase 22 | Pending |
| UX-03 | Phase 25 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-19*
*Last updated: 2026-04-19 after initial definition*
