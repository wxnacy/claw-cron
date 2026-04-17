# Project Research Summary

**Project:** claw-cron 微信通道 & Capture 增强
**Domain:** Message Channel Extension for Cron Task Manager
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

claw-cron 是一个 AI 驱动的定时任务管理器，需要新增企业微信通知通道并优化 capture 流程。研究发现三种微信集成方案，**推荐使用企业微信机器人 Webhook**，因其无需认证、配置简单、无封号风险，完美契合项目的通知场景。个人微信方案（itchat/WeChatBot）存在极高的账号封禁风险，不应采用。

架构层面，关键发现是企业微信 **不需要 capture 流程**——UserID 在企业通讯录中已知，这简化了实现。主要风险包括：API 频率限制（需实现重试+熔断+降级）、capture 流程用户体验差（需改进交互指引）、以及通道选择混淆（需统一 capture 模板）。

建议分三个阶段实施：Phase 1 重构架构（为 capture 建立统一抽象）、Phase 2 改进交互（自动询问、友好提示）、Phase 3 实现微信通道（应用消息 API）。此顺序基于依赖关系和风险优先级。

## Key Findings

### Recommended Stack

**核心技术方案：企业微信机器人 Webhook**

相比企业微信应用（需 OAuth2 + UserID 管理）和个人微信（封号风险），Webhook 方案最简单：只需 POST 到 webhook URL，无需认证、无需用户 ID 管理。支持文本、Markdown、图片、新闻等消息类型，频率限制为 20 条/分钟，满足通知场景需求。

**Core technologies:**
- **企业微信机器人 Webhook** — 群通知通道 — 零认证、零用户管理、POST 即用
- **httpx ^0.28.0** — 异步 HTTP 客户端 — 已在 QQBotChannel 验证，支持重试和超时
- **tenacity ^9.0.0** — 重试逻辑 — 已在 qqbot.py 和 feishu.py 使用，处理 API 限流
- **pydantic ^2.0.0** — 配置验证 — 所有通道使用统一的 pydantic-settings 模式

**关键决策：**
- ✅ Webhook 方案用于群通知（无 capture，静态配置）
- ⚠️ 企业微信应用仅当需要私聊时才考虑（需 OAuth2 + UserID）
- ❌ 个人微信方案禁止使用（封号风险不可接受）

### Expected Features

**Table Stakes (用户期望的功能):**
- 微信通道配置 — 与 QQ/飞书/邮件通道一致的交互式配置流程
- 微信文本消息发送 — 使用企业微信应用消息 API 发送私聊通知
- 用户标识获取 (capture) — 其他通道都有 capture 流程，微信需要等效机制
- capture 交互式列表 — 使用 InquirerPy 选择通道，优于命令行参数
- add 后自动 capture — 验证成功后自动提示或触发 capture（QQ/飞书已有）

**Differentiators (竞争优势):**
- 微信 Markdown 消息 — 企业微信支持 markdown_v2，增强通知格式（标题、代码块、表格）
- 微信图片/文件消息 — 通知中包含截图、日志文件等附件
- capture 进度反馈 — 使用 Rich console.status() 显示等待状态
- 自动 userid 映射 — 通过手机号/邮箱自动查找用户 userid（需通讯录权限）

**Defer to v2+:**
- 微信模板卡片消息 — 需要设计模板结构，复杂度高
- 多企业微信应用支持 — 多租户场景，暂无需求
- 个人微信 iLink API — 2026年3月发布，申请条件未知，需验证可用性

### Architecture Approach

现有架构采用通道抽象模式：`MessageChannel` ABC 定义统一接口，`CHANNEL_REGISTRY` 支持动态发现，`get_channel()` 工厂函数实例化通道。微信通道需遵循此模式，关键差异是 **企业微信使用已知 UserID**，无需 WebSocket capture。

**Major components:**
1. **MessageChannel ABC** — 新增 `supports_capture` 属性和 `capture_openid()` 方法，统一 capture 抽象
2. **WechatWorkChannel** — 新建通道类，实现 send_text/send_markdown，设置 `supports_capture = False`
3. **capture 命令统一入口** — 提取 `_capture_openid()` 为通用函数，移除通道特定实现
4. **Token 管理** — 缓存 access_token（7200s 有效期），提前 30 秒刷新

**新建文件:**
- `src/claw_cron/channels/wechat_work.py` — 企业微信 Webhook 通道实现

**修改文件:**
- `src/claw_cron/channels/base.py` — 新增 capture 支持
- `src/claw_cron/channels/qqbot.py` — 实现 `capture_openid()`
- `src/claw_cron/channels/feishu.py` — 实现 `capture_openid()`
- `src/claw_cron/cmd/channels.py` — 统一 capture 逻辑，增加自动询问

### Critical Pitfalls

**Top 5 风险及预防策略:**

1. **个人微信封号风险** — 必须使用企业微信应用 API，禁止 any 个人微信方案（itchat/Hook/协议破解）
2. **群机器人 vs 应用机器人选择错误** — 定时通知场景必须使用应用机器人（支持私聊），群机器人仅用于群广播
3. **API 频率限制导致通知丢失** — 实现 token 缓存 + 指数退避重试 + 熔断降级 + 降级通道（企业微信失败→QQ Bot）
4. **capture 流程用户不知道下一步** — 分步指引 + 带示例的操作说明 + 实时状态反馈 + 超时提示
5. **不同通道 capture 流程不一致** — 统一 capture 模板 + 通道差异对比表 + 状态显示

**Technical Debt Patterns:**
- 直接调用 API 不缓存 token → 频繁获取触发限流（Never acceptable）
- capture 无超时限制 → 用户浪费时间等待（必须设置 5 分钟超时）
- 忽略 webhook 签名验证 → 安全漏洞（生产环境必须验证）
- 日志只记录成功/失败 → 无法诊断问题（必须记录 recipient、error_code、latency）

## Implications for Roadmap

### Phase 1: 架构增强 - Capture 统一抽象

**Rationale:** 为后续功能提供基础架构，避免各通道 capture 逻辑分散

**Delivers:**
- MessageChannel 新增 `supports_capture` 属性和 `capture_openid()` 方法
- QQBotChannel 和 FeishuChannel 重构实现 `capture_openid()`
- 统一的 `_capture_openid()` 入口函数

**Addresses:**
- Table stakes: capture 交互式列表、统一配置流程
- Pitfalls: 不同通道 capture 流程不一致

**Avoids:**
- Pitfall 5: capture 流程用户混淆
- Technical debt: 通道特定实现分散

### Phase 2: Capture 交互改进

**Rationale:** 提升用户体验，减少配置步骤，基于 Phase 1 的统一抽象

**Delivers:**
- add 命令验证成功后自动询问是否 capture
- capture 命令对不支持 capture 的通道给出友好提示
- 实时状态反馈（Rich console.status）
- 超时和重连机制

**Addresses:**
- Table stakes: add 后自动 capture
- Pitfalls: capture 流程用户不知道下一步、网络超时失败

**Uses:**
- Phase 1 的 `supports_capture` 属性判断是否需要 capture
- Phase 1 的统一 `_capture_openid()` 入口

**Avoids:**
- Pitfall 4: 用户不知道下一步操作
- Pitfall 6: capture 永远等待无超时

### Phase 3: WechatWorkChannel 实现

**Rationale:** 核心功能实现，依赖 Phase 1 的架构基础

**Delivers:**
- 新建 `wechat_work.py` 文件，实现 WechatWorkChannel
- WechatConfig 配置类（webhook_url 或 corp_id + agent_id + secret）
- Token 管理和消息发送逻辑
- 注册到 CHANNEL_REGISTRY

**Addresses:**
- Table stakes: 微信通道配置、微信文本消息发送
- Differentiators: 微信 Markdown 消息

**Implements:**
- MessageChannel ABC 的 send_text 和 send_markdown
- API 频率限制处理（重试 + 熔断）

**Avoids:**
- Pitfall 1: 个人微信封号（使用官方 API）
- Pitfall 2: 选择错误（实现应用消息 API，不实现群机器人）
- Pitfall 3: 频率限制未处理

### Phase 4: 测试验证 & 版本升级

**Rationale:** 收尾工作，确保质量

**Delivers:**
- 功能测试（channels add/capture/verify 流程）
- 频率限制测试（模拟高频发送）
- 文档更新（README + PROJECT.md）
- 版本号升级到 0.2.1

**Addresses:**
- "Looks Done But Isn't" Checklist: token 刷新、错误处理、降级通道

### Phase Ordering Rationale

**依赖关系:**
- Phase 2 和 Phase 3 都依赖 Phase 1 的架构抽象
- Phase 2 和 Phase 3 可以并行执行（相互独立）
- Phase 4 最后执行（验证前面阶段）

**架构模式:**
- Phase 1 建立抽象层（MessageChannel capture 支持）
- Phase 2 改进现有流程（channels 命令交互）
- Phase 3 添加新组件（WechatWorkChannel）

**风险规避:**
- Phase 1 避免 capture 逻辑分散的技术债
- Phase 2 避免用户不知道下一步的 UX 问题
- Phase 3 避免频率限制导致通知丢失

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (WechatWorkChannel):** 需要验证微信 iLink API 可用性（2026年3月发布，申请条件未知），可能成为未来私聊通知的替代方案
- **Phase 3 (WechatWorkChannel):** 需要确认是否支持多个 webhook（多个群），recipients 数组格式需设计
- **Phase 3 (WechatWorkChannel):** Markdown V2 支持需验证客户端版本兼容性

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (架构增强):** MessageChannel ABC 扩展是标准的 Python 抽象类模式，已有 QQBotChannel 和 FeishuChannel 参考实现
- **Phase 2 (交互改进):** InquirerPy 和 Rich console 是成熟的 CLI 工具，使用方式明确

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | 企业微信官方文档详细（2025-08/09 更新），httpx/tenacity 已在项目中验证 |
| Features | MEDIUM | Table stakes 基于现有通道模式推断，Differentiators 需要实际使用反馈 |
| Architecture | HIGH | 现有架构清晰（MessageChannel ABC + CHANNEL_REGISTRY），扩展点明确 |
| Pitfalls | MEDIUM | 频率限制和封号风险基于社区实践，部分 WebSearch 结果未验证 |

**Overall confidence:** HIGH

**理由:**
- 官方文档支持（企业微信开发者中心）提供高置信度的 API 规范
- 现有代码库提供验证过的架构模式（QQBotChannel、FeishuChannel）
- 主要不确定性在于微信 iLink API 可用性，但这不影响 MVP 实现

### Gaps to Address

**需在实现阶段验证:**

1. **微信 iLink API 可用性** — 2026年3月文章提到官方开放个人号 Bot API，需要：
   - 查阅官方申请流程和条件
   - 验证是否支持私聊消息发送
   - 评估是否适合 claw-cron 的通知场景
   - 如适用，可能成为 Phase 3 的替代方案

2. **Webhook URL 管理** — 当前设计存储在 config.yaml，需要：
   - 确认是否支持多个 webhook（通知多个群）
   - 设计 recipients 数组格式：`["webhook:KEY1", "webhook:KEY2"]` vs full URLs

3. **Markdown V2 支持** — 文档提到 markdown_v2（4096字节），需要：
   - 确认是否需要支持 markdown_v2（vs markdown）
   - 验证客户端版本兼容性要求

4. **飞书联系人列表获取** — Phase 4 需要实现交互式列表选择，但：
   - 飞书 API 是否支持获取最近联系人列表未验证
   - 需要在 Phase 4 实现时调研 API 能力

**处理方式:**
- Phase 3 planning 时使用 `/gsd-research-phase` 深入调研微信 iLink API
- Phase 3 实现时设计灵活的 recipients 格式，支持未来扩展
- Phase 4 实现前验证飞书 API 能力，如不支持则降级到手动输入

## Sources

### Primary (HIGH confidence)

- **企业微信开发者中心 - 消息推送配置说明** (https://developer.work.weixin.qq.com/document/path/91770) — Webhook API 规范、消息类型、频率限制。最后更新: 2025-08-07。
- **企业微信开发者中心 - 发送应用消息** (https://developer.work.weixin.qq.com/document/path/90236) — 应用消息 API、touser 格式、userid 获取方法。最后更新: 2025-09-24。
- **企业微信开发者中心 - 专区程序SDK下载** (https://developer.work.weixin.qq.com/document/path/100250) — 官方 Python SDK v1.2.3 (2025-02-10)。
- **现有代码库** — `src/claw_cron/channels/qqbot.py`, `src/claw_cron/channels/feishu.py` — 已验证的 WebSocket capture 模式。

### Secondary (MEDIUM confidence)

- **weworkapi_python GitHub** (https://github.com/sbzhu/weworkapi_python) — 官方 Python 库，最后更新 2026-04-17，608 stars。活跃维护。
- **Python 企业微信机器人 Webhook 自动化消息推送实战** (https://blog.csdn.net/weixin_29032337/article/details/158753068) — Webhook 实现示例，2026-03-07。
- **微信 API 超时与熔断降级** (https://blog.csdn.net/ling_76539446/article/details/156560331) — 实践经验总结，包含重试和熔断策略。
- **Webhook 重试最佳实践** (https://dev.to/henry_hang/webhook-best-practices-retry-logic-idempotency-and-error-handling-27i3) — 行业标准模式。

### Tertiary (LOW confidence)

- **2026 年微信机器人开发指南：官方 iLink 协议详解** (https://zhuanlan.zhihu.com/p/2019677743126704371) — 提到官方 Bot API (iLink) 2026-03 发布。**需验证**: 申请条件、功能集、生产可用性。
- **微信接入AI避坑实战：ClawBot核心能力与封号风险解析** (https://blog.csdn.net/aidoudoulong/article/details/159430136) — 封号风险分析，2026-03-24。
- **微信封号规则 2026** (https://www.zhanghaobang.cn/policy/wechat-ban-rules-2026) — 第三方总结，非官方。

---
*Research completed: 2026-04-17*
*Ready for roadmap: yes*
