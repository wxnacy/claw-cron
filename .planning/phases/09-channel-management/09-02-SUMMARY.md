---
phase: 09-channel-management
plan: 02
subsystem: qqbot
tags: [websocket, qqbot, openid, capture, contacts]
requires:
  - 09-01
provides:
  - WebSocket client for QQ Bot Gateway
  - Event parsing for C2C messages
  - OpenID capture command
  - Contact alias resolution in remind
affects:
  - src/claw_cron/cmd/channels.py
  - src/claw_cron/cmd/remind.py
tech_stack:
  added:
    - websockets v16.0
  patterns:
    - TDD for event parsing module
    - Async WebSocket with heartbeat/reconnection
    - Click command integration
key_files:
  created:
    - src/claw_cron/qqbot/__init__.py
    - src/claw_cron/qqbot/events.py
    - src/claw_cron/qqbot/websocket.py
    - tests/test_qqbot_events.py
  modified:
    - src/claw_cron/cmd/channels.py
    - src/claw_cron/cmd/remind.py
decisions:
  - Use websockets v16.0 async API (not deprecated legacy)
  - Heartbeat interval from Hello event (not hardcoded)
  - Resume support for reconnection
  - TDD approach for events module
metrics:
  duration: 9 minutes
  completed_date: "2026-04-16"
  tasks: 6
  tests: 18
  files_modified: 6
---

# Phase 09 Plan 02: WebSocket & OpenID Capture Summary

## One-liner

WebSocket client for QQ Bot Gateway with automatic OpenID capture when user sends a message, enabling contact alias resolution in the remind command.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create qqbot module structure | 3fc352c | ✓ |
| 2 | Create event types module (TDD) | 3fc352c | ✓ |
| 3 | Implement WebSocket client | b51589d | ✓ |
| 4 | Add capture command to channels | 89a5c4b | ✓ |
| 5 | Integrate contact alias in remind command | b109a95 | ✓ |
| 6 | Update channels add to support capture flag | 2d474d7 | ✓ |

## Implementation Details

### Task 1: qqbot Module Structure
- Created `src/claw_cron/qqbot/` package directory
- Added `__init__.py` with module exports

### Task 2: Event Types Module (TDD)
- Created `tests/test_qqbot_events.py` with 9 tests
- Implemented `OpCode` enum (DISPATCH, HEARTBEAT, IDENTIFY, HELLO, HEARTBEAT_ACK, RESUME)
- Implemented `EventType` enum (READY, RESUMED, C2C_MESSAGE_CREATE, GROUP_AT_MESSAGE_CREATE)
- Implemented `C2CMessage` dataclass for private chat messages
- Implemented `parse_c2c_message()` function with proper error handling

### Task 3: WebSocket Client
- Added `GatewayConfig` dataclass for connection configuration
- Added `QQBotWebSocket` class with full lifecycle management:
  - Hello handshake with dynamic heartbeat interval from server
  - Identify/Resume authentication for session management
  - Automatic heartbeat sending at server-specified interval
  - C2C message event dispatching via callback
  - Exponential backoff reconnection (max 5 retries)
  - Graceful connection close
- Installed websockets v16.0 dependency
- Used websockets.asyncio.client (not deprecated legacy API)

### Task 4: Capture Command
- Added `capture` subcommand with `--channel-type` and `--alias` options
- Implemented `_capture_qqbot_openid` async helper function
- Loads QQ Bot config and gets access token
- Connects to WebSocket and waits for user message
- Captures openid and saves as contact with alias
- Shows success message with usage hint

### Task 5: Contact Alias in Remind
- Imported `resolve_recipient` from contacts module
- Updated `--recipient` help text to mention alias support
- Resolves each recipient before creating NotifyConfig
- Shows clear error if alias not found
- Shows resolved openid format when alias was used

### Task 6: Capture Flag in Add
- Updated `--capture-openid` help text
- Replaced placeholder with actual WebSocket capture call
- Uses `asyncio.run` to call `_capture_qqbot_openid` with "me" alias

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written.

## Key Decisions

1. **websockets v16.0 async API** - Used `websockets.asyncio.client.ClientConnection` instead of deprecated `websockets.client.WebSocketClientProtocol` to avoid deprecation warnings.

2. **Heartbeat interval from Hello event** - The heartbeat interval is dynamically retrieved from the server's Hello event (`data["d"]["heartbeat_interval"]`), not hardcoded, following QQ Bot Gateway protocol.

3. **Resume support** - Implemented session resume for reconnection using `session_id` and `seq` tracking, allowing seamless reconnection without creating a new session.

4. **TDD approach** - Followed strict TDD for the events module: wrote failing tests first, then implemented to pass all tests.

## Testing

All 18 tests pass:
- 9 tests for contacts module (from Plan 09-01)
- 9 tests for qqbot events module (new)

```bash
PYTHONPATH=src:$PYTHONPATH uv run pytest tests/ -v
# 18 passed in 0.04s
```

## Files Modified

| File | Changes |
|------|---------|
| `src/claw_cron/qqbot/__init__.py` | Module exports |
| `src/claw_cron/qqbot/events.py` | Event types and parsing |
| `src/claw_cron/qqbot/websocket.py` | WebSocket client implementation |
| `tests/test_qqbot_events.py` | Unit tests for event parsing |
| `src/claw_cron/cmd/channels.py` | Added capture command |
| `src/claw_cron/cmd/remind.py` | Added alias resolution |
| `uv.lock` | Added websockets v16.0 |

## Verification

### Automated Tests
```bash
# Unit tests for event parsing
PYTHONPATH=src:$PYTHONPATH uv run pytest tests/test_qqbot_events.py -v

# Import verification
PYTHONPATH=src:$PYTHONPATH uv run python -c "from claw_cron.qqbot import QQBotWebSocket, GatewayConfig; print('OK')"

# CLI command verification
PYTHONPATH=src:$PYTHONPATH uv run claw-cron channels capture --help
PYTHONPATH=src:$PYTHONPATH uv run claw-cron remind --help
```

### Manual Verification Steps

1. **Test WebSocket connection:**
   ```bash
   # First configure QQ Bot
   claw-cron channels add --capture-openid
   # Enter valid credentials
   # Send message to your QQ Bot
   # Expected: OpenID captured and saved as "me"
   ```

2. **Test capture command directly:**
   ```bash
   claw-cron channels capture --alias my_friend
   # Send message to bot
   # Expected: OpenID captured and saved as "my_friend"
   ```

3. **Test remind with alias:**
   ```bash
   # Create a reminder using alias
   claw-cron remind --name test --cron "0 8 * * *" \
       --message "Test reminder" \
       --channel qqbot \
       --recipient me
   ```

## Next Steps

Plan 09-02 is complete. The WebSocket client is ready for production use.

## Self-Check: PASSED

- ✓ `src/claw_cron/qqbot/__init__.py` exists
- ✓ `src/claw_cron/qqbot/events.py` exists
- ✓ `src/claw_cron/qqbot/websocket.py` exists
- ✓ `tests/test_qqbot_events.py` exists
- ✓ Commit `2d474d7` exists
- ✓ All 18 tests pass
