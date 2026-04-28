---
name: claw-cron
description: AI-powered cron task manager for scheduling and managing automated tasks. Use when users need to (1) create, list, or delete scheduled tasks (cron jobs), (2) set up timed reminders via iMessage or QQ Bot, (3) schedule AI agent tasks, or (4) manage tasks through natural language. Triggers include phrases like "创建定时任务", "设置提醒", "每天/每周执行", "定时提醒我", "添加 cron 任务".
---

# claw-cron

## Quick Start

```bash
# Add command task
claw-cron add --name test --cron "0 8 * * *" --type command --script "echo hello"

# Interactive command creation
claw-cron command

# Direct command creation
claw-cron command --name backup --cron "0 2 * * *" --script "backup.sh"

# Add AI agent task
claw-cron add --name ai-task --cron "0 9 * * *" --type agent --prompt "总结今日待办" --client codebuddy

# Add reminder
claw-cron remind --name morning --cron "0 8 * * *" \
    --message "Good morning! Today is {{ date }}" \
    --channel imessage --recipient "+8613812345678"
```

## Commands

| Command | Description |
|---------|-------------|
| `claw-cron add` | Add a new scheduled task |
| `claw-cron command` | Create a command-type task (supports interactive mode) |
| `claw-cron list` | List all tasks |
| `claw-cron update <name>` | Update fields of an existing task (`--cron`, `--enabled`, `--message`, `--script`, `--prompt`, notify options); omit all options for interactive mode |
| `claw-cron delete <name>` | Delete a task (`-y` to skip confirmation) |
| `claw-cron run <name>` | Execute a task immediately |
| `claw-cron log <name>` | View execution logs |
| `claw-cron remind` | Create a reminder (supports interactive mode) |
| `claw-cron chat` | Natural language task management |
| `claw-cron server` | Start/stop/restart the scheduler service |
| `claw-cron channels` | Manage notification channels (add, capture, send, etc.) |
| `claw-cron config` | Manage configuration |

## Task Types

| Type | Description | Required Params |
|------|-------------|-----------------|
| `command` | Execute shell command | `--script` |
| `agent` | Execute AI agent task | `--prompt`, `--client` |
| `reminder` | Send notification | `--message` |

## AI Clients

`kiro-cli`, `codebuddy`, `opencode`

## Notification Channels

| Channel | Description | Recipient Format |
|---------|-------------|-----------------|
| `system` | macOS desktop notification (default, no config needed) | `local` |
| `imessage` | iMessage | `+8613812345678` |
| `qqbot` | QQ Bot | `c2c:OPENID` / `group:GROUP_ID` |
| `wecom` | 企业微信 | openid |
| `feishu` | 飞书 | openid |
| `email` | Email | email address |

Tasks default to `system` channel. Multiple channels supported per task:

```yaml
notify:
  - channel: system
    recipients: [local]
  - channel: qqbot
    recipients: [c2c:OPENID]
    when: "signed_in == false"
```

## Template Variables

- `{{ date }}` - Current date (YYYY-MM-DD)
- `{{ time }}` - Current time (HH:MM:SS)
- `{{ context.KEY }}` - Task context value (e.g. `{{ context.signed_in }}`)

## Context Injection (v3.0)

Command tasks receive system context via environment variables:

| Variable | Description |
|----------|-------------|
| `CLAW_TASK_NAME` | Task name |
| `CLAW_TASK_TYPE` | Task type |
| `CLAW_LAST_EXIT_CODE` | Exit code of previous run |
| `CLAW_LAST_OUTPUT` | Output of previous run (max 4096 chars) |
| `CLAW_EXECUTION_TIME` | Current execution timestamp |
| `CLAW_EXECUTION_COUNT` | Total execution count |
| `CLAW_LAST_EXECUTION_TIME` | Previous execution timestamp |
| `CLAW_CONTEXT_FILE` | Path to full context JSON file |
| `CLAW_CONTEXT_<KEY>` | Custom env vars from task `env` field |

Custom env vars in task config:

```yaml
tasks:
  - name: my-task
    type: command
    cron: "0 8 * * *"
    env:
      API_KEY: "abc123"      # injected as CLAW_CONTEXT_API_KEY
      REGION: "us-east-1"    # injected as CLAW_CONTEXT_REGION
    script: "curl -H 'X-Key: $CLAW_CONTEXT_API_KEY' https://api.example.com"
```

## Context Feedback (v3.0)

Scripts can write back to context by printing JSON as the last line of stdout:

```python
import json

result = do_something()
# Last line must be valid JSON dict — gets merged into task context
print(json.dumps({"signed_in": result, "last_status": "ok"}))
```

Context persists at `~/.config/claw-cron/context/{task_name}.json` and is available in subsequent runs via env vars and `{{ context.KEY }}` templates.

## Conditional Notification (v3.0)

Use `when` in notify config to suppress notifications based on context:

```yaml
notify:
  channel: imessage
  recipients: ["+8613812345678"]
  when: "signed_in == false"   # only notify when condition is true
```

Supported operators: `==`, `!=`

Supported value types: `true`/`false` (bool), integers, floats, strings

**Behavior:**
- `when` omitted → always notify (backward compatible)
- Key missing in context → notify (conservative fallback)
- Parse error → notify (conservative fallback)

### Sign-in Task Example

```yaml
tasks:
  - name: daily_signin
    type: command
    cron: "0 8 * * *"
    script: python3 ~/scripts/signin.py
    notify:
      channel: imessage
      recipients: ["+8613812345678"]
      when: "signed_in == false"   # only notify on failure
```

```python
# signin.py — last line must be JSON
import json
success = do_signin()
print(json.dumps({"signed_in": success}))
```

## Server Command

```bash
# Start scheduler in foreground (default)
claw-cron server

# Start as background daemon
claw-cron server --daemon

# Stop the running daemon
claw-cron server --stop

# Restart the daemon (stop then start)
claw-cron server --restart

# Check daemon status (running/stopped, PID, log path)
claw-cron server --status
```

## Channels Command

```bash
# Add a notification channel (interactive)
claw-cron channels add

# Capture recipient ID (interactive, supports qqbot/wecom/feishu)
claw-cron channels capture

# Send a test message
claw-cron channels send "test message" --channel qqbot --recipient me

# List configured channels
claw-cron channels list
```

## Update Command

```bash
# Interactive mode (no options)
claw-cron update <name>

# Scalar fields
claw-cron update <name> --cron "0 9 * * *"
claw-cron update <name> --enabled false
claw-cron update <name> --script "new_script.sh"

# Notify: add channel
claw-cron update <name> --notify-add system
claw-cron update <name> --notify-add qqbot --notify-recipient c2c:XXX
claw-cron update <name> --notify-add qqbot --notify-recipient c2c:XXX --notify-when "signed_in == false"

# Notify: remove channel
claw-cron update <name> --notify-remove qqbot

# Notify: modify existing channel
claw-cron update <name> --notify-channel qqbot --notify-recipient c2c:NEW
claw-cron update <name> --notify-channel qqbot --notify-when "signed_in == false"
claw-cron update <name> --notify-channel qqbot --notify-when ""   # clear condition

# Notify: clear all
claw-cron update <name> --notify-clear
```

Interactive mode uses a `select` loop — pick a field, edit it, repeat, then choose "完成" to exit.

## Delete Command

```bash
claw-cron delete <name>        # prompts for confirmation
claw-cron delete <name> -y     # skip confirmation (for scripts)
```



5-field format: `minute hour day month weekday`

```
* * * * *
│ │ │ │ │
│ │ │ │ └─ 星期几 (0-7, 0和7都是周日)
│ │ │ └─── 月份 (1-12)
│ │ └───── 日期 (1-31)
│ └─────── 小时 (0-23)
└───────── 分钟 (0-59)
```

| Field | Range | Description |
|-------|-------|-------------|
| minute | 0-59 | Minute of hour |
| hour | 0-23 | Hour of day |
| day | 1-31 | Day of month |
| month | 1-12 | Month of year |
| weekday | 0-6 | Day of week (0=Sunday) |

### Special Characters

| Char | Meaning | Example |
|------|---------|---------|
| `*` | Any value | `* * * * *` = every minute |
| `,` | Value list | `0,30 * * * *` = at 0 and 30 min |
| `-` | Range | `0 9-17 * * *` = hourly 9am-5pm |
| `/` | Step | `*/15 * * * *` = every 15 min |

### Common Patterns

| Expression | Description |
|------------|-------------|
| `0 * * * *` | Every hour |
| `0 8 * * *` | Every day at 8am |
| `0 8 * * 1` | Every Monday at 8am |
| `0 9 1 * *` | 1st of every month at 9am |
| `*/30 * * * *` | Every 30 minutes |
| `0 8,12,18 * * *` | 8am, noon, 6pm daily |
| `0 9-17 * * 1-5` | Hourly 9-5 on weekdays |

## Examples

### Command Tasks

```bash
# Every hour health check
claw-cron add --name health-check --cron "0 * * * *" \
    --type command --script "curl -s https://api.example.com/health"

# Every 15 minutes sync data
claw-cron add --name sync-data --cron "*/15 * * * *" \
    --type command --script "rsync -av /data /backup"

# Daily cleanup at 2am
claw-cron add --name cleanup --cron "0 2 * * *" \
    --type command --script "find /tmp -mtime +7 -delete"

# Weekly report every Friday at 5pm
claw-cron add --name weekly-report --cron "0 17 * * 5" \
    --type command --script "./generate-report.sh"
```

### Interactive Command Creation

```bash
# Interactive mode - guided prompts (defaults to system channel notification)
claw-cron command

# Direct mode — system notification by default
claw-cron command --name backup --cron "0 2 * * *" --script "backup.sh"

# Disable notification
claw-cron command --name backup --cron "0 2 * * *" --script "backup.sh" --no-notify

# With QQ Bot notification
claw-cron command --name health-check --cron "*/30 * * * *" \
    --script "curl -s https://api.example.com/health" \
    --channel qqbot --recipient me
```

### AI Agent Tasks

```bash
# Daily morning summary at 9am
claw-cron add --name morning-summary --cron "0 9 * * *" \
    --type agent --prompt "总结今日待办事项" --client codebuddy

# Weekly work summary every Monday at 6pm
claw-cron add --name weekly-summary --cron "0 18 * * 1" \
    --type agent --prompt "总结本周工作内容，生成周报" --client codebuddy

# Monthly review on 1st at 10am
claw-cron add --name monthly-review --cron "0 10 1 * *" \
    --type agent --prompt "回顾上月项目进展，制定本月计划" --client codebuddy
```

### Reminders

```bash
# Interactive reminder creation (system channel available by default, no pre-config needed)
claw-cron remind

# Direct mode — system notification by default
claw-cron remind --name standup --cron "0 9 * * *" \
    --message "Daily standup at {{ time }}"

# With iMessage
claw-cron remind --name standup --cron "0 9 * * *" \
    --message "Daily standup meeting starting at {{ time }}" \
    --channel imessage --recipient "+8613812345678"

# Weekly meeting reminder via QQ Bot
claw-cron remind --name weekly-meeting --cron "0 14 * * 1" \
    --message "Weekly sync meeting in 10 minutes" \
    --channel qqbot --recipient "group:123456"
```

## Data Storage

`~/.config/claw-cron/tasks.yaml`
