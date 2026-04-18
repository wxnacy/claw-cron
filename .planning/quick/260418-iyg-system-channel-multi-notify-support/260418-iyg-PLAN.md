# Quick Task 260418-iyg: system channel & multi-notify support

**Date:** 2026-04-18
**Status:** Complete

## Description

新增 macOS 系统通知通道（system channel），支持多通道通知配置，并改进 command/remind/delete 命令的默认行为。

## Tasks

### Task 1: System Channel

- **Files:** `src/claw_cron/channels/system.py`, `src/claw_cron/channels/__init__.py`
- **Action:** 新增 `SystemChannel`，使用 `osascript` 发送 macOS 桌面通知，无需额外配置
- **Done:** ✅

### Task 2: Multi-channel Notify Support

- **Files:** `src/claw_cron/notifier.py`, `src/claw_cron/storage.py`, `src/claw_cron/executor.py`
- **Action:** `Task.notify` 支持 `list[NotifyConfig]`，executor/notifier 支持多通道并发通知
- **Done:** ✅

### Task 3: Command & Remind Default System Channel

- **Files:** `src/claw_cron/cmd/command.py`, `src/claw_cron/cmd/remind.py`, `src/claw_cron/contacts.py`
- **Action:** `command`/`remind` 默认使用 system 通道，`command` 新增 `--no-notify` 标志，交互式不再强制要求已配置通道
- **Done:** ✅

### Task 4: Delete -y Flag

- **Files:** `src/claw_cron/cmd/delete.py`
- **Action:** `delete` 命令新增 `-y/--yes` 标志跳过确认提示
- **Done:** ✅
