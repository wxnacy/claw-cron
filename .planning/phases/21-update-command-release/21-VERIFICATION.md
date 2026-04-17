---
phase: 21
status: passed
verified: 2026-04-18
---

# Verification: Phase 21 — Update Command & Release

## Must-Haves

| # | Requirement | Check | Status |
|---|-------------|-------|--------|
| 1 | UPD-01: `claw-cron update <name>` command exists and registered | `cli.add_command(update)` present, `def update(name: str, ...)` defined | ✓ PASS |
| 2 | UPD-02: `--cron` option works | `@click.option("--cron", ...)` + `updates["cron"] = cron` | ✓ PASS |
| 3 | UPD-03: `--enabled` option works | `@click.option("--enabled", ..., type=bool)` + `updates["enabled"] = enabled` | ✓ PASS |
| 4 | UPD-04: `--message` option works | `@click.option("--message", ...)` + `updates["message"] = message` | ✓ PASS |
| 5 | UPD-05: `--script` option works | `@click.option("--script", ...)` + `updates["script"] = script` | ✓ PASS |
| 6 | UPD-06: `--prompt` option works | `@click.option("--prompt", ...)` + `updates["prompt"] = prompt` | ✓ PASS |
| 7 | VER-02: Version is 0.3.1 | `__version__ = "0.3.1"` in `__about__.py` | ✓ PASS |
| 8 | Task-not-found returns exit code 1 | `raise SystemExit(1)` after red error message | ✓ PASS |
| 9 | No-options-provided returns exit code 0 | `raise SystemExit(0)` after yellow warning | ✓ PASS |

## Score: 9/9 must-haves verified

## Automated Checks

```
$ claw-cron update --help
Usage: claw-cron update [OPTIONS] NAME

  Update fields of an existing task by NAME.

Options:
  --cron TEXT        New cron expression (5 fields, e.g. '0 8 * * *')
  --enabled BOOLEAN  Enable or disable the task (true/false)
  --message TEXT     New notification message template
  --script TEXT      New shell script content (command type)
  --prompt TEXT      New AI prompt content (chat type)
  -h, --help         Show this message and exit.
```

## Requirement Traceability

| Requirement | Status |
|-------------|--------|
| UPD-01 | ✓ Complete |
| UPD-02 | ✓ Complete |
| UPD-03 | ✓ Complete |
| UPD-04 | ✓ Complete |
| UPD-05 | ✓ Complete |
| UPD-06 | ✓ Complete |
| VER-02 | ✓ Complete |
