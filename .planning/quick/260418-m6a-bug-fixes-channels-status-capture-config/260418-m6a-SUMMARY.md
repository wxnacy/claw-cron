# Quick Task 260418-m6a: Summary

**Date:** 2026-04-18
**Status:** Complete

## What Was Done

### fix: system channel 状态显示错误 (`fc79b4d`)

`get_channel_status` 先检查 `channel_id not in channels_config` 就返回 `○ 未配置`，system 没有配置文件条目所以被误判。在 not-in 分支加 system 特判，提前返回 `✓ 已配置`，并删除后面多余的 `elif channel_id == "system": pass`。

### fix: update 添加渠道显示全局配置状态而非 task 状态 (`3f05acd`)

`_notify_interactive` 的"添加渠道"用 `prompt_channel_select()` 显示全局 channel 配置状态，与当前 task 无关。改为内联 select，标注该 task 已添加的渠道为 `[已添加]`。

### fix: capture 未传 config 给 get_channel (`01b87ce`)

`capture` 和 `_do_wecom_capture` 调用 `get_channel(channel_type)` 不传 config，导致 `FeishuConfig()` 只读环境变量，`app_id=None` 报错。改为先从 `config.yaml` 读取对应 channel 配置再传入。

### fix: feishu capture event loop 冲突 (`382a63c`)

`lark.ws.Client.start()` 是同步阻塞方法，内部调 `loop.run_until_complete()`，在已有 event loop 里 `await` 报 `Cannot run the event loop while another loop is running`。改为 `threading.Thread(daemon=True)` 在后台线程运行，主 async loop 轮询 `captured_openid` 等待结果。

## Files Changed

- `src/claw_cron/channels/__init__.py`
- `src/claw_cron/channels/feishu.py`
- `src/claw_cron/cmd/channels.py`
- `src/claw_cron/cmd/update.py`

## Commits

- `3f05acd` fix(update): show task-level notify status instead of global channel config
- `fc79b4d` fix(channels): system channel always shows as configured
- `01b87ce` fix(channels): pass config.yaml to get_channel in capture commands
- `382a63c` fix(feishu): run ws_client.start() in daemon thread to avoid event loop conflict
