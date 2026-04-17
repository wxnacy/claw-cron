---
plan: 15-01
phase: 15
status: complete
completed: "2026-04-17"
tasks_total: 3
tasks_completed: 3
commits:
  - db93b97
  - ddd593d
---

# Summary: Capture Interaction

## What Was Built

改进了 capture 命令的交互体验，移除了参数驱动的流程，改为全交互式引导。

## Key Changes

### prompt.py
- 新增 `prompt_capture_channel_select()` 函数，仅展示 `supports_capture=True` 的通道（qqbot、feishu），过滤掉 imessage、email

### cmd/channels.py
- 新增 `CHANNEL_DISPLAY_NAMES` 字典（QQ Bot、飞书、企业微信）
- `capture` 命令：移除 `--channel-type` 参数，改为调用 `prompt_capture_channel_select()` 交互选择；status spinner 显示友好通道名；超时错误提示包含"5 分钟"和重试建议；防御性检查不支持 capture 的通道
- `add` 命令：移除 `--capture-openid` 参数；qqbot/feishu 配置成功后自动询问"是否立即获取用户 ID (capture)?"; 提取 `_do_capture()` 内部辅助函数复用逻辑

## Verification

- `channels capture --help` 不含 `--channel-type` ✓
- `channels add --help` 不含 `--capture-openid` ✓
- `CHANNEL_DISPLAY_NAMES` 存在于文件顶部 ✓
- 超时错误消息含"5 分钟"和"重试" ✓
- `prompt_capture_channel_select()` 函数存在 ✓
- 自动询问逻辑 `是否立即获取用户 ID` 出现 2 次（qqbot + feishu）✓

## Must-Haves Status

- [x] CAPT-01: capture 不再需要 --channel-type，改为交互式选择
- [x] CAPT-02: 不支持 capture 的通道显示友好提示
- [x] CAPT-03: add 成功后自动询问是否执行 capture
- [x] CAPT-04: capture 等待时显示包含通道名的 spinner 状态
- [x] CAPT-05: capture 超时后显示带重试建议的错误提示

## Self-Check: PASSED
