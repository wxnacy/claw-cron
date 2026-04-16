# Roadmap: claw-cron v2.1

**Created:** 2026-04-16
**Phases:** 1 (Phase 9, continuing from v2.0)
**Requirements:** 7 v2.1 requirements mapped

---

## Phase 9: 通道管理命令

**Goal:** 添加 channels 命令，支持交互式管理 QQ 通道配置，并通过 WebSocket 自动捕获用户 OpenID。

**Requirements:** CHAN-MGMT-01 ~ CHAN-MGMT-07

**Plans:** 2 plans in 2 waves

**Success Criteria:**
1. `claw-cron channels add` 可交互式配置 QQ Bot
2. WebSocket 连接可接收消息事件
3. 用户发送消息后自动捕获 openid
4. `remind` 命令支持使用联系人别名

**UI hint:** no

**Key Files:**
- `src/claw_cron/cmd/channels.py` — channels 命令组
- `src/claw_cron/qqbot/websocket.py` — WebSocket 客户端
- `src/claw_cron/contacts.py` — 联系人管理
- `src/claw_cron/config.py` — 扩展配置结构
- `pyproject.toml` — 添加 websockets 依赖

**Plans:**
- [ ] 09-01-PLAN.md — Channels Command & Configuration (Wave 1)
- [ ] 09-02-PLAN.md — WebSocket & OpenID Capture (Wave 2)

**Status:** Planned

---

## Coverage

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 9 | CHAN-MGMT-01~07 | 7 |
| **Total** | | **7** |

All v2.1 requirements mapped

---

## Dependencies

### New Dependencies

```toml
# pyproject.toml additions
dependencies = [
    # ... existing ...
    "websockets",  # QQ Bot WebSocket client
]
```

---

## Configuration Example

```yaml
# ~/.config/claw-cron/config.yaml
channels:
  qqbot:
    enabled: true
    app_id: "123456789"
    client_secret: "encrypted:xxx"  # 或明文存储

# ~/.config/claw-cron/contacts.yaml
contacts:
  me:
    openid: "ABC123DEF456"
    channel: qqbot
    alias: "我"
    created: "2026-04-16T10:00:00Z"
```

---

## User Flow

```
1. 配置通道
   $ claw-cron channels add
   ? Channel type: qqbot
   ? AppID: 123456789
   ? AppSecret: ********
   ✓ Credentials validated
   ? Connect now to capture openid? Y

2. 捕获 OpenID
   Connecting to QQ Bot WebSocket...
   ✓ Connected! Please send a message to your bot.
   Waiting for message...

   [User sends message in QQ]
   ✓ OpenID captured: ABC123DEF456
   ? Save as contact alias: me

3. 使用别名发送提醒
   $ claw-cron remind --name morning \
       --cron "0 8 * * *" \
       --message "早安！" \
       --channel qqbot \
       --recipient me
```

---

## Implementation Notes

### WebSocket Connection Flow

1. 获取 access_token (OAuth2)
2. 获取 gateway URL (`GET /gateway`)
3. 建立 WebSocket 连接
4. 发送 Identify (op=2) 认证
5. 接收 Ready 事件
6. 开始心跳循环
7. 接收消息事件，提取 openid

### Message Event Structure

```json
{
  "op": 0,
  "t": "C2C_MESSAGE_CREATE",
  "d": {
    "author": {
      "id": "USER_OPENID",
      ...
    },
    "content": "hello",
    ...
  }
}
```

---

*Created: 2026-04-16*
*Continues from v2.0 (Phase 1-8)*
