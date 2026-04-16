# Phase 8 Research: Task Notification Integration + Scheduled Reminders

**Researched:** 2026-04-16
**Requirements:** NOTIF-01~05, REMIND-01~03

---

## Research Summary

Phase 8 将消息通道集成到任务执行流程中，并新增定时提醒功能。研究涵盖：
1. Task 模型扩展方案
2. Notifier 设计模式
3. remind 命令实现方案
4. 消息模板变量支持

---

## Current Codebase Analysis

### Task Model (storage.py)

```python
@dataclass
class Task:
    name: str
    cron: str
    type: str
    script: str | None = None
    prompt: str | None = None
    client: str | None = None
    client_cmd: str | None = None
    enabled: bool = field(default=True)
```

需要扩展以支持 `notify` 字段。

### Task Execution (executor.py)

```python
def execute_task(task: Task) -> int:
    # 执行任务，返回 exit_code
    # 目前无通知机制
```

需要在执行完成后调用通知发送。

### Channel Factory (channels/__init__.py)

```python
def get_channel(channel_id: str, config: ChannelConfig | None = None) -> MessageChannel:
    # 返回消息通道实例
```

Notifier 将使用此工厂获取通道。

---

## Design Patterns

### Pattern 1: NotifyConfig Dataclass

```python
@dataclass
class NotifyConfig:
    """Notification configuration for a task."""
    channel: str  # 'imessage' | 'qqbot'
    recipients: list[str]  # ['+8613812345678', 'c2c:OPENID']
```

### Pattern 2: Task Model Extension

```python
@dataclass
class Task:
    name: str
    cron: str
    type: str  # 'command' | 'agent' | 'reminder'
    # ... existing fields ...
    notify: NotifyConfig | None = None
    message: str | None = None  # For reminder type
```

### Pattern 3: Notifier Class

```python
class Notifier:
    """Send task execution notifications."""

    async def notify_task_result(
        self,
        task: Task,
        exit_code: int,
        output: str | None = None,
    ) -> list[MessageResult]:
        """Send notification after task execution."""
        channel = get_channel(task.notify.channel)
        message = self._format_message(task, exit_code, output)
        results = []
        for recipient in task.notify.recipients:
            result = await channel.send_text(recipient, message)
            results.append(result)
        return results

    def _format_message(self, task: Task, exit_code: int, output: str | None) -> str:
        """Format notification message."""
        status = "成功" if exit_code == 0 else "失败"
        msg = f"📋 任务: {task.name}\n"
        msg += f"📊 状态: {status}\n"
        if output:
            msg += f"📝 结果:\n{output[:500]}"
        return msg
```

### Pattern 4: Reminder Template Variables

```python
def render_message(template: str) -> str:
    """Render message template with variables."""
    from datetime import datetime
    now = datetime.now()
    return template.replace("{{ date }}", now.strftime("%Y-%m-%d")) \
                   .replace("{{ time }}", now.strftime("%H:%M:%S"))
```

### Pattern 5: Executor Integration

```python
async def execute_task_with_notify(task: Task) -> int:
    """Execute task and send notification if configured."""
    exit_code = execute_task(task)

    if task.notify:
        notifier = Notifier()
        await notifier.notify_task_result(task, exit_code)

    return exit_code
```

---

## Implementation Approach

### Wave 1: Notification Infrastructure

**Requirements:** NOTIF-01~05

1. **Task Model Extension** (NOTIF-01, NOTIF-02)
   - Add `NotifyConfig` dataclass
   - Extend `Task` with `notify` field
   - Update `load_tasks()` to handle new fields

2. **Notifier Implementation** (NOTIF-03, NOTIF-05)
   - Create `src/claw_cron/notifier.py`
   - Implement `Notifier` class with async notification
   - Format messages with task name, status, result

3. **Executor Integration** (NOTIF-03)
   - Modify `execute_task()` to call Notifier
   - Handle async notification in sync context

4. **Config Command** (NOTIF-04)
   - Add `claw-cron config channels` subcommand
   - Display configured channels and their status

### Wave 2: Reminder Command

**Requirements:** REMIND-01~03

1. **Remind Command** (REMIND-01)
   - Create `src/claw_cron/cmd/remind.py`
   - Simplified task creation with `--message` and `--notify`

2. **Reminder Task Type** (REMIND-02)
   - Add `reminder` to task types
   - Handle reminder execution (no script/agent, just notification)

3. **Template Variables** (REMIND-03)
   - Implement `{{ date }}` and `{{ time }}` substitution
   - Apply at execution time

---

## Key Decisions

1. **Async Notification**: 通知发送使用 async 方法，但 executor 保持 sync，通过 `asyncio.run()` 调用
2. **NotifyConfig Separation**: 通知配置独立为 dataclass，便于扩展
3. **Template Variables**: 仅支持简单字符串替换，不引入完整模板引擎
4. **Config Command**: 使用 Click 命令组结构，与现有命令模式一致

---

## Files to Create/Modify

### New Files
- `src/claw_cron/notifier.py` — Notifier class implementation
- `src/claw_cron/cmd/remind.py` — remind command
- `src/claw_cron/cmd/config.py` — config command (for channels)

### Modified Files
- `src/claw_cron/storage.py` — Task model extension
- `src/claw_cron/executor.py` — Notification integration
- `src/claw_cron/cli.py` — Register remind and config commands

---

## Test Scenarios

1. Task with notification config executes and sends message
2. Task without notification config executes silently
3. Notification failure doesn't affect task execution result
4. Reminder command creates task with correct fields
5. Template variables are rendered at execution time
6. Multiple recipients receive notifications
