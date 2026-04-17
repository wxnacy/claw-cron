# Feature Research

**Domain:** claw-cron 微信通道 & Capture 增强
**Researched:** 2026-04-17
**Confidence:** MEDIUM

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| 微信通道配置 | 与 QQ/飞书/邮件通道一致的配置流程 | MEDIUM | 需要企业微信应用凭证（corp_id, agent_id, secret） |
| 微信文本消息发送 | 所有其他通道都支持文本消息 | LOW | 使用企业微信应用消息 API |
| 用户标识获取 (userid) | 其他通道都有 capture 流程获取 openid | HIGH | 企业微信需要用户授权或管理员查询 |
| capture 交互式列表 | 当前 capture 命令仅支持参数选择通道 | LOW | 使用 InquirerPy 实现列表选择 |
| add 后自动 capture | QQ/飞书通道已有此模式（--capture-openid） | LOW | 验证成功后提示执行 capture |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 微信 Markdown 消息 | 企业微信支持 markdown_v2，增强通知格式 | MEDIUM | 支持1-6级标题、代码块、表格等 |
| 微信图片/文件消息 | 通知中包含截图、日志文件等附件 | MEDIUM | 需要先上传素材获取 media_id |
| 微信模板卡片消息 | 更专业的通知展示（文本通知型、图文展示型） | HIGH | 需要设计模板内容结构 |
| capture 进度反馈 | 显示捕获等待状态、成功提示 | LOW | 使用 Rich console.status() |
| 自动 userid 映射 | 通过手机号/邮箱自动查找用户 userid | HIGH | 需要通讯录管理权限 |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Webhook 群机器人 | 配置简单，只需 webhook URL | 只能发群消息，无法私聊；安全性低（URL 泄露风险） | 使用企业微信应用消息 API，支持私聊 |
| 个人微信机器人 | 用户使用个人微信发送消息 | 违反微信服务条款，账号封禁风险 | 企业微信是官方认可的企业通知通道 |
| 微信消息接收/回复 | 双向交互、远程控制命令 | 需要服务器接收回调，增加复杂度；超出项目范围 | 保持单向通知模式，符合项目定位 |
| 自动添加用户到通讯录 | 简化用户标识获取流程 | 需要通讯录写权限，安全风险高 | 使用现有 capture 模式：用户主动发送消息 |

## Feature Dependencies

```
微信通道基础实现
    ├──requires──> 企业微信应用配置 (corp_id, agent_id, secret)
    ├──requires──> MessageChannel 抽象实现 (send_text, send_markdown)
    └──requires──> access_token 获取逻辑

用户标识获取 (capture 微信)
    ├──requires──> 微信通道基础实现
    ├──requires──> 企业微信 WebSocket 或回调服务器
    └──requires──> 用户与机器人交互（发送消息）

capture 交互式增强
    └──requires──> InquirerPy select prompt (已有 prompt_channel_select)

add 后自动 capture
    ├──requires──> capture 交互式增强
    └──requires──> 验证成功后调用 capture 流程

微信图片/文件消息
    └──requires──> 素材上传接口（获取 media_id）

自动 userid 映射
    ├──conflicts──> 最小权限原则（需要通讯录管理权限）
    └──requires──> 手机号/邮箱输入交互
```

### Dependency Notes

- **微信通道基础实现 requires MessageChannel 抽象:** 需要实现 `send_text()` 和 `send_markdown()` 方法，遵循现有通道模式
- **capture 微信 requires WebSocket/回调服务器:** 企业微信有两种接收消息方式：WebSocket 长连接（类似 QQ Bot）或回调服务器（类似飞书 Webhook）
- **add 后自动 capture requires capture 交互式增强:** 当前 `capture` 命令通过 `--channel-type` 参数选择通道，需要改为交互式列表以提供更好的用户体验
- **自动 userid 映射 conflicts with 最小权限原则:** 通讯录管理权限属于敏感权限，企业通常不会轻易授予，建议保持现有 capture 模式（用户主动交互）

## MVP Definition (v2.4 Milestone)

### Launch With

Minimum viable product — what's needed to validate the concept.

- [x] 微信通道基础实现 — 与其他通道保持一致的配置和发送体验
  - 配置：corp_id, agent_id, secret
  - 发送：send_text() 私聊消息
  - 验证：验证凭证获取 access_token
- [x] capture 交互式增强 — 提升用户体验
  - 使用 InquirerPy 列表选择通道
  - 支持微信通道（如实现）
- [x] add 后自动 capture — 简化配置流程
  - 验证成功后提示执行 capture
  - 可选：添加 `--capture-openid` 参数（与 QQ/飞书一致）

### Add After Validation (v2.x)

Features to add once core is working.

- [ ] 微信 Markdown 消息 — 增强通知格式
- [ ] capture 微信用户标识 — 获取 userid 用于私聊通知
- [ ] 微信图片/文件消息 — 支持附件通知

### Future Consideration (v3+)

Features to defer until product-market fit is established.

- [ ] 微信模板卡片消息 — 需要设计模板结构
- [ ] 自动 userid 映射 — 需要评估权限需求
- [ ] 多企业微信应用支持 — 多租户场景

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 微信通道基础实现 | HIGH | MEDIUM | P1 |
| capture 交互式增强 | MEDIUM | LOW | P1 |
| add 后自动 capture | MEDIUM | LOW | P1 |
| 微信 Markdown 消息 | MEDIUM | MEDIUM | P2 |
| capture 微信用户标识 | HIGH | HIGH | P2 |
| 微信图片/文件消息 | LOW | MEDIUM | P3 |
| 微信模板卡片消息 | LOW | HIGH | P3 |
| 自动 userid 映射 | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for v2.4 milestone
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | QQ Bot | 飞书 | 企业微信 | 我们的实现 |
|---------|--------|------|---------|-----------|
| 配置方式 | app_id + client_secret | app_id + app_secret | corp_id + agent_id + secret | 统一交互式配置 |
| 用户标识 | openid (WebSocket) | open_id (WebSocket) | userid (WebSocket/回调) | capture 命令获取 |
| 消息类型 | text, markdown | text, markdown, card | text, markdown, card, image, file | text, markdown (基础) |
| 私聊支持 | ✅ | ✅ | ✅ | ✅ (应用消息 API) |
| 群聊支持 | ✅ | ✅ | ✅ (webhook) | ❌ (仅私聊，避免 webhook 安全风险) |
| Markdown | 基础 | 完整 | markdown_v2 | 按通道能力适配 |

## Sources

- **企业微信官方文档 (HIGH confidence):**
  - 发送应用消息: https://developer.work.weixin.qq.com/document/path/90236
  - 消息推送配置: https://developer.work.weixin.qq.com/document/path/91770
  - 消息类型：text, image, voice, video, file, textcard, news, mpnews, markdown, miniprogram_notice, template_card

- **项目现有实现 (HIGH confidence):**
  - QQ Bot 通道: `src/claw_cron/channels/qqbot.py` — WebSocket 捕获 openid
  - 飞书通道: `src/claw_cron/channels/feishu.py` — WebSocket 捕获 open_id
  - channels 命令: `src/claw_cron/cmd/channels.py` — 配置、验证、捕获流程
  - prompt 工具: `src/claw_cron/prompt.py` — InquirerPy 交互式选择

- **Web 搜索 (MEDIUM confidence):**
  - 企业微信机器人功能详解 (2025): https://www.sohu.com/a/1010447425_122472236
  - 企业微信应用消息发送 Python 实践: https://blog.csdn.net/m0_65003953/article/details/144514272

---
*Feature research for: claw-cron v2.4 微信通道 & Capture 增强*
*Researched: 2026-04-17*
