# Quick Task 260418-iyg: Summary

**Date:** 2026-04-18
**Status:** Complete

## What Was Done

### 新增 System Channel（macOS 桌面通知）

- 新增 `src/claw_cron/channels/system.py`：`SystemChannel` 通过 `osascript` 发送 macOS Notification Center 通知，无需签名或额外配置
- 注册到 `CHANNEL_REGISTRY["system"]`，`get_channel_status` 支持 system 通道（无需配置项）
- 依赖新增：`desktop-notifier`, `pync`

### 多通道通知支持

- `Task.notify` 类型从 `NotifyConfig | None` 扩展为 `NotifyConfig | list[NotifyConfig] | None`
- `NotifyConfig.from_dict_list()` 新方法，支持单个或列表格式
- `storage._task_from_dict()` 支持 notify 字段为 list
- `executor.execute_task_with_notify()` 遍历多个 notify 配置，每个独立发送
- `notifier.Notifier.notify_task_result()` 支持多通道聚合结果

### Command 命令改进

- `--channel` 默认值改为 `"system"`，`--recipient` 默认值改为 `("local",)`
- 新增 `--no-notify` 标志禁用通知
- 交互式模式：通知确认默认改为 `True`，system 通道始终出现在可选列表首位，system 通道自动选择 `local` 收件人

### Remind 命令改进

- `--channel` 默认值改为 `"system"`，`--recipient` 默认值改为 `("local",)`
- 交互式模式：不再强制要求已配置通道，system 通道始终可用
- 进入交互式的条件从 `not all([name, cron, message, channel, recipients])` 改为 `not all([name, cron, message])`

### Delete 命令改进

- 新增 `-y/--yes` 标志，跳过删除确认提示，适合脚本自动化场景

### Contacts 改进

- `resolve_recipient()` 对 system channel 直接返回 recipient，跳过 openid 解析逻辑

## Files Changed

- `src/claw_cron/channels/system.py` (new)
- `src/claw_cron/channels/__init__.py`
- `src/claw_cron/cmd/command.py`
- `src/claw_cron/cmd/delete.py`
- `src/claw_cron/cmd/remind.py`
- `src/claw_cron/contacts.py`
- `src/claw_cron/executor.py`
- `src/claw_cron/notifier.py`
- `src/claw_cron/storage.py`
- `pyproject.toml`
- `uv.lock`
