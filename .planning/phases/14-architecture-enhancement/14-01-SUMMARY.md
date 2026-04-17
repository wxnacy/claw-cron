---
phase: 14-architecture-enhancement
plan: 01
subsystem: channels
tags: [capture, websocket, abstraction, qqbot, feishu]

requires:
  - phase: 13-email-channel
    provides: MessageChannel base class and channel registry

provides:
  - MessageChannel.supports_capture property (default False)
  - MessageChannel.capture_openid() method (default raises NotImplementedError)
  - QQBotChannel.capture_openid() with asyncio.wait_for timeout
  - FeishuChannel.capture_openid() with asyncio.wait_for timeout
  - Refactored cmd/channels.py capture command using channel abstraction

affects: [phase-15-capture-interaction, phase-16-wechat-channel]

tech-stack:
  added: []
  patterns: [channel abstraction for capture, asyncio.wait_for timeout pattern]

key-files:
  created: []
  modified:
    - src/claw_cron/channels/base.py
    - src/claw_cron/channels/qqbot.py
    - src/claw_cron/channels/feishu.py
    - src/claw_cron/cmd/channels.py

key-decisions:
  - "supports_capture defaults to False in base class — opt-in pattern"
  - "capture_openid() uses asyncio.wait_for for timeout, not manual polling"
  - "cmd/channels.py capture command delegates entirely to channel.capture_openid()"
  - "Removed _capture_qqbot_openid and _capture_feishu_openid — logic now in channel classes"

patterns-established:
  - "Capture abstraction: channel.supports_capture + channel.capture_openid() interface"
  - "asyncio.wait_for wrapping asyncio.gather for timeout on WebSocket capture"

requirements-completed: [ARCH-01, ARCH-02, ARCH-03, ARCH-04]

duration: 25min
completed: 2026-04-17
---

# Phase 14-01: Capture Abstraction Layer Summary

**Unified capture interface added to MessageChannel base — QQBot and Feishu capture logic moved from cmd layer into channel classes, cmd/channels.py now delegates via `channel.capture_openid()`.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-04-17T20:10:00+08:00
- **Completed:** 2026-04-17T20:35:00+08:00
- **Tasks:** 4 completed
- **Files modified:** 4

## Accomplishments

1. **MessageChannel base extended** — `supports_capture` property (default `False`) and `capture_openid(timeout=300)` method (raises `NotImplementedError`) added after `health_check()`.

2. **QQBotChannel.capture_openid()** — Connects to QQ Bot Gateway via `QQBotWebSocket`, registers `on_c2c_message` callback, uses `asyncio.wait_for` with configurable timeout. Raises `ChannelError` on timeout.

3. **FeishuChannel.capture_openid()** — Connects via `lark.ws.Client`, registers `P2ImMessageReceiveV1` handler, uses `asyncio.wait_for` with configurable timeout. Raises `ChannelError` on timeout.

4. **cmd/channels.py refactored** — `capture` command now calls `get_channel(channel_type).capture_openid()`. Deleted `_capture_qqbot_openid` and `_capture_feishu_openid` functions (~155 lines removed). Removed unused `GatewayConfig`, `QQBotWebSocket`, `QQBotConfig` imports.

## Self-Check: PASSED

- `MessageChannel.supports_capture` exists, returns `False` ✓
- `MessageChannel.capture_openid()` raises `NotImplementedError` ✓
- `QQBotChannel.supports_capture` returns `True` ✓
- `FeishuChannel.supports_capture` returns `True` ✓
- `asyncio.wait_for` timeout in both channel implementations ✓
- `_capture_qqbot_openid` and `_capture_feishu_openid` deleted ✓
- `capture` command uses `channel.capture_openid()` ✓
- All modules import cleanly ✓
