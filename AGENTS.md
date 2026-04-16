# AGENTS.md

## Project: claw-cron

AI-powered cron task manager.

## Entry Points

- CLI: `claw-cron` (via `uv run claw-cron`)
- Module: `python -m claw_cron`

## Key Files

- `src/claw_cron/cli.py` — Click CLI group entry
- `src/claw_cron/cmd/` — Subcommand modules
- `src/claw_cron/storage.py` — YAML task storage
- `~/.config/claw-cron/tasks.yaml` — Task data file

## Add a Task (Direct Mode)

```bash
claw-cron add --name test --cron "0 8 * * *" --type command --script "echo hello"
```
