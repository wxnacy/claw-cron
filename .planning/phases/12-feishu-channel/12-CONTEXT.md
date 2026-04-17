# Phase 12: Feishu Channel - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

实现飞书私聊消息通知通道，包括：
1. **凭证配置** — app_id, app_secret 配置与验证
2. **消息发送** — 通过 open_id 发送私聊文本和 Markdown 消息
3. **Token 管理** — tenant_access_token 自动获取和刷新
4. **频率限制** — 5 QPS/用户限制处理
5. **OpenID 获取** — 交互式 capture 命令获取用户 open_id

不包括：群聊消息、富媒体附件、交互式卡片（延后到后续阶段）。

</domain>

<decisions>
## Implementation Decisions

### OpenID 获取方式

- **D-01:** 采用交互式 `capture` 命令，与 QQ Bot 模式一致
  - 启动事件监听，等待用户给机器人发送消息
  - 自动捕获 open_id 并保存到 contacts.yaml
- **D-02:** 用户也可手动配置 open_id（备用方式）

### SDK 选择

- **D-03:** 使用 `lark-oapi` 官方 SDK
  - 自动 token 管理（tenant_access_token）
  - 类型安全的 API 调用
  - 完善的错误处理
- **D-04:** SDK 处理 tenant_access_token 生命周期，无需手动实现 token 缓存

### 频率限制处理

- **D-05:** 使用 tenacity 重试机制，与 QQBotChannel 保持一致
  - `stop_after_attempt(3)` — 最多重试 3 次
  - `wait_exponential` — 指数退避等待
  - 识别飞书频率限制错误码自动重试

### 收件人格式与消息类型

- **D-06:** 收件人格式使用 `c2c:OPENID`
  - 与 QQ Bot 格式一致
  - 复用现有 `parse_recipient` 函数
  - 未来扩展群聊时使用 `group:OPENID`
- **D-07:** 消息类型支持文本和 Markdown
  - `send_text()` — 纯文本消息
  - `send_markdown()` — Markdown 消息，不支持时回退纯文本

### 配置验证

- **D-08:** `channels add feishu` 保存前验证凭证
  - 调用飞书 API 获取 tenant_access_token 验证有效性
  - 验证通过才保存配置
- **D-09:** 新增 `channels verify feishu` 命令
  - 独立验证飞书通道凭证

### Claude's Discretion

- FeishuChannel 类的具体实现细节
- capture 命令的事件监听实现方式
- 频率限制错误码的识别逻辑
- 配置状态检查 `get_channel_status` 的飞书特定逻辑

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，MessageResult, ChannelConfig
- `src/claw_cron/channels/qqbot.py` — QQBotChannel 参考实现（token 管理、重试、收件人解析）
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY 注册表
- `src/claw_cron/channels/exceptions.py` — 通道异常类
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, capture, verify）
- `src/claw_cron/config.py` — 配置加载/保存
- `src/claw_cron/contacts.py` — 联系人管理
- `src/claw_cron/prompt.py` — 交互提示工具

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — FEISHU-01 至 FEISHU-05

### 调研文档
- `.planning/research/channels.md` — 消息通道研究报告，包含飞书集成建议

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MessageChannel` 抽象基类 — 定义 send_text/send_markdown 接口
- `QQBotChannel` 实现 — 完整的 token 管理、重试机制、错误处理可参考
- `parse_recipient()` — 收件人格式解析，可直接复用
- `tenacity` 重试装饰器 — 频率限制处理模式
- `CHANNEL_REGISTRY` — 通道注册表，新增飞书通道注册
- `capture` 命令框架 — 可复用交互式 open_id 捕获流程

### Established Patterns
- pydantic-settings 配置类 — QQBotConfig 模式
- httpx AsyncClient — 异步 HTTP 客户端
- Rich console 状态显示 — 凭证验证进度
- InquirerPy 交互 — 通道选择和确认

### Integration Points
- `channels/__init__.py` — 注册 FeishuChannel 到 CHANNEL_REGISTRY
- `cmd/channels.py:add()` — 新增 feishu 通道配置流程
- `cmd/channels.py:capture()` — 新增飞书 capture 支持
- `cmd/channels.py:verify()` — 新增飞书 verify 支持
- `cmd/channels.py:list_channels()` — 扩展 get_channel_status 支持飞书

</code_context>

<specifics>
## Specific Ideas

- 飞书通道配置示例：
  ```yaml
  channels:
    feishu:
      enabled: true
      app_id: "cli_xxx"
      app_secret: "xxx"
      created_at: "2026-04-17T10:00:00"
  ```

- 收件人使用示例：
  ```python
  channel = get_channel("feishu")
  result = await channel.send_text("c2c:ou_xxx", "任务执行完成")
  result = await channel.send_markdown("c2c:ou_xxx", "# 报告\n- 状态: **成功**")
  ```

- capture 命令流程：
  ```
  $ claw-cron channels capture --channel-type feishu --alias me
  正在连接飞书事件服务...
  请向机器人发送任意消息以捕获您的 open_id
  按 Ctrl+C 取消

  ✓ OpenID 捕获成功: ou_xxx
  ✓ 联系人已保存为 'me'
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-feishu-channel*
*Context gathered: 2026-04-17*
