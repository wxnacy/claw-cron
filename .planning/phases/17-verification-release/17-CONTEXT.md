# Phase 17: Verification & Release - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

验证所有功能正常工作，发布版本 0.2.1，包括：
1. **端到端验证** — 所有通道（QQ, 飞书, 邮件, 企业微信, iMessage）的 add/capture/send/verify/delete 全流程手动验证
2. **自动化测试** — 重点边界测试（错误处理、超时、不支持 capture 的通道、收件人解析）
3. **文档更新** — README.md（新增通道使用示例 + 配置说明）+ CHANGELOG.md + 版本号升级
4. **版本升级** — pyproject.toml 和 __about__.py 版本号升级到 0.2.1

不包括：PyPI 发布、git tag、新功能开发。

</domain>

<decisions>
## Implementation Decisions

### 验证策略

- **D-01:** 核心流程手动验证 + 边界情况自动化测试
  - 手动验证：每个通道的 add → capture → send → verify → delete 全流程，覆盖真实 API 调用
  - 自动化测试：重点测试边界情况（错误处理、超时、不支持 capture 的通道、收件人解析）
  - 手动测试更可靠，但自动化测试可重复捕获回归
- **D-02:** 全流程验证 — 所有通道 × 所有操作
  - 5 个通道（imessage, qqbot, feishu, email, wecom）均需验证
  - 每个通道验证 add/capture（如支持）/send/verify/delete
  - imessage 不支持 capture，email 不支持 capture
  - wecom capture 为手动输入 userid
- **D-03:** 自动化测试写 1-2 个测试文件，覆盖核心边界
  - 不追求全面覆盖，聚焦最容易出问题的边界
  - 测试场景：错误处理（配置缺失、API 错误）、超时机制、不支持 capture 的通道提示、收件人格式解析
  - 从 tests/ 目录新建，使用 pytest

### 文档更新范围

- **D-04:** 全量文档更新 — README + CHANGELOG + 版本号
  - README.md 更新：新增企业微信通道配置说明和使用示例、capture 交互改进说明
  - CHANGELOG.md 新建：记录 v0.2.1 所有变更（Phase 14-16 的功能）
  - pyproject.toml / __about__.py 版本号升级到 0.2.1

### 发布流程

- **D-05:** 仅升级版本号，不创建 git tag、不发布到 PyPI
  - pyproject.toml 和 __about__.py 版本号更新为 0.2.1
  - 不创建 v0.2.1 git tag
  - 不发布到 PyPI

### Claude's Discretion

- 手动验证的具体步骤和顺序
- 自动化测试的测试框架配置和 fixture 设计
- README 文档的具体结构和措辞
- CHANGELOG 的分组方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（验证目标）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，supports_capture, capture_openid()
- `src/claw_cron/channels/qqbot.py` — QQBotChannel 实现
- `src/claw_cron/channels/feishu.py` — FeishuChannel 实现
- `src/claw_cron/channels/email.py` — EmailChannel 实现
- `src/claw_cron/channels/wecom.py` — WeComChannel 实现（Phase 16 新增）
- `src/claw_cron/channels/imessage.py` — IMessageChannel 实现
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY, get_channel(), get_channel_status()
- `src/claw_cron/channels/exceptions.py` — 通道异常类
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, capture, verify, delete, list）
- `src/claw_cron/prompt.py` — prompt_channel_select(), prompt_capture_channel_select(), prompt_confirm()
- `src/claw_cron/contacts.py` — Contact, save_contact(), resolve_recipient()
- `src/claw_cron/__about__.py` — 当前版本号 "0.1.0"
- `pyproject.toml` — 项目配置

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — VERS-01 及所有 v2.4 需求

### 相关阶段上下文
- `.planning/phases/14-architecture-enhancement/14-CONTEXT.md` — Capture 抽象层设计
- `.planning/phases/15-capture-interaction/15-CONTEXT.md` — Capture 交互改进
- `.planning/phases/16-wechat-channel/16-CONTEXT.md` — 企业微信通道实现

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pytest` — 项目已配置为开发依赖
- `CHANNEL_REGISTRY` — 可遍历所有通道进行验证
- `get_channel_status()` — 检查通道配置状态
- 各通道的 `send_text()` / `send_markdown()` — 消息发送接口
- 各通道的 `capture_openid()` — capture 接口（qqbot/feishu/wecom 支持）
- `parse_recipient()` — 收件人格式解析

### Established Patterns
- httpx AsyncClient — 异步 HTTP（可用于测试 mock）
- pydantic-settings 配置类 — 通道配置验证
- Rich console — 输出格式化
- InquirerPy — 交互式选择
- tenacity retry — 重试机制

### Integration Points
- `tests/` — 新建测试目录
- `pyproject.toml` — 版本号升级
- `src/claw_cron/__about__.py` — 版本号升级
- `README.md` — 文档更新
- `CHANGELOG.md` — 新建变更日志

### 当前项目状态
- 版本号：0.1.0（需升级到 0.2.1）
- 5 个通道已实现：imessage, qqbot, feishu, email, wecom
- 3 个通道支持 capture：qqbot, feishu, wecom（手动输入）
- capture 交互已改进：交互式列表选择、add 后自动询问、状态反馈、超时机制
- 无现有测试文件

</code_context>

<specifics>
## Specific Ideas

### 手动验证清单示例
```
[ ] imessage: add → send_text → verify → delete
[ ] qqbot: add → capture → send_text → send_markdown → verify → delete
[ ] feishu: add → capture → send_text → send_markdown → verify → delete
[ ] email: add → send_text → send_markdown → verify → delete
[ ] wecom: add → capture(手动输入) → send_text → send_markdown → verify → delete
```

### 自动化测试场景示例
```python
# tests/test_channels.py
- test_capture_unsupported_channel() — imessage/email 调用 capture_openid 抛出 NotImplementedError
- test_capture_timeout() — capture 超时抛出 ChannelError
- test_recipient_parsing() — "c2c:openid" 格式解析
- test_channel_config_missing() — 配置缺失时抛出 ChannelConfigError
- test_wecom_token_expired() — token 过期自动刷新
```

### CHANGELOG 格式
```markdown
# Changelog

## 0.2.1 (2026-04-17)

### Added
- 企业微信应用消息通知通道 (WeChat Work)
- channels capture 交互式列表选择通道
- channels add 验证成功后自动询问是否执行 capture
- capture 流程实时状态反馈和 5 分钟超时机制
- MessageChannel supports_capture 属性和 capture_openid() 抽象方法

### Changed
- capture 命令移除 --channel-type 参数，改为交互式选择
- add 命令移除 --capture-openid 参数，改为自动询问
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-verification-release*
*Context gathered: 2026-04-17*
