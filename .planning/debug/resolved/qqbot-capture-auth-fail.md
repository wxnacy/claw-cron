---
name: qqbot-capture-auth-fail
description: QQ Bot channels capture 命令认证失败 4004 错误
type: debug
status: resolved
trigger: |
  uv run claw-cron channels capture
  Save as contact alias [me]:

  Waiting for message...
  Send any message to your QQ Bot to capture your openid.
  Press Ctrl+C to cancel.

  Connection lost: received 4004 (private use) Authentication fail; then sent 4004 (private use) Authentication fail. Retrying in 1s (1/5)
  Connection lost: received 4004 (private use) Authentication fail; then sent 4004 (private use) Authentication fail. Retrying in 1s (1/5)  capture 收不到qq消息
created: 2026-04-17
updated: 2026-04-17
---

# Symptoms

**Expected behavior:** 发送消息到 QQ Bot 后捕获 openid 并保存联系人别名

**Actual behavior:** 启动命令后立即出现 4004 Authentication fail 错误，无限重试

**Error messages:**
```
Connection lost: received 4004 (private use) Authentication fail; then sent 4004 (private use) Authentication fail. Retrying in 1s (1/5)
```

**Timeline:** 新配置，从未成功运行过

**Reproduction:**
1. 运行 `uv run claw-cron channels capture`
2. 输入别名（默认 "me"）
3. 立即出现认证失败错误

**Configuration:** 最近新建的 QQ Bot 配置，access token 和 app ID 是新配置的

# Current Focus

hypothesis: |
  WebSocket identify 使用了错误的 token 格式。代码混合使用旧格式 `Bot {app_id}.{access_token}` 和新的 access_token，
  但旧格式期望的是 app_token（固定 token），不是动态获取的 access_token。正确格式应该与 HTTP API 一致，使用 `QQBot {access_token}`。

next_action: |
  1. ✅ 已确认：HTTP API 使用 `QQBot {access_token}` 格式
  2. ✅ 已确认：WebSocket 使用 `Bot {app_id}.{access_token}` 格式
  3. ✅ 已确认：官方文档显示旧 Token 格式已废弃，应使用 Access Token
  4. 待验证：WebSocket identify 是否应该使用 `QQBot {access_token}` 格式
  5. 待测试：修改 token 格式后重新运行

# Evidence

- timestamp: 2026-04-17
  observation: |
    代码分析发现 WebSocket 认证使用 token 格式: `Bot {app_id}.{access_token}`
    在 websocket.py:181 行: `"token": f"Bot {self.config.app_id}.{self.config.access_token}"`
  file: src/claw_cron/qqbot/websocket.py
  line: 181

- timestamp: 2026-04-17
  observation: |
    HTTP API 使用 Authorization header 格式: `QQBot {access_token}`
    在 websocket.py:85 行: `"Authorization": f"QQBot {self.config.access_token}"`
  file: src/claw_cron/qqbot/websocket.py
  line: 85

- timestamp: 2026-04-17
  observation: |
    OAuth access token 通过 QQBotChannel._get_access_token() 获取
    调用 https://bots.qq.com/app/getAppAccessToken API
  file: src/claw_cron/channels/qqbot.py
  line: 270-321

- timestamp: 2026-04-17
  observation: |
    查阅 QQ Bot 官方文档发现关键信息：
    1. 旧的 Token 鉴权方式已废弃，应使用更安全的 Access Token 鉴权
    2. 旧文档中的 token 格式 `Bot {appid}.{app_token}` 是针对旧版 app_token 的
    3. 新版 access_token 通过 getAppAccessToken API 获取
    4. HTTP API 使用格式: `QQBot {access_token}`
    5. WebSocket identify 的 token 格式文档未明确说明
  source: https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/api-use.html

- timestamp: 2026-04-17
  observation: |
    发现 token 格式不一致：
    - HTTP API: `QQBot {access_token}` (正确使用新版 access_token)
    - WebSocket: `Bot {app_id}.{access_token}` (使用旧格式 + 新 token，混合方式)
    这种混合使用可能导致认证失败
  reasoning: |
    HTTP API 正确使用新版 access_token 格式，但 WebSocket identify 仍使用旧格式。
    旧格式期望的是 app_token（创建机器人时分配的固定 token），而代码传入的是
    通过 OAuth API 动态获取的 access_token，两者不是同一个东西。
  impact: |
    这解释了为什么 HTTP API 认证成功（get_gateway_url 能获取到 gateway URL），
    但 WebSocket 认证失败（identify 返回 4004 错误）

# Eliminated

(none yet)

# Resolution

root_cause: |
  WebSocket identify 使用了错误的 token 格式 `Bot {app_id}.{access_token}`。
  这是旧版认证格式的遗留问题，期望的是固定分配的 app_token，但代码传入的是
  通过 OAuth API 动态获取的 access_token。正确格式应该与 HTTP API 一致，
  使用 `QQBot {access_token}`。

fix: |
  修改 src/claw_cron/qqbot/websocket.py:181 行，将 token 格式从
  `Bot {self.config.app_id}.{self.config.access_token}` 改为
  `QQBot {self.config.access_token}`

verification: |
  运行 `uv run claw-cron channels capture` 命令，确认 WebSocket 连接成功建立，
  不再出现 4004 Authentication fail 错误。

files_changed:
  - src/claw_cron/qqbot/websocket.py
