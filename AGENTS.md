# AGENTS.md

## Project: claw-cron

AI-powered cron task manager.

## Entry Points

- CLI: `claw-cron` (via `uv run claw-cron`)
- Module: `python -m claw_cron`

## Key Files

- `src/claw_cron/cli.py` — Click CLI group entry
- `src/claw_cron/cmd/` — Subcommand modules
- `src/claw_cron/cmd/server.py` — Scheduler server command (start/stop/restart daemon)
- `src/claw_cron/scheduler.py` — Cron expression parser and scheduler loop
- `src/claw_cron/executor.py` — Task executor with notification support
- `src/claw_cron/storage.py` — YAML task storage
- `src/claw_cron/notifier.py` — Notification dispatch (qqbot, wecom, feishu, system, imessage, email)
- `src/claw_cron/channels/` — Channel implementations (qqbot, wecom, feishu)
- `~/.config/claw-cron/tasks.yaml` — Task data file
- `~/.config/claw-cron/config.yaml` — Channel configuration file
- `~/.config/claw-cron/claw-cron.pid` — Daemon PID file
- `~/.config/claw-cron/logs/claw-cron.log` — Scheduler system log

## Commands

### Server (Scheduler)

```bash
claw-cron server              # Start scheduler in foreground
claw-cron server --daemon     # Start scheduler as background daemon
claw-cron server --stop       # Stop the running daemon
claw-cron server --restart    # Restart the daemon (stop then start)
claw-cron server --status     # Show daemon status (running/stopped, PID, log path)
```

### Add a Task (Direct Mode)

```bash
claw-cron add --name test --cron "0 8 * * *" --type command --script "echo hello"
```
