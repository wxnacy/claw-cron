# Roadmap: claw-cron v2.4

**Milestone:** v2.4 微信通道 & Capture 增强
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Created:** 2026-04-17
**Granularity:** coarse

## Phases

- [x] **Phase 14: Architecture Enhancement** - Capture 统一抽象，为通道提供 capture 支持 *(completed 2026-04-17)*
- [x] **Phase 15: Capture Interaction** - 改进 capture 交互体验，自动化 capture 流程 *(completed 2026-04-17)*
- [x] **Phase 16: WeChat Channel** - 企业微信应用消息通知通道 *(completed 2026-04-17)*
- [x] **Phase 17: Verification & Release** - 功能验证与版本升级 (completed 2026-04-17)

## Phase Details

### Phase 14: Architecture Enhancement

**Goal:** 建立统一的 capture 抽象层，支持各通道实现特定的 capture 逻辑

**Depends on:** Phase 13 (completed)

**Requirements:** ARCH-01, ARCH-02, ARCH-03, ARCH-04

**Success Criteria** (what must be TRUE):
1. Developer can check if a channel supports capture by querying the `supports_capture` property
2. Developer can implement channel-specific capture logic by overriding the `capture_openid()` method
3. QQBotChannel capture logic is encapsulated in the `capture_openid()` method (refactored from scattered WebSocket code)
4. FeishuChannel capture logic is encapsulated in the `capture_openid()` method (refactored from existing open_id capture)

**Plans:** TBD

---

### Phase 15: Capture Interaction

**Goal:** 用户可以通过直观的交互界面执行 capture 流程，并在添加通道后自动被询问是否执行 capture

**Depends on:** Phase 14

**Requirements:** CAPT-01, CAPT-02, CAPT-03, CAPT-04, CAPT-05

**Success Criteria** (what must be TRUE):
1. User can select channel type from an interactive list when running `channels capture` (no need to remember --channel-type flag)
2. User receives a friendly message when trying to capture a channel that doesn't support capture (e.g., "This channel doesn't require capture")
3. User is automatically prompted to run capture after successfully adding a channel that supports capture
4. User sees real-time status feedback during capture process (e.g., "Waiting for message from QQ Bot...")
5. Capture process automatically times out after 5 minutes with a clear error message

**Plans:** TBD

**UI hint:** yes

---

### Phase 16: WeChat Channel

**Goal:** 用户可以通过企业微信应用接收私聊任务通知

**Depends on:** Phase 14

**Requirements:** WECHAT-01, WECHAT-02, WECHAT-03, WECHAT-04, WECHAT-05

**Success Criteria** (what must be TRUE):
1. User can configure WeChat Work app credentials (corp_id, agent_id, secret) interactively
2. User can receive private text messages via WeChat Work application
3. User can receive private Markdown messages via WeChat Work application
4. System automatically manages access_token lifecycle (acquisition, caching, refresh before expiration)
5. User can obtain their WeChat userid through the capture command

**Plans:** TBD

---

### Phase 17: Verification & Release

**Goal:** 验证所有功能正常工作，发布版本 0.2.1

**Depends on:** Phase 15, Phase 16

**Requirements:** VERS-01

**Success Criteria** (what must be TRUE):
1. User can successfully add, verify, and capture all channel types (QQ, Feishu, Email, WeChat)
2. User can send test notifications through all configured channels
3. All channels handle rate limits and errors gracefully
4. Version number is updated to 0.2.1 in pyproject.toml
5. Documentation reflects new features (WeChat channel, capture improvements)

**Plans:** 2/2 plans complete

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 14. Architecture Enhancement | 1/1 | Complete | 2026-04-17 |
| 15. Capture Interaction | 1/1 | Complete | 2026-04-17 |
| 16. WeChat Channel | 1/1 | Complete | 2026-04-17 |
| 17. Verification & Release | 2/2 | Complete    | 2026-04-17 |

## Coverage

- Total v2.4 requirements: 15
- Mapped to phases: 15 ✓
- Orphaned requirements: 0 ✓

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 14 | Complete |
| ARCH-02 | Phase 14 | Complete |
| ARCH-03 | Phase 14 | Complete |
| ARCH-04 | Phase 14 | Complete |
| CAPT-01 | Phase 15 | Pending |
| CAPT-02 | Phase 15 | Pending |
| CAPT-03 | Phase 15 | Pending |
| CAPT-04 | Phase 15 | Pending |
| CAPT-05 | Phase 15 | Pending |
| WECHAT-01 | Phase 16 | Complete |
| WECHAT-02 | Phase 16 | Complete |
| WECHAT-03 | Phase 16 | Complete |
| WECHAT-04 | Phase 16 | Complete |
| WECHAT-05 | Phase 16 | Complete |
| VERS-01 | Phase 17 | Pending |

---

*Roadmap created: 2026-04-17*
*Milestone: v2.4*
