# Architecture Research: Command Task Context Mechanism

**Domain:** CLI cron task manager — bidirectional context for command-type tasks
**Researched:** 2025-07-11
**Confidence:** HIGH (based on direct codebase analysis, no speculation)

## Current Architecture (v2.4)

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer (cli.py)                       │
│  add / list / run / start / delete / channel / config ...       │
├─────────────────────────────────────────────────────────────────┤
│                     Scheduler (scheduler.py)                     │
│  Per-minute loop → cron_matches() → Thread(run_task_with_notify)│
├──────────────────┬──────────────────────┬───────────────────────┤
│   Executor       │    Notifier          │    Storage            │
│ (executor.py)    │  (notifier.py)       │  (storage.py)        │
│                  │                      │                       │
│ execute_task()   │  NotifyConfig        │  Task dataclass       │
│   subprocess.run │  Notifier.notify()   │  load_tasks()         │
│   → (code, out)  │  render_message()    │  save_tasks()         │
│                  │                      │  update_task()        │
├──────────────────┴──────────────────────┴───────────────────────┤
│                    Channels (channels/)                          │
│  IMessageChannel / QQBotChannel / EmailChannel / FeishuChannel  │
├─────────────────────────────────────────────────────────────────┤
│              YAML Storage (~/.config/claw-cron/)                 │
│  tasks.yaml (task configs)  │  config.yaml (channel + AI cfg)  │
└─────────────────────────────────────────────────────────────────┘
```

### Current Data Flow (command type)

```
scheduler.py: cron_matches()
    → threading.Thread(run_task_with_notify, task)
        → executor.py: execute_task(task)
            → subprocess.run(task.script, shell=True, capture_output=True, text=True)
            → return (exit_code, stdout+stderr)
        → executor.py: execute_task_with_notify(task)
            → exit_code, output = execute_task(task)
            → if task.notify: Notifier.notify_task_result(task, exit_code, output)
            → return exit_code
```

### Current Task Dataclass

```python
# storage.py — line 22
@dataclass
class Task:
    name: str
    cron: str
    type: str                              # "command" | "agent" | "reminder"
    script: str | None = None              # Shell command (command type)
    prompt: str | None = None              # AI prompt (agent type)
    client: str | None = None              # AI client (agent type)
    client_cmd: str | None = None          # Command template override
    enabled: bool = True
    notify: NotifyConfig | None = None     # channel + recipients
    message: str | None = None             # Reminder message
```

### Current NotifyConfig

```python
# notifier.py — line 43
@dataclass
class NotifyConfig:
    channel: str                           # "imessage", "qqbot", etc.
    recipients: list[str] = field(default_factory=list)
```

### Key Integration Points

| Point | File | Line(s) | Current Behavior |
|-------|------|---------|------------------|
| subprocess invocation | `executor.py` | L80 | `subprocess.run(cmd, shell=True, capture_output=True, text=True)` — no `env` parameter |
| Output handling | `executor.py` | L83-87 | Concatenates stdout+stderr into single string |
| Task persistence | `storage.py` | L91-92 | `yaml.dump({"tasks": [asdict(t) for t in tasks]})` — flat serialize |
| Notify trigger | `executor.py` | L108 | Always notifies if `task.notify` is set — no conditional logic |
| NotifyConfig parse | `notifier.py` | L65-83 | `from_dict()` reads only `channel` and `recipients` |
| Template rendering | `notifier.py` | L86-109 | `render_message()` only supports `{{ date }}` and `{{ time }}` |
| Scheduler loop | `scheduler.py` | L97-113 | Loads tasks fresh each minute, no state carried between loops |

---

## Proposed Architecture (v3.0 Context Mechanism)

### New System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer (cli.py)                       │
├─────────────────────────────────────────────────────────────────┤
│                     Scheduler (scheduler.py)                     │
│  Per-minute loop → cron_matches() → Thread(run_task_with_notify)│
├──────────┬──────────┬──────────────┬────────────┬───────────────┤
│ Executor │ Notifier │  Context     │  Storage   │  Context      │
│(executor)│(notifier)│  Injector    │ (storage)  │  Store        │
│          │          │ (NEW)        │ (MODIFIED) │  (NEW)        │
├──────────┴──────────┴──────────────┴────────────┴───────────────┤
│                    Channels (channels/)                          │
├─────────────────────────────────────────────────────────────────┤
│              YAML Storage (~/.config/claw-cron/)                 │
│  tasks.yaml  │  config.yaml  │  contexts/ (NEW)                 │
└─────────────────────────────────────────────────────────────────┘
```

### New Data Flow (command type with context)

```
1. LOAD CONTEXT
   context_store.load(task.name)
       → dict of persisted context from previous run
       → {} if no previous context

2. INJECT CONTEXT
   context_injector.build_env(task, context)
       → env dict for subprocess.run(env=...)
       → Includes CLAW_CONTEXT_* env vars + template var resolution
   context_injector.render_script(task, context)
       → Replace {{ var }} placeholders in task.script
   context_injector.write_context_file(task, context)
       → Write JSON to ~/.config/claw-cron/contexts/{name}.json

3. EXECUTE
   subprocess.run(rendered_script, shell=True, env=env, capture_output=True, text=True)
       → (exit_code, stdout, stderr)

4. PARSE OUTPUT
   context_parser.parse(stdout)
       → Try JSON parse on stdout lines
       → If valid JSON: extract {"context": {...}, "output": "..."}
       → If not JSON: context=None, output=raw stdout
       → Always preserve stderr in logs

5. PERSIST CONTEXT
   if context_parser found JSON context:
       context_store.save(task.name, new_context)
       → Merge with existing context? Or replace? → REPLACE (simpler, predictable)

6. EVALUATE WHEN
   if task.notify and task.notify.when:
       should_notify = evaluate_when(task.notify.when, context)
       → Simple expressions: "status == changed", "count != 0"
   else:
       should_notify = True  (default: always notify)

7. NOTIFY
   if should_notify:
       Notifier.notify_task_result(task, exit_code, output)
   else:
       logger.info(f"Notification suppressed for '{task.name}': when condition not met")
```

---

## Component Design

### 1. NEW: `context.py` — Context Injection & Parsing

**File:** `src/claw_cron/context.py`
**Purpose:** Three injection paths + stdout JSON parsing

```python
"""Context injection and parsing for command-type tasks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from claw_cron.storage import Task

CONTEXT_DIR = Path.home() / ".config" / "claw-cron" / "contexts"


def load_context(task_name: str) -> dict[str, Any]:
    """Load persisted context for a task from contexts/{name}.json."""
    path = CONTEXT_DIR / f"{task_name}.json"
    if not path.exists():
        return {}
    with path.open() as f:
        return json.load(f)


def save_context(task_name: str, context: dict[str, Any]) -> None:
    """Persist context to contexts/{name}.json."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    path = CONTEXT_DIR / f"{task_name}.json"
    with path.open("w") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)


def build_env(task: Task, context: dict[str, Any]) -> dict[str, str]:
    """Build environment variables dict for subprocess.run().

    Injects context as CLAW_CONTEXT_{KEY}=value env vars.
    Merges with current process environment (inherit + override).
    """
    env = os.environ.copy()
    for key, value in context.items():
        env_key = f"CLAW_CONTEXT_{key.upper()}"
        env[env_key] = str(value)
    return env


def render_script(task: Task, context: dict[str, Any]) -> str:
    """Replace {{ var }} placeholders in task.script with context values.

    Also supports {{ date }} and {{ time }} from render_message().
    """
    from claw_cron.notifier import render_message
    script = task.script or ""
    # First: render date/time variables
    script = render_message(script)
    # Then: render context variables
    for key, value in context.items():
        script = script.replace(f"{{{{ {key} }}}}", str(value))
    return script


def write_context_file(task: Task, context: dict[str, Any]) -> Path:
    """Write context as JSON file for scripts that prefer file-based input.

    Writes to ~/.config/claw-cron/contexts/{name}_input.json
    Returns the path so it can be injected as CLAW_CONTEXT_FILE env var.
    """
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    path = CONTEXT_DIR / f"{task.name}_input.json"
    with path.open("w") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)
    return path


def parse_stdout(stdout: str) -> tuple[dict[str, Any] | None, str]:
    """Parse JSON context from stdout.

    Strategy:
      1. If entire stdout is valid JSON → use it as context, output = json.dumps(parsed)
      2. If last non-empty line is valid JSON → context from that line, output = everything before
      3. If no JSON found → context=None, output=raw stdout

    Returns:
        (context_dict_or_None, display_output)
    """
    if not stdout or not stdout.strip():
        return None, stdout

    # Strategy 1: entire stdout is JSON
    try:
        parsed = json.loads(stdout.strip())
        if isinstance(parsed, dict):
            # Check if it has a "context" key wrapping
            if "context" in parsed and isinstance(parsed["context"], dict):
                output = parsed.get("output", json.dumps(parsed["context"], ensure_ascii=False))
                return parsed["context"], output
            # The entire dict IS the context
            return parsed, json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    # Strategy 2: last line is JSON
    lines = stdout.strip().splitlines()
    if len(lines) > 1:
        try:
            parsed = json.loads(lines[-1].strip())
            if isinstance(parsed, dict):
                output = "\n".join(lines[:-1])
                if "context" in parsed and isinstance(parsed["context"], dict):
                    return parsed["context"], output or parsed.get("output", "")
                return parsed, output
        except json.JSONDecodeError:
            pass

    # Strategy 3: no JSON
    return None, stdout
```

**Key Design Decisions:**
- `build_env()` inherits current `os.environ` and adds `CLAW_CONTEXT_*` overrides — scripts can use all normal env vars plus injected ones
- `render_script()` reuses existing `render_message()` for date/time, then adds context variable replacement
- `parse_stdout()` uses three strategies with graceful fallback — scripts that don't output JSON work fine, scripts that do get context extraction
- Context files written to separate `contexts/` directory, not mixed into `tasks.yaml`

### 2. NEW: `when_eval.py` — Conditional Notification Evaluation

**File:** `src/claw_cron/when_eval.py`
**Purpose:** Evaluate simple `when` expressions against context

```python
"""Simple when-condition evaluator for conditional notifications."""

from __future__ import annotations

import re
from typing import Any


def evaluate_when(when_expr: str, context: dict[str, Any]) -> bool:
    """Evaluate a simple when expression against context.

    Supported formats:
        "key == value"   → True if context[key] equals value
        "key != value"   → True if context[key] does not equal value

    Rules:
        - Key must exist in context for == to be True (missing key → False)
        - Key must NOT exist in context for != to be True (missing key → True for !=)
        - Values are compared as strings (context values are str()'d)
        - Whitespace around operator and values is trimmed

    Args:
        when_expr: Simple expression like "status == changed"
        context: Context dict from task execution output

    Returns:
        True if condition is met, False otherwise.
    """
    # Match: key op value
    match = re.match(r"^\s*(\w+)\s*(==|!=)\s*(.+?)\s*$", when_expr)
    if not match:
        # Invalid expression — default to True (don't suppress notifications on bad syntax)
        return True

    key, op, value = match.groups()

    if op == "==":
        if key not in context:
            return False
        return str(context[key]) == value
    elif op == "!=":
        if key not in context:
            return True  # Key missing means it's definitely != value
        return str(context[key]) != value

    return True  # Unknown operator — don't suppress
```

**Key Design Decisions:**
- Missing key + `==` → `False` (can't equal something that doesn't exist)
- Missing key + `!=` → `True` (absence is inequality)
- Invalid expression → `True` (fail-open: don't suppress notifications on bad syntax, log a warning instead)
- String comparison only — keeps it simple, matches PROJECT.md constraint of `==` / `!=` only

### 3. MODIFIED: `storage.py` — Task Dataclass Changes

**Changes to Task dataclass:**

```python
@dataclass
class Task:
    name: str
    cron: str
    type: str
    script: str | None = None
    prompt: str | None = None
    client: str | None = None
    client_cmd: str | None = None
    enabled: bool = field(default=True)
    notify: NotifyConfig | None = None
    message: str | None = None
    # NEW: context injection configuration
    context_inject: str | None = None  # "env" | "template" | "file" | "all" (default: None = no injection)
```

**Why `context_inject` field instead of a new dataclass:**
- Only one new field — a nested dataclass would be over-engineering for v3.0
- `None` means "no context injection" — backward compatible with existing tasks
- String enum: `"env"`, `"template"`, `"file"`, `"all"` — explicit and self-documenting
- Can evolve to a `ContextConfig` dataclass in future if more options are needed

**YAML serialization impact:**
- `asdict(task)` already handles `None` fields → they serialize as `null` in YAML
- `_task_from_dict()` already handles `Task(**raw)` → new field with default `None` is backward compatible
- No migration needed for existing `tasks.yaml` files

**YAML example (new task with context):**

```yaml
- name: disk-check
  cron: "0 8 * * *"
  type: command
  script: "check-disk.sh"
  context_inject: env
  notify:
    channel: qqbot
    recipients:
      - c2c:ABC123
    when: "status == warning"
```

### 4. MODIFIED: `notifier.py` — NotifyConfig Changes

**Changes to NotifyConfig dataclass:**

```python
@dataclass
class NotifyConfig:
    channel: str
    recipients: list[str] = field(default_factory=list)
    when: str | None = None  # NEW: conditional expression, e.g. "status == warning"
```

**Changes to `from_dict()`:**

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> NotifyConfig:
    return cls(
        channel=data.get("channel", ""),
        recipients=data.get("recipients", []),
        when=data.get("when"),  # NEW
    )
```

**Impact on `asdict()` serialization:**
- `asdict()` will include `when: null` for tasks without it — harmless
- Backward compatible: old YAML files without `when` key work fine

### 5. MODIFIED: `executor.py` — Integration of Context Flow

**Changes to `execute_task()`:**

```python
def execute_task(task: Task) -> tuple[int, str, dict[str, Any] | None]:
    """Execute a task and return (exit_code, output, context).

    CHANGED: Return type now includes optional context dict.
    """
    log_path = _task_log_path(task.name)
    ts_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if task.type == "reminder":
        # ... unchanged, return (0, message, None)
        message = render_message(task.message or "")
        # ... log ...
        return 0, message, None

    if task.type == "command":
        # NEW: Context injection
        from claw_cron.context import (
            build_env, load_context, parse_stdout,
            render_script, write_context_file,
        )

        context = load_context(task.name) if task.context_inject else {}
        cmd = render_script(task, context) if task.context_inject in ("template", "all") else (task.script or "")

        env = None  # Default: inherit os.environ without override
        if task.context_inject in ("env", "all"):
            env = build_env(task, context)
            # Also set CLAW_CONTEXT_FILE if file injection requested
        if task.context_inject in ("file", "all"):
            ctx_path = write_context_file(task, context)
            if env is None:
                env = os.environ.copy()
            env["CLAW_CONTEXT_FILE"] = str(ctx_path)
    elif task.type == "agent":
        # ... unchanged agent logic ...
        cmd = ...
        env = None
    else:
        raise ValueError(f"Unknown task type: {task.type!r}")

    _write_log(log_path, f"[{ts_start}] START: {task.name}\n")

    # CHANGED: Pass env parameter
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)

    ts_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # NEW: Parse stdout for context
    new_context = None
    if task.type == "command" and task.context_inject:
        new_context, display_output = parse_stdout(result.stdout)
        output = display_output
        if result.stderr:
            output += result.stderr
    else:
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += result.stderr

    # NEW: Persist context
    if new_context is not None:
        from claw_cron.context import save_context
        save_context(task.name, new_context)

    _write_log(log_path, f"{output}[{ts_end}] END (exit_code={result.returncode})\n\n")

    return result.returncode, output, new_context
```

**Changes to `execute_task_with_notify()`:**

```python
async def execute_task_with_notify(task: Task) -> int:
    exit_code, output, context = execute_task(task)  # CHANGED: unpack 3 values

    if task.notify:
        # NEW: Evaluate when condition
        should_notify = True
        if task.notify.when and context is not None:
            from claw_cron.when_eval import evaluate_when
            should_notify = evaluate_when(task.notify.when, context)
            if not should_notify:
                logger.info(
                    f"Notification suppressed for '{task.name}': "
                    f"when '{task.notify.when}' not met"
                )

        if should_notify:
            try:
                notifier = Notifier()
                results = await notifier.notify_task_result(task, exit_code, output)
                # ... existing error handling ...
            except Exception as e:
                logger.error(...)

    return exit_code
```

**Breaking change:** `execute_task()` return type changes from `tuple[int, str]` to `tuple[int, str, dict[str, Any] | None]`.

**Callers affected:**
- `execute_task_with_notify()` — updated (shown above)
- Any CLI commands that call `execute_task()` directly — must handle 3-tuple return
- **Search needed for all callers** before implementation

### 6. MODIFIED: `notifier.py` — Template Enhancement (Optional)

**Enhancement to `render_message()`:** Add `{{ task_name }}` and context variable support.

```python
def render_message(template: str, context: dict[str, Any] | None = None) -> str:
    now = datetime.now()
    result = (
        template.replace("{{ date }}", now.strftime("%Y-%m-%d"))
        .replace("{{ time }}", now.strftime("%H:%M:%S"))
    )
    # Context variables
    if context:
        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))
    return result
```

---

## File Change Summary

| File | Action | Scope | Description |
|------|--------|-------|-------------|
| `src/claw_cron/context.py` | **NEW** | Full file | Context loading, injection (env/template/file), stdout parsing, persistence |
| `src/claw_cron/when_eval.py` | **NEW** | Full file | Simple `==`/`!=` expression evaluator |
| `src/claw_cron/storage.py` | **MODIFY** | Task dataclass | Add `context_inject: str \| None = None` field |
| `src/claw_cron/notifier.py` | **MODIFY** | NotifyConfig dataclass | Add `when: str \| None = None` field + `from_dict()` update |
| `src/claw_cron/executor.py` | **MODIFY** | `execute_task()` + `execute_task_with_notify()` | Context injection, JSON parsing, when evaluation |
| `src/claw_cron/notifier.py` | **MODIFY** | `render_message()` | Add context variable support (optional) |

## Build Order (Dependency-Aware)

```
Phase 1: Data Layer (no dependencies)
  ├── context.py: load_context(), save_context() — pure YAML/JSON I/O
  ├── when_eval.py: evaluate_when() — pure function, no I/O
  └── storage.py: Add context_inject field — backward compatible

Phase 2: Injection Layer (depends on Phase 1)
  ├── context.py: build_env(), render_script(), write_context_file()
  └── notifier.py: Add when field to NotifyConfig + from_dict()

Phase 3: Integration Layer (depends on Phase 1 + 2)
  ├── executor.py: Modify execute_task() — inject context, parse stdout, persist
  ├── executor.py: Modify execute_task_with_notify() — when evaluation
  └── notifier.py: Enhance render_message() with context vars (optional)

Phase 4: CLI Layer (depends on Phase 3)
  └── cmd/: Add context_inject and when options to `add`/`update` commands
```

**Rationale:** Phase 1 can be fully tested in isolation. Phase 2 depends on Phase 1 data structures. Phase 3 wires everything together. Phase 4 exposes to users.

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `context.py` | Load/save context, inject into subprocess, parse stdout | `storage.Task` (reads task.name, context_inject, script), `executor` (called by) |
| `when_eval.py` | Evaluate when expressions | `notifier.NotifyConfig` (reads when field), `executor` (called by) |
| `storage.Task` | Task configuration including context_inject | All components (read task config) |
| `notifier.NotifyConfig` | Notification config including when | `executor` (reads when), `storage` (serialized in tasks.yaml) |
| `executor.execute_task()` | Orchestrate context→execute→parse→persist | `context`, `when_eval`, `storage`, `notifier` |

---

## Data Storage Design

### Context Files: `~/.config/claw-cron/contexts/`

```
contexts/
├── disk-check.json          # Persisted context from last run
├── disk-check_input.json    # Temporary input file for current run (overwritten each time)
├── price-monitor.json
└── ...
```

**Why separate files instead of tasks.yaml?**
1. **Separation of concerns** — task config is static, context is dynamic runtime state
2. **Size** — context could grow large; keeping it out of tasks.yaml avoids cluttering the user-editable config
3. **Atomicity** — writing context doesn't require rewriting the entire tasks.yaml
4. **Cleanup** — easy to `rm contexts/*.json` without affecting task definitions
5. **Consistency with existing pattern** — logs already use separate `logs/` directory

### Context JSON Format

```json
{
  "status": "warning",
  "disk_usage": 85,
  "last_check": "2025-07-11T08:00:00"
}
```

Simple flat dict. No nesting — keeps `when` evaluation simple (no dot-notation needed).

---

## Architectural Patterns

### Pattern 1: Fail-Open for Notification

**What:** When context parsing fails or when expression is invalid, default to sending the notification.
**When:** Any conditional notification logic.
**Trade-offs:** May send unwanted notifications on misconfiguration vs. missing important notifications. Fail-open is safer — users can see the error and fix it.

### Pattern 2: Graceful Degradation for stdout Parsing

**What:** `parse_stdout()` uses three strategies with fallback. Non-JSON output works fine.
**When:** Scripts that don't participate in context mechanism.
**Trade-offs:** Slightly more complex parsing logic vs. requiring all scripts to output JSON. Graceful degradation means existing scripts work unchanged.

### Pattern 3: Explicit Opt-In via context_inject Field

**What:** Context injection only happens when `task.context_inject` is set. Default `None` = no injection.
**When:** All task types. Agent and reminder types ignore context entirely.
**Trade-offs:** Requires explicit configuration vs. auto-injecting for all command tasks. Opt-in is safer — no surprise env vars in scripts that don't expect them.

### Pattern 4: Context as Flat Dict

**What:** Context is always a flat `dict[str, Any]`. No nested objects.
**When:** All context storage and evaluation.
**Trade-offs:** Limits expressiveness (no nested data) vs. keeps when-eval and env-var injection trivially simple. Aligns with PROJECT.md constraint of simple `==`/`!=` expressions.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Context in tasks.yaml

**What people might do:** Add a `context` field to the Task dataclass and persist it alongside task config.
**Why it's wrong:** tasks.yaml is user-editable config. Runtime state mixed with config creates confusing diffs and merge conflicts. Context changes every execution; task config changes rarely.
**Do this instead:** Separate `contexts/{name}.json` files.

### Anti-Pattern 2: Complex Expression Parser

**What people might do:** Support `and`, `or`, `>`, `<`, function calls in when expressions.
**Why it's wrong:** Scope creep. PROJECT.md explicitly scopes to `==`/`!=`. Complex expressions need a real parser, error handling, testing matrix. Not justified for v3.0.
**Do this instead:** Simple regex-based parser in `when_eval.py`. Evolve later if needed.

### Anti-Pattern 3: Modifying subprocess.run Return Handling

**What people might do:** Change `subprocess.run()` to use `stdout=subprocess.PIPE` separately and change how output is concatenated.
**Why it's wrong:** Existing logging, error handling, and notification all depend on the current `(exit_code, output)` contract. Changing subprocess output handling risks breaking agent/reminder types.
**Do this instead:** Add parsing on top of existing `result.stdout` — don't change how subprocess is called, only how its output is interpreted.

### Anti-Pattern 4: Context Injection Without env Inheritance

**What people might do:** Build env dict from scratch with only CLAW_CONTEXT_* vars.
**Why it's wrong:** Scripts often depend on PATH, HOME, etc. Stripping the environment breaks most real-world scripts.
**Do this instead:** `env = os.environ.copy()` then add CLAW_CONTEXT_* overrides.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-50 tasks | Current design is fine. Context files are small. YAML storage works. |
| 50-500 tasks | Context directory could get cluttered. Consider cleanup of stale context files. YAML still fine for config. |
| 500+ tasks | May need SQLite for context storage. YAML starts to slow on load_tasks(). But this is a single-user local CLI — unlikely to hit this. |

### Scaling Priorities

1. **First bottleneck:** Context file I/O on every execution — for most tasks (1-50), this is negligible. No optimization needed.
2. **Second bottleneck:** YAML full-rewrite on every context update — mitigated by using separate context files, not tasks.yaml.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| executor ↔ context | Direct function calls | executor calls context.load/save/build_env/parse. No events, no queue. |
| executor ↔ when_eval | Direct function call | executor calls evaluate_when() with notify.when and context dict |
| storage ↔ context | context reads task.name, task.context_inject | No back-reference. Context doesn't import storage. |
| notifier ↔ when_eval | None | when evaluation happens in executor, before notifier is called |
| scheduler ↔ context | None | Scheduler doesn't need to know about context. Transparent. |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| User scripts | Env vars + context file + template vars | Scripts opt in by reading CLAW_CONTEXT_* or CLAW_CONTEXT_FILE or using {{ var }} |
| subprocess.run | `env` parameter | Standard Python subprocess interface |

---

## Sources

- Direct codebase analysis of `storage.py`, `executor.py`, `scheduler.py`, `notifier.py`, `config.py`, `channels/__init__.py`
- PROJECT.md v3.0 milestone requirements
- Python subprocess.run documentation for `env` parameter behavior

---
*Architecture research for: claw-cron v3.0 context mechanism*
*Researched: 2025-07-11*
