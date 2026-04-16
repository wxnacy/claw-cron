---
phase: "02"
status: issues_found
depth: standard
files_reviewed: 5
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
reviewed: "2026-04-16"
---

# Code Review: Phase 02 — Task Management Commands

## Files Reviewed

- `src/claw_cron/agent.py`
- `src/claw_cron/cli.py`
- `src/claw_cron/cmd/add.py`
- `src/claw_cron/cmd/delete.py`
- `src/claw_cron/cmd/list.py`

---

## Findings

### WR-01 · WARNING · agent.py — Infinite loop with no max-turns guard

**Location:** `run_ai_add()` while loop (line ~93)

**Issue:** The conversation loop has no exit condition other than `stop_reason == "tool_use"`. If the model repeatedly returns `end_turn` without calling the tool (e.g., it keeps asking questions indefinitely, or the user keeps giving ambiguous answers), the loop never terminates.

**Risk:** Runaway API calls, unbounded cost, hung CLI process.

**Recommendation:** Add a `MAX_TURNS` guard:
```python
MAX_TURNS = 10
for _ in range(MAX_TURNS):
    ...
    if response.stop_reason == "tool_use":
        ...
        return
    ...
console.print("[red]Could not collect task details after {MAX_TURNS} turns. Aborting.[/red]")
raise SystemExit(1)
```

---

### INFO-01 · INFO · agent.py — No API error handling

**Location:** `api_client.messages.create(...)` call

**Issue:** `anthropic.APIError` (auth failure, rate limit, network error) will surface as an unhandled exception with a raw traceback rather than a user-friendly message.

**Recommendation:** Wrap the API call:
```python
try:
    response = api_client.messages.create(...)
except anthropic.APIError as e:
    console.print(f"[red]API error: {e}[/red]")
    raise SystemExit(1)
```

---

### INFO-02 · INFO · add.py — Deferred import inside function body

**Location:** `add()` function, line ~50

**Issue:** `from claw_cron.agent import run_ai_add` is imported inside the function body. This is intentional (avoids importing `anthropic` at CLI startup when not needed), but it's a non-standard pattern that could confuse future contributors.

**Recommendation:** Add a comment explaining the intent:
```python
# Deferred import: avoids loading anthropic at startup for direct-mode users
from claw_cron.agent import run_ai_add  # noqa: PLC0415
```

The comment is already partially there (`# noqa: PLC0415`). Consider adding the explanation.

---

## Summary

No critical bugs. One warning (infinite loop risk in AI mode) worth addressing before Phase 3 builds on this. Two informational items are low priority.

Overall code quality is good — clean structure, proper error handling in direct mode, Rich output consistent across commands.
