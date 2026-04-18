# Phase 22: Codebuddy Provider - Research

**Researched:** 2026-04-19
**Phase Goal:** 新增 Codebuddy Provider，支持 agent 和 model 参数选择

---

## Research Summary

本阶段需要实现 CodebuddyProvider 以支持 Codebuddy SDK 集成。核心挑战在于 Codebuddy SDK 使用 MCP (Model Context Protocol) 协议进行工具调用，与现有的 Anthropic/OpenAI 工具调用模式不同。

---

## Key Findings

### 1. Codebuddy SDK 架构

**来源:** [SDK Custom Tools Guide](https://www.codebuddy.cn/docs/cli/sdk-custom-tools)

Codebuddy SDK 的核心组件:

```python
from codebuddy_agent_sdk import query, create_sdk_mcp_server, tool
```

| 组件 | 用途 |
|------|------|
| `query()` | 执行对话，返回异步生成器 |
| `create_sdk_mcp_server()` | 创建 MCP 服务器，注册自定义工具 |
| `@tool` 装饰器 | 定义工具，包括名称、描述、参数 |

### 2. 工具定义格式差异

**现有格式 (ToolDefinition):**
```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
```

**Codebuddy SDK 格式:**
```python
@tool(
    "tool_name",
    "Description",
    {"param": str, "count": int}  # 简单类型映射 或 JSON Schema
)
async def handler(args: dict[str, Any]) -> dict[str, Any]:
    return {'result': ...}
```

**转换需求:** 需要 `to_codebuddy_tool` 转换器将 `ToolDefinition` 转换为 `@tool` 装饰器格式。

### 3. query() 函数行为

```python
result = query(
    prompt='User message',
    options={
        'mcp_servers': {
            'my-tools': mcp_server,
        },
    },
)

async for message in result:
    print(message)  # 流式返回消息
```

**关键特性:**
- 返回异步生成器，需要异步迭代
- `options` 字典包含 MCP 服务器配置
- 无直接 `messages` 参数，对话历史通过 session 管理

### 4. API Key 处理

**环境变量:** `CODEBUDDY_API_KEY`

**检测方法:**
```python
import os
api_key = os.environ.get('CODEBUDDY_API_KEY')
if not api_key:
    # 友好提示，exit(0)
    ...
```

### 5. Provider 工厂模式

**当前实现 (`providers/__init__.py:62-100`):**
```python
ProviderType = Literal["claude", "openai"]

def get_provider(
    provider: ProviderType,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> BaseProvider:
    providers = {
        "claude": AnthropicProvider,
        "openai": OpenAIProvider,
    }
    ...
```

**需要更新:**
1. `ProviderType = Literal["claude", "openai", "codebuddy"]`
2. 添加 `"codebuddy": CodebuddyProvider` 到 providers 字典

---

## Technical Patterns

### 1. BaseProvider 接口要求

CodebuddyProvider 必须实现 (`providers/base.py:72-111`):

```python
def chat_with_tools(
    self,
    messages: list[dict[str, Any]],
    system_prompt: str,
    tools: list[ToolDefinition],
    max_tokens: int = 1024,
) -> ProviderResult:
    ...
```

**挑战:** Codebuddy SDK 的 `query()` 函数不直接支持:
- 传入 `messages` 列表（历史对话）
- 返回 `ProviderResult` 结构

**解决方案:**
- 使用 session 机制管理对话历史（Phase 24）
- 本阶段暂不支持多轮对话，每次调用独立处理
- 将 `query()` 结果包装为 `ProviderResult`

### 2. 异步执行

Codebuddy SDK 的 `query()` 是异步函数，但 BaseProvider 的 `chat_with_tools()` 是同步方法。

**方案:** 使用 `asyncio.run()` 或类似机制在同步上下文中执行异步代码。

### 3. 错误处理

现有异常类 (`providers/exceptions.py`):
- `ProviderAuthError` - 认证失败
- `ProviderRateLimitError` - 限流
- `ProviderResponseError` - 响应错误
- `ProviderError` - 通用错误

**Codebuddy SDK 可能的异常:** 需要测试确认。

---

## Dependencies

### 新增依赖

需要在 `pyproject.toml` 添加:
```
codebuddy-agent-sdk
```

**注意:** 包名需要确认，可能是 `codebuddy_agent_sdk` 或其他名称。

### 现有依赖

- `anthropic` (已有)
- `openai` (已有)
- `rich` (已有，用于错误提示格式化)

---

## Integration Points

### 文件创建

| 文件 | 用途 |
|------|------|
| `src/claw_cron/providers/codebuddy.py` | CodebuddyProvider 实现 |
| `src/claw_cron/providers/tools.py` | 添加 `to_codebuddy_tool` 转换器 |

### 文件修改

| 文件 | 修改内容 |
|------|----------|
| `src/claw_cron/providers/__init__.py` | 更新 ProviderType, get_provider, __all__ |
| `src/claw_cron/cmd/chat.py` | 添加 --agent/--model 参数 |
| `pyproject.toml` | 添加 codebuddy-agent-sdk 依赖 |

---

## Implementation Approach

### 推荐顺序

1. **添加依赖** - pyproject.toml
2. **创建转换器** - `to_codebuddy_tool` in tools.py
3. **实现 CodebuddyProvider** - providers/codebuddy.py
4. **更新工厂** - providers/__init__.py
5. **添加参数** - cmd/chat.py
6. **API Key 处理** - 友好错误提示

### 代码模板

**CodebuddyProvider 骨架:**

```python
from codebuddy_agent_sdk import query, create_sdk_mcp_server, tool
from typing import Any
import os

from .base import BaseProvider, ProviderResult
from .tools import ToolDefinition, ToolCall, to_codebuddy_tool

class CodebuddyProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        super().__init__(api_key=api_key, model=model, base_url=base_url)
    
    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[ToolDefinition],
        max_tokens: int = 1024,
    ) -> ProviderResult:
        # 1. 转换工具为 MCP 格式
        # 2. 创建 MCP 服务器
        # 3. 调用 query()
        # 4. 解析结果为 ProviderResult
        ...
```

---

## Risks & Mitigations

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| SDK 包名不确定 | 安装失败 | 先测试 pip search 或文档确认 |
| 异步/同步冲突 | 接口不兼容 | 使用 asyncio.run() 包装 |
| MCP 协议差异 | 工具调用失败 | 仔细测试转换器 |
| query() 无 messages 参数 | 无多轮对话 | Phase 24 实现 session |

---

## Open Questions

1. **SDK 包名?** 需要确认 PyPI 上的实际包名
2. **模型列表?** Codebuddy 支持哪些模型？默认 minimax-m2.5
3. **异常类型?** Codebuddy SDK 抛出哪些异常？
4. **token 消耗?** query() 是否返回 token 使用信息？

---

## References

- [SDK Custom Tools Guide](https://www.codebuddy.cn/docs/cli/sdk-custom-tools)
- `src/claw_cron/providers/base.py` - BaseProvider 接口
- `src/claw_cron/providers/anthropic.py` - 参考实现
- `src/claw_cron/providers/tools.py` - 现有转换器
- `src/claw_cron/cmd/chat.py` - 现有 chat 命令

---

*Research complete: 2026-04-19*
