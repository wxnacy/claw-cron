# Requirements: claw-cron

**Defined:** 2026-04-16
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行。

## v1 Requirements

### Project Setup

- [ ] **SETUP-01**: 项目遵循 python-cli-project-design 规范（hatch 构建，uv 管理依赖，Python 3.12）
- [ ] **SETUP-02**: CLI 入口使用 Click，支持 `-h` 查看帮助，`-v/--version` 查看版本号
- [ ] **SETUP-03**: 使用 Rich 美化输出

### Task Storage

- [ ] **STORE-01**: 任务配置以 YAML 文件存储，项目自管理（不依赖系统 crontab）
- [ ] **STORE-02**: 每个任务包含：名称、cron 表达式、执行类型（command/agent）、脚本或提示词、AI 客户端（agent 类型时）、启用状态

### Add Command

- [ ] **ADD-01**: `add` 命令无参数时进入 AI 交互模式，通过 Anthropic Agent 对话解析用户意图，生成 cron 表达式和任务配置
- [ ] **ADD-02**: `add` 命令支持直接模式：提供完整参数（`--cron`、`--type`、`--script`/`--prompt`、`--client`、`--name`）时跳过 AI 交互直接写入任务
- [ ] **ADD-03**: 直接模式供其他 Agent 作为 skill 调用（无需人工交互）
- [ ] **ADD-04**: AI 交互模式中，询问用户选择 AI 客户端（kiro-cli/codebuddy/opencode），默认 kiro-cli

### List & Delete Commands

- [ ] **LIST-01**: `list` 命令展示所有任务（名称、cron 表达式、类型、状态）
- [ ] **DELETE-01**: `delete` 命令按任务名称或 ID 删除任务
- [ ] **CHAT-01**: `chat` 命令启动 AI 对话模式，支持通过自然语言完成增删查操作

### Execution Engine

- [ ] **EXEC-01**: command 类型任务通过 subprocess 直接执行脚本/命令
- [ ] **EXEC-02**: agent 类型任务通过指定 AI 客户端的无交互模式执行（如 `kiro-cli -a --no-interactive "prompt"`）
- [ ] **EXEC-03**: 支持 kiro-cli、codebuddy、opencode 三种 AI 客户端

### Server Command

- [ ] **SERVER-01**: `server` 命令启动调度服务，自实现 cron 表达式解析和任务调度
- [ ] **SERVER-02**: 默认前台运行，输出调度日志
- [ ] **SERVER-03**: `--daemon` 参数支持守护进程模式后台运行

## v2 Requirements

### Enhancements

- **V2-01**: 任务执行历史记录和日志查询
- **V2-02**: 任务执行失败通知（邮件/webhook）
- **V2-03**: `enable`/`disable` 命令启用/禁用任务（不删除）
- **V2-04**: 任务执行超时配置

## Out of Scope

| Feature | Reason |
|---------|--------|
| 系统 crontab 集成 | 项目自管理调度，跨平台一致，可存储额外元数据 |
| Web UI | CLI 优先，保持工具简洁 |
| 多用户/权限管理 | 单用户本地工具 |
| 分布式调度 | 超出 v1 范围 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Pending |
| SETUP-02 | Phase 1 | Pending |
| SETUP-03 | Phase 1 | Pending |
| STORE-01 | Phase 1 | Pending |
| STORE-02 | Phase 1 | Pending |
| ADD-01 | Phase 2 | Pending |
| ADD-02 | Phase 2 | Pending |
| ADD-03 | Phase 2 | Pending |
| ADD-04 | Phase 2 | Pending |
| LIST-01 | Phase 2 | Pending |
| DELETE-01 | Phase 2 | Pending |
| CHAT-01 | Phase 3 | Pending |
| EXEC-01 | Phase 3 | Pending |
| EXEC-02 | Phase 3 | Pending |
| EXEC-03 | Phase 3 | Pending |
| SERVER-01 | Phase 4 | Pending |
| SERVER-02 | Phase 4 | Pending |
| SERVER-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 18
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after initial definition*
