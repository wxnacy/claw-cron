---
name: capture-hangs-after-openid
description: channels capture 捕获 openid 后程序卡住不退出
type: debug
status: resolved
trigger: |
  uv run claw-cron channels capture
  Save as contact alias [me]:

  Waiting for message...
  Send any message to your QQ Bot to capture your openid.
  Press Ctrl+C to cancel.

  ✓ Session established
  📩 Message from E75D5875AE7F78E3E069459E888D8BB8: 你好，我

  ✓ OpenID captured: E75D5875AE7F78E3E069459E888D8BB8
  Message content: 你好，我
  （程序卡住，没有退出）
created: 2026-04-17
updated: 2026-04-17
---

# Symptoms

**Expected behavior:** 捕获 openid 后，程序应该保存联系人，友好提示后自动退出

**Actual behavior:** 程序捕获 openid 后卡住，没有继续执行保存和退出逻辑

**Error messages:** 无错误消息，程序正常输出但挂起

**Timeline:** 认证失败问题修复后首次测试发现

**Reproduction:**
1. 运行 `uv run claw-cron channels capture`
2. 输入别名
3. 发送消息到 QQ Bot
4. 看到 "✓ OpenID captured" 后程序挂起

# Current Focus

hypothesis: |
  asyncio.gather() 等待所有任务完成，但 ws_client.connect() 的 _connection_loop 是无限循环

next_action: |
  修改 wait_for_capture() 在捕获后主动关闭 WebSocket 连接

# Evidence

- timestamp: 2026-04-17
  observation: |
    代码在 channels.py:248-251 使用 asyncio.gather 并发运行 ws_client.connect() 和 wait_for_capture()
    wait_for_capture() 通过检查 captured_openid 变量来决定是否退出
  file: src/claw_cron/cmd/channels.py
  line: 248-251

- timestamp: 2026-04-17
  observation: |
    ws_client.connect() 调用 _connection_loop()，该循环使用 while self._running 条件
    _running 在 close() 方法中设置为 False
  file: src/claw_cron/qqbot/websocket.py
  line: 104-124

- timestamp: 2026-04-17
  observation: |
    on_message 回调在 channels.py:229-233 设置 captured_openid
    但没有触发 ws_client 的关闭
  file: src/claw_cron/cmd/channels.py
  line: 229-233

- timestamp: 2026-04-17
  observation: |
    asyncio.gather() 默认等待所有传入的任务完成 (return_exceptions=False)
    当 wait_for_capture() 完成后，ws_client.connect() 仍在运行
    因为 _connection_loop() 的 while self._running 条件仍为 True
  file: src/claw_cron/cmd/channels.py
  line: 248-251

- timestamp: 2026-04-17
  observation: |
    finally 块中的 ws_client.close() (line 256) 永远不会执行
    因为 gather() 永远不会返回
  file: src/claw_cron/cmd/channels.py
  line: 255-256

# Eliminated

- hypothesis: wait_for_capture 任务没有正确终止
  reason: wait_for_capture() 正确地在 captured_openid 设置后退出循环，问题不在这里

# Resolution

root_cause: |
  asyncio.gather() 等待所有任务完成。wait_for_capture() 在捕获 openid 后退出，
  但 ws_client.connect() 内部的 _connection_loop() 是无限循环 (while self._running)，
  且 self._running 在捕获后没有被设置为 False，导致 gather() 永远不返回。

fix: |
  在 wait_for_capture() 中捕获到 openid 后，调用 ws_client.close() 来：
  1. 设置 self._running = False
  2. 触发 WebSocket 连接关闭
  3. 使 _connection_loop 退出
  4. 让 gather() 能够返回

  修改 channels.py:244-247 的 wait_for_capture() 函数：

  ```python
  async def wait_for_capture() -> None:
      while not captured_openid:
          await asyncio.sleep(0.5)
      # Capture complete - close WebSocket to allow gather() to return
      await ws_client.close()
  ```

  这样可以确保：
  1. 捕获 openid 后主动关闭连接
  2. _connection_loop 的 while self._running 条件变为 False
  3. ws_client.connect() 任务正常退出
  4. gather() 返回，程序继续执行 finally 和后续逻辑

applied: 2026-04-17
verified: Syntax check passed
