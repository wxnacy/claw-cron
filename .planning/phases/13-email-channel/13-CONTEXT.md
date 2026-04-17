# Phase 13: Email Channel - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

实现 SMTP 邮件通知通道，包括：
1. **SMTP 配置** — host, port, username, password, from_email, use_tls
2. **纯文本邮件** — send_text() 发送 plain text 邮件
3. **HTML 邮件** — send_markdown() 将 Markdown 转换为 HTML 发送
4. **多收件人** — 逗号分隔字符串格式，一次发送多人
5. **附件支持** — 文件路径方式附加文件

不包括：邮件模板（EMAIL-F01）、Markdown 转 HTML 高级渲染（EMAIL-F02）、发送状态追踪（EMAIL-F03）— 延后到后续阶段。

</domain>

<decisions>
## Implementation Decisions

### 收件人格式

- **D-01:** 使用直接邮箱地址格式
  - `recipient = "user@example.com"` 或 `"user1@ex.com, user2@ex.com"`
  - 简单直观，符合邮件使用习惯
  - 不复用 `c2c:` 前缀模式

### 附件处理

- **D-02:** 仅支持文件路径方式
  - `attachments` 参数为 `list[str]` 文件路径列表
  - 适合任务执行后附加日志文件场景
  - 不支持内存数据（bytes）附件

### Markdown 转 HTML

- **D-03:** send_markdown() 使用 markdown 库转换为 HTML
  - 使用 `markdown` Python 库进行转换
  - 生成 `multipart/alternative` 邮件（包含 text 和 HTML 部分）
  - 实现 send_markdown 的真正意义，而非直接发送原始 HTML

### 多收件人处理

- **D-04:** 使用逗号分隔字符串
  - `recipient = "a@example.com, b@example.com"`
  - 一次 SMTP 发送，所有收件人在同一封邮件
  - 保持与 MessageChannel 接口一致的单一 recipient 参数

### SMTP 凭证验证

- **D-05:** `channels add email` 发送测试邮件验证
  - 向配置的 from_email 地址发送验证邮件
  - 验证完整的发送流程（连接、认证、发送）
  - 测试邮件内容标明为验证邮件

### 配置字段

- **D-06:** SMTP 配置包含基础字段：
  - `host` — SMTP 服务器地址
  - `port` — SMTP 端口（默认 587）
  - `username` — 认证用户名
  - `password` — 认证密码
  - `from_email` — 发件人邮箱地址
  - `use_tls` — 是否使用 TLS（默认 true）
  - `enabled` — 是否启用

### Claude's Discretion

- EmailChannel 类的具体实现细节
- 错误处理和重试逻辑
- 邮件主题格式（默认使用任务名称）
- 配置状态检查 `get_channel_status` 的 email 特定逻辑

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，MessageResult, ChannelConfig
- `src/claw_cron/channels/feishu.py` — FeishuChannel 参考实现（配置类、验证、错误处理）
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY 注册表
- `src/claw_cron/channels/exceptions.py` — 通道异常类
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, verify）
- `src/claw_cron/config.py` — 配置加载/保存

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束（aiosmtplib 异步 SMTP）
- `.planning/REQUIREMENTS.md` — EMAIL-01 至 EMAIL-05

### 调研文档
- `.planning/research/channels.md` — 消息通道研究报告

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MessageChannel` 抽象基类 — 定义 send_text/send_markdown 接口
- `FeishuChannel` 实现 — 完整的配置类、验证逻辑、错误处理可参考
- `pydantic-settings` — 配置类模式
- `CHANNEL_REGISTRY` — 通道注册表
- `channels add` 流程 — Phase 11 已实现交互式选择
- `get_channel_status()` — 状态检查函数

### Established Patterns
- pydantic-settings 配置类 — 继承 ChannelConfig
- httpx AsyncClient — 异步 HTTP 客户端（用于验证 API）
- Rich console 状态显示 — 凭证验证进度
- InquirerPy 交互 — 通道选择和确认

### Integration Points
- `channels/__init__.py` — 注册 EmailChannel 到 CHANNEL_REGISTRY
- `cmd/channels.py:add()` — 新增 email 通道配置流程
- `cmd/channels.py:verify()` — 新增 email verify 支持
- `channels/__init__.py:get_channel_status()` — 扩展 email 状态检查

</code_context>

<specifics>
## Specific Ideas

- 邮件通道配置示例：
  ```yaml
  channels:
    email:
      enabled: true
      host: "smtp.qq.com"
      port: 587
      username: "user@qq.com"
      password: "authorization_code"
      from_email: "user@qq.com"
      use_tls: true
      created_at: "2026-04-17T10:00:00"
  ```

- 使用示例：
  ```python
  from claw_cron.channels import get_channel

  channel = get_channel("email")
  # 发送纯文本
  result = await channel.send_text(
      "user@example.com",
      "任务执行完成"
  )
  # 发送 Markdown（自动转 HTML）
  result = await channel.send_markdown(
      "user1@ex.com, user2@ex.com",
      "# 报告\n- 状态: **成功**"
  )
  ```

- 配置验证流程：
  ```
  $ claw-cron channels add
  选择通道类型: email
  SMTP Host: smtp.qq.com
  SMTP Port [587]: 587
  Username: user@qq.com
  Password: ********
  From Email: user@qq.com
  Use TLS [Y/n]: Y

  正在发送验证邮件...
  ✓ 验证邮件已发送到 user@qq.com
  ✓ 通道 'email' 配置完成
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-email-channel*
*Context gathered: 2026-04-17*
