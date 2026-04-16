# Phase 4: Scheduler Server — Research

**Date:** 2026-04-16
**Phase:** 04-scheduler-server
**Requirements:** SERVER-01, SERVER-02, SERVER-03

---

## 1. Cron Expression Parsing

### 决策：纯 Python 实现，不引入第三方库

项目当前依赖：click, rich, pyyaml, anthropic。无 croniter/APScheduler。

**纯 Python 实现方案**（已验证可行）：

```python
def cron_matches(expr: str, dt: datetime) -> bool:
    """Check if 5-field cron expression matches datetime."""
    minute, hour, day, month, weekday = expr.strip().split()
    
    def match_field(field: str, value: int) -> bool:
        if field == '*':
            return True
        for part in field.split(','):
            if '/' in part:
                base, step = part.split('/')
                start = 0 if base == '*' else int(base)
                if value >= start and (value - start) % int(step) == 0:
                    return True
            elif '-' in part:
                lo, hi = part.split('-')
                if int(lo) <= value <= int(hi):
                    return True
            elif int(part) == value:
                return True
        return False
    
    return (
        match_field(minute, dt.minute) and
        match_field(hour, dt.hour) and
        match_field(day, dt.day) and
        match_field(month, dt.month) and
        match_field(weekday, dt.weekday())  # 0=Monday (Python) vs 0=Sunday (cron)
    )
```

**注意：weekday 对齐**
- Python `datetime.weekday()`: 0=Monday, 6=Sunday
- 标准 cron: 0=Sunday, 6=Saturday（或 7=Sunday）
- 决策：使用 cron 标准（0=Sunday），在 `match_field` 中转换：`(dt.weekday() + 1) % 7`

**支持的语法**：
- `*` — 任意值
- `*/N` — 每 N 单位（如 `*/5` = 每5分钟）
- `N-M` — 范围（如 `1-5` = 周一到周五）
- `N,M` — 列举（如 `1,3,5`）
- 具体数字（如 `8`）

---

## 2. 调度循环设计

### 主循环策略：sleep-to-next-minute

```python
import time
from datetime import datetime

def scheduler_loop(stop_event):
    while not stop_event.is_set():
        now = datetime.now().replace(second=0, microsecond=0)
        tasks = load_tasks()
        for task in tasks:
            if task.enabled and cron_matches(task.cron, now):
                threading.Thread(target=execute_task, args=(task,), daemon=True).start()
        
        # Sleep until start of next minute
        next_minute = (time.time() // 60 + 1) * 60
        sleep_secs = next_minute - time.time()
        stop_event.wait(timeout=sleep_secs)
```

**优点**：
- 无第三方依赖
- 精确到分钟（cron 标准粒度）
- 任务并发执行（threading），不阻塞调度循环
- stop_event 支持优雅退出

---

## 3. 前台模式（SERVER-02）

### 日志输出

- 系统日志写入 `~/.config/claw-cron/logs/claw-cron.log`（Phase 3 已定义）
- 前台模式同时输出到 stdout（Rich 格式）
- 格式：`[timestamp] Scheduler started` / `[timestamp] Triggered: <task_name>`

### 信号处理

```python
import signal

def handle_sigterm(signum, frame):
    stop_event.set()

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)
```

---

## 4. 守护进程模式（SERVER-03）

### 双 fork 方案（POSIX 标准）

```python
def daemonize(pid_file: Path, log_file: Path) -> None:
    # Fork 1
    if os.fork() > 0:
        sys.exit(0)
    os.setsid()
    # Fork 2
    if os.fork() > 0:
        sys.exit(0)
    # Redirect stdio to log file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    os.dup2(fd, sys.stdout.fileno())
    os.dup2(fd, sys.stderr.fileno())
    os.close(fd)
    # Write PID
    pid_file.write_text(str(os.getpid()))
```

**PID 文件路径**：`~/.config/claw-cron/claw-cron.pid`

**守护进程日志**：写入 `~/.config/claw-cron/logs/claw-cron.log`（与前台模式相同文件）

### 启动提示

```
Scheduler started as daemon (PID: 12345)
Log: ~/.config/claw-cron/logs/claw-cron.log
Stop: kill 12345
```

---

## 5. 模块结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `src/claw_cron/scheduler.py` | cron 解析 + 调度循环 |
| `src/claw_cron/cmd/server.py` | `server` Click 命令 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/claw_cron/cli.py` | 注册 `server` 命令 |

---

## 6. 波次规划

| Wave | 计划 | 内容 | 依赖 |
|------|------|------|------|
| 1 | 01 | scheduler.py（cron 解析 + 调度循环） | 无 |
| 2 | 02 | cmd/server.py（前台 + daemon 模式） | Wave 1 |
| 3 | 03 | cli.py 注册 server 命令 | Wave 2 |

---

## RESEARCH COMPLETE
