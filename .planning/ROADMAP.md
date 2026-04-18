# Roadmap: claw-cron v3.2

**Milestone:** v3.2 Codebuddy Agent 集成
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Created:** 2026-04-19
**Granularity:** coarse

## Milestones

- ✅ **v3.1 Update 命令** - Phase 21 (shipped 2026-04-17)
- 🚧 **v3.2 Codebuddy Agent 集成** - Phases 22-25 (in progress)

## Phases

<details>
<summary>✅ v3.1 Update 命令 (Phase 21) - SHIPPED 2026-04-17</summary>

### Phase 21: Update Command & Release
**Goal:** 用户可通过 update 命令修改已有任务的指定字段
**Plans:** 1 plan complete

</details>

### 🚧 v3.2 Codebuddy Agent 集成 (In Progress)

**Milestone Goal:** 将 chat 命令迁移到 Codebuddy SDK，支持多模型选择，集成内置工具为 Agent Tools

#### Phase 22: Codebuddy Provider
**Goal:** 新增 Codebuddy Provider，支持 agent 和 model 参数选择

**Depends on:** Phase 21 (completed)

**Requirements:** PROV-01, PROV-02, PROV-03, UX-02

**Success Criteria** (what must be TRUE):
1. User can run `claw-cron chat --agent codebuddy` to use Codebuddy SDK
2. User can run `claw-cron chat --model minimax-m2.5` to select specific model
3. CodebuddyProvider implements BaseProvider interface correctly
4. API Key missing shows friendly message instead of throwing exception
5. Provider factory returns correct provider based on `--agent` parameter

**Plans:** 0/1 plans complete

#### Phase 23: Custom Tools
**Goal:** 将内置方法集成为 Agent 自定义工具

**Depends on:** Phase 22

**Requirements:** TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05

**Success Criteria** (what must be TRUE):
1. Agent can call list_tasks tool to list all scheduled tasks
2. Agent can call add_task tool to create new task with specified parameters
3. Agent can call update_task tool to modify existing task
4. Agent can call delete_task tool to remove task
5. Agent can call run_task tool to execute task immediately

**Plans:** 0/1 plans complete

#### Phase 24: Session & Token
**Goal:** Agent 对话日志持久化和 Token 消耗显示

**Depends on:** Phase 23

**Requirements:** SESS-01, SESS-02, UX-01

**Success Criteria** (what must be TRUE):
1. Session logs are saved to `~/.config/claw-cron/sessions/{session_id}.jsonl`
2. User can resume conversation from previous session
3. Chat displays token consumption per turn (input, output, cache)
4. Session log format is JSONL and human-readable

**Plans:** 0/1 plans complete

#### Phase 25: Progressive Tools & Release
**Goal:** 渐进式批量工具机制，版本发布

**Depends on:** Phase 24

**Requirements:** TOOL-06, UX-03

**Success Criteria** (what must be TRUE):
1. System prompt shows tool names and descriptions only
2. Agent can call get_tool_details to get full parameter schema
3. Agent uses tools correctly after getting details
4. Version number is updated to 0.3.3 in pyproject.toml
5. All requirements verified and milestone complete

**Plans:** 0/1 plans complete

---

## Progress

**Execution Order:**
Phase 22 → Phase 23 → Phase 24 → Phase 25

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 22. Codebuddy Provider | v3.2 | 0/1 | Pending | — |
| 23. Custom Tools | v3.2 | 0/1 | Pending | — |
| 24. Session & Token | v3.2 | 0/1 | Pending | — |
| 25. Progressive Tools & Release | v3.2 | 0/1 | Pending | — |

## Coverage

- Total v3.2 requirements: 14
- Mapped to phases: 14 ✓
- Orphaned requirements: 0 ✓

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

---

*Roadmap created: 2026-04-19*
*Milestone: v3.2*
