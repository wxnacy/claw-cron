---
phase: 06-message-channels-imessage
plan: 02
subsystem: channels
tags: [imessage, macos, applescript, messaging]
requires:
  - 06-01
provides:
  - IMessageChannel class
  - IMessageConfig configuration
affects:
  - channels module
  - notification system (future)
tech-stack:
  added:
    - macpymessenger>=0.2.0
  patterns:
    - AppleScript integration via subprocess
    - Platform-specific channel implementation
key-files:
  created:
    - src/claw_cron/channels/imessage.py
  modified:
    - pyproject.toml
    - src/claw_cron/channels/__init__.py
decisions:
  - Use AppleScript via subprocess instead of Python API (macpymessenger 0.2.0 only provides .scpt file)
metrics:
  duration: 3m
  completed_date: "2026-04-16"
  tasks: 3
  files: 3
  commits: 2
---

# Phase 6 Plan 02: iMessage Implementation Summary

## One-Liner

IMessageChannel implementation using AppleScript subprocess calls, registered in channel registry for macOS iMessage notifications.

## Objective

Implement the iMessage channel using AppleScript integration, enabling message notifications on macOS.

## Completed Tasks

| Task | Description | Status | Commit |
|------|-------------|--------|--------|
| 1 | Add macpymessenger dependency | ✅ Complete | eef5672 |
| 2 | Implement IMessageChannel class | ✅ Complete | 660cc89 |
| 3 | Add First-Run Permission Documentation | ✅ Complete | 660cc89 |

## Key Changes

### 1. Added macpymessenger Dependency

**File:** `pyproject.toml`

- Added `macpymessenger>=0.2.0` for iMessage support on macOS
- Package provides AppleScript for Messages.app integration

### 2. Implemented IMessageChannel Class

**File:** `src/claw_cron/channels/imessage.py`

Created `IMessageChannel` class with:
- `IMessageConfig` configuration class (inherits from `ChannelConfig`)
- `send_text()` - sends plain text iMessage via AppleScript
- `send_markdown()` - falls back to plain text (iMessage doesn't support markdown)
- `health_check()` - verifies Messages.app is available
- `_normalize_phone()` - normalizes phone numbers including +86 format
- `_send_applescript()` - sends message via osascript subprocess

**Platform Detection:**
- Raises `ChannelNotAvailableError` on non-macOS platforms
- Graceful error messages for permission issues

### 3. Registered Channel in Registry

**File:** `src/claw_cron/channels/__init__.py`

- Imported `IMessageChannel` from imessage module
- Registered in `CHANNEL_REGISTRY["imessage"]`
- Available via `get_channel("imessage")`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] AppleScript Direct Integration**

- **Found during:** Task 1 verification
- **Issue:** macpymessenger 0.2.0 only contains a .scpt AppleScript file, not a Python API as documented in research
- **Fix:** Implemented `_send_applescript()` method using subprocess to call osascript directly, using the bundled .scpt file or inline AppleScript as fallback
- **Files modified:** `src/claw_cron/channels/imessage.py`
- **Commit:** 660cc89

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| IMSG-01 | Implement IMessageChannel class | ✅ Complete |
| IMSG-02 | Add macpymessenger dependency | ✅ Complete |
| IMSG-03 | Support +86 international number format | ✅ Complete |
| IMSG-04 | First-run permission request prompt | ✅ Complete |

## Verification Results

```bash
✓ Channel registered in CHANNEL_REGISTRY
✓ channel_id returns "imessage"
✓ IMessageConfig created successfully
✓ MessageResult works correctly
✓ Type check passed (0 errors, 0 warnings)
```

## Files Created/Modified

| File | Type | Description |
|------|------|-------------|
| `pyproject.toml` | Modified | Added macpymessenger dependency |
| `src/claw_cron/channels/imessage.py` | Created | IMessageChannel implementation |
| `src/claw_cron/channels/__init__.py` | Modified | Registered IMessageChannel |
| `uv.lock` | Modified | Lockfile updated |

## Commits

| Hash | Message |
|------|---------|
| eef5672 | feat(06): add macpymessenger dependency |
| 660cc89 | feat(06): implement IMessageChannel class |

## Technical Notes

### Implementation Details

1. **AppleScript Integration:**
   - Uses `subprocess.run()` to execute osascript
   - Supports bundled .scpt file from macpymessenger package
   - Falls back to inline AppleScript if .scpt not found

2. **Phone Number Normalization:**
   - Removes spaces, dashes, parentheses
   - Preserves + prefix for international format
   - Supports +86 Chinese mobile numbers

3. **Permission Handling:**
   - Catches accessibility permission errors
   - Returns user-friendly error message with setup instructions
   - Module docstring documents first-time setup steps

### Platform Requirements

- **macOS Only:** Channel raises `ChannelNotAvailableError` on Linux/Windows
- **Messages.app:** Must be logged into iMessage account
- **Accessibility Permission:** Required for AppleScript to control Messages.app

## Next Steps

1. Test iMessage sending on macOS with real phone number
2. Proceed to Phase 7 (QQ Channel) or Phase 8 (Task Notification Integration)
3. Consider adding unit tests for phone number normalization

## Self-Check

| Check | Status |
|-------|--------|
| Files exist | ✅ PASSED |
| Commits exist | ✅ PASSED |
| Type check passed | ✅ PASSED |
| Channel registered | ✅ PASSED |

**Self-Check: PASSED**
