# Roadmap: claw-cron v2.3

**Milestone:** v2.3 邮件 & 飞书通道
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Created:** 2026-04-17
**Granularity:** coarse

## Phases

- [x] **Phase 11: UX Improvements** - 交互体验改进：列表选择、配置状态展示 (completed 2026-04-17)
- [ ] **Phase 12: Feishu Channel** - 飞书私聊消息通知通道
- [ ] **Phase 13: Email Channel** - SMTP 邮件通知通道

## Phase Details

### Phase 11: UX Improvements

**Goal:** 用户可以直观地选择和配置消息通道，并查看各通道的配置状态

**Depends on:** Phase 10 (completed)

**Requirements:** UX-01, UX-02, UX-03

**Success Criteria** (what must be TRUE):
1. User can select channel type from an interactive list when running `channels add`
2. User can see which channels are configured/unconfigured in the `channels add` selection list
3. User can view detailed configuration status for each channel in `channels list` output

**Plans:** 3/3 plans complete

**Plan List:**
- [x] 11-01-PLAN.md — Channel status functions (get_channel_status, prompt_channel_select)
- [x] 11-02-PLAN.md — Interactive channel add command with overwrite confirmation
- [x] 11-03-PLAN.md — Enhanced channel list and verify commands

**UI hint:** yes

---

### Phase 12: Feishu Channel

**Goal:** 用户可以通过飞书私聊接收任务通知

**Depends on:** Phase 11

**Requirements:** FEISHU-01, FEISHU-02, FEISHU-03, FEISHU-04, FEISHU-05

**Success Criteria** (what must be TRUE):
1. User can configure Feishu app credentials (app_id, app_secret) for authentication
2. User can send private chat messages via open_id after interacting with the bot
3. User can obtain their open_id through an interactive capture command
4. System automatically manages tenant_access_token lifecycle (acquisition and refresh)
5. System handles Feishu API rate limits (5 QPS per user) with automatic retry

**Plans:** 2 plans in 2 waves

**Plan List:**
- [ ] 12-01-PLAN.md — Core FeishuChannel implementation with SDK integration
- [ ] 12-02-PLAN.md — CLI integration for feishu channel (add/verify/capture)

---

### Phase 13: Email Channel

**Goal:** 用户可以通过邮件接收任务通知和执行结果

**Depends on:** Phase 12

**Requirements:** EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05

**Success Criteria** (what must be TRUE):
1. User can configure SMTP server settings (host, port, username, password, from_email)
2. User can send plain text email notifications
3. User can send HTML formatted email notifications
4. User can specify multiple email recipients
5. User can attach files to email notifications

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 11. UX Improvements | 3/3 | Complete    | 2026-04-17 |
| 12. Feishu Channel | 0/2 | Ready | - |
| 13. Email Channel | 0/0 | Not started | - |

## Coverage

- Total v2.3 requirements: 13
- Mapped to phases: 13 ✓
- Orphaned requirements: 0 ✓

| Requirement | Phase | Status |
|-------------|-------|--------|
| UX-01 | Phase 11 | Pending |
| UX-02 | Phase 11 | Pending |
| UX-03 | Phase 11 | Pending |
| FEISHU-01 | Phase 12 | Pending |
| FEISHU-02 | Phase 12 | Pending |
| FEISHU-03 | Phase 12 | Pending |
| FEISHU-04 | Phase 12 | Pending |
| FEISHU-05 | Phase 12 | Pending |
| EMAIL-01 | Phase 13 | Pending |
| EMAIL-02 | Phase 13 | Pending |
| EMAIL-03 | Phase 13 | Pending |
| EMAIL-04 | Phase 13 | Pending |
| EMAIL-05 | Phase 13 | Pending |

---

*Roadmap created: 2026-04-17*
*Milestone: v2.3*
