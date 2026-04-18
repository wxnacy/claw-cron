# Stack Research: Codebuddy Agent 集成

**Researched:** 2026-04-19
**Milestone:** v3.2 Codebuddy Agent 集成

## 核心发现

### 1. Codebuddy Python SDK 安装

```bash
uv add codebuddy-agent-sdk
# 或
pip install codebuddy-agent-sdk
```

**版本要求：**
- Python >= 3.10
- CodeBuddy CLI 已安装

### 2. 环境变量配置

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `CODEBUDDY_API_KEY` | API Key 认证 | 可选（已有登录凭据则无需） |
| `CODEBUDDY_INTERNET_ENVIRONMENT` | 环境选择（internal/ioa） | 中国版/iOA 版需要 |
| `CODEBUDDY_CODE_PATH` | CLI 可执行文件路径 | 可选 |

**重要提示：**
- 中国版用户需要设置：`CODEBUDDY_INTERNET_ENVIRONMENT=internal`
- iOA 版用户需要设置：`CODEBUDDY_INTERNET_ENVIRONMENT=ioa`
- 如果未设置 API Key，SDK 会自动使用已有登录凭据

### 3. 与现有 Provider 层的集成方案

**方案 A：新增 Codebuddy Provider（推荐）**

在 `providers/` 目录新增 `codebuddy.py`，实现 `CodebuddyProvider(BaseProvider)`：

```python
from codebuddy_agent_sdk import query, CodeBuddyAgentOptions

class CodebuddyProvider(BaseProvider):
    def __init__(self, config: AIConfig):
        self.config = config

    def chat_with_tools(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[ToolDefinition]
    ) -> ProviderResult:
        # 使用 Codebuddy SDK
        options = CodeBuddyAgentOptions(
            model=self.config.model,
            permission_mode="bypassPermissions",
            # ... 其他配置
        )
        # 调用 SDK
```

**方案 B：直接替换 chat.py 中的 Anthropic SDK**

在 `chat.py` 中替换 `anthropic.Anthropic()` 为 Codebuddy SDK 调用。

### 4. 不需要的依赖

- **不需要** `@anthropic-ai/sdk` — Codebuddy SDK 内部处理
- **不需要** 额外的 MCP 服务器 — Custom Tools 直接在进程内定义
- **不需要** 独立的工具进程 — 使用 `createSdkMcpServer` 内联定义

## 推荐集成方式

```
chat.py
    └── CodebuddyProvider (新增)
            └── codebuddy_agent_sdk.query()
                    └── 自定义工具 (Custom Tools)
```

## 关键 API

### query() 函数

```python
from codebuddy_agent_sdk import query, CodeBuddyAgentOptions

async for message in query(
    prompt="...",
    options=CodeBuddyAgentOptions(
        model="minimax-m2.5",
        permission_mode="bypassPermissions",
        max_turns=20,
        cwd="/path/to/project",
        env={"CODEBUDDY_API_KEY": "..."}
    )
):
    # 处理消息
```

### Client API（多轮对话）

```python
from codebuddy_agent_sdk import CodeBuddySDKClient, CodeBuddyAgentOptions

async with CodeBuddySDKClient(options=options) as client:
    # 第一轮对话
    await client.query("分析这个项目")
    async for msg in client.receive_response():
        print(msg)

    # 第二轮对话（保持上下文）
    await client.query("继续分析")
    async for msg in client.receive_response():
        print(msg)
```

## Session ID 和对话恢复

SDK 支持 `session_id` 在 ResultMessage 中返回，可用于恢复对话：

```python
from codebuddy_agent_sdk import ResultMessage

if isinstance(message, ResultMessage):
    session_id = message.session_id
    # 保存 session_id 用于后续恢复
```

恢复对话：

```python
options = CodeBuddyAgentOptions(
    resume=session_id,  # 恢复之前的会话
    # 或
    continue_conversation=True  # 继续最近的会话
)
```

## Token 消耗追踪

ResultMessage 包含 `usage` 字段：

```python
@dataclass
class ResultMessage:
    duration_ms: int
    duration_api_ms: int
    num_turns: int
    session_id: str
    total_cost_usd: float | None = None
    usage: dict[str, Any] | None = None  # 包含 token 详情
```

## 验证状态

- [x] SDK 安装方式已确认
- [x] 环境变量配置已明确
- [x] 与 Provider 层集成方案已设计
- [x] 不需要的依赖已排除
- [x] 关键 API 已识别
