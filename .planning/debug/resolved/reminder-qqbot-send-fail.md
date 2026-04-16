---
name: reminder-qqbot-send-fail
description: reminder 任务消息发送不到 QQ，且日志不够详细
type: debug
status: resolved
trigger: |
  test-reminder 任务每分钟运行一次，日志显示任务执行，但消息没有发送到 QQ。
  日志内容：
  [2026-04-17 00:43:00] REMINDER: test-reminder
  Test reminder at 00:43:00

  任务配置：
  tasks:
  - client: null
    client_cmd: null
    cron: '* * * * *'
    enabled: true
    message: Test reminder at {{ time }}
    name: test-reminder
    notify:
      channel: qqbot
      recipients:
      - c2c:E75D5875AE7F78E3E069459E888D8BB8
    prompt: null
    script: null
    type: reminder
created: 2026-04-17
updated: 2026-04-17
---

# Symptoms

**Expected behavior:** 任务执行后应该发送消息到 QQ，并且日志应该记录详细过程

**Actual behavior:** 任务日志只显示 REMINDER，没有通知发送过程，也没有收到 QQ 消息

**Error messages:** 无错误消息显示

**Timeline:** 任务在运行，但消息从未发送成功

**Reproduction:**
1. 创建 reminder 类型任务，配置 notify.channel=qqbot
2. 等待任务执行
3. 日志显示 REMINDER，但 QQ 没收到消息

# Current Focus

reasoning_checkpoint:
  hypothesis: "get_channel() doesn't load channel config from config.yaml, causing ChannelConfigError when trying to instantiate QQBotChannel. The exception is then silently caught and ignored in executor.py."
  confirming_evidence:
    - "Test confirmed: get_channel('qqbot') creates channel with config.app_id=None"
    - "config.yaml has qqbot credentials, but they're not loaded by get_channel()"
    - "_get_access_token() raises ChannelConfigError: 'QQ Bot app_id is required'"
    - "executor.py catches all exceptions and uses 'pass' statement, hiding the error"
  falsification_test: "After adding config loading logic, get_channel() should successfully instantiate QQBotChannel with valid credentials, and notifications should be sent"
  fix_rationale: "Modify notifier.py to load channel config from config.yaml before calling get_channel(). Add logging to executor.py to capture notification errors. This addresses the root cause (missing config loading) and makes debugging possible (proper logging)."
  blind_spots: "Haven't tested if the QQ Bot API credentials are actually valid (only checked that they exist in config.yaml). Haven't verified the recipient openid format is correct."

hypothesis: |
  executor.py:101-103 捕获所有异常并静默忽略，导致通知失败时无法追踪原因。
  同时，notifier.notify_task_result() 的返回值（MessageResult列表）未被检查，
  即使发送失败也无法知道具体原因。

test: |
  1. 检查 QQ bot 配置是否存在（config.yaml 或环境变量）
  2. 测试 get_channel('qqbot') 是否能正确实例化
  3. 检查 notify_task_result 的返回值是否包含错误信息

expecting: |
  - 如果 QQ bot 配置缺失，会抛出 ChannelConfigError
  - 如果配置存在但发送失败，MessageResult 会包含错误信息
  - 但由于 executor.py 的 pass 语句，这些错误都被静默处理了

next_action: |
  实现修复方案：
  1. 修改 notifier.py 加载 channel 配置
  2. 在 executor.py 添加错误日志
  3. 测试修复后的通知功能

# Evidence

- timestamp: 2026-04-17
  observation: |
    executor.py:98-103 异常处理静默失败：
    try:
        notifier = Notifier()
        await notifier.notify_task_result(task, exit_code, output)
    except Exception:
        # Log but don't fail the task
        pass
  file: src/claw_cron/executor.py
  line: 98-103

- timestamp: 2026-04-17
  observation: |
    任务配置正确，notify 字段有 channel=qqbot 和 recipients
  file: ~/.config/claw-cron/tasks.yaml

- timestamp: 2026-04-17
  observation: |
    日志只记录 REMINDER，没有记录通知发送过程
  file: src/claw_cron/executor.py
  line: 52

- timestamp: 2026-04-17
  observation: |
    notifier.py 返回 MessageResult 列表，包含 success/error 字段，
    但 executor.py 没有检查返回值。notifier 内部在获取 channel 时（148-157行）
    和发送消息时（163-172行）都捕获了异常并返回包含错误信息的 MessageResult。
  file: src/claw_cron/notifier.py
  line: 128-174

- timestamp: 2026-04-17
  observation: |
    QQBotChannel 需要 app_id 和 client_secret 配置。
    配置优先级：环境变量(CLAW_CRON_QQBOT_*) > config.yaml。
    如果配置缺失会抛出 ChannelConfigError。
  file: src/claw_cron/channels/qqbot.py
  line: 54-77, 253-268

- timestamp: 2026-04-17
  observation: |
    channels/__init__.py 正确注册了 'qqbot' channel。
    CHANNEL_REGISTRY['qqbot'] = QQBotChannel
  file: src/claw_cron/channels/__init__.py
  line: 102-103

- timestamp: 2026-04-17
  observation: |
    **ROOT CAUSE CONFIRMED**: config.yaml 中有 qqbot 配置（app_id 和 client_secret），
    但 get_channel('qqbot') 调用时没有传递 config 参数。QQBotChannel 使用默认配置初始化，
    尝试从环境变量读取 CLAW_CRON_QQBOT_APP_ID 和 CLAW_CRON_QQBOT_CLIENT_SECRET。
    由于环境变量未设置，app_id 和 client_secret 为 None，导致 _validate_config()
    抛出 ChannelConfigError。该异常在 executor.py 被捕获并静默忽略。

    测试验证：
    - Channel created successfully with None config
    - get_channel('qqbot') returns channel but config.app_id = None
    - _get_access_token() raises ChannelConfigError: "QQ Bot app_id is required"
  file: src/claw_cron/notifier.py, src/claw_cron/channels/__init__.py, src/claw_cron/channels/qqbot.py
  line: notifier.py:149, channels/__init__.py:95, qqbot.py:259-268

# Eliminated

(none yet)

# Resolution

root_cause: |
  **Two bugs found:**

  1. **Config loading bug (Primary)**: notifier.py 调用 get_channel(task.notify.channel) 时
     没有传递 channel 配置。config.yaml 中的 qqbot 凭证被忽略，导致 ChannelConfigError。

  2. **Silent failure bug (Secondary)**: executor.py:101-103 捕获所有异常并静默忽略（pass），
     导致 ChannelConfigError 和其他通知错误无法被追踪和调试。

fix: |
  **Three files modified:**

  1. **src/claw_cron/notifier.py**: Load channel config from config.yaml and pass to get_channel()
  2. **src/claw_cron/channels/qqbot.py**: Accept dict in __init__ and convert to QQBotConfig
  3. **src/claw_cron/executor.py**: Add proper logging to capture notification errors
  4. **src/claw_cron/cli.py**: Configure logging format for better visibility

  **Test verification:**
  - Created test task with qqbot notification
  - Successfully obtained access token from QQ Bot API
  - Successfully sent message to recipient via QQ Bot
  - Logging correctly shows "Notification sent successfully to 1 recipient(s) via qqbot"

verification: |
  ✓ Test script confirmed notification sent successfully
  ✓ Logging now shows detailed notification process
  ✓ QQ Bot API calls succeeded (access token + message send)
  ✓ Message delivered to recipient

files_changed:
  - src/claw_cron/notifier.py (load config from config.yaml)
  - src/claw_cron/channels/qqbot.py (accept dict config)
  - src/claw_cron/executor.py (add logging)
  - src/claw_cron/cli.py (configure logging)
