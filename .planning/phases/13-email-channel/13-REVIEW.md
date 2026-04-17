---
phase: 13
status: clean
depth: standard
files_reviewed: 4
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
reviewed: "2026-04-17"
---

# Code Review: Phase 13 — email-channel

## Files Reviewed

- `src/claw_cron/channels/email.py`
- `src/claw_cron/channels/__init__.py`
- `src/claw_cron/cmd/channels.py`
- `pyproject.toml`

## Findings

### WR-01: Shadowed asyncio import in channels.py (Warning)

**File:** `src/claw_cron/cmd/channels.py`
**Location:** `add()` email branch, inside `with console.status(...):`

`import asyncio as _asyncio` is declared inside the `with` block, shadowing the module-level `asyncio` import. This works correctly but is confusing — the outer `asyncio` is used for `asyncio.run(...)` in other branches, while `_asyncio` is used only in the email branch.

**Recommendation:** Remove the local import and use the module-level `asyncio` directly (same pattern as qqbot/feishu branches). Same applies to the `verify` email branch.

---

### WR-02: Redundant key filtering in verify email branch (Warning)

**File:** `src/claw_cron/cmd/channels.py`
**Location:** `verify()` email branch

```python
EmailConfig(**{k: v for k, v in email_cfg.items() if k not in ("created_at", "enabled")})
```

`EmailConfig` already has `extra = "ignore"`, so unknown keys like `created_at` and `enabled` are silently dropped. The dict comprehension is redundant. Minor style issue — no functional impact.

**Recommendation:** Simplify to `EmailConfig(**email_cfg)`.

---

### INFO-01: Empty subject edge case in send_markdown (Info)

**File:** `src/claw_cron/channels/email.py`
**Location:** `send_markdown()`, subject extraction

```python
msg["Subject"] = content.split("\n")[0].lstrip("# ")[:50]
```

If `content` is an empty string, subject will be `""`. Empty subjects are technically valid per RFC 5322 but may trigger spam filters. Not a bug — just worth noting.

---

### INFO-02: MIMEMultipart() vs MIMEMultipart("mixed") for attachments (Info)

**File:** `src/claw_cron/channels/email.py`
**Location:** `send_text()` with attachments

`MIMEMultipart()` defaults to `"mixed"` subtype, which is correct for text + attachments. Explicit `MIMEMultipart("mixed")` would be clearer but is functionally identical.

---

## Summary

No critical or blocking issues. Two minor style warnings (shadowed import, redundant dict filter) that don't affect correctness. The implementation correctly follows the `FeishuChannel` pattern, handles multi-recipient, and properly raises `ChannelAuthError` vs returning `MessageResult(success=False)` for auth vs send failures.
