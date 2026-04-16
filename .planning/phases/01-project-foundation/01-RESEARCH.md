# Phase 1: Project Foundation — Research

**Date:** 2026-04-16
**Phase:** 1 — Project Foundation
**Requirements:** SETUP-01, SETUP-02, SETUP-03, STORE-01, STORE-02

---

## Research Summary

### 1. Project Scaffold (SETUP-01, SETUP-02, SETUP-03)

#### Hatch CLI Template

`hatch new --cli claw-cron` 生成的标准结构：

```
claw-cron/
├── src/
│   └── claw_cron/
│       ├── cli/
│       │   └── __init__.py   # Click group 入口
│       ├── __about__.py      # __version__ = "0.1.0"
│       ├── __init__.py
│       └── __main__.py
├── tests/
│   └── __init__.py
├── LICENSE.txt
├── README.md
└── pyproject.toml
```

**注意：** hatch 生成的 `cli/` 是包目录，但 python-cli-project-design 规范要求 `cmd/` 存放子命令。需要在 hatch 生成后手动调整：
- 保留 `cli.py`（或 `cli/__init__.py`）作为 Click group 入口
- 新增 `cmd/` 目录存放各子命令文件

#### pyproject.toml 关键配置

```toml
[project]
name = "claw-cron"
requires-python = ">=3.12"
dynamic = ["version"]
dependencies = [
    "click",
    "rich",
    "pyyaml",
    "anthropic",
]

[project.scripts]
claw-cron = "claw_cron.cli:cli"

[tool.hatch.version]
path = "src/claw_cron/__about__.py"

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "SIM"]
ignore = ["E501"]

[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "strict"
```

#### Click 入口规范

```python
# src/claw_cron/cli.py
import click
from claw_cron.__about__ import __version__

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-v", "--version")
def cli() -> None:
    """claw-cron: AI-powered cron task manager."""
    pass
```

#### 环境配置

- `.python-version` 文件内容：`3.12`
- `.envrc` 内容：`source .venv/bin/activate`
- 初始化命令：`uv venv && uv sync`

---

### 2. YAML Storage Layer (STORE-01, STORE-02)

#### 任务数据模型

每个任务包含以下字段（STORE-02）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | str | 任务唯一名称 |
| `cron` | str | 标准 5 字段 cron 表达式 |
| `type` | str | `command` 或 `agent` |
| `script` | str \| None | command 类型的执行脚本 |
| `prompt` | str \| None | agent 类型的提示词 |
| `client` | str \| None | agent 类型的 AI 客户端（kiro-cli/codebuddy/opencode） |
| `enabled` | bool | 是否启用，默认 True |

#### YAML 文件结构

```yaml
# ~/.config/claw-cron/tasks.yaml  或  ./tasks.yaml（开发时）
tasks:
  - name: daily-backup
    cron: "0 2 * * *"
    type: command
    script: "tar -czf backup.tar.gz ~/Documents"
    prompt: null
    client: null
    enabled: true
  - name: morning-report
    cron: "0 8 * * 1-5"
    type: agent
    script: null
    prompt: "生成今日工作计划并发送到邮件"
    client: kiro-cli
    enabled: true
```

#### 存储路径策略

- 生产：`~/.config/claw-cron/tasks.yaml`（XDG 规范）
- 使用 `pathlib.Path` 管理路径
- 目录不存在时自动创建

#### Storage 模块设计

```python
# src/claw_cron/storage.py
from pathlib import Path
from dataclasses import dataclass, field
import yaml

TASKS_FILE = Path.home() / ".config" / "claw-cron" / "tasks.yaml"

@dataclass
class Task:
    name: str
    cron: str
    type: str          # "command" | "agent"
    script: str | None = None
    prompt: str | None = None
    client: str | None = None
    enabled: bool = True

def load_tasks() -> list[Task]: ...
def save_tasks(tasks: list[Task]) -> None: ...
def get_task(name: str) -> Task | None: ...
def add_task(task: Task) -> None: ...
def delete_task(name: str) -> bool: ...
```

---

### 3. 技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 任务存储格式 | YAML | 人类可读，pyyaml 成熟稳定 |
| 数据模型 | dataclass | 轻量，无需 pydantic 依赖 |
| 存储路径 | `~/.config/claw-cron/` | XDG 规范，跨平台一致 |
| CLI 框架 | Click | 项目规范要求 |
| 输出美化 | Rich | 项目规范要求 |
| 构建工具 | hatch | 项目规范要求 |
| 依赖管理 | uv | 项目规范要求 |

---

### 4. 文件清单

Phase 1 需要创建/修改的文件：

```
claw-cron/
├── src/
│   └── claw_cron/
│       ├── __about__.py      # 版本号
│       ├── __init__.py       # 包初始化
│       ├── __main__.py       # python -m claw_cron 入口
│       ├── cli.py            # Click group + version/help
│       ├── storage.py        # YAML 读写层
│       └── cmd/              # 子命令目录（Phase 2 填充）
│           └── __init__.py
├── tests/
│   └── __init__.py
├── .python-version           # 3.12
├── .envrc                    # source .venv/bin/activate
├── pyproject.toml            # hatch + uv + ruff + pyright 配置
├── README.md
└── AGENTS.md
```

---

## RESEARCH COMPLETE

Phase 1 研究完成。关键发现：
1. `hatch new --cli` 生成基础结构，需手动调整 `cli/` → `cli.py` + `cmd/` 目录
2. YAML 存储使用 dataclass + pyyaml，路径遵循 XDG 规范
3. pyproject.toml 需要配置 ruff（替代 flake8+black）和 pyright（类型检查）
4. Click 入口需支持 `-h` 和 `-v/--version`
