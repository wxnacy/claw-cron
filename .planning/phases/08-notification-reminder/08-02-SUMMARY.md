# Phase 8 Plan 02 Summary: Reminder Command

**Completed:** 2026-04-16
**Requirements:** REMIND-01~03

---

## What Was Done

### Task 1: Message Field to Task Model

Added `message: str | None = None` field to Task dataclass in `src/claw_cron/storage.py`.
This field is used by reminder type tasks to store the reminder message template.

### Task 2: Reminder Execution Support

Added to `src/claw_cron/notifier.py`:
- `render_message()` function for template variable substitution
- Supports `{{ date }}` (YYYY-MM-DD) and `{{ time }}` (HH:MM:SS)

Modified `src/claw_cron/executor.py`:
- Added handling for `type='reminder'`
- Reminder tasks return rendered message without running script/agent

### Task 3: Remind Command Implementation

Created `src/claw_cron/cmd/remind.py`:
- `remind` command with required options: --name, --cron, --message, --channel, --recipient
- Creates Task with type='reminder'
- Automatically configures NotifyConfig

Modified `src/claw_cron/cli.py`:
- Imported and registered remind command

### Task 4: Add Command Reminder Support

Modified `src/claw_cron/cmd/add.py`:
- Added 'reminder' to type choices
- Added validation for reminder type (--prompt used as message)
- User guidance to use remind command for better UX

---

## Files Modified

| File | Changes |
|------|---------|
| `src/claw_cron/storage.py` | message field (Plan 01) |
| `src/claw_cron/notifier.py` | render_message() |
| `src/claw_cron/executor.py` | reminder type handling |
| `src/claw_cron/cmd/remind.py` | New file - remind command |
| `src/claw_cron/cmd/add.py` | reminder type support |
| `src/claw_cron/cli.py` | Registered remind command |

---

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| REMIND-01 | remind command creates reminder tasks | Complete |
| REMIND-02 | Reminder task type is 'reminder' with message field | Complete |
| REMIND-03 | Template variables {{ date }} and {{ time }} work | Complete |

---

## Usage Examples

```bash
# Daily morning reminder via iMessage
claw-cron remind --name morning --cron "0 8 * * *" \
    --message "Good morning! Today is {{ date }}" \
    --channel imessage --recipient "+8613812345678"

# Weekly meeting reminder via QQ Bot
claw-cron remind --name weekly-meeting --cron "0 14 * * 1" \
    --message "Weekly meeting starting at {{ time }}" \
    --channel qqbot --recipient "group:123456"
```

---

## Verification

```bash
# remind command help
uv run claw-cron remind --help

# add command accepts reminder type
uv run claw-cron add --help | grep reminder

# render_message works
uv run python -c "from claw_cron.notifier import render_message; ..."
```

---

## Notes

- Reminder tasks are simpler than command/agent tasks - they only send notifications
- The `add` command supports reminder type but `remind` command is preferred
- Template variables are rendered at execution time, not at task creation time
