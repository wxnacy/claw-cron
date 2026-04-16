# Phase 2: Task Management Commands — Research

**Date:** 2026-04-16
**Phase:** 2 — Task Management Commands
**Requirements:** ADD-01, ADD-02, ADD-03, ADD-04, LIST-01, DELETE-01

---

## Research Summary

### 1. Click 子命令结构（ADD-01~04, LIST-01, DELETE-01）

每个命令一个文件，放在 `src/claw_cron/cmd/`，在 `cli.py` 中注册：

```python
# src/claw_cron/cli.py
from claw_cron.cmd.add import add
from claw_cron.cmd.list import list_tasks
from claw_cron.cmd.delete import delete

cli.add_command(add)
cli.add_command(list_tasks, name="list")
cli.add_command(delete)
```

#### add 命令参数设计

```python
@click.command()
@click.option("--name", default=None, help="Task name")
@click.option("--cron", default=None, help="Cron expression (5 fields)")
@click.option("--type", "task_type", default=None, type=click.Choice(["command", "agent"]))
@click.option("--script", default=None, help="Shell command (command type)")
@click.option("--prompt", "ai_prompt", default=None, help="AI prompt (agent type)")
@click.option("--client", default=None, type=click.Choice(["kiro-cli", "codebuddy", "opencode"]))
def add(name, cron, task_type, script, ai_prompt, client): ...
```

**直接模式判断：** 当 `name` + `cron` + `task_type` 均提供时，跳过 AI 交互直接写入。

**AI 交互模式：** 任意必填参数缺失时，启动 Anthropic Agent 对话。

#### list 命令

```python
@click.command("list")
def list_tasks(): ...
```

使用 Rich Table 展示：Name / Cron / Type / Script or Prompt / Status

#### delete 命令

```python
@click.command()
@click.argument("name")
def delete(name): ...
```

---

### 2. Anthropic Agent 对话模式（ADD-01, ADD-04）

使用 `anthropic.Anthropic().messages.create()` + tool_use 实现结构化输出。

#### 工具定义（tool_use）

```python
CREATE_TASK_TOOL = {
    "name": "create_task",
    "description": "Create a scheduled task with the parsed configuration",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique task name"},
            "cron": {"type": "string", "description": "5-field cron expression"},
            "type": {"type": "string", "enum": ["command", "agent"]},
            "script": {"type": "string", "description": "Shell command (command type)"},
            "prompt": {"type": "string", "description": "AI prompt (agent type)"},
            "client": {"type": "string", "enum": ["kiro-cli", "codebuddy", "opencode"]},
        },
        "required": ["name", "cron", "type"],
    },
}
```

#### 对话流程

```python
def run_ai_add(partial_args: dict) -> Task:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": "...用户描述..."}]
    
    while True:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            tools=[CREATE_TASK_TOOL],
            messages=messages,
        )
        
        if response.stop_reason == "tool_use":
            # 提取 tool_use block，解析参数，创建任务
            tool_block = next(b for b in response.content if b.type == "tool_use")
            return Task(**tool_block.input)
        
        # 继续对话
        assistant_text = next(b.text for b in response.content if b.type == "text")
        messages.append({"role": "assistant", "content": response.content})
        user_reply = click.prompt(assistant_text)
        messages.append({"role": "user", "content": user_reply})
```

#### AI 客户端选择（ADD-04）

当 `type=agent` 且 `client` 未指定时，用 `click.prompt` 询问：

```python
client_choice = click.prompt(
    "Select AI client",
    type=click.Choice(["kiro-cli", "codebuddy", "opencode"]),
    default="kiro-cli",
)
```

---

### 3. Rich 输出（LIST-01）

```python
from rich.console import Console
from rich.table import Table

console = Console()

def show_tasks(tasks: list[Task]) -> None:
    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return
    
    table = Table(title="Tasks", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Cron", style="green")
    table.add_column("Type")
    table.add_column("Script/Prompt", overflow="fold")
    table.add_column("Status")
    
    for t in tasks:
        content = t.script or t.prompt or "-"
        status = "✓ enabled" if t.enabled else "✗ disabled"
        table.add_row(t.name, t.cron, t.type, content, status)
    
    console.print(table)
```

---

### 4. 文件结构

```
src/claw_cron/
├── cli.py          # 注册子命令
├── cmd/
│   ├── __init__.py
│   ├── add.py      # add 命令（直接模式 + AI 模式）
│   ├── list.py     # list 命令（Rich 表格）
│   └── delete.py   # delete 命令
└── agent.py        # Anthropic Agent 对话逻辑（ADD-01, ADD-04）
```

---

### 5. 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| AI 结构化输出 | tool_use | 强制 JSON 输出，避免解析文本 |
| AI 模型 | claude-3-5-haiku-20241022 | 快速、低成本，适合交互式对话 |
| 客户端选择时机 | agent 类型且 client 未指定时询问 | 直接模式不打断，AI 模式自然询问 |
| 命令注册方式 | cli.add_command() | 保持 cli.py 简洁，命令逻辑分离 |
| delete 确认 | click.confirm() | 防误删，符合 CLI 惯例 |

---

## RESEARCH COMPLETE

Phase 2 研究完成。关键发现：
1. `add` 命令双模式：所有必填参数齐全时直接写入，否则启动 Anthropic tool_use 对话
2. Anthropic SDK 0.95.0 支持 tool_use，`stop_reason == "tool_use"` 时提取结构化参数
3. Rich Table 已验证可正常渲染，用于 `list` 命令
4. 每个命令独立文件放 `cmd/`，`agent.py` 封装 AI 对话逻辑
