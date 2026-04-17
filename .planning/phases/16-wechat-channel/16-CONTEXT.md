# Phase 16: WeChat Channel - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

实现企业微信应用消息通知通道，包括：
1. **凭证配置** — corp_id, agent_id, secret 配置与验证
2. **消息发送** — 通过 userid 发送私聊文本和 Markdown 消息
3. **Token 管理** — access_token 自动获取、内存缓存、过期刷新
4. **Capture** — 先支持手动输入 userid，后续再加 HTTP 回调方式
5. **频率限制** — tenacity 重试机制处理 API 限流

不包括：企业微信群机器人 Webhook、微信图片/文件消息、模板卡片消息、个人微信 API、HTTP 回调 capture（延后）。

</domain>

<decisions>
## Implementation Decisions

### Capture 实现方式

- **D-01:** 先支持手动输入 userid，后续再加 HTTP 回调方式
  - 企业微信没有类似 QQ Bot 的 WebSocket 推送服务
  - HTTP 回调需要公网 URL，配置复杂度高
  - 手动输入最简单：用户在企业微信管理后台查看自己的 userid，在 capture 命令中输入
  - 回调方式记录为 deferred idea，后续 phase 实现
- **D-02:** capture 流程优先尝试回调方式（未来），失败则引导手动输入
  - 当回调方式实现后，capture 优先尝试自动捕获
  - 未配置回调或捕获失败时，提示用户手动输入 userid
  - 当前 phase 仅实现手动输入分支
- **D-03:** 手动输入 capture 时提供引导提示
  - 提示用户如何查看自己的企业微信 userid（管理后台路径）
  - 输入后验证 userid 格式（非空字符串）
  - 保存为 Contact，与其他通道 capture 行为一致

### 消息类型与格式

- **D-04:** 支持文本和 Markdown 两种消息类型
  - `send_text()` — 纯文本消息（msgtype=text）
  - `send_markdown()` — Markdown 消息（msgtype=markdown）
  - 满足 REQUIREMENTS WECHAT-02 和 WECHAT-03
- **D-05:** Markdown 不支持时回退纯文本
  - 企业微信 Markdown 支持有限（仅标题、加粗、引用、代码，不支持图片/链接/表格）
  - 发送失败时自动回退为纯文本消息
  - 与 QQBot/Feishu 的 Markdown 回退策略一致
- **D-06:** 收件人格式复用 `c2c:userid` 格式
  - 与 QQBot（c2c:openid）、Feishu（c2c:openid）保持一致
  - `parse_recipient()` 解析时提取冒号后的 userid
  - 企业微信私聊消息使用 userid 标识用户

### Token 管理

- **D-07:** 复用 QQBot 的 TokenInfo 模式，在 WeComChannel 内独立实现
  - `TokenInfo` dataclass：存储 access_token + expires_at
  - `_get_access_token()`：检查缓存是否过期，过期则通过 HTTP 重新获取
  - token 存储在实例变量 `self._token` 中
  - 不抽取公共 TokenManager，避免影响已完成 phase
- **D-08:** access_token 仅内存缓存，不持久化
  - 进程重启后重新获取 access_token
  - 与 QQBot 模式一致
  - 简单可靠，避免并发安全和缓存一致性问题
- **D-09:** 企业微信 access_token 获取 API
  - `GET https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=ID&corpsecret=SECRET`
  - 返回 access_token + expires_in（7200 秒）
  - 提前 60 秒刷新（buffer），与 QQBot 的 buffer_seconds 一致

### 频率限制与错误处理

- **D-10:** 复用 tenacity 重试模式
  - `stop_after_attempt(3)` — 最多重试 3 次
  - `wait_exponential` — 指数退避等待
  - 定义 `WeComRateLimitError`，仅对限流错误重试
  - 与 QQBot/Feishu 的重试策略保持一致
- **D-11:** channels add wecom 时验证凭证
  - 调用 access_token API 验证 corpid + secret 有效性
  - 验证通过才保存配置
  - 与 QQBot 的 add 验证模式一致
- **D-12:** 配置字段：corp_id, agent_id, secret
  - `corp_id` — 企业 ID
  - `agent_id` — 应用 AgentId
  - `secret` — 应用 Secret
  - 环境变量前缀：`CLAW_CRON_WECOM_`

### Claude's Discretion

- WeComChannel 类的具体实现细节
- WeComConfig 配置类字段和验证
- 企业微信 API 错误码识别和映射
- capture 手动输入的交互提示语
- 配置状态检查 `get_channel_status` 的 wecom 特定逻辑

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，supports_capture, capture_openid(), ChannelConfig
- `src/claw_cron/channels/qqbot.py` — QQBotChannel 参考实现（TokenInfo 模式、tenacity 重试、Markdown 回退）
- `src/claw_cron/channels/feishu.py` — FeishuChannel 参考实现（SDK 模式、capture 流程）
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY, get_channel(), get_channel_status()
- `src/claw_cron/channels/exceptions.py` — ChannelError, ChannelAuthError, ChannelSendError, ChannelConfigError
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, capture, verify, delete, list）
- `src/claw_cron/prompt.py` — prompt_channel_select(), prompt_capture_channel_select(), prompt_confirm()
- `src/claw_cron/contacts.py` — Contact, save_contact(), resolve_recipient()
- `src/claw_cron/config.py` — load_config(), save_config()

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — WECHAT-01 至 WECHAT-05

### 相关阶段上下文
- `.planning/phases/14-architecture-enhancement/14-CONTEXT.md` — Capture 抽象层设计
- `.planning/phases/15-capture-interaction/15-CONTEXT.md` — Capture 交互改进
- `.planning/phases/12-feishu-channel/12-CONTEXT.md` — 飞书通道实现参考
- `.planning/phases/13-email-channel/13-CONTEXT.md` — 邮件通道（不需要 capture 的参考）

### 企业微信 API 文档
- 企业微信应用消息发送：`https://developer.work.weixin.qq.com/document/path/90236`
- 企业微信获取 access_token：`https://developer.work.weixin.qq.com/document/path/91039`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MessageChannel` 抽象基类 — 定义 send_text/send_markdown/supports_capture/capture_openid 接口
- `QQBotChannel` TokenInfo 模式 — 可直接复制用于企业微信 token 管理
- `parse_recipient()` — 收件人格式解析，可直接复用
- `tenacity` 重试装饰器 — 频率限制处理模式
- `CHANNEL_REGISTRY` — 通道注册表，新增 wecom 注册即可自动出现在交互选择中
- `Contact` / `save_contact()` — 联系人保存机制已存在
- `prompt_channel_select()` / `prompt_capture_channel_select()` — 新通道注册后自动出现在选择列表

### Established Patterns
- pydantic-settings 配置类 — QQBotConfig 模式，继承 BaseSettings + ChannelConfig
- httpx AsyncClient — 异步 HTTP 客户端（已有依赖）
- Rich console.status — 凭证验证进度
- InquirerPy 交互 — 通道选择和确认
- TokenInfo + _get_access_token() — 内存缓存 token 管理模式
- tenacity retry — 频率限制重试模式

### Integration Points
- `channels/wecom.py` — 新建 WeComConfig + WeComChannel
- `channels/__init__.py` — 注册 WeComChannel 到 CHANNEL_REGISTRY + get_channel_status() 添加 wecom 分支
- `cmd/channels.py` — add/capture/verify/delete/list 命令添加 wecom 支持
- `CHANNEL_DISPLAY_NAMES` — 添加 "wecom" → "企业微信"

### 企业微信 API 关键信息
- Token 获取：`GET https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=ID&corpsecret=SECRET`
- 发送消息：`POST https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=TOKEN`
- 消息体格式：`{ "touser": "userid", "msgtype": "text", "agentid": 1000002, "text": { "content": "..." } }`
- 无官方 Python SDK，使用 httpx 直接调用 REST API

</code_context>

<specifics>
## Specific Ideas

### 企业微信通道配置示例
```yaml
channels:
  wecom:
    enabled: true
    corp_id: "ww1234567890"
    agent_id: 1000002
    secret: "xxx"
    created_at: "2026-04-17T10:00:00"
```

### 使用示例
```python
from claw_cron.channels import get_channel

channel = get_channel("wecom")
# 发送纯文本
result = await channel.send_text("c2c:zhangsan", "任务执行完成")
# 发送 Markdown
result = await channel.send_markdown("c2c:zhangsan", "# 报告\n- 状态: **成功**")
```

### Capture 手动输入流程
```
$ claw-cron channels capture
选择通道类型: 企业微信 (wecom)

请输入你的企业微信 userid
（可在企业微信管理后台 → 通讯录 中查看）
UserID: zhangsan

✓ UserID 已捕获: zhangsan
✓ 联系人已保存为 'me'
```

### 配置验证流程
```
$ claw-cron channels add
选择通道类型: 企业微信 (wecom)
Corp ID: ww1234567890
Agent ID: 1000002
Secret: ********

⠋ 正在验证凭证...
✓ 凭证验证成功
✓ 通道 'wecom' 配置完成

是否立即获取用户 ID (capture)? [Y/n]: y

请输入你的企业微信 userid
...
```

</specifics>

<deferred>
## Deferred Ideas

- **HTTP 回调 capture** — 企业微信 capture 的自动捕获方式，需配置回调 URL（公网可访问），复杂度高，延后到后续 phase 实现。实现时优先尝试回调自动捕获，失败则引导手动输入。

</deferred>

---

*Phase: 16-wechat-channel*
*Context gathered: 2026-04-17*
