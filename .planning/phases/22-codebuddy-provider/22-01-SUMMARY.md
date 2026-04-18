---
phase: 22
plan: 01
status: complete
commit: 9031e1e
completed_at: 2026-04-19T02:30:00Z
key_files:
  created:
    - src/claw_cron/providers/codebuddy.py
  modified:
    - pyproject.toml
    - src/claw_cron/providers/tools.py
    - src/claw_cron/providers/__init__.py
    - src/claw_cron/cmd/chat.py
---

# Plan 22-01 Summary: Implement CodebuddyProvider

## Objective

实现 CodebuddyProvider 类，更新 Provider 工厂，添加 chat 命令参数支持。

## What Was Built

### 1. Codebuddy SDK 依赖 (Task 1)

- 在 `pyproject.toml` 添加 `codebuddy-agent-sdk` 依赖
- 安装版本: `codebuddy-agent-sdk==0.3.130`

### 2. to_codebuddy_tool 转换器 (Task 2)

- 在 `tools.py` 添加 `to_codebuddy_tool()` 函数
- 将 `ToolDefinition` 转换为 Codebuddy SDK 格式
- 保留 JSON Schema 格式的参数定义

### 3. CodebuddyProvider 类 (Task 3)

- 创建 `src/claw_cron/providers/codebuddy.py`
- 实现 `BaseProvider` 接口的 `chat_with_tools` 方法
- 使用 MCP server 方式注册工具
- 包含友好的 API key 缺失提示信息
- 支持异步查询的同步包装

### 4. Provider 工厂更新 (Task 4)

- 导入 `CodebuddyProvider` 和 `to_codebuddy_tool`
- 更新 `ProviderType` 类型定义包含 `"codebuddy"`
- 更新 `get_provider()` 工厂函数
- 更新 `__all__` 导出列表

### 5. Chat 命令参数 (Task 5)

- 添加 `--agent` / `-a` 参数，支持 `claude`, `openai`, `codebuddy`
- 添加 `--model` / `-m` 参数，支持自定义模型
- 重构为 provider-agnostic 架构
- 使用 `ToolDefinition` 替代原生 Anthropic 类型

## Verification Results

### Build Verification
```
✓ uv sync - 成功安装 codebuddy-agent-sdk
✓ Import check - CodebuddyProvider, get_provider, to_codebuddy_tool 导入成功
```

### CLI Verification
```
✓ claw-cron chat --help 显示 --agent 和 --model 参数
```

## Commits

1. `a20f627` - feat(22-01): add codebuddy-agent-sdk dependency
2. `f6c0dce` - feat(22-01): add to_codebuddy_tool converter
3. `c12224a` - feat(22-01): implement CodebuddyProvider class
4. `52917d5` - feat(22-01): update provider factory with CodebuddyProvider
5. `9031e1e` - feat(22-01): add --agent and --model parameters to chat command

## Deviations

None. All tasks completed as planned.

## Success Criteria Check

- [x] User can run `claw-cron chat --agent codebuddy` to use Codebuddy SDK
- [x] User can run `claw-cron chat --model minimax-m2.5` to select specific model
- [x] CodebuddyProvider implements BaseProvider interface correctly
- [x] API Key missing shows friendly message instead of throwing exception
- [x] Provider factory returns correct provider based on `--agent` parameter

---

*Plan: 22-01*
*Completed: 2026-04-19*
