# Pitfalls Research

**Domain:** Command 上下文机制 & 条件化通知 (v3.0)
**Researched:** 2026-04-17
**Confidence:** HIGH (基于代码审查 + Python 标准库文档 + 社区实践)

---

## Critical Pitfalls

### Pitfall 1: YAML 并发写入导致 tasks.yaml 损坏

**What goes wrong:**
调度器在多个 daemon 线程中并发执行 `run_task_with_notify`，每个任务执行后可能更新 context 状态并调用 `save_tasks()` 写入 `tasks.yaml`。两个线程同时读-改-写 YAML 文件，后写入者覆盖前者的修改，导致数据丢失或文件内容损坏（YAML 半截写入）。

**Why it happens:**
- 当前 `storage.py` 的 `save_tasks()` 是纯 `open("w")` 写入，没有任何锁保护
- `scheduler.py` 第 106 行用 `threading.Thread` 启动任务，多个任务可能同时完成
- `update_task()` 也是 read-modify-write 模式（`load_tasks` → 修改 → `save_tasks`），无原子性保证
- 即使 Python GIL 存在，`open() + write()` 不是原子操作——线程 A 可能在线程 B 的 `load_tasks()` 和 `save_tasks()` 之间插入写入

**How to avoid:**
```python
import threading

# 全局文件锁 — 保护所有 tasks.yaml 读写操作
_tasks_lock = threading.Lock()

def save_tasks(tasks: list[Task], path: Path = TASKS_FILE) -> None:
    with _tasks_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        # 先写临时文件，再原子重命名（防止半截写入）
        tmp_path = path.with_suffix(".yaml.tmp")
        with tmp_path.open("w") as f:
            yaml.dump({"tasks": [asdict(t) for t in tasks]}, f,
                      default_flow_style=False, allow_unicode=True)
        tmp_path.replace(path)  # 原子操作

def update_task(name: str, path: Path = TASKS_FILE, **kwargs: Any) -> bool:
    with _tasks_lock:
        tasks = load_tasks(path)  # 锁内读
        for task in tasks:
            if task.name == name:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                save_tasks(tasks, path)  # 锁内写
                return True
        return False
```

**Warning signs:**
- 日志中出现 YAML 解析错误（`yaml.scanner.ScannerError`）
- 任务莫名消失（被并发写入覆盖）
- `tasks.yaml` 文件大小突然变为 0

**Phase to address:**
**Phase 1 (上下文注入基础设施)** — 在引入 context 写入之前就必须建立文件锁机制，否则第一个并发 context 更新就会触发此问题

---

### Pitfall 2: 脚本 stdout 混杂非 JSON 输出导致上下文解析失败

**What goes wrong:**
设计意图是 script 通过 stdout 输出 JSON（如 `{"signed_in": false}`），系统解析后存为 context。但实际脚本经常混杂非 JSON 输出：
- 调试日志：`Checking sign-in status...` 然后 `{"signed_in": false}`
- 进度信息：`Progress: 50%` 然后 JSON
- stderr 和 stdout 混合（当前 `executor.py` 第 84-87 行合并了两者）
- 脚本报错时输出 traceback + 部分 JSON

**Why it happens:**
- 当前 `execute_task()` 把 stdout 和 stderr 合并为一个 `output` 字符串（第 84-87 行）
- 没有约定 JSON 输出的位置（开头？结尾？独立行？）
- 没有容错机制——`json.loads()` 对混合内容直接报错

**How to avoid:**
```python
import json
import re

def parse_context_from_output(output: str) -> dict[str, Any]:
    """从脚本输出中提取 JSON context。

    策略：
    1. 尝试整体解析（纯净 JSON 输出）
    2. 找到最后一个 JSON 对象（允许前面有日志输出）
    3. 解析失败返回空 dict（不阻塞任务执行）
    """
    output = output.strip()
    if not output:
        return {}

    # 策略 1: 整体解析
    try:
        result = json.loads(output)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # 策略 2: 找最后一个 { ... } 块（允许前面有日志）
    # 匹配最后一个完整的 JSON 对象
    brace_depth = 0
    last_open = -1
    for i, ch in enumerate(output):
        if ch == '{':
            if brace_depth == 0:
                last_open = i
            brace_depth += 1
        elif ch == '}':
            brace_depth -= 1
            if brace_depth == 0 and last_open >= 0:
                candidate = output[last_open:i+1]
                try:
                    result = json.loads(candidate)
                    if isinstance(result, dict):
                        return result
                except json.JSONDecodeError:
                    continue

    # 策略 3: 解析失败，返回空 dict，记录警告
    logger.warning(f"Could not parse JSON context from output: {output[:200]}")
    return {}
```

**额外设计决策：**
- **分离 stdout/stderr**：`subprocess.run()` 应分别捕获 stdout 和 stderr，只从 stdout 解析 JSON，stderr 仅供日志
- **输出约定**：文档中明确说明"JSON 必须是 stdout 的最后一行有效输出"

**Warning signs:**
- `json.decoder.JSONDecodeError` 频繁出现在日志
- context 始终为空 dict
- 用户脚本加上 `echo "debug..."` 后通知不再工作

**Phase to address:**
**Phase 2 (JSON stdout 上下文回传)** — 这是 context 回传的核心解析逻辑，必须在实现时就考虑容错

---

### Pitfall 3: 环境变量注入导致 shell 注入或变量名冲突

**What goes wrong:**
系统通过环境变量向 script 注入上下文（如 `CLAW_CRON_TASK_NAME=sign_in_check`），存在两类风险：

1. **Shell 注入**：如果 context 值包含特殊字符（如 `; rm -rf /`），通过环境变量传递给 `shell=True` 的 subprocess 可能被 shell 解释执行
2. **变量名冲突**：注入的环境变量名与 script 依赖的现有环境变量冲突（如覆盖 `PATH`、`HOME` 等）

**Why it happens:**
- 当前 `executor.py` 第 80 行使用 `subprocess.run(cmd, shell=True, ...)`——shell 会解释环境变量中的特殊字符
- 如果 context 值中包含 `$()` 或反引号，shell 可能执行命令替换
- 环境变量没有命名空间隔离——如果直接用 context key 作为变量名（如 `signed_in=false`），可能与系统变量冲突

**How to avoid:**
```python
import os

# 安全的环境变量前缀 — 避免与系统变量冲突
CONTEXT_ENV_PREFIX = "CLAW_CONTEXT_"

def build_context_env(context: dict[str, Any]) -> dict[str, str]:
    """从 context dict 构建安全的环境变量。

    规则：
    1. 所有 key 添加 CLAW_CONTEXT_ 前缀
    2. key 转为大写，非字母数字替换为 _
    3. value 转为字符串（JSON 序列化复杂值）
    """
    env = {}
    for key, value in context.items():
        safe_key = CONTEXT_ENV_PREFIX + re.sub(r'[^A-Za-z0-9_]', '_', key.upper())
        if isinstance(value, (dict, list)):
            safe_value = json.dumps(value, ensure_ascii=False)
        else:
            safe_value = str(value)
        env[safe_key] = safe_value
    return env

# 在 executor.py 中使用
def execute_task(task: Task) -> tuple[int, str]:
    if task.type == "command":
        cmd = task.script or ""
        env = {**os.environ, **build_context_env(task.context or {})}
        result = subprocess.run(cmd, shell=True, capture_output=True,
                                text=True, env=env)
```

**关键安全措施：**
1. **CLAW_CONTEXT_ 前缀**：避免与 `PATH`、`HOME` 等系统变量冲突
2. **环境变量传递而非字符串拼接**：通过 `env` 参数传递，不拼接到 `cmd` 字符串中——环境变量在 shell 中默认是安全的，不会被命令替换
3. **key 白名单/清洗**：只允许字母数字下划线，防止恶意 key
4. **值类型安全**：复杂值 JSON 序列化，避免 `__import__('os').system('rm -rf /')` 等攻击向量

**Warning signs:**
- 用户报告脚本行为异常（环境变量被覆盖）
- 安全审计发现 `shell=True` + 用户控制的值

**Phase to address:**
**Phase 1 (上下文注入基础设施)** — 环境变量注入是 Phase 1 的核心功能，安全模式必须在设计阶段确定

---

### Pitfall 4: 上下文文件临时文件泄漏和并发访问冲突

**What goes wrong:**
系统为 script 提供上下文文件（如 `/tmp/claw-cron-sign_in_check-ctx.json`），script 读取初始 context 并写入结果。两类问题：

1. **临时文件泄漏**：脚本异常退出后，临时文件未被清理，`/tmp` 逐渐堆积
2. **并发访问**：同一任务被快速连续触发（如 cron `* * * * *`），两个线程同时写同一个上下文文件，后者覆盖前者

**Why it happens:**
- 当前没有上下文文件机制，需要新实现
- `tempfile.NamedTemporaryFile` 默认在 `close()` 时删除，但如果 script 需要读取该文件，需要 `delete=False`
- 文件路径基于任务名生成，同一任务并发时路径相同
- 没有文件锁机制

**How to avoid:**
```python
import tempfile
import uuid

def create_context_file(task_name: str, context: dict[str, Any]) -> tuple[str, str]:
    """创建上下文文件，返回 (file_path, env_var_name)。

    使用唯一文件名避免并发冲突。
    """
    # 唯一后缀 — 避免并发写入同一文件
    unique_id = uuid.uuid4().hex[:8]
    ctx_dir = Path.home() / ".config" / "claw-cron" / "context"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    ctx_path = ctx_dir / f"{task_name}-{unique_id}.json"

    with ctx_path.open("w") as f:
        json.dump(context, f, ensure_ascii=False, indent=2)

    # 环境变量指向文件路径
    return str(ctx_path), "CLAW_CONTEXT_FILE"

def cleanup_context_file(path: str) -> None:
    """清理上下文文件，静默处理已删除的情况。"""
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        pass

# 在 execute_task 中使用 try/finally 确保清理
def execute_task(task: Task) -> tuple[int, str]:
    ctx_file = None
    try:
        if task.type == "command" and task.context:
            ctx_path, _ = create_context_file(task.name, task.context)
            ctx_file = ctx_path
            # ... 执行脚本
    finally:
        if ctx_file:
            cleanup_context_file(ctx_file)
```

**关键设计决策：**
1. **不用 /tmp** — 用 `~/.config/claw-cron/context/` 目录，避免被系统清理策略意外删除
2. **唯一文件名** — `{task_name}-{uuid}.json`，避免并发冲突
3. **try/finally 清理** — 确保异常时也清理临时文件
4. **启动时清理遗留文件** — 服务启动时清理上次异常退出遗留的上下文文件

**Warning signs:**
- `/tmp` 或 context 目录中堆积大量 `claw-cron-*` 文件
- 磁盘空间告警
- 上下文文件内容为空（被并发写入覆盖）

**Phase to address:**
**Phase 1 (上下文注入基础设施)** — 上下文文件是三种注入方式之一，文件管理和清理逻辑必须在实现时就到位

---

### Pitfall 5: 条件表达式 when 评估的边界情况导致通知丢失或误发

**What goes wrong:**
`notify.when` 条件字段（如 `signed_in == false`）存在多种边界情况：

1. **类型不匹配**：context 中 `signed_in` 是布尔 `false`，when 表达式中 `"false"` 是字符串——`false == "false"` 结果为 `false`
2. **key 不存在**：脚本没输出某个 key，when 条件中引用了它——`None == false` 结果如何？
3. **大小写敏感**：`False` vs `false` vs `FALSE`——Python 布尔 vs JSON vs 用户输入
4. **数值比较**：`count == 0` 中的 `0` 是整数还是字符串？
5. **空值处理**：`output != ""` 当 output 为 `None` 时的行为

**Why it happens:**
- JSON 输出的值类型由脚本决定，不可控
- 用户在 YAML 中写的 when 表达式是字符串，需要类型推断
- 简单的 `==`/`!=` 在 Python 中跨类型比较结果不符合用户预期（`0 == "0"` → `False`，`0 == False` → `True`）

**How to avoid:**
```python
def evaluate_when(when_expr: str, context: dict[str, Any]) -> bool:
    """评估 when 条件表达式。

    支持格式: "key == value" 或 "key != value"

    类型强制规则：
    - 布尔比较：字符串 "true"/"false" 映射为 True/False
    - 数值比较：尝试将两边转为数值比较
    - None 处理：key 不存在时，== None 和 != "xxx" 合理处理
    """
    # 解析表达式
    if " == " in when_expr:
        key, expected = when_expr.split(" == ", 1)
        op = "=="
    elif " != " in when_expr:
        key, expected = when_expr.split(" != ", 1)
        op = "!="
    else:
        logger.warning(f"Invalid when expression: {when_expr}")
        return True  # 无效表达式 → 默认发送通知

    key = key.strip()
    expected = expected.strip().strip('"').strip("'")
    actual = context.get(key)

    # 类型强制转换
    actual = _coerce_for_comparison(actual, expected)
    expected_typed = _coerce_for_comparison(expected, expected)

    if op == "==":
        return actual == expected_typed
    else:
        return actual != expected_typed

def _coerce_for_comparison(value: Any, reference: str) -> Any:
    """根据参考值推断类型。"""
    if value is None:
        return None

    # 布尔映射
    bool_map = {"true": True, "false": False}
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in bool_map:
        return bool_map[value.lower()]

    # 尝试数值
    try:
        return int(value) if '.' not in str(value) else float(value)
    except (ValueError, TypeError):
        pass

    return str(value)
```

**关键设计决策：**
1. **when 表达式缺失 → 默认发送通知**（宁可多通知，不可漏通知）
2. **布尔映射明确**：`"true"`/`"false"` → Python `True`/`False`，文档明确说明
3. **key 不存在时的行为**：`==` 评估为 `False`（不匹配），`!=` 评估为 `True`（不等于预期值）
4. **不支持 `>`, `<`, `>=`, `<=`** — v3.0 限定为简单等值判断，降低复杂度

**Warning signs:**
- 用户报告"明明 signed_in 是 false 却没收到通知"
- 通知发送了但条件不满足（误报）
- when 表达式中写了 `> 5` 但不被支持

**Phase to address:**
**Phase 3 (条件化通知)** — when 条件评估是此阶段的核心逻辑，类型强制转换规则必须在设计阶段明确

---

### Pitfall 6: 上下文状态漂移 — 旧 context 残留影响后续执行

**What goes wrong:**
任务 A 的执行输出 `{"signed_in": true, "error_count": 3}`，存为 context。下次执行时脚本输出 `{"signed_in": false}`（没有 `error_count` 字段）。如果 context 采用"合并更新"策略，`error_count: 3` 会残留，导致：
- 条件判断基于过时数据
- context 无限增长
- 调试困难（不知道哪个值是当前的，哪个是残留的）

**Why it happens:**
- "合并更新"（merge）是最直觉的实现——新值覆盖旧值，旧 key 保留
- JSON 输出的字段集合可能因脚本逻辑变化而不同
- 没有明确的"这是完整的 context 还是增量的 context"语义约定

**How to avoid:**
**采用"替换而非合并"策略**（推荐）：

```python
def update_task_context(task_name: str, new_context: dict[str, Any]) -> None:
    """更新任务上下文 — 替换策略。

    每次 script 输出的 JSON 完全替换之前的 context，
    而非合并。如果 script 需要保留之前的值，
    应在 script 中自行读取 CLAW_CONTEXT_FILE 并回传。
    """
    with _tasks_lock:
        update_task(task_name, context=new_context)
```

**如果需要合并策略**（某些场景更方便），则必须：
1. 提供 `context_mode: replace | merge` 配置选项
2. merge 模式下支持 `null` 值删除 key（`{"error_count": null}` → 删除 `error_count`）
3. 文档明确说明两种模式的语义差异

**推荐默认 replace** — 更可预测，脚本可以完全控制输出什么。

**Warning signs:**
- context 中的 key 数量持续增长
- 条件通知基于用户认为已不存在的值触发
- 用户困惑"为什么 when 表达式还能匹配到旧值"

**Phase to address:**
**Phase 2 (JSON stdout 上下文回传)** — context 更新策略在回传逻辑设计时必须确定

---

### Pitfall 7: 向后兼容性破坏 — 现有无 context 的任务停止工作

**What goes wrong:**
v3.0 为 Task dataclass 添加 `context` 字段和 NotifyConfig 添加 `when` 字段后：
1. **YAML 反序列化失败**：旧 tasks.yaml 中没有 `context` 和 `when` 字段，`Task(**raw)` 因缺少新必需字段而报错
2. **执行逻辑变更**：`execute_task()` 中新增了 context 注入代码，没有 context 的任务走了新代码路径但 context 为 None，可能触发 `AttributeError`
3. **通知逻辑变更**：`notify_task_result()` 新增了 when 条件判断，没有 when 的 NotifyConfig 行为是否改变？

**Why it happens:**
- `Task` dataclass 的 `context` 字段如果是必需的，旧 YAML 加载就报错
- `NotifyConfig.from_dict()` 如果不处理 `when` 字段，旧配置会丢失或报错
- `execute_task()` 的代码路径没有 `if task.context:` 保护

**How to avoid:**
```python
# 1. Task 新增字段必须有默认值
@dataclass
class Task:
    name: str
    cron: str
    type: str
    script: str | None = None
    # ... 现有字段 ...
    context: dict[str, Any] | None = None  # 新增，默认 None
    context_inject: dict[str, str] | None = None  # 新增，注入配置

# 2. NotifyConfig 新增 when 字段
@dataclass
class NotifyConfig:
    channel: str
    recipients: list[str] = field(default_factory=list)
    when: str | None = None  # 新增，默认 None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotifyConfig:
        return cls(
            channel=data.get("channel", ""),
            recipients=data.get("recipients", []),
            when=data.get("when"),  # 新增
        )

# 3. 执行逻辑中的保护
def execute_task(task: Task) -> tuple[int, str]:
    # context 注入只在有 context 时执行
    env_overrides = {}
    if task.context:
        env_overrides = build_context_env(task.context)
    # ...

# 4. 通知逻辑中的保护
async def notify_task_result(self, task, exit_code, output, context=None):
    if not task.notify:
        return []
    # when 条件只在有 when 时评估
    if task.notify.when and context is not None:
        if not evaluate_when(task.notify.when, context):
            logger.info(f"Notification skipped: when condition not met for '{task.name}'")
            return []
    # ... 正常发送逻辑
```

**关键原则：**所有新增字段必须有默认值，所有新代码路径必须有 fallback，现有任务零修改即可运行。

**Warning signs:**
- 升级后 `claw-cron list` 报 `TypeError` 或 `KeyError`
- 已有任务不再发送通知
- 用户报告"升级后什么都不工作了"

**Phase to address:**
**Phase 1 (上下文注入基础设施)** — Task/NotifyConfig 数据模型变更必须从一开始就保持向后兼容

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **context 合并而非替换** | script 只输出变化的字段 | 状态漂移、残留旧值、条件判断不可预测 | **Never** — 默认替换，merge 可作为高级选项 |
| **stdout/stderr 不分离** | 复用现有 `output` 合并逻辑 | JSON 解析困难（stderr 日志混入 stdout） | **MVP only** — 必须分离，只从 stdout 解析 context |
| **环境变量不加前缀** | 更短的变量名，脚本更简洁 | 与系统变量冲突，安全风险 | **Never** — 必须使用 `CLAW_CONTEXT_` 前缀 |
| **when 表达式支持 eval()** | 灵活的条件判断 | 代码注入风险，安全漏洞 | **Never** — 只支持 `==`/`!=` 简单表达式 |
| **上下文文件用 /tmp** | 零配置，系统自动清理 | 系统重启丢失、被 OS 清理策略删除、权限问题 | **Never** — 用 `~/.config/claw-cron/context/` |
| **不加文件锁直接写 YAML** | 简单实现 | 并发写入导致数据丢失或文件损坏 | **Never** — 必须加 threading.Lock + 原子写入 |

---

## Integration Gotchas

Common mistakes when connecting the new context mechanism to existing components.

| Integration Point | Common Mistake | Correct Approach |
|-------------------|----------------|------------------|
| **executor.py ↔ storage.py** | execute_task 完成后直接调用 `save_tasks()` 更新 context | 通过 `update_task(context=new_ctx)` 统一接口，内部加锁 |
| **subprocess env** | 直接用 `os.environ` 修改全局环境 | 创建 `env = {**os.environ, **context_env}` 副本传给 subprocess |
| **NotifyConfig.when ↔ context** | when 条件在 Notifier 中评估，但 Notifier 不知道 context | `execute_task_with_notify()` 传递 parsed context 给 Notifier |
| **模板变量 {{ }}** | 用 `str.format()` 渲染模板 | 用自定义渲染（`{{ key }}`），避免 `{key}` 与 Python format 冲突 |
| **context 文件路径传递** | 文件路径硬编码在环境变量名中 | 使用 `CLAW_CONTEXT_FILE` 固定环境变量名，路径值动态生成 |
| **YAML round-trip** | context dict 存入 YAML 后类型变化（如 `true` → `True`） | YAML 中 context 使用 JSON 字符串存储，避免类型歧义 |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **每次执行都完整重写 tasks.yaml** | 多任务并发时磁盘 I/O 频繁 | 考虑 context 单独存储（独立 JSON 文件），减少 YAML 写入频率 | > 20 个并发任务 |
| **context 不限制大小** | 单个 context JSON 增长到 MB 级 | 限制 context 大小（如 10KB），超出截断或拒绝 | 脚本输出大量数据时 |
| **上下文文件不清理** | `~/.config/claw-cron/context/` 堆积数千文件 | 每次执行后立即清理，启动时扫描遗留文件 | 运行数周后 |
| **JSON 解析正则匹配** | 嵌套 JSON 对象正则匹配失败 | 使用括号匹配而非正则，或要求 JSON 在独立行 | 脚本输出复杂嵌套 JSON 时 |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **环境变量值包含 shell 特殊字符** | `shell=True` 下可能被 shell 解释执行 | 通过 `env` 参数传递（安全），不拼接到 cmd 字符串中 |
| **when 表达式使用 eval/exec** | 任意代码执行 | 只支持 `==`/`!=` 简单解析，不用 eval |
| **context 文件权限过于开放** | 其他用户可读取 context 中的敏感信息 | 创建文件时设置 `mode=0o600` |
| **模板变量注入** | 用户在 YAML 中配置模板 `{{ __import__('os').system('rm -rf /') }}` | 模板渲染只支持预定义变量（`{{ date }}`、`{{ time }}`、`{{ context.key }}`），不支持表达式 |
| **context key 注入** | 脚本输出 `{"__proto__": {...}}` 等 key | 清洗 key（只允许字母数字下划线），忽略非法 key |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **context JSON 格式错误无反馈** | 用户不知道为什么条件通知不工作 | 执行日志中明确显示解析结果："Parsed context: {signed_in: false}" 或 "Failed to parse context from output" |
| **when 条件不满足时静默跳过** | 用户以为通知功能坏了 | 日志中记录："Notification skipped: when condition 'signed_in == false' not met (actual: true)" |
| **环境变量名不直观** | 用户不知道脚本中用什么变量名接收 context | 文档示例 + `claw-cron run --dry-run` 显示注入的环境变量列表 |
| **context 输出要求不清楚** | 用户不知道脚本该输出什么格式的 JSON | 文档明确：stdout 最后一行输出 `{"key": "value"}` 格式的 JSON |
| **when 表达式语法不明确** | 用户写了 `signed_in = false`（单等号） | 报错时提示正确语法："Use '==' for comparison, not '='. Example: signed_in == false" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **环境变量注入：** 往往只注入了 context，没注入元信息（task_name, execution_time） — 验证脚本是否能获取当前任务名
- [ ] **上下文文件：** 往往只创建了文件，没在 finally 中清理 — 验证脚本异常退出后文件是否被清理
- [ ] **JSON 解析：** 往往只处理了纯净 JSON 输出，没处理混合输出 — 验证 `echo "checking..." && echo '{"ok": true}'` 是否正常解析
- [ ] **when 条件：** 往往只处理了字符串比较，没处理布尔/数值类型 — 验证 `signed_in == false` 当 context 中是 `false`（布尔）时是否工作
- [ ] **向后兼容：** 往往只测试了新任务，没测试旧 YAML 加载 — 验证没有 context/when 字段的旧 tasks.yaml 是否正常加载
- [ ] **线程安全：** 往往只在单任务场景测试，没测并发 — 验证两个同 schedule 任务同时执行时 YAML 是否损坏
- [ ] **通知条件：** 往往只测了 when 条件满足的场景，没测不满足 — 验证 when 条件不满足时通知确实不发送
- [ ] **模板变量：** 往往只支持了 `{{ date }}` 等内置变量，没支持 `{{ context.key }}` — 验证模板中是否可以使用 context 中的值

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **YAML 文件损坏** | MEDIUM | 1. 检查 `.yaml.tmp` 文件是否完整<br>2. 手动修复 YAML 格式<br>3. 从日志重建任务配置 |
| **Context 状态漂移** | LOW | 1. `claw-cron run --reset-context <task>` 重置 context<br>2. 或手动编辑 tasks.yaml 清空 context 字段 |
| **通知误发（when 条件逻辑错误）** | LOW | 1. 修改 when 表达式<br>2. 临时设置 `enabled: false` 停止任务 |
| **通知漏发（when 条件永远不满足）** | MEDIUM | 1. 检查 context 解析日志<br>2. 用 `claw-cron run --debug <task>` 查看解析结果<br>3. 检查类型匹配（布尔 vs 字符串） |
| **环境变量冲突** | LOW | 1. 修改变量名加 CLAW_CONTEXT_ 前缀<br>2. 重新运行任务 |
| **上下文文件堆积** | LOW | 1. 手动清理 `~/.config/claw-cron/context/`<br>2. 重启服务（启动时自动清理） |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **YAML 并发写入损坏** | Phase 1 (上下文注入基础设施) | 多线程并发写测试，YAML 完整性校验 |
| **stdout 非 JSON 解析失败** | Phase 2 (JSON stdout 上下文回传) | 混合输出测试：日志 + JSON、仅日志、仅 JSON、空输出 |
| **环境变量注入安全风险** | Phase 1 (上下文注入基础设施) | 注入 `; rm -rf /` 值验证不执行命令；验证 CLAW_CONTEXT_ 前缀 |
| **上下文文件泄漏/并发** | Phase 1 (上下文注入基础设施) | 异常退出后检查文件清理；并发执行检查文件独立性 |
| **when 条件类型不匹配** | Phase 3 (条件化通知) | 布尔/字符串/数值/None 组合测试；签到检查端到端测试 |
| **Context 状态漂移** | Phase 2 (JSON stdout 上下文回传) | 连续执行测试：先输出 {a, b}，再输出 {a}，验证 b 不残留 |
| **向后兼容性破坏** | Phase 1 (上下文注入基础设施) | 用 v2.4 的 tasks.yaml 测试加载和执行；零修改运行旧任务 |

---

## 签到检查端到端场景风险分析

关键场景：script 检查签到状态，输出 `{"signed_in": true/false}`，notify 只在 `signed_in == false` 时发送。

| 步骤 | 风险 | 影响 | 缓解 |
|------|------|------|------|
| 1. 调度器触发任务 | 线程启动，context 从 YAML 加载 | 并发加载可能读到脏数据 | 加载在锁内完成 |
| 2. 环境变量注入 | `CLAW_CONTEXT_SIGNED_IN=true` | 值类型安全（环境变量都是字符串） | 脚本端负责类型转换 |
| 3. 上下文文件写入 | 文件创建并写入 JSON | 文件泄漏或并发写入 | UUID 文件名 + finally 清理 |
| 4. 脚本执行 | subprocess.run(shell=True) | 环境变量安全，无 shell 注入 | env 参数传递 |
| 5. stdout 解析 | `{"signed_in": false}` | 混杂日志导致解析失败 | 容错解析（最后一行 JSON） |
| 6. context 更新 | 写入 tasks.yaml | 并发写入损坏 | 文件锁 + 原子写入 |
| 7. when 条件评估 | `signed_in == false` | 布尔/字符串类型不匹配 | 类型强制转换 |
| 8. 通知发送/跳过 | 条件不满足时跳过 | 用户不知道为什么没收到通知 | 日志明确记录评估结果 |

---

## Sources

- **Python subprocess 安全最佳实践：** https://snyk.io/blog/command-injection-python-prevention-examples/ (HIGH confidence - Snyk 官方安全博客)
- **Python subprocess shell=True 风险分析：** https://sqlpey.com/python/python-subprocess-shell-tradeoffs/ (HIGH confidence - 与 Python 官方文档一致)
- **Python threading.Lock 并发保护：** https://docs.python.org/3/library/threading.html#lock-objects (HIGH confidence - Python 官方文档)
- **YAML 文件并发写入问题：** 社区实践（HIGH confidence - 读写竞争是经典并发问题）
- **JSON 容错解析策略：** 基于实际开发经验（HIGH confidence - 混合输出是 subprocess 使用常见问题）
- **代码审查：** `src/claw_cron/storage.py` (HIGH confidence - 已验证代码中的 read-modify-write 模式)
- **代码审查：** `src/claw_cron/executor.py` (HIGH confidence - 已验证 stdout/stderr 合并逻辑)
- **代码审查：** `src/claw_cron/scheduler.py` (HIGH confidence - 已验证 threading.Thread 启动模式)

---

*Pitfalls research for: Command 上下文机制 & 条件化通知 (v3.0)*
*Researched: 2026-04-17*
