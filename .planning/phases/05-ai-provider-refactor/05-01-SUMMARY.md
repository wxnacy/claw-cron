---
phase: 05-ai-provider-refactor
plan: 01
subsystem: providers
tags:
  - infrastructure
  - configuration
  - abstraction
  - tool-use
requires: []
provides:
  - BaseProvider abstract class
  - AIConfig configuration
  - ToolDefinition dataclass
  - Tool converter functions
  - Provider exception hierarchy
affects:
  - src/claw_cron/agent.py (Plan 02)
  - src/claw_cron/providers/anthropic.py (Plan 02)
  - src/claw_cron/providers/openai.py (Plan 02)
tech-stack:
  added:
    - openai==2.32.0
    - pydantic-settings==2.13.1
    - python-dotenv==1.2.2
  patterns:
    - Provider Pattern (abstract base class)
    - Data Transfer Objects (ToolDefinition, ToolCall, ProviderResult)
    - Configuration as Code (pydantic-settings)
key-files:
  created:
    - src/claw_cron/providers/__init__.py
    - src/claw_cron/providers/base.py
    - src/claw_cron/providers/tools.py
    - src/claw_cron/providers/exceptions.py
  modified:
    - pyproject.toml
    - src/claw_cron/config.py
decisions:
  - Use pydantic-settings for configuration management (supports env vars, .env files)
  - Define tools once in neutral ToolDefinition format, providers convert internally
  - Create exception hierarchy for granular error handling
  - Preserve existing config.py functions for backward compatibility
metrics:
  duration: 5m
  completed_date: 2026-04-16
  tasks_completed: 3
  commits: 3
  files_created: 4
  files_modified: 2
  lines_added: 435
---

# Phase 5 Plan 01: Provider Infrastructure & Configuration Summary

## One-liner

Established provider infrastructure with AIConfig, tool abstraction, and BaseProvider interface for multi-provider AI support.

## What Changed

### Dependencies Added
- **openai** (2.32.0) — OpenAI SDK for GPT models
- **pydantic-settings** (2.13.1) — Configuration management with environment variable support
- **python-dotenv** (1.2.2) — .env file support (transitive dependency)

### Provider Module Structure Created
```
src/claw_cron/providers/
├── __init__.py      # Public exports and module documentation
├── base.py          # BaseProvider abstract class + ProviderResult
├── tools.py         # ToolDefinition, ToolCall, converter functions
└── exceptions.py    # Provider exception hierarchy
```

### Configuration Extended
- **AIConfig** class with pydantic-settings integration
- Environment variable support with `CLAW_CRON_` prefix
- Provider default models (Claude: `claude-3-5-haiku-20241022`, OpenAI: `gpt-4o-mini`)
- `get_effective_model()` for automatic default resolution

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add Dependencies & Create Provider Directory Structure | e00748e | pyproject.toml, providers/__init__.py, providers/exceptions.py |
| 2 | Implement AIConfig Configuration Class | d8c03e1 | src/claw_cron/config.py |
| 3 | Implement Tool Abstraction & BaseProvider | e9bcf8d | providers/tools.py, providers/base.py, providers/__init__.py |

## Key Artifacts

### AIConfig Configuration
```python
from claw_cron.config import AIConfig

# Load from environment variables
cfg = AIConfig()  # Reads CLAW_CRON_PROVIDER, CLAW_CRON_API_KEY, etc.

# Or load from config.yaml with env var overrides
cfg = load_ai_config()

# Get effective model (with provider default)
model = cfg.get_effective_model()  # Returns default if not set
```

### Tool Abstraction
```python
from claw_cron.providers import ToolDefinition, to_anthropic_tool, to_openai_tool

tool = ToolDefinition(
    name="create_task",
    description="Create a scheduled task",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "cron": {"type": "string"}
        },
        "required": ["name", "cron"]
    }
)

# Convert to provider-specific formats
anthropic_tool = to_anthropic_tool(tool)  # Uses "input_schema"
openai_tool = to_openai_tool(tool)        # Uses "parameters"
```

### BaseProvider Interface
```python
from claw_cron.providers import BaseProvider, ProviderResult

class AnthropicProvider(BaseProvider):
    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[ToolDefinition],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        # Implementation in Plan 02
        ...
```

## Requirements Addressed

| Requirement | Description | Status |
|-------------|-------------|--------|
| **PROV-02** | Implement BaseProvider abstract base class with chat_with_tools() | ✅ Complete |
| **PROV-05** | Add AIConfig configuration class | ✅ Complete |
| **PROV-06** | Support environment variables (CLAW_CRON_API_KEY, CLAW_CRON_MODEL, CLAW_CRON_PROVIDER) | ✅ Complete |
| **TOOL-01** | Define neutral format ToolDefinition dataclass | ✅ Complete |
| **TOOL-02** | Define ToolCall dataclass | ✅ Complete |
| **TOOL-03** | Implement Tool format converters | ✅ Complete |

## Verification Results

All success criteria passed:

- ✓ `openai` and `pydantic-settings` dependencies added
- ✓ `AIConfig` loads from environment variables with `CLAW_CRON_` prefix
- ✓ `ToolDefinition` and `ToolCall` dataclasses defined
- ✓ `to_anthropic_tool()` and `to_openai_tool()` converters work correctly
- ✓ `BaseProvider` abstract class defines `chat_with_tools()` interface
- ✓ `ProviderResult` dataclass standardizes response format
- ✓ All exports available from `claw_cron.providers` module
- ✓ Existing `config.py` functions unchanged (backward compatible)

## Deviations from Plan

None — plan executed exactly as written.

## Next Steps

**Plan 02** will implement:

1. **PROV-01**: Refactor `agent.py` to use Provider pattern
2. **PROV-03**: Implement `AnthropicProvider` with Tool Use support
3. **PROV-04**: Implement `OpenAIProvider` with Tool Use support
4. **PROV-07**: Provider factory function (`get_provider()`)
5. **TOOL-04**: Ensure `create_task` tool works with both providers

## Technical Notes

### Environment Variable Mapping

| Variable | Maps To | Example |
|----------|---------|---------|
| `CLAW_CRON_PROVIDER` | `AIConfig.provider` | `claude`, `openai` |
| `CLAW_CRON_API_KEY` | `AIConfig.api_key` | `sk-ant-...`, `sk-...` |
| `CLAW_CRON_MODEL` | `AIConfig.model` | `claude-3-5-sonnet-20241022` |
| `CLAW_CRON_BASE_URL` | `AIConfig.base_url` | `http://localhost:11434/v1` |

### Exception Hierarchy

```
ProviderError (base)
├── ProviderAuthError — Authentication failures
├── ProviderRateLimitError — Rate limit exceeded (includes retry_after)
├── ProviderModelNotFoundError — Model not available
└── ProviderResponseError — Malformed/unexpected response
```

### Tool Conversion Differences

| Provider | Key Name | Structure |
|----------|----------|-----------|
| **Anthropic** | `input_schema` | `{"name": str, "description": str, "input_schema": dict}` |
| **OpenAI** | `parameters` | `{"type": "function", "function": {"name": str, "description": str, "parameters": dict}}` |
