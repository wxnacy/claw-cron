# Requirements: claw-cron v2

**Defined:** 2026-04-16
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。
**Milestone:** v2.0 - 多 Provider 支持 + 消息通道

---

## v1 Requirements (Completed)

所有 v1 需求已在 v1.0 里程碑中完成。参见 `.planning/REQUIREMENTS.md` 历史记录。

---

## v2 Requirements

### AI Provider 重构

- [x] **PROV-01**: 重构 `agent.py` 为 Provider 模式，支持多 AI 提供商
- [x] **PROV-02**: 实现 `BaseProvider` 抽象基类，包含 `chat_with_tools()` 方法
- [x] **PROV-03**: 实现 `AnthropicProvider`，迁移现有 Anthropic 逻辑并支持 Tool Use
- [x] **PROV-04**: 实现 `OpenAIProvider`，支持 OpenAI API 和 Tool Use
- [x] **PROV-05**: 添加 `AIConfig` 配置类，支持 `provider`、`model`、`api_key`、`base_url` 参数
- [x] **PROV-06**: 支持环境变量配置 (`CLAW_CRON_API_KEY`, `CLAW_CRON_MODEL`, `CLAW_CRON_PROVIDER`)
- [x] **PROV-07**: Provider 工厂函数 `get_provider()` 自动选择实现

### Tool Use 支持

- [x] **TOOL-01**: 定义中性格式的 `ToolDefinition` 数据类
- [x] **TOOL-02**: 定义 `ToolCall` 数据类，统一 Anthropic 和 OpenAI 的调用结果
- [x] **TOOL-03**: 实现 Tool 格式转换器 (`to_anthropic_tool`, `to_openai_tool`)
- [x] **TOOL-04**: 保持现有 `create_task` Tool 功能正常工作

### 消息通道基础设施

- [ ] **CHAN-01**: 实现 `MessageChannel` 抽象基类
- [ ] **CHAN-02**: 实现 `ChannelConfig` 配置基类
- [ ] **CHAN-03**: 实现 `MessageResult` 结果数据类
- [ ] **CHAN-04**: 实现 `get_channel()` 工厂函数和 `CHANNEL_REGISTRY`

### iMessage 通道

- [ ] **IMSG-01**: 添加 `macpymessenger` 依赖
- [ ] **IMSG-02**: 实现 `IMessageChannel` 类，支持发送文本消息
- [ ] **IMSG-03**: 实现 `IMessageConfig` 配置类（无需额外参数）
- [ ] **IMSG-04**: 支持国际电话号码格式 (`+86...`)

### QQ 通道

- [ ] **QQ-01**: 实现 `QQBotChannel` 类，支持 QQ 开放平台 API
- [ ] **QQ-02**: 实现 `QQBotConfig` 配置类，包含 `app_id`、`client_secret`
- [ ] **QQ-03**: 支持 OAuth2 认证获取 access_token
- [ ] **QQ-04**: 支持私聊消息发送 (`c2c:OPENID` 格式)
- [ ] **QQ-05**: 支持群聊消息发送 (`group:GROUP_OPENID` 格式)
- [ ] **QQ-06**: 支持 Markdown 消息格式 (msg_type=2)

### 任务通知集成

- [ ] **NOTIF-01**: 扩展 `Task` 模型，添加 `notify` 字段
- [ ] **NOTIF-02**: `notify` 字段包含 `channel`（通道名称）和 `recipients`（接收者列表）
- [ ] **NOTIF-03**: 实现 `Notifier` 类，任务执行完成后发送通知
- [ ] **NOTIF-04**: 支持 `claw-cron config channels` 命令配置消息通道
- [ ] **NOTIF-05**: 通知消息包含任务名称、执行状态、执行结果

### 定时提醒功能

- [ ] **REMIND-01**: 新增 `remind` 命令，创建纯提醒任务
- [ ] **REMIND-02**: 提醒任务类型为 `reminder`，仅需 `cron` + `message` + `notify`
- [ ] **REMIND-03**: 提醒消息支持模板变量 `{{ date }}`, `{{ time }}`

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| 微信/飞书通道 | v2 聚焦 iMessage 和 QQ，后续扩展 |
| Telegram/Discord 通道 | v2 不包含，后续扩展 |
| 消息接收/远程控制 | v2 仅支持发送通知，不接收用户指令 |
| QQ Bot 主动推送 | QQ 开放平台 2025 年 4 月后取消此能力 |
| 多账号支持 | v2 每个通道仅支持单账号 |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROV-01 | Phase 5 | ✅ Complete (05-02) |
| PROV-02 | Phase 5 | ✅ Complete (05-01) |
| PROV-03 | Phase 5 | ✅ Complete (05-02) |
| PROV-04 | Phase 5 | ✅ Complete (05-02) |
| PROV-05 | Phase 5 | ✅ Complete (05-01) |
| PROV-06 | Phase 5 | ✅ Complete (05-01) |
| PROV-07 | Phase 5 | ✅ Complete (05-02) |
| TOOL-01 | Phase 5 | ✅ Complete (05-01) |
| TOOL-02 | Phase 5 | ✅ Complete (05-01) |
| TOOL-03 | Phase 5 | ✅ Complete (05-01) |
| TOOL-04 | Phase 5 | ✅ Complete (05-02) |
| CHAN-01 | Phase 6 | Pending |
| CHAN-02 | Phase 6 | Pending |
| CHAN-03 | Phase 6 | Pending |
| CHAN-04 | Phase 6 | Pending |
| IMSG-01 | Phase 6 | Pending |
| IMSG-02 | Phase 6 | Pending |
| IMSG-03 | Phase 6 | Pending |
| IMSG-04 | Phase 6 | Pending |
| QQ-01 | Phase 7 | Pending |
| QQ-02 | Phase 7 | Pending |
| QQ-03 | Phase 7 | Pending |
| QQ-04 | Phase 7 | Pending |
| QQ-05 | Phase 7 | Pending |
| QQ-06 | Phase 7 | Pending |
| NOTIF-01 | Phase 8 | Pending |
| NOTIF-02 | Phase 8 | Pending |
| NOTIF-03 | Phase 8 | Pending |
| NOTIF-04 | Phase 8 | Pending |
| NOTIF-05 | Phase 8 | Pending |
| REMIND-01 | Phase 8 | Pending |
| REMIND-02 | Phase 8 | Pending |
| REMIND-03 | Phase 8 | Pending |

**Coverage:**
- v2 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 for v2.0 milestone*
