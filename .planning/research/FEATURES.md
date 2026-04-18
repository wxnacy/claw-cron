# Features Research: Codebuddy Agent 集成

**Researched:** 2026-04-19
**Milestone:** v3.2 Codebuddy Agent 集成

## 功能分类

### Table Stakes（必须有）

| 功能 | 说明 | 复杂度 |
|------|------|--------|
| 自定义工具定义 | 使用 `@tool` 装饰器定义工具 | 低 |
| 工具参数验证 | 支持 JSON Schema 验证 | 低 |
| 模型选择 | 通过 `model` 参数指定 | 低 |
| 权限控制 | `permission_mode` 参数 | 低 |
| 对话历史 | 通过 Client API 多轮对话 | 中 |
| Session 持久化 | 通过 `session_id` 恢复对话 | 中 |

### Differentiators（差异化功能）

| 功能 | 说明 | 复杂度 |
|------|------|--------|
| 渐进式批量工具 | 系统提示词给名称，agent 按需获取 | 高 |
| Hook 系统 | 在工具执行前后插入自定义逻辑 | 中 |
| Token 消耗追踪 | 实时显示每轮 token 使用情况 | 中 |
| 多模型 fallback | 主模型失败时切换备用模型 | 低 |
| canUseTool 回调 | 细粒度权限控制 | 中 |

### Anti-Features（不要做）

| 功能 | 原因 |
|------|------|
| 外部 MCP 服务器 | Custom Tools 已足够，无需额外进程 |
| 完全替代现有 Provider 层 | 保持向后兼容，逐步迁移 |
| 每次都创建新 Session | 支持恢复和继续对话 |

## 渐进式批量工具（Progressive Tool Batching）

### 核心概念

渐进式批量工具是一种让 Agent 按需获取工具详细信息的机制：

1. **系统提示词**：只给工具名称和简短描述
2. **Agent 决策**：根据名称判断是否需要该工具
3. **按需获取**：调用时才提供完整参数 schema

### 实现方式

Codebuddy SDK 支持在系统提示词中定义工具元信息：

```python
from codebuddy_agent_sdk import create_sdk_mcp_server, tool

# 定义一个"获取工具详情"的元工具
@tool(
    "get_tool_details",
    "获取指定工具的详细参数信息",
    {"tool_name": str}
)
async def get_tool_details(args: dict) -> dict:
    # 返回工具的完整参数 schema
    tool_schemas = {
        "list_tasks": {"type": "object", "properties": {...}},
        "add_task": {"type": "object", "properties": {...}},
        # ...
    }
    return tool_schemas.get(args['tool_name'], {})

# 创建 MCP 服务器
server = create_sdk_mcp_server(
    name='claw-cron-tools',
    tools=[get_tool_details]
)
```

### 系统提示词模板

```python
SYSTEM_PROMPT = """
你是 claw-cron 的任务管理助手。你有以下内置工具：

- list_tasks: 列出所有定时任务
- add_task: 添加新任务
- update_task: 修改已有任务
- delete_task: 删除任务
- run_task: 立即执行任务
- remind_task: 设置任务提醒

当用户请求某个操作时，先确认需要哪个工具，然后调用它。
如果需要了解工具的详细参数，使用 get_tool_details 获取。
"""
```

## Session 管理

### Session ID 获取

```python
from codebuddy_agent_sdk import ResultMessage

async for message in query(prompt="...", options=options):
    if isinstance(message, ResultMessage):
        session_id = message.session_id
        # 持久化 session_id
```

### Session 日志保存

建议将 session 日志保存到文件系统：

```python
import json
from pathlib import Path

def save_session_log(session_id: str, messages: list[dict]):
    log_dir = Path.home() / ".config" / "claw-cron" / "sessions"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{session_id}.jsonl"
    with open(log_file, 'a') as f:
        for msg in messages:
            f.write(json.dumps(msg) + '\n')
```

## Token 消耗追踪

### 实时显示

```python
from codebuddy_agent_sdk import ResultMessage, StreamEvent

async for message in query(prompt="...", options=options):
    if isinstance(message, StreamEvent):
        # 流式事件中可能包含 token 信息
        event = message.event
        if 'usage' in event:
            usage = event['usage']
            print(f"输入: {usage.get('input_tokens')}")
            print(f"输出: {usage.get('output_tokens')}")
            print(f"缓存: {usage.get('cache_read_tokens', 0)}")

    if isinstance(message, ResultMessage):
        usage = message.usage or {}
        print(f"总计费用: ${message.total_cost_usd:.4f}")
        print(f"API 耗时: {message.duration_api_ms}ms")
        print(f"总耗时: {message.duration_ms}ms")
```

### usage 字段结构

```python
usage: {
    "input_tokens": 1234,
    "output_tokens": 567,
    "cache_read_tokens": 100,  # 缓存读取
    "cache_write_tokens": 50,  # 缓存写入
}
```

## 错误处理

### 友好提示 API Key 缺失

```python
from codebuddy_agent_sdk import CLINotFoundError, CLIConnectionError

try:
    async for msg in query(prompt="...", options=options):
        print(msg)
except CLINotFoundError:
    print("CodeBuddy CLI 未安装，请先安装 CLI")
except CLIConnectionError as e:
    print(f"连接失败，请检查 CODEBUDDY_API_KEY 是否正确设置: {e}")
except ExecutionError as e:
    if "authentication" in str(e).lower():
        print("认证失败，请设置 CODEBUDDY_API_KEY 环境变量")
    else:
        print(f"执行错误: {e}")
```

## 验证状态

- [x] 功能分类完成
- [x] 渐进式批量工具设计完成
- [x] Session 管理方案确定
- [x] Token 追踪方式明确
- [x] 错误处理策略确定
