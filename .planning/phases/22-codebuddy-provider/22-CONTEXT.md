# Phase 22: Codebuddy Provider - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

新增 CodebuddyProvider 实现 BaseProvider 接口，支持 `--agent` 和 `--model` 参数选择 AI 后端和模型。包含 Provider 工厂更新、参数解析、API Key 缺失处理、Tool 格式转换器。

</domain>

<decisions>
## Implementation Decisions

### SDK 集成方式
- **D-01:** 使用 Codebuddy Python SDK (`codebuddy_agent_sdk`)
- **D-02:** 工具调用使用 MCP 协议，需要新的转换器 `to_codebuddy_tool`
- **D-03:** CodebuddyProvider 使用 `create_sdk_mcp_server` 和 `query` 函数

### 参数设计
- **D-04:** `--agent` / `-a` 参数默认值为 `codebuddy`
- **D-05:** `--model` / `-m` 参数默认值为 `minimax-m2.5`
- **D-06:** 支持配置文件 `~/.config/claw-cron/config.yaml` 设置默认 agent 和 model
- **D-07:** 参数优先级: 命令行参数 > 配置文件 > 默认值

### API Key 缺失处理
- **D-08:** 显示详细指引，包括环境变量设置方法 (`export CODEBUDDY_API_KEY=xxx`) 和配置文件方法
- **D-09:** 友好退出 (exit code 0)，不抛异常
- **D-10:** 错误信息使用 Rich 格式化，与其他命令风格一致

### Tool 格式适配
- **D-11:** 新增 `to_codebuddy_tool` 转换器，将 `ToolDefinition` 转换为 MCP 装饰器格式
- **D-12:** 工具定义使用 `@tool` 装饰器，参数使用简单类型映射或 JSON Schema

### Provider 工厂更新
- **D-13:** 更新 `ProviderType` 为 `Literal["claude", "openai", "codebuddy"]`
- **D-14:** 更新 `get_provider` 工厂函数支持 "codebuddy"

### Claude's Discretion
- 具体的错误提示文案
- 配置文件的具体格式和字段名

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Codebuddy SDK 文档
- `https://www.codebuddy.cn/docs/cli/sdk-custom-tools` — SDK Custom Tools Guide，工具定义格式、MCP 服务器创建、query 函数使用

### 现有 Provider 架构
- `src/claw_cron/providers/base.py` — BaseProvider 抽象类定义，chat_with_tools 接口
- `src/claw_cron/providers/__init__.py` — Provider 工厂函数 get_provider，ProviderType 定义
- `src/claw_cron/providers/tools.py` — ToolDefinition, ToolCall, 现有转换器
- `src/claw_cron/providers/anthropic.py` — AnthropicProvider 实现，作为参考

### 现有 Chat 命令
- `src/claw_cron/cmd/chat.py` — 现有 chat 命令实现，需要添加参数支持

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `BaseProvider` 抽象类: 定义了 `chat_with_tools` 接口，CodebuddyProvider 需要实现
- `ToolDefinition` / `ToolCall`: 工具定义和调用的数据类，可以复用
- `ProviderResult`: 统一的返回结果数据类，可以复用
- 现有异常类: `ProviderAuthError`, `ProviderError` 等，可以复用

### Established Patterns
- Provider 工厂模式: `get_provider(provider, api_key, model)` 返回具体 Provider 实例
- 错误处理: 捕获 SDK 异常并转换为自定义异常
- Rich 格式化: 所有用户输出使用 `rich.console.Console`

### Integration Points
- `src/claw_cron/providers/codebuddy.py` — 新建，实现 CodebuddyProvider
- `src/claw_cron/providers/tools.py` — 添加 `to_codebuddy_tool` 转换器
- `src/claw_cron/providers/__init__.py` — 更新 ProviderType 和 get_provider
- `src/claw_cron/cmd/chat.py` — 添加 `--agent` 和 `--model` 参数
- `src/claw_cron/config.py` — 添加配置文件读取逻辑（如需要）

</code_context>

<specifics>
## Specific Ideas

- Codebuddy SDK 使用 MCP 协议，工具定义格式:
  ```python
  @tool("tool_name", "description", {"param": type})
  async def handler(args: dict[str, Any]) -> dict[str, Any]:
      return {'result': ...}
  ```
- 配置文件路径: `~/.config/claw-cron/config.yaml`
- API Key 环境变量: `CODEBUDDY_API_KEY`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 22-codebuddy-provider*
*Context gathered: 2026-04-19*
