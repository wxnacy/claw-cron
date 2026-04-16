# Roadmap: claw-cron v2.1

**Created:** 2026-04-16
**Updated:** 2026-04-16
**Phases:** 5 (Phase 5-9, continuing from v1)
**Requirements:** 40 v2.x requirements mapped ✓

---

## Phase 5: AI Provider 重构

**Goal:** 重构 agent.py 为 Provider 模式，支持 Anthropic 和 OpenAI 双提供商。

**Requirements:** PROV-01 ~ PROV-07, TOOL-01 ~ TOOL-04

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. `claw-cron add` 可使用 Anthropic 或 OpenAI Provider（通过配置选择）
2. Tool Use 功能正常工作，`create_task` Tool 可被正确调用
3. 配置支持环境变量 `CLAW_CRON_PROVIDER`、`CLAW_CRON_API_KEY`、`CLAW_CRON_MODEL`
4. 现有 `agent.py` 对话流程不变，用户无感知切换

**UI hint**: no

**Key Files:**
- `src/claw_cron/providers/__init__.py` — Provider 工厂
- `src/claw_cron/providers/base.py` — BaseProvider 抽象类
- `src/claw_cron/providers/anthropic.py` — Anthropic 实现
- `src/claw_cron/providers/openai.py` — OpenAI 实现
- `src/claw_cron/providers/tools.py` — Tool 格式转换
- `src/claw_cron/config.py` — 添加 AIConfig

**Plans:**
- [x] 05-01-PLAN.md — Provider Infrastructure & Configuration (Wave 1) ✅
- [x] 05-02-PLAN.md — Provider Implementations & Agent Refactor (Wave 2) ✅

**Status:** ✅ Complete (2026-04-16)

---

## Phase 6: 消息通道基础 + iMessage

**Goal:** 建立消息通道抽象层，实现 iMessage 通道支持。

**Requirements:** CHAN-01 ~ CHAN-04, IMSG-01 ~ IMSG-04

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. `MessageChannel` 基类可被继承扩展
2. `IMessageChannel` 可在 macOS 上发送 iMessage
3. 支持 `+86` 国际号码格式
4. 首次运行请求 macOS 辅助功能权限

**UI hint**: no

**Key Files:**
- `src/claw_cron/channels/__init__.py` — Channel 工厂
- `src/claw_cron/channels/base.py` — MessageChannel 抽象类
- `src/claw_cron/channels/imessage.py` — iMessage 实现
- `pyproject.toml` — 添加 `macpymessenger` 依赖

**Plans:**
- [x] 06-01-PLAN.md — Channel Infrastructure (Wave 1) ✅
- [x] 06-02-PLAN.md — iMessage Implementation (Wave 2) ✅

**Status:** ✅ Complete (2026-04-16)

---

## Phase 7: QQ 通道

**Goal:** 实现 QQ Bot 消息通道，支持私聊和群聊通知。

**Requirements:** QQ-01 ~ QQ-06

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. `QQBotChannel` 可通过 QQ 开放平台 API 发送消息
2. OAuth2 认证正常工作，自动获取 access_token
3. 支持 `c2c:OPENID` 私聊格式
4. 支持 `group:GROUP_OPENID` 群聊格式
5. 支持 Markdown 消息格式

**UI hint**: no

**Key Files:**
- `src/claw_cron/channels/qqbot.py` — QQ Bot 实现
- `pyproject.toml` — 添加 `tenacity` 依赖

**Plans:**
- [x] 07-01-PLAN.md — QQ Bot Infrastructure + OAuth2 (Wave 1) ✅
- [x] 07-02-PLAN.md — QQ Bot Message Sending (Wave 2) ✅

**Status:** ✅ Complete (2026-04-16)

---

## Phase 8: 任务通知集成 + 定时提醒

**Goal:** 将消息通道集成到任务执行流程，新增定时提醒功能。

**Requirements:** NOTIF-01 ~ NOTIF-05, REMIND-01 ~ REMIND-03

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. 任务 YAML 可配置 `notify.channel` 和 `notify.recipients`
2. 任务执行完成后自动发送通知
3. `claw-cron remind` 命令可创建纯提醒任务
4. 通知消息包含任务名称、状态、结果

**UI hint**: no

**Key Files:**
- `src/claw_cron/storage.py` — Task 模型扩展
- `src/claw_cron/notifier.py` — 通知发送逻辑
- `src/claw_cron/cmd/remind.py` — remind 命令
- `src/claw_cron/executor.py` — 集成通知调用

**Plans:**
- [x] 08-01-PLAN.md — Task Notification Integration (Wave 1) ✅
- [x] 08-02-PLAN.md — Reminder Command (Wave 2) ✅

**Status:** ✅ Complete (2026-04-16)

---

## Phase 9: Channel Management Commands

**Goal:** 添加 `channels` 命令，支持交互式管理 QQ 通道配置，并通过 WebSocket 自动捕获用户 OpenID。

**Requirements:** CHAN-MGMT-01 ~ CHAN-MGMT-07

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. `claw-cron channels add` 可交互式配置 QQ Bot
2. WebSocket 连接可接收消息事件
3. 用户发送消息后自动捕获 openid
4. `remind` 命令支持使用联系人别名

**UI hint**: no

**Key Files:**
- `src/claw_cron/cmd/channels.py` — channels 命令组
- `src/claw_cron/contacts.py` — 联系人管理
- `src/claw_cron/qqbot/websocket.py` — WebSocket 客户端
- `src/claw_cron/qqbot/events.py` — 事件类型定义

**Plans:**
- [ ] 09-01-PLAN.md — Channels Command & Configuration (Wave 1)
- [ ] 09-02-PLAN.md — WebSocket & OpenID Capture (Wave 2)

**Status:** 📋 Planned

---

## Coverage

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 5 | PROV-01~07, TOOL-01~04 | 11 |
| Phase 6 | CHAN-01~04, IMSG-01~04 | 8 |
| Phase 7 | QQ-01~06 | 6 |
| Phase 8 | NOTIF-01~05, REMIND-01~03 | 8 |
| Phase 9 | CHAN-MGMT-01~07 | 7 |
| **Total** | | **40** |

All v2.x requirements mapped ✓

---

## Dependencies

### New Dependencies

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    "openai",           # OpenAI Provider
    "pydantic-settings", # AIConfig
    "macpymessenger>=0.2.0",  # iMessage (macOS only)
    "tenacity",         # QQ Bot retry logic
]
```

### Optional Dependencies

```toml
[project.optional-dependencies]
imessage = ["macpymessenger>=0.2.0"]  # macOS only
```

---

## Configuration Example

```yaml
# ~/.config/claw-cron/config.yaml
ai:
  provider: claude  # or "openai"
  model: claude-3-5-haiku-20241022
  # api_key: from env CLAW_CRON_API_KEY

channels:
  imessage:
    enabled: true

  qqbot:
    enabled: true
    app_id: ${QQ_BOT_APP_ID}
    client_secret: ${QQ_BOT_CLIENT_SECRET}
```

```yaml
# ~/.config/claw-cron/contacts.yaml
contacts:
  me:
    openid: E4F4AEA33253A2797FB897C50B81D7ED
    channel: qqbot
    alias: me
    created: "2026-04-16T22:00:00"
```

```yaml
# ~/.config/claw-cron/tasks.yaml
- name: daily_backup
  cron: "0 2 * * *"
  type: command
  script: ./backup.sh
  notify:
    channel: imessage
    recipients:
      - "+8613812345678"

- name: morning_reminder
  cron: "0 8 * * *"
  type: reminder
  message: "早安！今天有 3 个任务待完成"
  notify:
    channel: qqbot
    recipients:
      - "me"  # Uses contact alias instead of openid
```

---
*Created: 2026-04-16*
*Updated: 2026-04-16*
*Continues from v1.0 (Phase 1-4)*
