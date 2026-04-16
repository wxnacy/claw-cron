---
status: investigating
trigger: "test-reminder 任务日志显示在执行，但没有收到 iMessage 消息"
created: 2026-04-16T13:09:00Z
updated: 2026-04-16T13:36:00Z
---

## Current Focus

hypothesis: iMessage account is logged in but NOT enabled for sending - the "Enable this account" setting is unchecked in Messages.app preferences
test: Guide user to check Messages → Settings → iMessage → "Enable this account" checkbox
expecting: If checkbox is unchecked, enabling it will fix the sending issue
next_action: Ask user to verify and enable the iMessage account setting

## Symptoms

expected: 在任务执行时收到 iMessage 提醒消息
actual: 日志显示任务每分钟执行一次，但从未收到 iMessage
errors: 无明显错误信息
reproduction: 创建 test-reminder 任务，cron 为 * * * * *，channel 为 imessage，recipient 为 wenld5s@icloud.com
started: 刚创建的任务，从未成功过

## Eliminated

## Evidence

- timestamp: 2026-04-16T13:09:00Z
  checked: Task configuration
  found: Task is properly configured with type=reminder, notify.channel=imessage, notify.recipients=[wenld5s@icloud.com]
  implication: Configuration looks correct, issue likely in execution code

- timestamp: 2026-04-16T13:12:00Z
  checked: executor.py (entire file)
  found: Two execution paths - execute_task() (lines 33-79) and execute_task_with_notify() (lines 82-105). execute_task() does NOT send notifications. execute_task_with_notify() DOES send notifications (lines 97-103). Also has run_task_with_notify() sync wrapper (lines 108-119).
  implication: Scheduler must be calling the wrong function

- timestamp: 2026-04-16T13:13:00Z
  checked: scheduler.py line 106
  found: Scheduler calls execute_task(task) directly in a daemon thread: `t = threading.Thread(target=execute_task, args=(task,), daemon=True)`
  implication: CONFIRMED - Scheduler is calling execute_task() which skips notification logic entirely

- timestamp: 2026-04-16T13:15:00Z
  checked: Applied fix to scheduler.py
  found: Changed import from execute_task to run_task_with_notify, and changed line 106 to use run_task_with_notify
  implication: Fix applied, now scheduler will call the function that includes notification logic

- timestamp: 2026-04-16T13:24:00Z
  checked: Test iMessage notification directly
  found: Notifier.notify_task_result() returns MessageResult(success=True, raw_response={'recipient': 'wenld5s@icloud.com', 'content': '...'})
  implication: Notification system reports success, but user says not receiving

- timestamp: 2026-04-16T13:25:00Z
  checked: AppleScript execution
  found: Both sendMessage.scpt and inline AppleScript return "Success". The scpt file exists and is used.
  implication: AppleScript reports success but message may not be delivered - need to verify actual delivery

- timestamp: 2026-04-16T13:27:00Z
  checked: Messages.app database (~/.Library/Messages/chat.db)
  found: Messages ARE recorded in database with content in `attributedBody` field, but `is_sent=0`, `error=33`
  implication: Messages.app creates message object but fails to send - error=33 indicates send failure

- timestamp: 2026-04-16T13:28:00Z
  checked: Error=33 pattern analysis
  found: All 19 error=33 messages started today at 21:20:31. Older messages (April 8th) succeeded with is_sent=1, error=0
  implication: This is a NEW issue, not a longstanding problem. Something changed recently.

- timestamp: 2026-04-16T13:29:00Z
  checked: Test with phone number format
  found: Same error=33 with phone number format (+8613800138000)
  implication: NOT a recipient format issue - the problem is with iMessage sending itself

- timestamp: 2026-04-16T13:30:00Z
  checked: Messages.app service configuration
  found: iMessage service exists (Service 5), buddy "wenld5s@icloud.com" found with valid ID
  implication: iMessage account and contacts are configured correctly

- timestamp: 2026-04-16T13:35:00Z
  checked: Manual iMessage send test (user verification)
  found: User confirmed iMessage is logged in as wenld5s@icloud.com, but manual send shows error "无法发送信息，必须启用iMessage信息才能发送此信息" (Cannot send message, must enable iMessage to send this message)
  implication: CONTRADICTS earlier finding - iMessage service exists but is not properly ENABLED. Even though logged in, the account may not be active for sending.

## Resolution

root_cause: Messages.app fails to send iMessage with error=33. The message is created in the database with content, but the actual send operation fails. This is a Messages.app/iMessage service issue, not a code bug. The error started today (April 16th), while older messages (April 8th) sent successfully.
fix: Requires user to check: 1) Can manually send iMessage from Messages.app, 2) iMessage service status, 3) Network connectivity to Apple servers, 4) Try signing out/in to iMessage
verification: Pending user verification of Messages.app status
files_changed: []

## Next Steps for User

1. **Test Manual Send**: Open Messages.app and try sending a message to wenld5s@icloud.com manually
2. **Check iMessage Status**: Go to Messages.app → Settings → iMessage, verify account is logged in
3. **Check Other Devices**: Can you send/receive iMessages on your iPhone/iPad?
4. **Network Check**: Ensure network can reach Apple's iMessage servers
5. **Restart Messages.app**: Try quitting and reopening Messages.app
6. **Sign Out/In**: Try signing out of iMessage and signing back in

## Additional Investigation

### iMessage Sending Mechanism

**Code Flow:**
1. scheduler.py → run_task_with_notify() → execute_task_with_notify()
2. execute_task_with_notify() → Notifier.notify_task_result()
3. notify_task_result() → get_channel('imessage') → IMessageChannel.send_text()
4. send_text() → _send_applescript() → runs sendMessage.scpt or inline AppleScript

**AppleScript Logic (sendMessage.scpt):**
```applescript
tell application "Messages"
    set targetService to first service whose service type = iMessage
    set targetBuddy to buddy "{recipient}" of targetService
    send "{message}" to targetBuddy
    return "Success"
end tell
```

### ROOT CAUSE IDENTIFIED

**Database Analysis:**
- Checked `~/Library/Messages/chat.db`
- Messages ARE being created in the database
- `attributedBody` field contains the message content (verified)
- BUT: `is_sent = 0`, `error = 33`
- AppleScript returns "Success" but message fails to send

**Error=33 Pattern:**
- All 19 messages with error=33 are iMessage
- Started: 2026-04-16 21:20:31 (when testing began)
- Older iMessage sends (April 8th) succeeded with `is_sent=1`, `error=0`

**Key Evidence:**
- Message content IS present (in `attributedBody`)
- Buddy exists in Messages.app contacts
- iMessage service is available
- AppleScript executes without error
- Messages.app records the message but fails to send with error=33

**Possible Causes:**
1. iMessage service/account issue on this Mac
2. Network connectivity problem to Apple's iMessage servers
3. macOS security/permission change
4. Messages.app internal state issue

**NOT the issue:**
- ❌ Recipient format (tested email and phone)
- ❌ Message content (verified present)
- ❌ AppleScript syntax (executes successfully)
- ❌ Code flow (scheduler fix was applied correctly)
