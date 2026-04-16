# Roadmap: claw-cron

**Created:** 2026-04-16
**Phases:** 4
**Requirements:** 18 v1 requirements mapped ✓

---

## Phase 1: Project Foundation

**Goal:** 搭建符合 python-cli-project-design 规范的项目骨架，实现任务配置的 YAML 存储层。

**Requirements:** SETUP-01, SETUP-02, SETUP-03, STORE-01, STORE-02

**Success Criteria:**
1. `claw-cron --version` 输出版本号，`-h` 输出帮助信息
2. 任务 YAML 文件可正确读写，包含所有必要字段（名称、cron、类型、脚本/提示词、客户端、状态）
3. `uv run claw-cron` 可正常启动，Rich 输出正常渲染

**UI hint**: no

---

## Phase 2: Task Management Commands

**Goal:** 实现任务的增删查 CLI 命令，add 支持直接模式（完整参数）和 AI 交互模式（Anthropic Agent）。

**Requirements:** ADD-01, ADD-02, ADD-03, ADD-04, LIST-01, DELETE-01

**Success Criteria:**
1. `claw-cron add --cron "0 8 * * *" --type command --script "echo hello" --name test` 直接创建任务，无需交互
2. `claw-cron add`（无参数）启动 Anthropic Agent 对话，引导用户描述任务并生成配置
3. `claw-cron list` 以表格形式展示所有任务
4. `claw-cron delete <name>` 删除指定任务并确认

**UI hint**: no

---

## Phase 3: Execution Engine & Chat

**Goal:** 实现任务执行引擎（command/agent 两种模式）和 AI 对话管理界面。

**Requirements:** EXEC-01, EXEC-02, EXEC-03, CHAT-01

**Success Criteria:**
1. command 类型任务通过 subprocess 执行，输出捕获并记录
2. agent 类型任务通过 `kiro-cli -a --no-interactive`、`codebuddy`、`opencode` 等无交互模式执行
3. `claw-cron chat` 启动对话，用户可用自然语言完成增删查（"删除 test 任务"、"列出所有任务"）

**UI hint**: no

---

## Phase 4: Scheduler Server

**Goal:** 实现自管理调度服务，解析 cron 表达式，按时触发任务执行。

**Requirements:** SERVER-01, SERVER-02, SERVER-03

**Success Criteria:**
1. `claw-cron server` 前台启动，输出调度日志，按 cron 表达式准时触发任务
2. `claw-cron server --daemon` 以守护进程模式后台运行
3. 调度器正确解析标准 5 字段 cron 表达式（分 时 日 月 周）

**UI hint**: no

---

## Coverage

| Phase | Requirements | Count |
|-------|-------------|-------|
| Phase 1 | SETUP-01, SETUP-02, SETUP-03, STORE-01, STORE-02 | 5 |
| Phase 2 | ADD-01, ADD-02, ADD-03, ADD-04, LIST-01, DELETE-01 | 6 |
| Phase 3 | EXEC-01, EXEC-02, EXEC-03, CHAT-01 | 4 |
| Phase 4 | SERVER-01, SERVER-02, SERVER-03 | 3 |
| **Total** | | **18** |

All v1 requirements mapped ✓

---
*Created: 2026-04-16*
