# Phase 3: Execution Engine & Chat — Research

**Date:** 2026-04-16
**Phase:** 03-execution-engine-chat
**Requirements:** EXEC-01, EXEC-02, EXEC-03, CHAT-01

---

## 1. Execution Engine

### command 类型 (EXEC-01)

使用 `subprocess.run(cmd, shell=True, capture_output=True, text=True)` 执行 shell 命令。

- 输出写入 `~/.config/claw-cron/logs/<name>.log`
- 日志格式：`[timestamp] START\n{stdout}\n{stderr}\n[timestamp] END (exit_code=N)`
- 日志目录与 tasks.yaml 同级：`~/.config/claw-cron/logs/`

### agent 类型 (EXEC-02, EXEC-03)

内置命令模板（`{prompt}` 为占位符）：

| 客户端 | 命令模板 |
|--------|---------|
| kiro-cli | `kiro-cli -a --no-interactive "{prompt}"` |
| codebuddy | `codebuddy -y -p "{prompt}"` |
| opencode | `opencode run --dangerously-skip-permissions "{prompt}"` |

执行流程：
1. 解析优先级：任务级 `client_cmd` > `~/.config/claw-cron/config.yaml` > 内置默认
2. 用 `task.prompt` 替换 `{prompt}` 占位符
3. 同 command 类型，用 subprocess 执行，输出写入任务日志

### 模块结构

`src/claw_cron/executor.py` — 独立模块，暴露 `execute_task(task: Task) -> int` 函数。

---

## 2. 配置系统

### 全局配置文件

`~/.config/claw-cron/config.yaml`：

```yaml
clients:
  kiro-cli: "kiro-cli -a --no-interactive {prompt}"
  codebuddy: "codebuddy -y -p {prompt}"
  opencode: "opencode run --dangerously-skip-permissions {prompt}"
```

### 加载策略

按需加载（executor 调用时），用简单函数 `load_config() -> dict` 读取，文件不存在时返回空 dict。

### Task 新字段

`storage.Task` 新增 `client_cmd: str | None = None`（任务级命令覆盖，优先级最高）。

---

## 3. 日志系统

### 目录结构

```
~/.config/claw-cron/
├── tasks.yaml
├── config.yaml
└── logs/
    ├── claw-cron.log   # 系统日志（Phase 4 server 使用）
    └── <name>.log      # 任务日志
```

### log 命令实现

直接调用系统 `tail -f`（macOS/Linux 均支持，简洁可靠）：

```python
subprocess.run(["tail", "-f", log_file])
```

- `claw-cron log` → `logs/claw-cron.log`（文件不存在时提示）
- `claw-cron log <name>` → `logs/<name>.log`

---

## 4. chat 命令

### 复用 agent.py 的 tool_use 模式

参考 `src/claw_cron/agent.py` 的 Anthropic tool_use 循环，定义 6 个工具：

| 工具 | 参数 | 实现 |
|------|------|------|
| `list_tasks` | 无 | `storage.load_tasks()` |
| `add_task` | name, cron, type, script, prompt, client | `cmd/add._add_direct()` |
| `delete_task` | name | `storage.delete_task()` |
| `run_task` | name | `executor.execute_task()` |
| `enable_task` | name | `storage.update_task(name, enabled=True)` |
| `disable_task` | name | `storage.update_task(name, enabled=False)` |

### 单轮 intent 识别（D-09）

每条消息独立，不保留会话历史。流程：
1. 用户输入 → Anthropic API（tool_use）
2. AI 识别意图 → 调用工具
3. 执行工具 → 结果返回 AI → AI 输出确认文本
4. 等待下一条消息（REPL 循环）

---

## 5. storage 变更

### Task dataclass

新增字段：`client_cmd: str | None = None`

### 新增函数

```python
def update_task(name: str, path: Path = TASKS_FILE, **kwargs) -> bool:
    """Update fields of an existing task. Returns True if found."""
```

---

## 6. 波次规划

| Wave | 计划 | 内容 | 依赖 |
|------|------|------|------|
| 1 | 01 | storage 更新（Task.client_cmd + update_task） | 无 |
| 2 | 02 | executor.py + config 加载 | Wave 1 |
| 3 | 03 | cmd/run.py（run 命令）| Wave 2 |
| 3 | 04 | cmd/log.py（log 命令）| Wave 2 |
| 4 | 05 | cmd/chat.py（chat 命令）| Wave 1, 2 |
| 5 | 06 | cli.py 注册 run/log/chat 命令 | Wave 3, 4 |

---

## RESEARCH COMPLETE
