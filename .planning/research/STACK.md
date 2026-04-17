# Stack Research

**Domain:** Command Task Context Mechanism (v3.0)
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

The v3.0 command task context mechanism requires **zero new external dependencies**. All capabilities can be built with Python stdlib and the existing stack (PyYAML, Click, Rich). The four new features — environment variable injection, template variable expansion, context file passing, and JSON stdout parsing — map directly to stdlib primitives: `subprocess.run(env=...)`, `str.replace()` (matching existing `{{ var }}` pattern), `tempfile`/`pathlib`, and `json.loads()`. The conditional notification `when` field needs only `==`/`!=` comparison, which is a ~30-line custom parser — not worth adding simpleeval for.

Key design decisions influenced by reference implementations: GitHub Actions' file-based `$GITHUB_OUTPUT` pattern inspires the context file approach (write JSON to a known path via env var), and Airflow XCom's explicit push/pull model informs the stdout JSON protocol (script explicitly outputs structured data, system parses it). Unlike these systems, claw-cron is single-user and single-machine, so we avoid their complexity (no distributed coordination, no serialization backends).

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python stdlib: json** | 3.12+ | Parse JSON from script stdout | Built-in, zero dependencies. `json.loads()` handles the full JSON spec. Scripts write JSON to stdout, system parses it. Matches GitHub Actions `$GITHUB_OUTPUT` file-write pattern but simpler (stdout vs file). |
| **Python stdlib: subprocess** | 3.12+ | Execute scripts with injected env vars | `subprocess.run(env={...})` parameter merges custom env with `os.environ`. Already used in `executor.py` — just needs `env` parameter added. |
| **Python stdlib: pathlib** | 3.12+ | Manage context file paths | `~/.config/claw-cron/context/{task_name}.json` for per-task context files. Already used throughout codebase. |
| **Python stdlib: tempfile** | 3.12+ | Create temporary context input files | `NamedTemporaryFile(suffix=".json", delete=False)` for context files passed to scripts via `CLAW_CRON_CONTEXT_FILE` env var. Auto-cleaned after execution. Alternative: write to persistent context dir directly. |
| **Python stdlib: os** | 3.12+ | Build environment variable dict | `os.environ | custom_env` merges existing env with injected context vars. Python 3.9+ dict merge operator. |
| **PyYAML** | existing | Persist task config with new fields | Extend `Task` dataclass with `context` field. Context state stored in separate JSON files, not in tasks.yaml (separation of config vs state). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **json (stdlib)** | 3.12+ | Persist task context between executions | Write to `~/.config/claw-cron/context/{task_name}.json` after each run. Read before next run for template/env injection. |
| **re (stdlib)** | 3.12+ | Parse `when` conditional expressions | Simple regex to split `field == "value"` or `field != "value"` into (field, operator, value) tuple. No external lib needed for `==`/`!=` only. |
| **datetime (stdlib)** | 3.12+ | Inject date/time template variables | Already used in `render_message()`. Extend to `{{ date }}`, `{{ time }}`, `{{ datetime }}` for script templates. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **jq** | Test script JSON output manually | `your-script.sh | jq .` to verify JSON output format |
| **env** | Verify environment variable injection | `env | grep CLAW_CRON_` inside test scripts |
| **cat** | Inspect context files | `cat ~/.config/claw-cron/context/task_name.json` |

## Installation

```bash
# No new packages needed!
# All v3.0 features use Python stdlib or existing dependencies.

# Existing dependencies used:
# - PyYAML (task config storage)
# - Click (CLI argument additions)
# - Rich (output formatting)

# Dev dependencies for testing:
uv add --dev pytest pytest-asyncio  # Already in dev group
```

## New Feature Stack Details

### Feature 1: Environment Variable Context Injection

**Mechanism:** Construct env dict with `CLAW_CRON_` prefixed variables, pass to `subprocess.run(env=...)`.

**Variables to inject:**

| Env Var | Value | Example |
|---------|-------|---------|
| `CLAW_CRON_TASK_NAME` | Task name | `"backup-check"` |
| `CLAW_CRON_TASK_TYPE` | Task type | `"command"` |
| `CLAW_CRON_CRON` | Cron expression | `"0 8 * * *"` |
| `CLAW_CRON_DATE` | Current date | `"2026-04-17"` |
| `CLAW_CRON_TIME` | Current time | `"08:00:00"` |
| `CLAW_CRON_DATETIME` | Current datetime | `"2026-04-17T08:00:00"` |
| `CLAW_CRON_CONTEXT_FILE` | Path to context JSON file | `"/tmp/claw-cron-ctx-XXXX.json"` |

**Implementation pattern:**

```python
import os
import subprocess

def _build_env(task: Task) -> dict[str, str]:
    """Build environment dict with injected context variables."""
    now = datetime.now()
    custom = {
        "CLAW_CRON_TASK_NAME": task.name,
        "CLAW_CRON_TASK_TYPE": task.type,
        "CLAW_CRON_CRON": task.cron,
        "CLAW_CRON_DATE": now.strftime("%Y-%m-%d"),
        "CLAW_CRON_TIME": now.strftime("%H:%M:%S"),
        "CLAW_CRON_DATETIME": now.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    # Add context file path if previous context exists
    context_file = _context_file_path(task.name)
    if context_file.exists():
        custom["CLAW_CRON_CONTEXT_FILE"] = str(context_file)
    return os.environ | custom

# In execute_task:
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=_build_env(task))
```

**Reference:** GitHub Actions injects `GITHUB_*` env vars into every step. Same pattern, `CLAW_CRON_*` prefix.

---

### Feature 2: Template Variable Context Injection

**Mechanism:** Extend existing `render_message()` pattern to script field. Replace `{{ var }}` placeholders before execution.

**Variables available:**

| Template Var | Resolves To | Example |
|-------------|-------------|---------|
| `{{ date }}` | Current date | `"2026-04-17"` |
| `{{ time }}` | Current time | `"08:00:00"` |
| `{{ datetime }}` | Current datetime | `"2026-04-17T08:00:00"` |
| `{{ context.key }}` | Previous context value | `"3"` (from last run's JSON output) |

**Implementation pattern:**

```python
def _render_script(task: Task, context: dict[str, Any] | None = None) -> str:
    """Render script template with variables."""
    script = task.script or ""
    now = datetime.now()
    script = script.replace("{{ date }}", now.strftime("%Y-%m-%d"))
    script = script.replace("{{ time }}", now.strftime("%H:%M:%S"))
    script = script.replace("{{ datetime }}", now.strftime("%Y-%m-%dT%H:%M:%S"))
    # Inject previous context values
    if context:
        for key, value in context.items():
            script = script.replace(f"{{{{ context.{key} }}}}", str(value))
    return script
```

**Why `str.replace()` over `string.Template`:** Consistency. The existing reminder system uses `{{ var }}` with `str.replace()` (see `notifier.py:render_message`). Using `string.Template` would introduce `$var` syntax inconsistency. Keep `{{ var }}` everywhere.

---

### Feature 3: Context File Injection (System → Script)

**Mechanism:** Write previous execution's context JSON to a temp file, set `CLAW_CRON_CONTEXT_FILE` env var pointing to it.

**Two approaches:**

| Approach | Path | Lifecycle | Trade-off |
|----------|------|-----------|-----------|
| **A: Persistent context dir** | `~/.config/claw-cron/context/{task_name}.json` | Persists between runs, manual cleanup | Script can re-read outside execution; survives restarts |
| **B: Temp file per execution** | `/tmp/claw-cron-ctx-{task_name}-{random}.json` | Created before run, deleted after | Cleaner lifecycle; script can't read stale data between runs |

**Recommendation: Approach A (persistent context dir).**

Why:
1. Script might fail mid-way — temp file cleanup would lose the previous context, making debugging harder
2. Persistent file allows manual inspection (`cat ~/.config/claw-cron/context/backup.json`)
3. Context file IS the state store — it should persist between runs (that's the whole point)
4. If `CLAW_CRON_CONTEXT_FILE` points to the persistent path, scripts can also write to it (though stdout JSON is preferred)

**Implementation pattern:**

```python
CONTEXT_DIR = Path.home() / ".config" / "claw-cron" / "context"

def _context_file_path(task_name: str) -> Path:
    """Return the context file path for a task."""
    return CONTEXT_DIR / f"{task_name}.json"

def _load_context(task_name: str) -> dict[str, Any] | None:
    """Load previous context for a task."""
    path = _context_file_path(task_name)
    if path.exists():
        return json.loads(path.read_text())
    return None

def _save_context(task_name: str, context: dict[str, Any]) -> None:
    """Save context for a task after execution."""
    path = _context_file_path(task_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2))
```

**Reference:** GitHub Actions' `$GITHUB_OUTPUT` writes `key=value` pairs to a file whose path is set via env var. Same pattern: `CLAW_CRON_CONTEXT_FILE` points to `~/.config/claw-cron/context/{task_name}.json`.

---

### Feature 4: JSON stdout Context Feedback (Script → System)

**Mechanism:** After script execution, parse stdout as JSON. If valid JSON, store as task context for next run.

**Protocol:**

```
Script writes JSON to stdout → System captures via subprocess.run(capture_output=True)
→ json.loads(stdout) → If valid, save to context file → Available next run via env var + template var
```

**Parsing strategy (ordered):**

1. **Try full stdout as JSON** — `json.loads(stdout.strip())`. Works for scripts that output ONLY JSON.
2. **Try last line as JSON** — Scripts may output diagnostic text before JSON. Parse only the last non-empty line. This handles `echo "Starting..." && echo '{"status": "ok"}'`.
3. **No valid JSON** — Treat entire stdout as plain text output (existing behavior). No context update.

**Why last-line parsing:** Real-world scripts often mix logging and structured output. GitHub Actions uses `echo "key=value" >> $GITHUB_OUTPUT` (append to file) — but JSON stdout is cleaner for structured data. The "last line is JSON" convention is simple and well-understood.

**Implementation pattern:**

```python
def _parse_context_from_stdout(stdout: str) -> dict[str, Any] | None:
    """Try to extract JSON context from script stdout.

    Strategy:
    1. Try parsing entire stdout as JSON
    2. Try parsing last non-empty line as JSON
    3. Return None if no valid JSON found
    """
    stdout = stdout.strip()
    if not stdout:
        return None

    # Try full stdout
    try:
        result = json.loads(stdout)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try last line
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if lines:
        try:
            result = json.loads(lines[-1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None
```

**Validation rules:**
- Only `dict` (JSON object) is accepted as context — arrays, scalars are ignored
- Keys must be strings (JSON requirement)
- Values should be JSON-serializable (strings, numbers, bools, null, nested dicts/lists)
- Context dict size limit: keep under 64KB (don't store large data — this is metadata, not a database)

**Reference:** Airflow XCom requires serializable values and warns against large data. Same principle — context is for small metadata (status, counters, flags), not data payloads.

---

### Feature 5: Conditional Notification (when field)

**Mechanism:** Add `when` field to `NotifyConfig`. Before sending notification, evaluate the expression against current context.

**Expression format:**

```
field == "value"      # Equality (string comparison)
field != "value"      # Inequality (string comparison)
field == 42           # Equality (numeric comparison)
field != 0            # Inequality (numeric comparison)
```

**Scope:** Only `==` and `!=` operators. No `and`/`or`, no functions, no arithmetic. Per PROJECT.md constraints.

**Implementation: Custom parser (no external library)**

Why NOT simpleeval:
1. Only 2 operators needed — simpleeval supports 15+ operators, 90% unused
2. Adds a dependency for trivial functionality
3. Custom parser is ~30 lines of code, fully understood, no attack surface concerns
4. If scope expands later, we can add simpleeval then (it's a drop-in replacement)

```python
import re

_WHEN_PATTERN = re.compile(
    r'^(\w+)\s*(==|!=)\s*(.+)$'
)

def evaluate_when(when: str, context: dict[str, Any]) -> bool:
    """Evaluate a when condition against context.

    Args:
        when: Expression like 'status == "ok"' or 'count != 0'
        context: Current task context dict

    Returns:
        True if condition matches, False otherwise.
        Returns True (always notify) if expression is invalid.
    """
    match = _WHEN_PATTERN.match(when.strip())
    if not match:
        logger.warning(f"Invalid when expression: {when!r}")
        return True  # Default: send notification on invalid expression

    field, operator, value_str = match.groups()
    value_str = value_str.strip()

    # Remove surrounding quotes if present
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
        value_str = value_str[1:-1]

    # Get field value from context
    if field not in context:
        return operator == "!="  # Missing field: != is True, == is False

    context_value = context[field]

    # Compare values
    if operator == "==":
        return str(context_value) == value_str
    elif operator == "!=":
        return str(context_value) != value_str

    return True  # Unknown operator: default to notify
```

**Design decisions:**
- String comparison via `str()` conversion — simple, predictable
- Missing field: `!=` evaluates True (notify), `==` evaluates False (skip) — conservative default
- Invalid expression: default to notify (fail-open for notifications, since missing a notification is worse than an extra one)
- No type coercion beyond string — keep it simple. `status == "ok"` compares string-to-string.

---

### Feature 6: YAML Schema Changes

**Task dataclass additions:**

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
    # NEW v3.0 fields:
    context: dict[str, Any] | None = None  # In-memory only, NOT saved to tasks.yaml
```

**NotifyConfig additions:**

```python
@dataclass
class NotifyConfig:
    channel: str
    recipients: list[str] = field(default_factory=list)
    # NEW v3.0 field:
    when: str | None = None  # Conditional expression, e.g. 'status != "ok"'
```

**Important: `context` is NOT persisted in tasks.yaml.** Context state lives in `~/.config/claw-cron/context/{task_name}.json` as a separate JSON file. Reasons:
1. tasks.yaml is config (rarely changes, user-edited) — context is state (changes every run, machine-generated)
2. Writing context to tasks.yaml on every execution would bloat it and create merge conflicts for version-controlled configs
3. JSON is a better format for programmatic read/write of structured state
4. Follows the separation principle: config (YAML) vs state (JSON)

**Example tasks.yaml with new fields:**

```yaml
tasks:
  - name: disk-check
    cron: "0 8 * * *"
    type: command
    script: "df -h / | tail -1 | awk '{print \"{\\\"usage\\\": \\\"\" $5 \"\\\"}\" }'"
    notify:
      channel: qqbot
      recipients:
        - "c2c:ABC123"
      when: 'usage != "0%"'  # Only notify if disk has usage
```

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| **Custom `when` parser** | simpleeval (v1.0.7) | Only need `==`/`!=` — adding a 60KB dependency for 2 operators is overkill. simpleeval supports 15+ operators, compound types, custom functions — 90% unused. Custom parser is ~30 LOC, zero dependencies, zero attack surface. Add simpleeval later IF scope expands beyond `==`/`!=`. |
| **Persistent context dir** (JSON files) | Context in tasks.yaml | tasks.yaml is user config, not runtime state. Mixing config + state in one file creates bloat, merge conflicts, and confusion. Separate JSON files follow the config/state separation principle. |
| **`str.replace()` for templates** | `string.Template` ($var syntax) | Existing codebase uses `{{ var }}` with `str.replace()` in `render_message()`. Introducing `$var` syntax would be inconsistent. Keep `{{ var }}` everywhere. |
| **Last-line JSON parsing** | Structured output format (e.g., `::context::` prefix) | Simple convention (last line = JSON) is sufficient for the use case. Adding a prefix marker (like GitHub Actions `::set-output`) adds complexity for minimal gain. Scripts can still output debug text before the JSON line. |
| **`os.environ \| custom`** | Full env replacement | Must preserve existing env vars (PATH, HOME, etc.). Merge operator preserves all existing vars while adding/overriding CLAW_CRON_ prefixed ones. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **simpleeval** | Overkill for `==`/`!=` only. Adds dependency, attack surface, and learning curve for 2 operators. | Custom ~30-line regex-based parser |
| **asteval** | Even more overkill than simpleeval — full Python subset interpreter | Custom parser |
| **eval()** | Security risk — arbitrary code execution | Custom parser with regex validation |
| **Jinja2** | Template engine overkill — we just do `str.replace()` for `{{ var }}` | `str.replace()` (matches existing pattern) |
| **SQLite** | Unnecessary for small key-value context data. Adds complexity, migration, and dependency. | JSON files in context dir |
| **pickle** | Security risk — arbitrary code execution on load | JSON (safe, human-readable, debuggable) |
| **Context in tasks.yaml** | Config vs state mixing, bloat, merge conflicts | Separate JSON files in `~/.config/claw-cron/context/` |
| **Cross-task context sharing** | Out of scope for v3.0 (per PROJECT.md). Adds complexity (namespacing, cleanup, dependency tracking). | Per-task context files. Future: may add `context_from: other_task` reference. |

## Stack Patterns by Variant

**If `when` expression scope expands beyond `==`/`!=` (future milestone):**
- Replace custom parser with simpleeval
- Add `simpleeval>=1.0.7` to dependencies
- Keep the same `evaluate_when()` interface — only internals change
- simpleeval supports `>`, `<`, `>=`, `<=`, `in`, `not in`, `and`, `or`, if-expressions
- Migration is seamless since the `when` string format remains the same

**If context data grows large (>64KB per task):**
- Consider adding size warning in `_save_context()`
- Log warning and truncate if context exceeds limit
- Don't migrate to database — context is metadata, not a data store

**If cross-task context sharing is needed (future):**
- Add `context_from: task_name` field to Task
- Read that task's context file instead of own
- Keep same JSON format, just different file path
- No new dependencies needed

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Python 3.12 json | All supported Python versions | `json.loads()` and `json.dumps()` are stable since Python 3.0 |
| Python 3.12 subprocess | All supported Python versions | `env` parameter available since Python 3.0 |
| Python 3.12 re | All supported Python versions | `re.compile()` is stable |
| Python 3.12 os.environ | All supported Python versions | Dict merge `|` operator requires Python 3.9+ (already required) |
| PyYAML | Existing version | No new features needed — just extending dataclass fields |
| Click | Existing version | No new features needed — just adding `--when` option |

## Reference Implementation Comparison

| Aspect | GitHub Actions | Airflow XCom | Jenkins | This Project (claw-cron) |
|--------|---------------|--------------|---------|--------------------------|
| **Output mechanism** | `$GITHUB_OUTPUT` file (key=value) | `xcom_push()` or return value | Build result + env inject | JSON on stdout (last line) |
| **Input mechanism** | `env:` block + `$GITHUB_OUTPUT` | `xcom_pull()` | Env inject + parameters | Env vars + context file + template vars |
| **Scope** | Step → Step (within job) | Task → Task (within DAG) | Build → Build | Execution → Execution (same task) |
| **Storage** | Temp file per workflow run | Database (pluggable backend) | Build metadata | JSON file per task |
| **Size limit** | Not documented | "Small data" warning | N/A | 64KB recommended |
| **Serialization** | String key-value pairs | JSON-serializable | String | JSON object (dict) |
| **Conditional logic** | `${{ if }}` expressions | Python conditions | `when` directive | `when: 'field == "value"'` |
| **Complexity** | High (distributed runners) | High (distributed workers) | High (plugin system) | Low (single machine, single user) |

## Sources

### High Confidence (Official Documentation / Stdlb)

- **Python 3.12 json module** (https://docs.python.org/3/library/json.html) — `json.loads()`, `json.dumps()` API. Stable since Python 3.0.
- **Python 3.12 subprocess module** (https://docs.python.org/3/library/subprocess.html) — `subprocess.run(env=...)` parameter. Verified: `env` mapping is passed to `Popen`, replaces default `os.environ`.
- **Python 3.12 re module** (https://docs.python.org/3/library/re.html) — `re.compile()` for expression parsing. Stable API.
- **GitHub Actions: Workflow commands** (https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands) — `$GITHUB_OUTPUT` file-based output mechanism. Pattern: write `key=value` to file path from env var.
- **Airflow XComs** (https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html) — Push/pull data passing pattern. Explicit serialization, small data recommendation, pluggable backends.

### Medium Confidence (Community / Verified)

- **simpleeval PyPI** (https://pypi.org/project/simpleeval/) — Version 1.0.7 (2026-03-16), MIT license, Python >=3.9. Safe expression evaluator. Evaluated and rejected for v3.0 (overkill for `==`/`!=` only).
- **GitHub Actions: Passing job outputs** (https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/pass-job-outputs) — `GITHUB_OUTPUT` file path mechanism verified. Step writes `echo "key=value" >> "$GITHUB_OUTPUT"`.

### Low Confidence (Flagged for Validation)

- None — All recommendations are based on stdlib APIs or verified official documentation.

---

*Stack research for: Command Task Context Mechanism (v3.0)*
*Researched: 2026-04-17*
