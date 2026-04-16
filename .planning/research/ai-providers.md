# Research: AI Provider Pattern Refactoring

**Project:** claw-cron
**Reference:** agent-summary
**Researched:** 2025-01-13
**Mode:** Ecosystem (with comparison elements)

## Executive Summary

This research analyzes how to refactor `claw-cron/agent.py` from a single-provider implementation (Anthropic only) to a Provider Pattern that supports multiple AI providers (Anthropic, OpenAI, etc.). The reference project `agent-summary` demonstrates a clean, well-structured provider abstraction that can be adapted for claw-cron's needs.

Key findings:
1. **Current implementation is tightly coupled** to Anthropic's SDK, with hardcoded model name and direct tool use integration
2. **Provider pattern from agent-summary is well-designed** but lacks Tool Use support, which is critical for claw-cron
3. **Configuration needs to be extended** to support provider-specific settings (api_key, model, base_url)
4. **Tool Use is provider-specific** - each provider has different tool/function calling APIs

## 1. Current agent.py Structure and Functionality

### File Location
`/Users/wxnacy/Projects/claw-cron/src/claw_cron/agent.py`

### Structure Analysis

```
agent.py (143 lines)
├── Constants
│   ├── _MODEL = "claude-3-5-haiku-20241022"
│   ├── _CREATE_TASK_TOOL (ToolParam schema)
│   └── _SYSTEM_PROMPT (conversation guidance)
├── Function: run_ai_add()
│   ├── Creates Anthropic client (hardcoded, no config)
│   ├── Builds initial message from partial CLI args
│   └── Conversation loop:
│       ├── Calls messages.create() with tools
│       ├── Handles tool_use stop_reason → creates Task
│       └── Handles text response → continues conversation
```

### Key Characteristics

| Aspect | Current Implementation | Issue |
|--------|------------------------|-------|
| **Provider** | Anthropic only | No flexibility to switch providers |
| **Model** | Hardcoded `claude-3-5-haiku-20241022` | Should be configurable |
| **API Key** | Uses `anthropic.Anthropic()` auto-detection from env | No explicit config management |
| **Tool Use** | Native Anthropic ToolParam schema | Provider-specific, needs abstraction |
| **Conversation** | Single function with while loop | Could be extracted to a session class |

### Tool Definition (Anthropic-specific)

```python
_CREATE_TASK_TOOL: anthropic.types.ToolParam = {
    "name": "create_task",
    "description": "Create a scheduled task with the parsed configuration from the conversation",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique task name (snake_case)"},
            "cron": {"type": "string", "description": "Standard 5-field cron expression..."},
            "type": {"type": "string", "enum": ["command", "agent"], ...},
            "script": {"type": "string", ...},
            "prompt": {"type": "string", ...},
            "client": {"type": "string", "enum": ["kiro-cli", "codebuddy", "opencode"], ...},
        },
        "required": ["name", "cron", "type"],
    },
}
```

### Usage Context

The `run_ai_add()` function is called from `cmd/add.py` when required arguments are missing:

```python
# cmd/add.py line 52-54
from claw_cron.agent import run_ai_add
run_ai_add(name=name, cron=cron, task_type=task_type, ...)
```

---

## 2. Reference: agent-summary Provider Pattern

### Directory Structure

```
providers/
├── __init__.py      # Factory function get_provider(), exports
├── base.py          # Abstract BaseProvider class
├── anthropic.py     # AnthropicProvider implementation
├── openai.py        # OpenAIProvider implementation
├── exceptions.py    # Custom exception hierarchy
└── result.py        # SummarizeResult, TokenUsage dataclasses
```

### BaseProvider Abstract Class

```python
class BaseProvider(ABC):
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    def summarize(self, content: str, system_prompt: str) -> SummarizeResult:
        ...
```

### Factory Pattern

```python
def get_provider(
    provider_name: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseProvider:
    providers = {
        "openai": OpenAIProvider,
        "claude": AnthropicProvider,
    }
    return providers[provider_name](api_key=api_key, model=model, base_url=base_url)
```

### Exception Hierarchy

```
ProviderError (base)
├── ProviderAuthError
├── ProviderRateLimitError
└── ProviderModelNotFoundError
```

### Configuration Integration (from agent-summary)

The provider is instantiated via an `AIClient` wrapper that reads from a `Config` class:

```python
class AIClient:
    def __init__(self, config: Config) -> None:
        self.provider = get_provider(
            provider_name=config.ai.provider,  # "claude" or "openai"
            api_key=config.ai.api_key,
            model=config.ai.model,
            base_url=config.ai.base_url,
        )
```

### Config Structure (agent-summary)

```python
class AIConfig(BaseSettings):
    provider: str = "claude"  # "claude", "openai", "ollama"
    model: str | None = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_retries: int = 3
    retry_delay: float = 1.0

    class Config:
        env_prefix = "ARCHIVE_SUMMARY_"
```

---

## 3. Proposed File Structure for claw-cron

### New Directory Structure

```
src/claw_cron/
├── providers/
│   ├── __init__.py      # get_provider(), exports
│   ├── base.py          # BaseProvider abstract class
│   ├── anthropic.py     # AnthropicProvider
│   ├── openai.py        # OpenAIProvider (future)
│   ├── exceptions.py    # ProviderError hierarchy
│   └── result.py        # ProviderResult (or reuse for tokens)
├── agent.py             # Refactored to use providers
├── config.py            # Extended with AIConfig
└── ...
```

### Files to Create

| File | Purpose | Lines (Est.) |
|------|---------|--------------|
| `providers/__init__.py` | Factory function, exports | ~60 |
| `providers/base.py` | Abstract base class | ~50 |
| `providers/anthropic.py` | Anthropic implementation with Tool Use | ~120 |
| `providers/openai.py` | OpenAI implementation (future) | ~100 |
| `providers/exceptions.py` | Exception hierarchy | ~35 |
| `providers/result.py` | Result dataclasses | ~40 |

### Files to Modify

| File | Changes |
|------|---------|
| `config.py` | Add `AIConfig` class, update load logic |
| `agent.py` | Refactor to use Provider pattern |
| `pyproject.toml` | Add `openai` dependency (optional for now) |

---

## 4. Configuration Management

### Recommended Config Structure

Extend the existing `config.py` to include AI settings:

```python
# config.py (proposed addition)

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional

class AIConfig(BaseSettings):
    """AI provider configuration."""
    
    provider: str = Field(
        default="claude", 
        description="AI provider: claude, openai"
    )
    model: Optional[str] = Field(
        default=None,  # Will use provider-specific defaults
        description="Model name (e.g., claude-3-5-haiku-20241022, gpt-4o)"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="API key (from env var if not set)"
    )
    base_url: Optional[str] = Field(
        default=None, 
        description="Custom API base URL (for proxies or local models)"
    )
    
    class Config:
        env_prefix = "CLAW_CRON_"  # CLAW_CRON_API_KEY, CLAW_CRON_MODEL, etc.


class Config(BaseSettings):
    """Main configuration."""
    
    ai: AIConfig = Field(default_factory=AIConfig)
    clients: dict[str, str] = Field(default_factory=dict)  # Existing client templates
    
    @classmethod
    def load(cls) -> "Config":
        """Load from config.yaml with env var overrides."""
        # Similar to agent-summary's Config.load()
        ...
```

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `CLAW_CRON_API_KEY` | API key for the provider | `sk-ant-...` or `sk-...` |
| `CLAW_CRON_MODEL` | Override model name | `claude-3-5-sonnet-20241022` |
| `CLAW_CRON_BASE_URL` | Custom API endpoint | `http://localhost:11434/v1` |
| `CLAW_CRON_PROVIDER` | Provider selection | `claude` or `openai` |
| `ANTHROPIC_API_KEY` | Fallback (Anthropic SDK auto-detects) | `sk-ant-...` |
| `OPENAI_API_KEY` | Fallback (OpenAI SDK auto-detects) | `sk-...` |

### Config File Example (~/.config/claw-cron/config.yaml)

```yaml
ai:
  provider: claude
  model: claude-3-5-haiku-20241022
  # api_key: sk-ant-...  # Prefer env var

clients:
  kiro-cli: 'kiro-cli -a --no-interactive "{prompt}"'
  codebuddy: 'codebuddy -y -p "{prompt}"'
  opencode: 'opencode run --dangerously-skip-permissions "{prompt}"'
```

---

## 5. Tool Use Support (Critical Challenge)

### The Problem

Tool Use (Function Calling) is **not standardized** across providers:

| Provider | Tool Definition | Response Handling |
|----------|-----------------|-------------------|
| **Anthropic** | `tools: [ToolParam]` with `input_schema` | `stop_reason == "tool_use"` |
| **OpenAI** | `tools: [dict]` with `function.parameters` | `finish_reason == "tool_calls"` |
| **Ollama** | Similar to OpenAI | Varies by model |

### Anthropic Tool Use (Current)

```python
# Current implementation
response = api_client.messages.create(
    model=_MODEL,
    max_tokens=1024,
    system=_SYSTEM_PROMPT,
    tools=[_CREATE_TASK_TOOL],  # ToolParam schema
    messages=messages,
)

if response.stop_reason == "tool_use":
    tool_block = next(b for b in response.content if b.type == "tool_use")
    task_input = tool_block.input
```

### OpenAI Tool Use (Different)

```python
# OpenAI equivalent
response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        *messages
    ],
    tools=[{
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "...",
            "parameters": {  # Note: "parameters" not "input_schema"
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }]
)

if response.choices[0].finish_reason == "tool_calls":
    tool_calls = response.choices[0].message.tool_calls
    task_input = json.loads(tool_calls[0].function.arguments)
```

### Proposed Abstraction

**Option A: Normalize Tool Schema in BaseProvider**

```python
# providers/base.py

@dataclass
class ToolDefinition:
    """Provider-agnostic tool definition."""
    name: str
    description: str
    parameters: dict  # JSON Schema format


@dataclass 
class ToolCall:
    """Provider-agnostic tool call result."""
    name: str
    arguments: dict


class BaseProvider(ABC):
    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[ToolDefinition],
    ) -> ChatResult:
        """Chat with tool support.
        
        Returns ChatResult with:
        - content: str (text response)
        - tool_calls: list[ToolCall] (if any)
        - stop_reason: "end" | "tool_use"
        """
        ...
```

**Option B: Keep Tools in agent.py, Use Provider-specific Conversion**

```python
# agent.py - define tools once in a neutral format

TOOLS = [
    {
        "name": "create_task",
        "description": "Create a scheduled task...",
        "parameters": {
            "type": "object",
            "properties": {...},
            "required": ["name", "cron", "type"]
        }
    }
]

# Provider converts to native format internally
response = provider.chat_with_tools(messages, system_prompt, TOOLS)
```

### Recommendation

**Use Option B** with a `ToolConverter` helper:

```python
# providers/tools.py

def to_anthropic_tool(tool: dict) -> anthropic.types.ToolParam:
    """Convert neutral tool definition to Anthropic format."""
    return {
        "name": tool["name"],
        "description": tool["description"],
        "input_schema": tool["parameters"]  # Rename key
    }


def to_openai_tool(tool: dict) -> dict:
    """Convert neutral tool definition to OpenAI format."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
    }
```

---

## 6. Implementation Plan

### Phase 1: Foundation (Minimum Viable)

1. Create `providers/` directory structure
2. Implement `BaseProvider` with `chat()` method (no tools yet)
3. Implement `AnthropicProvider` (migrate existing non-tool logic)
4. Add `AIConfig` to `config.py`
5. Refactor `agent.py` to use provider (basic chat only)

### Phase 2: Tool Use Support

1. Add `ToolDefinition` and `ToolCall` dataclasses
2. Add `chat_with_tools()` to `BaseProvider`
3. Implement Anthropic tool conversion
4. Refactor `agent.py` conversation loop

### Phase 3: Multi-Provider

1. Add `openai` dependency to `pyproject.toml`
2. Implement `OpenAIProvider` with tool support
3. Add provider auto-detection from model name
4. Add tests for both providers

---

## 7. Key Differences: agent-summary vs claw-cron Needs

| Aspect | agent-summary | claw-cron | Implication |
|--------|--------------|-----------|-------------|
| **Operation** | Single-shot summarize | Multi-turn conversation | Need session/message management |
| **Tool Use** | Not needed | Critical | Need to add to base class |
| **Response Type** | Text only | Text + Tool Calls | Need richer result type |
| **Max Tokens** | Fixed 4096 | Variable (1024 in current) | Make configurable |
| **Streaming** | Not used | Not used | Future consideration |

---

## 8. Dependencies

### Current (claw-cron)
```toml
dependencies = [
    "click",
    "rich",
    "pyyaml",
    "anthropic",
]
```

### Proposed Additions
```toml
dependencies = [
    "click",
    "rich",
    "pyyaml",
    "anthropic",
    "openai",           # Add for OpenAI support
    "pydantic-settings", # For AIConfig
]
```

---

## 9. Open Questions

1. **Default model for each provider?**
   - Claude: `claude-3-5-haiku-20241022` (current)
   - OpenAI: `gpt-4o-mini` (cost-effective) or `gpt-4o`?
   
2. **Should `base_url` be validated?**
   - Useful for local models (Ollama, LM Studio)
   - Could enable "bring your own endpoint"

3. **Conversation persistence?**
   - Current: In-memory only
   - Future: Save/resume sessions?

4. **Error recovery in conversation?**
   - If API call fails mid-conversation, can user retry?
   - Should partial progress be saved?

---

## 10. Files Reference

### Source Files Analyzed

| File | Path |
|------|------|
| claw-cron agent.py | `/Users/wxnacy/Projects/claw-cron/src/claw_cron/agent.py` |
| claw-cron config.py | `/Users/wxnacy/Projects/claw-cron/src/claw_cron/config.py` |
| claw-cron storage.py | `/Users/wxnacy/Projects/claw-cron/src/claw_cron/storage.py` |
| claw-cron cmd/add.py | `/Users/wxnacy/Projects/claw-cron/src/claw_cron/cmd/add.py` |
| agent-summary base.py | `/Users/wxnacy/Projects/agent-summary/src/archive_summary/providers/base.py` |
| agent-summary anthropic.py | `/Users/wxnacy/Projects/agent-summary/src/archive_summary/providers/anthropic.py` |
| agent-summary openai.py | `/Users/wxnacy/Projects/agent-summary/src/archive_summary/providers/openai.py` |
| agent-summary config.py | `/Users/wxnacy/Projects/agent-summary/src/archive_summary/config.py` |
| agent-summary ai_client.py | `/Users/wxnacy/Projects/agent-summary/src/archive_summary/ai_client.py` |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Current agent.py structure | HIGH | Read directly from codebase |
| Provider pattern (agent-summary) | HIGH | Read directly from codebase |
| Tool Use differences | HIGH | Documented in official SDK docs |
| Configuration approach | MEDIUM | Based on agent-summary pattern, needs testing |
| OpenAI implementation details | MEDIUM | From SDK documentation, not tested with tools |
| Proposed file structure | HIGH | Following established patterns |
