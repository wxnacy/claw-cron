# Architecture Research: Codebuddy Agent 集成

**Researched:** 2026-04-19
**Milestone:** v3.2 Codebuddy Agent 集成

## 现有架构

```
src/claw_cron/
├── providers/
│   ├── __init__.py      # get_provider() 工厂函数
│   ├── base.py          # BaseProvider(ABC)
│   ├── tools.py         # ToolDefinition, ToolCall
│   ├── anthropic.py     # AnthropicProvider
│   └── openai.py        # OpenAIProvider
├── cmd/
│   ├── chat.py          # 直接调用 anthropic SDK (绕过 Provider)
│   └── add.py           # 调用 agent.run_ai_add() -> Provider
├── agent.py             # run_ai_add() 通过 Provider 调用
└── storage.py           # YAML 任务存储
```

### 问题

1. **chat.py 绕过 Provider 层**：直接使用 `anthropic.Anthropic()` SDK
2. **工具定义分散**：chat.py 有 6 个硬编码工具，agent.py 有 1 个
3. **无统一工具注册机制**：工具逻辑在 `_handle_tool()` 中用 if/elif 分发

## 目标架构

```
src/claw_cron/
├── providers/
│   ├── __init__.py      # get_provider() 工厂函数
│   ├── base.py          # BaseProvider(ABC)
│   ├── tools.py         # ToolDefinition, ToolCall
│   ├── anthropic.py     # AnthropicProvider
│   ├── openai.py        # OpenAIProvider
│   └── codebuddy.py     # CodebuddyProvider (新增)
├── tools/                # 内置工具模块 (新增)
│   ├── __init__.py      # 工具注册中心
│   ├── list_tasks.py    # 列出任务
│   ├── add_task.py      # 添加任务
│   ├── update_task.py   # 更新任务
│   ├── delete_task.py   # 删除任务
│   ├── run_task.py      # 执行任务
│   └── get_tool.py      # 渐进式获取工具详情
├── cmd/
│   └── chat.py          # 改用 Provider 层
└── sessions/            # Session 日志存储 (新增)
    └── {session_id}.jsonl
```

## 新增组件

### 1. CodebuddyProvider

```python
# src/claw_cron/providers/codebuddy.py

from codebuddy_agent_sdk import query, CodeBuddyAgentOptions, create_sdk_mcp_server
from .base import BaseProvider, ProviderResult
from .tools import ToolDefinition

class CodebuddyProvider(BaseProvider):
    """使用 Codebuddy SDK 的 Provider"""

    def __init__(self, config: AIConfig):
        self.config = config
        self._client = None

    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[ToolDefinition]
    ) -> ProviderResult:
        # 将 ToolDefinition 转换为 Custom Tools
        custom_tools = self._convert_tools(tools)

        # 创建 MCP 服务器
        mcp_server = create_sdk_mcp_server(
            name='claw-cron',
            tools=custom_tools
        )

        # 调用 Codebuddy SDK
        options = CodeBuddyAgentOptions(
            model=self.config.model or "minimax-m2.5",
            permission_mode="bypassPermissions",
            mcp_servers={'claw-cron': mcp_server},
            max_turns=20,
        )

        # ... 异步调用逻辑
```

### 2. 工具注册中心

```python
# src/claw_cron/tools/__init__.py

from codebuddy_agent_sdk import tool
from typing import Any, Callable

# 工具注册表
_REGISTRY: dict[str, Callable] = {}

def register_tool(name: str, description: str, schema: dict):
    """装饰器：注册工具"""
    def decorator(func: Callable):
        # 创建 Codebuddy tool
        wrapped = tool(name, description, schema)(func)
        _REGISTRY[name] = wrapped
        return wrapped
    return decorator

def get_all_tools() -> list:
    """获取所有注册的工具"""
    return list(_REGISTRY.values())

def get_tool_schemas() -> dict[str, dict]:
    """获取所有工具的 schema（用于渐进式加载）"""
    return {
        name: {"description": "...", "schema": {...}}
        for name, wrapped in _REGISTRY.items()
    }
```

### 3. 内置工具示例

```python
# src/claw_cron/tools/list_tasks.py

from codebuddy_agent_sdk import tool
from typing import Any
from ..storage import get_storage

@tool(
    "list_tasks",
    "列出所有定时任务",
    {}
)
async def list_tasks(args: dict[str, Any]) -> dict[str, Any]:
    """列出所有定时任务"""
    storage = get_storage()
    tasks = storage.load_tasks()
    return {
        "success": True,
        "tasks": [t.model_dump() for t in tasks],
        "count": len(tasks)
    }
```

### 4. Session 日志管理

```python
# src/claw_cron/sessions/__init__.py

import json
from pathlib import Path
from datetime import datetime

SESSIONS_DIR = Path.home() / ".config" / "claw-cron" / "sessions"

def save_session(session_id: str, messages: list[dict]):
    """保存 session 日志"""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = SESSIONS_DIR / f"{session_id}.jsonl"

    with open(log_file, 'a') as f:
        for msg in messages:
            msg['_timestamp'] = datetime.now().isoformat()
            f.write(json.dumps(msg) + '\n')

def load_session(session_id: str) -> list[dict]:
    """加载 session 日志"""
    log_file = SESSIONS_DIR / f"{session_id}.jsonl"
    if not log_file.exists():
        return []

    messages = []
    with open(log_file) as f:
        for line in f:
            messages.append(json.loads(line))
    return messages
```

## 数据流

### Chat 命令流程（改造后）

```
用户输入 → chat.py
    ↓
选择 Provider (codebuddy/anthropic/openai)
    ↓
如果是 codebuddy:
    → CodebuddyProvider.chat_with_tools()
        → 创建 MCP Server (内置工具)
        → query() 调用 Codebuddy SDK
        → Agent 调用工具
        → 返回结果
    ↓
处理消息流
    ↓
显示 Token 消耗
    ↓
保存 Session 日志
```

## 构建顺序

1. **Phase 1: Codebuddy Provider**
   - 新增 `providers/codebuddy.py`
   - 实现 `CodebuddyProvider(BaseProvider)`
   - 更新 `get_provider()` 工厂函数

2. **Phase 2: 工具注册中心**
   - 新增 `tools/` 目录
   - 迁移 chat.py 中的 6 个工具
   - 实现工具注册装饰器

3. **Phase 3: chat.py 改造**
   - 添加 `--agent` / `--model` 参数
   - 改用 Provider 层
   - 集成 Token 显示和 Session 日志

4. **Phase 4: 渐进式工具**
   - 实现 `get_tool_details` 元工具
   - 修改系统提示词

## 验证状态

- [x] 现有架构分析完成
- [x] 目标架构设计完成
- [x] 新增组件确定
- [x] 数据流设计完成
- [x] 构建顺序确定
