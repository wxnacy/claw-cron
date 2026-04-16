---
phase: 05-ai-provider-refactor
plan: 02
subsystem: providers
tags:
  - implementation
  - provider-pattern
  - anthropic
  - openai
  - tool-use
requires:
  - 05-01 (Provider Infrastructure)
provides:
  - AnthropicProvider implementation
  - OpenAIProvider implementation
  - get_provider() factory function
  - Refactored agent.py using provider pattern
affects: []
tech-stack:
  added:
    - anthropic SDK (used in AnthropicProvider)
    - openai SDK (used in OpenAIProvider)
  patterns:
    - Factory Pattern (get_provider)
    - Strategy Pattern (provider switching)
    - Data Transfer Objects (ToolDefinition, ToolCall, ProviderResult)
key-files:
  created:
    - src/claw_cron/providers/anthropic.py
    - src/claw_cron/providers/openai.py
  modified:
    - src/claw_cron/providers/__init__.py
    - src/claw_cron/agent.py
decisions:
  - Migrate existing Anthropic logic from agent.py to AnthropicProvider (preserves behavior)
  - Parse OpenAI tool arguments from JSON string format (OpenAI convention)
  - Prepend system message in OpenAI provider (OpenAI convention vs Anthropic separate param)
  - Fallback to provider-specific env vars (ANTHROPIC_API_KEY, OPENAI_API_KEY) for backward compat
  - Use neutral ToolDefinition format in agent.py, providers convert internally
metrics:
  duration: 8m
  completed_date: 2026-04-16
  tasks_completed: 3
  commits: 3
  files_created: 2
  files_modified: 2
  lines_added: 235
---

# Phase 5 Plan 02: Provider Implementations & Agent Refactor Summary

## One-liner

Implemented Anthropic and OpenAI providers with tool calling support, refactored agent.py to use the provider pattern for seamless AI backend switching.

## What Changed

### Provider Implementations Created
```
src/claw_cron/providers/
├── anthropic.py   # AnthropicProvider with Claude Tool Use
└── openai.py      # OpenAIProvider with Function Calling
```

### Factory Function Added
- `get_provider(provider, api_key, model, base_url)` creates provider instances
- Supports `'claude'` and `'openai'` provider names
- Returns `BaseProvider` interface for polymorphic usage

### Agent Refactored
- Removed direct Anthropic SDK dependency
- Uses `get_provider()` factory for provider instantiation
- Tool definition in neutral `ToolDefinition` format
- Configuration loaded from `AIConfig` via `load_ai_config()`
- Fallback to provider-specific env vars for backward compatibility

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Implement AnthropicProvider & Factory Function | dcd4076 | providers/anthropic.py, providers/__init__.py, uv.lock |
| 2 | Implement OpenAIProvider | e894ab7 | providers/openai.py, providers/__init__.py |
| 3 | Refactor agent.py to Use Provider Pattern | 69b57d4 | agent.py |

## Key Artifacts

### AnthropicProvider
```python
from claw_cron.providers import AnthropicProvider, ToolDefinition

provider = AnthropicProvider(
    api_key="sk-ant-...",
    model="claude-3-5-haiku-20241022"
)

result = provider.chat_with_tools(
    messages=[{"role": "user", "content": "Create a daily backup task"}],
    system_prompt="You are a task assistant...",
    tools=[create_task_tool],
)

if result.stop_reason == "tool_use":
    for call in result.tool_calls:
        print(f"Tool: {call.name}, Args: {call.arguments}")
```

### OpenAIProvider
```python
from claw_cron.providers import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",
    model="gpt-4o-mini"
)

# Same interface as AnthropicProvider
result = provider.chat_with_tools(messages, system_prompt, tools)
```

### Factory Function
```python
from claw_cron.providers import get_provider

# Create Claude provider
provider = get_provider("claude", api_key="...", model="claude-3-5-haiku-20241022")

# Create OpenAI provider
provider = get_provider("openai", api_key="...", model="gpt-4o-mini")
```

### Refactored agent.py
```python
from claw_cron.config import load_ai_config
from claw_cron.providers import get_provider

ai_config = load_ai_config()
provider = get_provider(
    provider=ai_config.provider,
    api_key=ai_config.api_key or _get_api_key_from_env(ai_config.provider),
    model=ai_config.get_effective_model(),
)

# Same conversation flow, now provider-agnostic
result = provider.chat_with_tools(messages, system_prompt, tools)
```

## Requirements Addressed

| Requirement | Description | Status |
|-------------|-------------|--------|
| **PROV-01** | Refactor agent.py to Provider pattern | ✅ Complete |
| **PROV-03** | Implement AnthropicProvider with Tool Use | ✅ Complete |
| **PROV-04** | Implement OpenAIProvider with Tool Use | ✅ Complete |
| **PROV-07** | Provider factory function `get_provider()` | ✅ Complete |
| **TOOL-04** | Ensure create_task tool works with both providers | ✅ Complete |

## Verification Results

All success criteria passed:

- ✓ `AnthropicProvider` implements `chat_with_tools()` with tool calling
- ✓ `OpenAIProvider` implements `chat_with_tools()` with function calling
- ✓ `get_provider()` factory supports 'claude' and 'openai'
- ✓ `agent.py` uses provider pattern (no direct SDK calls)
- ✓ Tool definition in neutral `ToolDefinition` format
- ✓ Configuration loaded from `AIConfig`
- ✓ All exports available from `claw_cron.providers` module
- ✓ Error mapping to provider exception hierarchy verified

## Deviations from Plan

None — plan executed exactly as written.

## Phase 5 Complete

With Plan 02 complete, Phase 5 (AI Provider Refactor) is finished.

### Deliverables
- Multi-provider AI support (Anthropic + OpenAI)
- Unified Tool Use interface
- Configuration-driven provider selection
- No breaking changes for existing users

### Usage Examples

**Default (Claude):**
```bash
claw-cron add
# Uses ANTHROPIC_API_KEY or CLAW_CRON_API_KEY
```

**With OpenAI:**
```bash
CLAW_CRON_PROVIDER=openai CLAW_CRON_API_KEY=sk-... claw-cron add
```

**With config file:**
```yaml
# ~/.config/claw-cron/config.yaml
ai:
  provider: openai
  model: gpt-4o-mini
```

## Technical Notes

### Provider Differences Handled

| Aspect | Anthropic | OpenAI |
|--------|-----------|--------|
| System prompt | Separate `system` param | First message in array |
| Tool schema key | `input_schema` | `parameters` |
| Tool arguments | Already parsed dict | JSON string to parse |
| Stop reason | `tool_use` | `tool_calls` |

### Error Mapping

| SDK Error | Provider Exception |
|-----------|-------------------|
| `AuthenticationError` | `ProviderAuthError` |
| `RateLimitError` | `ProviderRateLimitError` |
| `APIError` | `ProviderError` |
| Other exceptions | `ProviderResponseError` |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `CLAW_CRON_PROVIDER` | Provider selection (`claude` or `openai`) |
| `CLAW_CRON_API_KEY` | API key for selected provider |
| `CLAW_CRON_MODEL` | Model override |
| `CLAW_CRON_BASE_URL` | Custom API endpoint |
| `ANTHROPIC_API_KEY` | Fallback for Claude |
| `OPENAI_API_KEY` | Fallback for OpenAI |

## Self-Check: PASSED

All files and commits verified:
- ✓ src/claw_cron/providers/anthropic.py exists
- ✓ src/claw_cron/providers/openai.py exists
- ✓ src/claw_cron/agent.py exists
- ✓ Commit dcd4076 exists
- ✓ Commit e894ab7 exists
- ✓ Commit 69b57d4 exists
