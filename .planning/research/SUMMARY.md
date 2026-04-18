# Research Summary: Codebuddy Agent 集成

**Synthesized:** 2026-04-19
**Milestone:** v3.2 Codebuddy Agent 集成

---

## Stack Additions

**核心依赖：**
- `codebuddy-agent-sdk` — Python SDK，通过 `uv add codebuddy-agent-sdk` 安装

**环境变量：**
- `CODEBUDDY_API_KEY` — API Key（可选，已登录 CLI 则无需）
- `CODEBUDDY_INTERNET_ENVIRONMENT` — 环境选择（中国版 `internal`，iOA 版 `ioa`）

**集成方式：**
- 新增 `CodebuddyProvider` 继承 `BaseProvider`
- 使用 `createSdkMcpServer` 创建自定义工具
- 通过 `query()` 或 `CodeBuddySDKClient` 调用

---

## Feature Table Stakes

| 功能 | 实现方式 |
|------|----------|
| 自定义工具 | `@tool` 装饰器定义，`createSdkMcpServer` 注册 |
| 模型选择 | `CodeBuddyAgentOptions(model="minimax-m2.5")` |
| 权限控制 | `permission_mode="bypassPermissions"` |
| 多轮对话 | `CodeBuddySDKClient` 上下文管理器 |
| Session 持久化 | `ResultMessage.session_id` + 文件日志 |
| Token 追踪 | `ResultMessage.usage` 字段 |

---

## Architecture Changes

**新增目录：**
```
src/claw_cron/
├── providers/codebuddy.py  # 新增 Provider
├── tools/                  # 工具注册中心
│   ├── __init__.py
│   ├── list_tasks.py
│   ├── add_task.py
│   ├── update_task.py
│   ├── delete_task.py
│   └── run_task.py
└── sessions/              # Session 日志
```

**关键修改：**
- `chat.py` 改用 Provider 层（不再直接调用 Anthropic SDK）
- 添加 `--agent` / `--model` 参数
- 集成 Token 显示和 Session 日志保存

---

## Watch Out For

| 陷阱 | 预防策略 |
|------|----------|
| API Key 缺失 | 友好提示，不抛异常；检测已登录 CLI |
| 网络问题 | 重试机制 + 指数退避 |
| Session 日志过大 | 限制单个 session 10MB，归档旧日志 |
| Token 统计不准 | 只在 `ResultMessage` 中显示最终统计 |
| 渐进式工具困惑 | 系统提示词明确说明工具使用方式 |
| Provider 切换状态丢失 | 切换时提示用户，清理状态 |

---

## Build Order

1. **Phase 1: Codebuddy Provider** — 新增 Provider 实现
2. **Phase 2: 工具注册中心** — 迁移现有工具到 `tools/` 目录
3. **Phase 3: chat.py 改造** — 参数、Token 显示、Session 日志
4. **Phase 4: 渐进式工具** — 元工具 + 系统提示词

---

## Key Decisions

| 决策 | 理由 |
|------|------|
| 新增 Provider 而非替换 | 保持向后兼容，支持多 Provider 切换 |
| Custom Tools 而非外部 MCP | 内进程执行，零额外依赖 |
| 文件存储 Session 日志 | 简单可靠，方便调试 |
| 渐进式批量工具 | 减少 Agent 决策负担，按需获取详情 |

---

## Next Steps

进入需求定义阶段 → `/gsd-new-milestone` Step 9
