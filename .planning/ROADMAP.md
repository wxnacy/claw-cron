# Roadmap: claw-cron v3.0

**Milestone:** v3.0 Command 上下文机制
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Created:** 2026-04-17
**Granularity:** coarse

## Milestones

- ✅ **v2.4 微信通道 & Capture 增强** - Phases 14-17 (shipped 2026-04-17)
- 🚧 **v3.0 Command 上下文机制** - Phases 18-20 (in progress)

## Phases

<details>
<summary>✅ v2.4 微信通道 & Capture 增强 (Phases 14-17) - SHIPPED 2026-04-17</summary>

### Phase 14: Architecture Enhancement
**Goal:** 建立统一的 capture 抽象层
**Plans:** 1 plan complete

### Phase 15: Capture Interaction
**Goal:** 改进 capture 交互体验
**Plans:** 1 plan complete

### Phase 16: WeChat Channel
**Goal:** 企业微信应用消息通知通道
**Plans:** 1 plan complete

### Phase 17: Verification & Release
**Goal:** 功能验证与版本升级
**Plans:** 2 plans complete

</details>

### 🚧 v3.0 Command 上下文机制 (In Progress)

**Milestone Goal:** 为 command 类型任务增加双向上下文机制，让脚本可获取系统状态并回传执行结果，实现条件化通知

- [x] **Phase 18: Data Model & Context Storage** - 扩展数据模型，支持上下文配置和持久化 *(completed 2026-04-17)*
- [ ] **Phase 19: Context Injection & Feedback** - 实现上下文注入与 JSON 回传
- [ ] **Phase 20: Conditional Notification & Release** - 条件通知与版本发布

## Phase Details

### Phase 18: Data Model & Context Storage

**Goal:** 任务配置支持环境变量定义和上下文持久化，通知可配置条件控制

**Depends on:** Phase 17 (completed)

**Requirements:** CTX-02, CTX-06, COND-01

**Success Criteria** (what must be TRUE):
1. User can define custom environment variables in task config via the `env` field (key-value list)
2. Task context data persists across executions — context from a previous run is available in subsequent runs
3. User can specify a `when` condition expression in notify config to control notification delivery

**Plans:** TBD

---

### Phase 19: Context Injection & Feedback

**Goal:** 脚本在执行时可接收系统注入的上下文，并可通过 stdout 回传结构化数据

**Depends on:** Phase 18

**Requirements:** CTX-01, CTX-03, CTX-04, CTX-05

**Success Criteria** (what must be TRUE):
1. Scripts can read system context (task name, type, last exit code, last output) via CLAW_TASK_NAME, CLAW_TASK_TYPE, CLAW_LAST_EXIT_CODE, CLAW_LAST_OUTPUT environment variables
2. Scripts can reference context values in script content using `{{ context.xxx }}` template syntax (e.g., `{{ context.signed_in }}`)
3. Scripts can read full context JSON from a temp file whose path is provided in CLAW_CONTEXT_FILE environment variable
4. Scripts can output JSON to stdout that gets parsed and persisted as task context for subsequent executions

**Plans:** TBD

---

### Phase 20: Conditional Notification & Release

**Goal:** 通知仅在条件满足时发送，版本升级到 0.3.0

**Depends on:** Phase 19

**Requirements:** COND-02, COND-03, VER-01

**Success Criteria** (what must be TRUE):
1. Notification is sent only when the `when` expression evaluates to true against the task context (e.g., `signed_in == false` suppresses notification when user is signed in)
2. `==` and `!=` operators work correctly for string and boolean value comparisons in when expressions
3. Notifications are sent as before when no `when` field is specified — existing tasks continue to work unchanged
4. Version number is updated to 0.3.0 in pyproject.toml

**Plans:** TBD

---

## Progress

**Execution Order:**
Phases execute in numeric order: 18 → 19 → 20

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 18. Data Model & Context Storage | v3.0 | 1/1 | Complete | 2026-04-17 |
| 19. Context Injection & Feedback | v3.0 | 0/? | Not started | - |
| 20. Conditional Notification & Release | v3.0 | 0/? | Not started | - |

## Coverage

- Total v3.0 requirements: 10
- Mapped to phases: 10 ✓
- Orphaned requirements: 0 ✓

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

---

*Roadmap created: 2026-04-17*
*Milestone: v3.0*
