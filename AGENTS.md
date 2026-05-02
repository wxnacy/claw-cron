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
- `src/claw_cron/cmd/chat.py` — Natural language chat for task management (claude/openai/codebuddy)
- `src/claw_cron/scheduler.py` — Cron expression parser and scheduler loop
- `src/claw_cron/executor.py` — Task executor with notification support
- `src/claw_cron/storage.py` — YAML task storage
- `src/claw_cron/notifier.py` — Notification dispatch (qqbot, wecom, feishu, system, imessage, email)
- `src/claw_cron/channels/` — Channel implementations (qqbot, wecom, feishu)
- `src/claw_cron/providers/` — AI provider abstractions (claude, openai, codebuddy)
- `src/claw_cron/providers/codebuddy.py` — Codebuddy SDK provider with MCP tool support
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
claw-cron server --pid        # Print daemon PID (empty if not running)
```

### List Tasks

```bash
claw-cron list              # List all tasks with Name, Cron, Type, Script/Prompt, Channels, Status
```

### Add a Task (Direct Mode)

```bash
claw-cron add --name test --cron "0 8 * * *" --type command --script "echo hello"
```

### Chat (Natural Language)

```bash
claw-cron chat                          # Interactive AI chat (default: claude)
claw-cron chat --agent codebuddy        # Use codebuddy provider
claw-cron chat -a openai -m gpt-4o-mini # Use openai with specific model
```

Supported operations via chat: list tasks, add task, delete task, run task, enable/disable task.

## Brew Service (macOS)

Register `claw-cron server` as a launchd service managed by Homebrew Services.

```bash
make service            # 生成 plist 并注册服务（开机自启）
make service-uninstall  # 停止并注销服务
```

日常管理（注册后）：

```bash
brew services start claw-cron
brew services stop claw-cron
brew services restart claw-cron
brew services list
```

- plist 路径：`~/Library/LaunchAgents/homebrew.mxcl.claw-cron.plist`
- 服务日志：`~/.config/claw-cron/server.log`
- 二进制路径通过 `uv tool dir` 动态获取
