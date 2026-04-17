# Feature Landscape

**Domain:** claw-cron v3.0 Command Task Context Mechanism
**Researched:** 2026-04-17
**Overall confidence:** HIGH

## Context

This research covers the NEW features for v3.0: bidirectional context passing for command-type cron tasks.
Existing features (v1-v2) are NOT in scope — they're already built.

### Reference Systems Studied

| System | Context Injection | Context Feedback | State Persistence | Conditional Logic |
|--------|------------------|-----------------|-------------------|-------------------|
| **GitHub Actions** | `env` at workflow/job/step level, `GITHUB_ENV` file | `GITHUB_OUTPUT` file (`echo "name=value" >> $GITHUB_OUTPUT`), `steps.<id>.outputs.<name>` | Built-in (runner manages env files per job) | `if: ${{ steps.check.outputs.status == 'success' }}` |
| **Airflow XCom** | Task context via `**kwargs`, Jinja templates | `xcom_push(key, value)`, auto `return_value` on task return | Database backend (default), pluggable custom backends | `TriggerRule`, downstream task reads XCom |
| **Jenkins** | Environment injection plugin, `env` global | Build variables, `env.WORKSPACE`, plugin-managed state | Build artifacts, persistent build variables | `when { expression }` in declarative pipeline |
| **SaltStack** | Pillar (static data), Grains (system facts), SLS context | State return data, `context` dict in state compiler | Mine (cached grains), SDB (key-value store) | `onlyif`, `unless` requisites |
| **Rundeck** | Job options, context variables (`option.*`) | Export Var step, `data` key in job reference | Job state persistence via Export/Log Data | Node filters, step conditions |

---

## Table Stakes

Features users expect. Missing = product feels incomplete for a context-aware task scheduler.

| Feature | Why Expected | Complexity | Category | Dependencies |
|---------|--------------|------------|----------|-------------|
| **Environment variable injection** | Standard in every job runner (GitHub Actions `env`, crontab env vars, Jenkins env injection). Scripts naturally read env vars. | LOW | Context Injection | Existing `subprocess.run` in `executor.py` |
| **Template variable injection** | Already exists for `reminder` type (`{{ date }}`, `{{ time }}`). Users expect this for command scripts too. | LOW | Context Injection | Existing `render_message()` in `notifier.py` |
| **Context file injection** | GitHub Actions uses `$GITHUB_OUTPUT`/`$GITHUB_ENV` files. Scripts that prefer file-based input over env vars expect a context file path. | MEDIUM | Context Injection | New: temp file creation, `CLAW_CONTEXT_FILE` env var pointing to it |
| **JSON stdout context feedback** | Structured output is the industry standard (GitHub Actions `GITHUB_OUTPUT`, Airflow XCom `return_value`). Scripts output JSON, system parses it. | MEDIUM | Context Feedback | Existing `subprocess.run` captures stdout; needs JSON parser |
| **Task state persistence** | Without persistence, context is lost between executions. Users expect prior run's output to inform the next run. | MEDIUM | State Persistence | New: context storage alongside `tasks.yaml` |
| **Conditional notification (`when`)** | GitHub Actions has `if` conditions. Notifying on every execution is noisy; users want to filter by script output. | LOW | Conditional Notification | Requires: context feedback + state persistence |

---

## Differentiators

Features that set claw-cron apart from simple cron and other task schedulers.

| Feature | Value Proposition | Complexity | Category | Notes |
|---------|-------------------|------------|----------|-------|
| **Inline mode (check + notify in one task)** | Most cron tools require separate "check" and "notify" tasks. Claw-cron's inline mode combines them — script checks condition, outputs JSON, `when` decides whether to notify. Simpler user model. | LOW | Conditional Notification | Already decided in PROJECT.md: "内联模式为主" |
| **Three-way context injection** | env vars + template vars + context file covers all script styles: shell one-liners (env), complex scripts (file), message templates (template vars). No other cron tool offers all three. | LOW | Context Injection | Each path serves a different use case; all are simple to implement |
| **Per-task context namespace** | Context is scoped per task (not global like crontab env vars, not cross-task like Airflow XCom). Avoids naming collisions and keeps the model simple. | LOW | State Persistence | Decision: v3.0 only same-task context, cross-task is Out of Scope |
| **Simple `when` expression** | Just `==` and `!=` — intentionally limited. Users don't need a full expression language for 90% of cases (is backup done? did check pass?). Avoids the complexity of GitHub Actions `${{ }}` expressions or Airflow `TriggerRule`. | LOW | Conditional Notification | Explicitly scoped in PROJECT.md: no and/or/function calls |

---

## Anti-Features

Features to explicitly NOT build, with reasoning.

| Anti-Feature | Why Requested | Why Problematic | What to Do Instead |
|-------------|---------------|-----------------|-------------------|
| **Cross-task context sharing** | "Let task A read task B's output" | Creates hidden coupling between tasks. If task B is renamed/disabled, task A silently breaks. Airflow XCom has this problem — teams struggle with implicit DAG dependencies. | Use context file as a shared filesystem approach: task A writes to a known file path, task B reads it. Explicit, debuggable. Or defer to v4+. |
| **Complex condition expressions (and/or/nested/regex)** | "I want `status == 'failed' or status == 'warning'`" | Scope creep into a full expression parser. GitHub Actions uses `${{ }}` with Jinja-like syntax — a DSL that's hard to debug and learn. For a CLI tool, simplicity wins. | Use script-level logic: script does the complex check, outputs `should_notify: true/false`. The `when` field only needs `should_notify == "true"`. |
| **Structured output schema validation** | "Validate that script output has the right fields" | Adds complexity for little value in a single-user CLI tool. Scripts are user-authored — if the output is wrong, the user fixes the script. | Parse JSON best-effort, log warnings for malformed output. No schema enforcement. |
| **Context versioning / history** | "Keep the last N context states for audit" | Premature optimization. Nobody asked for this yet. Storage grows unbounded. | Store only the latest context per task. If audit is needed, existing log files (`~/.config/claw-cron/logs/`) already capture full output. |
| **Context file as YAML** | "Use YAML like tasks.yaml for consistency" | YAML is harder to parse in shell scripts than JSON. JSON is universally supported (`jq`, `python -c "import json"`, `node -e`). | Use JSON for stdout output. Context file on disk can be JSON (simple to read with any tool). |
| **GITHUB_OUTPUT-style file write for feedback** | "Script writes to `$CLAW_OUTPUT` file like GitHub Actions" | Adds complexity over JSON stdout. Requires teaching users about a file protocol (`echo "key=value" >> $CLAW_OUTPUT`). JSON stdout is simpler — just `echo '{"status": "ok"}'`. | JSON stdout only. One clear protocol, not two. The file-based approach is for INPUT (context file), not output. |
| **Agent-type task context** | "AI agents should also output context" | Agent output is unstructured AI text, not JSON. Parsing it reliably is a hard NLP problem. | Scope to command-type only. Agent tasks return raw text; reminder tasks have no output. |

---

## Feature Dependencies

```
Environment variable injection
    └──requires──> executor.py: subprocess.run with env parameter

Template variable injection
    ├──requires──> Existing render_message() pattern
    └──extends──> Template vars for script field (not just message field)

Context file injection
    ├──requires──> Environment variable injection (CLAW_CONTEXT_FILE path)
    ├──requires──> Temp file creation with context data
    └──requires──> Template variable injection ({{ context_file }} as alternative)

JSON stdout context feedback
    ├──requires──> executor.py: parse stdout after subprocess.run
    ├──requires──> JSON validation (try json.loads, handle failure gracefully)
    └──requires──> Task model: no schema change needed (stdout is already captured)

Task state persistence
    ├──requires──> JSON stdout context feedback (source of state data)
    ├──requires──> New storage: per-task context file or dict in tasks.yaml
    └──enables──> Conditional notification (when field reads persisted state)

Conditional notification (when)
    ├──requires──> Task state persistence (context to evaluate against)
    ├──requires──> NotifyConfig model: add `when` field
    └──requires──> Expression evaluator (simple == / != parser)
```

### Dependency on Existing Features

| New Feature | Existing Feature | How It Integrates |
|------------|-----------------|-------------------|
| Env var injection | `executor.py` `subprocess.run(cmd, shell=True)` | Add `env` parameter with context vars |
| Template vars | `notifier.py` `render_message()` | Extend to support `{{ task_name }}`, `{{ last_status }}`, etc. in script field |
| Context file | `storage.py` `Task` dataclass | Context file path derived from task name |
| JSON feedback | `executor.py` `result.stdout` | Parse stdout as JSON after execution |
| State persistence | `storage.py` YAML storage | New file `~/.config/claw-cron/context/<task_name>.json` |
| When condition | `notifier.py` `NotifyConfig` | Add `when: str | None` field; evaluate before sending |
| When condition | `executor.py` `execute_task_with_notify()` | Evaluate `when` before calling `notifier.notify_task_result()` |

---

## Feature Detail: Context Injection (System → Script)

### Environment Variables

**What:** Inject system context as environment variables before script execution.

**Vars to inject:**

| Variable | Value | Example |
|----------|-------|---------|
| `CLAW_TASK_NAME` | Task name | `"backup-check"` |
| `CLAW_TASK_TYPE` | Task type | `"command"` |
| `CLAW_TASK_CRON` | Cron expression | `"0 8 * * *"` |
| `CLAW_CONTEXT_FILE` | Path to context file | `"/home/user/.config/claw-cron/context/backup-check.json"` |
| `CLAW_LAST_EXIT_CODE` | Previous execution exit code | `"0"` |
| `CLAW_LAST_RUN_TIME` | Previous execution timestamp | `"2026-04-17T08:00:00"` |

**Implementation:** Add `env` dict to `subprocess.run()` call in `executor.py`. Merge with `os.environ` (scripts need PATH, HOME, etc.).

**Complexity:** LOW — 5-line change to `execute_task()`.

### Template Variables

**What:** Extend existing `{{ date }}` / `{{ time }}` template rendering to script field.

**Vars to support:**

| Variable | Value | Example |
|----------|-------|---------|
| `{{ date }}` | Current date (existing) | `"2026-04-17"` |
| `{{ time }}` | Current time (existing) | `"08:00:00"` |
| `{{ task_name }}` | Task name | `"backup-check"` |
| `{{ last_status }}` | Previous run status string | `"success"` or `"failed"` |
| `{{ last_exit_code }}` | Previous exit code | `"0"` |

**Implementation:** Call `render_message()` on `task.script` before execution. Add new template vars.

**Complexity:** LOW — extend existing function.

### Context File

**What:** Write current + last context to a JSON file, pass path via `CLAW_CONTEXT_FILE` env var.

**File format:**
```json
{
  "task_name": "backup-check",
  "last_run": {
    "time": "2026-04-17T08:00:00",
    "exit_code": 0,
    "status": "success",
    "output": { "disk_usage": "45%", "healthy": true }
  },
  "current_run": {
    "time": "2026-04-17T09:00:00"
  }
}
```

**Implementation:** Write file before subprocess, clean up after. Scripts that don't need it can ignore the env var.

**Complexity:** MEDIUM — file I/O + JSON serialization, but straightforward.

---

## Feature Detail: Context Feedback (Script → System)

### JSON Stdout Parsing

**What:** Script outputs JSON to stdout. System parses it and persists as task context.

**Protocol:**
1. Script outputs JSON as the LAST line of stdout (allows other output before it)
2. System tries to parse last line as JSON
3. If valid JSON: merge into task context and persist
4. If not JSON: treat as plain output (no context update)

**Why last-line JSON (not entire stdout):**
- Scripts often produce diagnostic output before the result
- GitHub Actions uses file-based (`GITHUB_OUTPUT`) which is harder to learn
- Airflow XCom auto-captures return value — our equivalent is JSON on stdout
- Alternative: JSON wrapped in markers (`::JSON_START::` / `::JSON_END::`) — more robust but more complex

**Decision: Last-line JSON** — simplest protocol, covers 90% of cases. If a script's last stdout line is valid JSON, it's context. Otherwise, it's just output.

**Example:**
```bash
#!/bin/bash
echo "Checking disk usage..."
DISK=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
echo "{\"disk_usage\": \"$DISK%\", \"healthy\": $([ $DISK -lt 80 ] && echo true || echo false)}"
```

**Implementation:** After `subprocess.run`, split stdout by newline, try `json.loads(last_line)`. On success, store as task context.

**Complexity:** MEDIUM — need to handle edge cases (no stdout, no newline, mixed output + JSON).

---

## Feature Detail: State Persistence

### Per-Task Context Storage

**What:** Store task context (from JSON stdout feedback) between executions.

**Storage location:** `~/.config/claw-cron/context/<task_name>.json`

**Why separate files (not in tasks.yaml):**
- `tasks.yaml` is user-editable config; context is runtime state
- Context can be large (script output); bloating tasks.yaml is bad UX
- Separate files allow easy cleanup (`rm ~/.config/claw-cron/context/backup-check.json`)
- Follows the pattern of log files being separate from task config

**File format:**
```json
{
  "last_run_time": "2026-04-17T08:00:00",
  "last_exit_code": 0,
  "last_status": "success",
  "output": {
    "disk_usage": "45%",
    "healthy": true
  },
  "history": []
}
```

**History:** By design, we store ONLY the last run's context (not a list). The `history` key is reserved but empty — see Anti-Feature "Context versioning / history".

**Implementation:**
- New module: `context.py` with `load_context(task_name)` / `save_context(task_name, data)`
- Called from `executor.py` after JSON parsing succeeds
- Loaded before execution to populate env vars and context file

**Complexity:** MEDIUM — new module, file I/O, but simple JSON read/write.

---

## Feature Detail: Conditional Notification

### `when` Field on NotifyConfig

**What:** Add a `when` field to `NotifyConfig` that controls whether notification is sent based on task context.

**YAML format:**
```yaml
tasks:
  - name: disk-check
    cron: "0 */6 * * *"
    type: command
    script: "check-disk.sh"
    notify:
      channel: qqbot
      recipients: ["c2c:ABC123"]
      when: "healthy != true"    # Only notify when disk is unhealthy
```

**Expression syntax:** `<key> <operator> <value>`
- Keys: reference output fields from context (e.g., `healthy`, `disk_usage`, `status`)
- Operators: `==` (equals), `!=` (not equals)
- Values: string literals (quoted or unquoted), numbers, `true`, `false`

**Examples:**
| Expression | Meaning |
|-----------|---------|
| `status == "failed"` | Notify only on failure |
| `healthy != true` | Notify when not healthy |
| `disk_usage == "90%"` | Notify at exact threshold |
| `exit_code != 0` | Notify on non-zero exit |

**Evaluation logic:**
1. After script execution, load persisted context
2. If `when` is set, evaluate expression against context
3. If expression is true → send notification
4. If expression is false → skip notification, log "notification suppressed by when condition"
5. If key not found in context → treat as false (fail-safe: don't notify on missing data)

**Why NOT support `and`/`or`:**
- Adds parser complexity (operator precedence, nesting)
- 90% of use cases are single-condition
- Complex conditions belong in the script itself (script outputs `should_notify: true`)
- PROJECT.md explicitly scopes: "仅支持 == / != 简单判断"

**Implementation:**
- Add `when: str | None = None` to `NotifyConfig` dataclass
- New function: `evaluate_when(when_expr: str, context: dict) -> bool`
- Parse with simple regex: `r'(\w+)\s*(==|!=)\s*(.+)'`
- Call in `execute_task_with_notify()` before `notifier.notify_task_result()`

**Complexity:** LOW — simple string parsing, < 30 lines of code.

---

## MVP Recommendation

### Build First (Core Context Loop)

These form the essential feedback loop: inject context → script runs → output context → persist → notify conditionally.

1. **Environment variable injection** — LOW complexity, enables all other features
2. **Template variable injection** — LOW complexity, extends existing pattern
3. **JSON stdout context feedback** — MEDIUM complexity, core feedback mechanism
4. **Task state persistence** — MEDIUM complexity, required for context to survive across runs
5. **Conditional notification (when)** — LOW complexity, the key user-facing value

### Build Second (Enhanced Context)

6. **Context file injection** — MEDIUM complexity, for scripts that prefer file-based input

### Defer

- Cross-task context sharing (v4+)
- Complex condition expressions (and/or)
- Context history/versioning
- Agent-type context feedback

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Phase Priority | Category |
|---------|------------|---------------------|---------------|----------|
| Environment variable injection | HIGH | LOW | P1 | Context Injection |
| Template variable injection | MEDIUM | LOW | P1 | Context Injection |
| JSON stdout context feedback | HIGH | MEDIUM | P1 | Context Feedback |
| Task state persistence | HIGH | MEDIUM | P1 | State Persistence |
| Conditional notification (when) | HIGH | LOW | P1 | Conditional Notification |
| Context file injection | MEDIUM | MEDIUM | P2 | Context Injection |

---

## Comparison: Context Feedback Approaches

| Approach | Used By | Pros | Cons | Verdict |
|----------|---------|------|------|---------|
| **JSON on stdout (last line)** | Custom | Simple, no file protocol, works with any language | Mixed output can confuse parsing | **Recommended** — simplest for CLI scripts |
| File write (`$CLAW_OUTPUT`) | GitHub Actions | Robust, no parsing ambiguity | Two protocols (env + file), harder to learn | Rejected — adds unnecessary complexity |
| Key-value on stdout (`::set-output`) | GitHub Actions (deprecated) | Familiar to Actions users | Deprecated for a reason — fragile | Rejected — GitHub itself moved away from this |
| Exit code only | crontab | Universal | Too limited (only 0/non-zero) | Insufficient — users need richer data |
| Stderr for metadata | Some tools | Separates data from output | Non-standard, confusing | Rejected — stderr is for errors |

---

## Sources

- **GitHub Actions documentation (HIGH confidence):**
  - Workflow commands: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands
  - Variables: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-variables
  - Key pattern: `GITHUB_OUTPUT` file write, `GITHUB_ENV` file write, `steps.<id>.outputs.<name>` reference

- **Airflow XCom documentation (HIGH confidence):**
  - XComs: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html
  - Key pattern: `xcom_push(key, value)` / `xcom_pull(task_ids, key)`, auto `return_value`, database backend, pluggable storage

- **Crontab environment variables (HIGH confidence):**
  - https://cronitor.io/guides/cron-environment-variables
  - Key pattern: env vars declared in crontab file, limited env by default

- **Claw-cron existing codebase (HIGH confidence):**
  - `executor.py`: subprocess.run with capture_output, no env injection yet
  - `notifier.py`: NotifyConfig with channel + recipients, no `when` field
  - `storage.py`: Task dataclass, YAML-based, no context storage
  - `scheduler.py`: cron matching + thread-based execution

- **Web search (MEDIUM confidence):**
  - Rundeck data passing: https://github.com/rundeck/rundeck/issues/116 (Export Var step)
  - SaltStack context: Pillar/Grains/SLS pattern for stateful execution

---
*Feature research for: claw-cron v3.0 Command Context Mechanism*
*Researched: 2026-04-17*
