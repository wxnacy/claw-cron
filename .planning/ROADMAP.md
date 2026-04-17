# Roadmap: claw-cron v3.1

**Milestone:** v3.1 Update 命令
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Created:** 2026-04-18
**Granularity:** coarse

## Milestones

- ✅ **v2.4 微信通道 & Capture 增强** - Phases 14-17 (shipped 2026-04-17)
- ✅ **v3.0 Command 上下文机制** - Phases 18-20 (shipped 2026-04-18)
- 🚧 **v3.1 Update 命令** - Phase 21 (in progress)

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

<details>
<summary>✅ v3.0 Command 上下文机制 (Phases 18-20) - SHIPPED 2026-04-18</summary>

### Phase 18: Data Model & Context Storage
**Goal:** 任务配置支持环境变量定义和上下文持久化，通知可配置条件控制
**Plans:** 1 plan complete

### Phase 19: Context Injection & Feedback
**Goal:** 脚本在执行时可接收系统注入的上下文，并可通过 stdout 回传结构化数据
**Plans:** 3 plans complete

### Phase 20: Conditional Notification & Release
**Goal:** 通知仅在条件满足时发送，版本升级到 0.3.0
**Plans:** 1 plan complete

</details>

### 🚧 v3.1 Update 命令 (In Progress)

**Milestone Goal:** 增加 update 命令，支持修改已有任务的字段，版本升级到 0.3.1

- [x] **Phase 21: Update Command & Release** - 实现 update 子命令，支持修改任务字段，版本升级到 0.3.1 (completed 2026-04-17)

## Phase Details

### Phase 21: Update Command & Release

**Goal:** 用户可通过 update 命令修改已有任务的指定字段

**Depends on:** Phase 20 (completed)

**Requirements:** UPD-01, UPD-02, UPD-03, UPD-04, UPD-05, UPD-06, VER-02

**Success Criteria** (what must be TRUE):
1. User can run `claw-cron update <name>` to modify an existing task — name is required and locates the target task
2. User can change a task's cron schedule via `--cron` option
3. User can enable or disable a task via `--enabled` option
4. User can update notification message, script content, or prompt content via `--message`, `--script`, `--prompt` options respectively
5. Version number is updated to 0.3.1 in pyproject.toml

**Plans:** 1/1 plans complete

---

## Progress

**Execution Order:**
Phase 21

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 21. Update Command & Release | v3.1 | 1/1 | Complete    | 2026-04-17 |

## Coverage

- Total v3.1 requirements: 7
- Mapped to phases: 7 ✓
- Orphaned requirements: 0 ✓

| Requirement | Phase | Status |
|-------------|-------|--------|
| UPD-01 | Phase 21 | Pending |
| UPD-02 | Phase 21 | Pending |
| UPD-03 | Phase 21 | Pending |
| UPD-04 | Phase 21 | Pending |
| UPD-05 | Phase 21 | Pending |
| UPD-06 | Phase 21 | Pending |
| VER-02 | Phase 21 | Pending |

---

*Roadmap created: 2026-04-18*
*Milestone: v3.1*
