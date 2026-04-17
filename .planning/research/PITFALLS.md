# Pitfalls Research

**Domain:** 邮件和飞书通知通道集成
**Researched:** 2026-04-17
**Confidence:** HIGH (基于官方文档和实战经验)

## Critical Pitfalls

### Pitfall 1: SMTP 凭证明文存储在配置文件

**What goes wrong:**
将 SMTP 密码/App Password 直接写入 `tasks.yaml` 或代码中，导致：
- Git 提交后凭证泄露到版本控制
- 公开仓库暴露邮件服务器访问权限
- 攻击者利用凭证发送钓鱼邮件

**Why it happens:**
开发者为方便测试，直接硬编码凭证，忘记移除就提交代码

**How to avoid:**
1. 使用环境变量存储所有敏感凭证
   - `CLAW_CRON_SMTP_PASSWORD`
   - `CLAW_CRON_SMTP_USERNAME`
2. 参考 QQBot 的配置模式：使用 `pydantic_settings.BaseSettings` + 环境变量前缀
3. 在 `.env.example` 中提供模板，`.env` 加入 `.gitignore`
4. 配置验证时检查环境变量而非配置文件值

**Warning signs:**
- 配置文件中包含明文密码
- Git diff 显示密码提交
- `.gitignore` 中缺少 `.env`

**Phase to address:**
Phase 1 (通道基础架构) - 在 EmailChannel 配置类设计时就使用环境变量

---

### Pitfall 2: 忽略 SMTP 临时失败 (4xx) 和永久失败 (5xx) 的区别

**What goes wrong:**
- 所有失败都重试 → 永久失败的邮箱（不存在、已停用）浪费重试资源
- 所有失败都不重试 → 临时限流导致的通知丢失
- 没有退信处理 → 无效邮箱累积，影响发送信誉

**Why it happens:**
开发者不熟悉 SMTP 错误码体系，将邮件发送当作"成功/失败"二元操作

**How to avoid:**
1. **区分错误类型**：
   - **4xx (临时失败)**：自动重试，指数退避
     - 421: 临时限流 → 减少发送频率，稍后重试
     - 450: 连接过多 → 延长重试间隔
     - 451: 服务器临时错误 → 自动重试（最多 72 小时）
   - **5xx (永久失败)**：不重试，记录并清理
     - 550: 邮箱不可用 → 标记为无效
     - 551: 用户不存在 → 从通知列表移除
     - 553: 无效邮箱格式 → 记录错误日志

2. **实现退信跟踪**：
   ```python
   # 伪代码示例
   async def handle_smtp_error(error_code: int, recipient: str):
       if 400 <= error_code < 500:
           return await retry_with_backoff(...)
       elif 500 <= error_code < 600:
           mark_recipient_invalid(recipient)
           return MessageResult(success=False, permanent_failure=True)
   ```

3. **提供退信统计**：
   - 记录连续失败次数
   - 达到阈值后自动禁用该收件人

**Warning signs:**
- 日志显示同一邮箱反复失败
- 重试队列无限增长
- 没有永久失败的处理逻辑

**Phase to address:**
Phase 2 (邮件通道实现) - 在错误处理逻辑中实现区分处理

---

### Pitfall 3: 飞书机器人未订阅必需事件

**What goes wrong:**
- WebSocket 连接成功，但收不到任何用户消息
- 机器人配置完成，测试时无响应
- 日志显示 "ws client ready" 但没有后续事件

**Why it happens:**
飞书采用事件推送机制，必须在开发者后台主动订阅事件，否则飞书不会推送消息

**How to avoid:**
1. **必需的事件订阅**：
   - `im.message.receive_v1` - 接收用户消息（必需）

2. **配置步骤清单**：
   - [ ] 飞书开发者后台 → 事件与回调
   - [ ] 订阅方式：选择"使用长连接接收事件/回调"
   - [ ] 添加事件：`im.message.receive_v1`
   - [ ] **必须发布版本**才能生效

3. **参考 QQBot 模式**：
   QQBot 使用 WebSocket 捕获 OpenID，FeishuChannel 可采用类似方式：
   - 启动时连接 WebSocket
   - 接收事件以获取用户 open_id
   - 使用 open_id 发送私聊消息

**Warning signs:**
- WebSocket 连接正常但无事件日志
- 开发者后台未配置事件订阅
- 配置变更后未发布版本

**Phase to address:**
Phase 3 (飞书通道实现) - 在实现时确保事件订阅配置完整

---

### Pitfall 4: 飞书 token 过期导致批量通知失败

**What goes wrong:**
- `tenant_access_token` 默认 2 小时过期
- 缓存的 token 过期后，所有发送请求失败
- 错误码：99991663 (访问凭证无效)、99991665 (tenant_access_token 非法)

**Why it happens:**
开发者缓存 token 后忘记实现自动刷新机制

**How to avoid:**
1. **参考 QQBot 的 Token 管理**：
   ```python
   @dataclass
   class TokenInfo:
       access_token: str
       expires_at: float  # Unix timestamp
       buffer_seconds: int = 60  # 提前 60 秒刷新

       def is_expired(self) -> bool:
           return time.time() >= (self.expires_at - self.buffer_seconds)
   ```

2. **实现自动刷新**：
   - 发送前检查 `token.is_expired()`
   - 过期则调用刷新接口
   - 使用锁机制避免并发刷新

3. **错误码识别**：
   - 遇到 99991663/99991665 → 立即刷新 token 并重试一次

**Warning signs:**
- 运行一段时间后突然全部失败
- 错误日志显示 "访问凭证无效"
- 没有提前刷新机制（buffer_seconds）

**Phase to address:**
Phase 3 (飞书通道实现) - 参考 QQBot 的 token 管理实现

---

### Pitfall 5: 飞书用户不在应用可用范围内

**What goes wrong:**
- 配置了正确的 open_id，但发送失败
- 错误码：230013 (机器人无权访问该用户)、230029 (用户已离职)
- 测试环境正常，生产环境失败

**Why it happens:**
飞书机器人只能向"应用可用范围"内的用户发送私聊消息，管理员未正确配置范围

**How to avoid:**
1. **发送前验证**：
   - 使用 `contact:contact.base:readonly` 权限查询用户信息
   - 验证用户是否在可用范围内

2. **友好的错误处理**：
   - 捕获 230013 错误 → 提示"用户未在应用可用范围内，请联系管理员"
   - 捕获 230029 错误 → 提示"用户已离职，无法发送通知"

3. **配置建议**：
   - 开发者后台 → 应用可用范围 → 设置为"全部成员"
   - 或明确指定需要通知的部门/用户

**Warning signs:**
- 部分用户能收到，部分收不到
- 错误日志显示 230013
- 应用可用范围配置为"指定部门"

**Phase to address:**
Phase 3 (飞书通道实现) - 在配置验证和错误处理中覆盖

---

### Pitfall 6: 忽略飞书频率限制 (5 QPS per user)

**What goes wrong:**
- 批量发送通知时触发限流
- 错误码：230020 (触发频率限制)
- 部分用户收不到通知

**Why it happens:**
飞书对向同一用户发送消息限频 5 QPS，批量发送未做速率控制

**How to avoid:**
1. **参考 QQBot 的重试机制**：
   ```python
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type(RateLimitError),
   )
   async def _send_with_retry(self, endpoint, payload):
       ...
   ```

2. **实现速率限制**：
   - 使用 `asyncio.Semaphore` 控制并发
   - 或在批量发送时添加延迟（每用户间隔 200ms）

3. **识别限流错误码**：
   - Feishu: 230020
   - QQBot: 22009, 20028, 304045-304050
   - SMTP: 421, 450

**Warning signs:**
- 批量通知时部分失败
- 日志显示频率限制错误码
- 没有速率控制逻辑

**Phase to address:**
Phase 2-3 (邮件和飞书通道实现) - 在发送逻辑中实现速率控制

---

### Pitfall 7: 多通道错误处理不一致

**What goes wrong:**
- QQBot 返回 `MessageResult(success=False, error=str)`
- Email 抛出异常
- Feishu 返回不同的错误格式
- 上层调度器无法统一处理失败情况

**Why it happens:**
每个通道独立实现，没有遵循统一的错误处理接口

**How to avoid:**
1. **统一错误类型**：
   参考 `channels/exceptions.py` 中的异常层级：
   - `ChannelConfigError` - 配置错误（不重试）
   - `ChannelAuthError` - 认证错误（不重试，或刷新 token 后重试一次）
   - `ChannelSendError` - 发送错误（可重试）

2. **统一返回结构**：
   ```python
   @dataclass
   class MessageResult:
       success: bool
       message_id: str | None = None
       error: str | None = None
       permanent_failure: bool = False  # 是否永久失败
       raw_response: dict | None = None
   ```

3. **每个通道实现**：
   - 捕获所有异常
   - 转换为统一的 `MessageResult`
   - 标记 `permanent_failure` 以便上层决定是否重试

**Warning signs:**
- 调度器中出现大量 `try-except` 处理不同通道
- 某个通道失败导致整个通知流程中断
- 无法区分临时失败和永久失败

**Phase to address:**
Phase 1 (通道基础架构) - 在 MessageChannel 基类中定义统一接口

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| SMTP 凭证硬编码在配置文件 | 快速测试，无需配置环境变量 | 凭证泄露风险，代码不可公开 | **Never** - 必须使用环境变量 |
| 所有失败都重试 3 次 | 简化错误处理逻辑 | 浪费资源在无效邮箱，污染日志 | **Never** - 必须区分临时/永久失败 |
| 忽略飞书事件订阅，直接发送 | 跳过配置步骤 | 无法获取用户 open_id，私聊功能受限 | 仅限群组通知场景 |
| Token 不缓存，每次都刷新 | 避免过期问题 | API 调用翻倍，可能触发限流 | 仅限 MVP 测试 |
| 统一错误处理留到后期 | 快速完成功能 | 多个通道错误处理逻辑分散，重构成本高 | **Never** - 必须在 Phase 1 定义统一接口 |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **SMTP** | 忽略发件人身份验证 (Sender Identity) | 配置 SPF/DKIM，验证发件人邮箱 |
| **SMTP** | 发送大量邮件不预热 IP | IP 预热，逐步增加发送量 |
| **SMTP** | 错误处理不区分 4xx/5xx | 参考本文 Pitfall 2 |
| **Feishu** | 未订阅 `im.message.receive_v1` 事件 | 在开发者后台配置事件订阅并发布版本 |
| **Feishu** | 使用 `user_id` 而非 `open_id` | 使用 `open_id`（用户在应用中的唯一标识） |
| **Feishu** | 用户不在应用可用范围内 | 配置应用可用范围为"全部成员"或明确指定用户 |
| **Feishu** | 修改权限后未发布版本 | 所有配置变更后必须创建版本并发布 |
| **Multi-Channel** | 每个通道错误处理方式不同 | 使用统一的 `MessageResult` 和异常层级 |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **同步发送多个通知** | 通知延迟累积，单个通道慢影响全部 | 使用 `asyncio.gather()` 并发发送，或消息队列 | >10 个并发通知 |
| **SMTP 无连接池** | 每次发送都建立新连接，延迟高 | 使用 `aiosmtplib` 连接池 | >5 封/分钟 |
| **Token 不缓存** | API 调用翻倍，响应时间增加 | 参考 QQBot 的 TokenInfo 缓存机制 | 持续运行 >1 小时 |
| **忽略速率限制** | 频繁触发限流，部分通知丢失 | 使用 `asyncio.Semaphore` 或间隔延迟 | 飞书：>5 QPS/user，SMTP：依服务商而定 |
| **无退信处理** | 无效邮箱累积，发送信誉下降 | 记录失败次数，自动禁用连续失败的收件人 | 累积 >100 个无效邮箱 |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **SMTP 密码硬编码** | 凭证泄露，邮件服务器被滥用 | 使用环境变量，参考 QQBot 配置模式 |
| **.env 文件提交到 Git** | 凭证进入版本控制，公开后不可撤销 | `.gitignore` 包含 `.env`，使用 `.env.example` 模板 |
| **飞书 App Secret 泄露** | 攻击者可调用 API 冒充机器人 | 使用环境变量 `CLAW_CRON_FEISHU_APP_SECRET` |
| **日志中打印敏感信息** | 密码/token 出现在日志文件 | 日志脱敏，不打印完整密码/token |
| **邮件内容未转义** | XSS 风险（如果邮件内容包含用户输入） | 使用 HTML 转义，或发送纯文本 |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **`channels add` 不验证配置** | 配置错误导致通知失败，用户不知情 | 添加时发送测试消息验证配置 |
| **`channels list` 不显示配置状态** | 用户不知道哪个通道配置正确 | 显示每个通道的配置验证状态（✅/❌） |
| **发送失败无日志提示** | 用户不知道为什么收不到通知 | 记录失败原因到日志，提供排查建议 |
| **飞书 open_id 获取困难** | 用户不知道如何获取自己的 open_id | 提供 WebSocket 捕获方式，用户发消息给机器人后自动获取 |
| **邮件退信无提示** | 用户不知道邮箱地址无效 | 显示退信统计，提示用户更新邮箱地址 |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Email 通道:** 能发送邮件，但未处理退信 — 验证永久失败 (5xx) 是否被记录并清理
- [ ] **Email 通道:** 使用 SMTP，但未验证发件人身份 — 验证 SPF/DKIM 配置
- [ ] **Feishu 通道:** 能调用 API，但未订阅事件 — 验证开发者后台 `im.message.receive_v1` 已订阅
- [ ] **Feishu 通道:** Token 缓存实现，但无自动刷新 — 验证过期前 (buffer_seconds) 会自动刷新
- [ ] **Feishu 通道:** 发送成功，但用户收不到 — 验证用户在应用可用范围内
- [ ] **Multi-Channel:** 每个通道能工作，但错误处理不一致 — 验证所有通道返回统一的 `MessageResult`
- [ ] **Multi-Channel:** 能发送通知，但无速率控制 — 验证批量发送时不会触发限流
- [ ] **Security:** 代码无硬编码密码，但 `.env` 未忽略 — 验证 `.gitignore` 包含 `.env`

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **SMTP 凭证泄露** | HIGH | 1. 立即更改密码/App Password<br>2. 检查发送日志，确认无异常邮件<br>3. 启用 2FA（如未启用）<br>4. 从 Git 历史中移除敏感文件（使用 `git filter-branch`） |
| **飞书 Token 过期导致批量失败** | LOW | 1. 触发 token 刷新<br>2. 重新发送失败的通知<br>3. 添加提前刷新机制防止再次发生 |
| **飞书事件订阅未配置** | MEDIUM | 1. 开发者后台配置事件订阅<br>2. 发布新版本<br>3. 通知用户重新测试 |
| **多通道错误处理不一致** | HIGH | 1. 定义统一的 `MessageResult` 接口<br>2. 重构每个通道的错误处理<br>3. 更新调度器的错误处理逻辑 |
| **触发频率限制** | LOW | 1. 降低发送速率<br>2. 添加速率限制逻辑<br>3. 等待限流解除后重试 |
| **无效邮箱累积** | MEDIUM | 1. 扫描退信记录，识别无效邮箱<br>2. 清理通知列表<br>3. 实现自动退信处理 |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SMTP 凭证明文存储 | Phase 1 (通道基础架构) | 检查 EmailConfig 使用环境变量，无硬编码 |
| 忽略 SMTP 错误码区别 | Phase 2 (邮件通道实现) | 测试 4xx/5xx 错误码处理逻辑，验证退信记录 |
| 飞书事件订阅未配置 | Phase 3 (飞书通道实现) | 验证开发者后台事件订阅配置 |
| 飞书 Token 过期 | Phase 3 (飞书通道实现) | 测试 token 自动刷新，验证 buffer_seconds 逻辑 |
| 飞书用户不在可用范围 | Phase 3 (飞书通道实现) | 测试不同用户场景，验证错误提示 |
| 忽略频率限制 | Phase 2-3 (邮件和飞书) | 批量发送测试，验证无 230020/421 错误 |
| 多通道错误处理不一致 | Phase 1 (通道基础架构) | 检查所有通道返回统一的 `MessageResult` |
| `channels add` 不验证 | Phase 4 (交互改进) | 测试添加通道时发送测试消息 |
| `channels list` 无状态 | Phase 4 (交互改进) | 验证显示配置状态（✅/❌） |

---

## Sources

- **官方文档：**
  - 飞书开放平台：通用错误码 - https://open.larkoffice.com/document/server-docs/api-call-guide/generic-error-code
  - 飞书开放平台：发送消息 API - https://open.feishu.cn/document/server-docs/im-v1/message/create
  - 飞书开放平台：机器人概述 - https://open.feishu.cn/document/client-docs/bot-v3/bot-overview
  - SendGrid：SMTP Errors and Troubleshooting - https://www.twilio.com/docs/sendgrid/for-developers/sending-email/smtp-errors-and-troubleshooting

- **实战经验：**
  - 飞书机器人接入踩坑指南 - https://leapvale.com/blog/technique/feishu-bot-setup-guide/
  - SMTP Retries and Deferrals - https://www.warmy.io/blog/smtp-retries-and-deferrals-understanding-email-delays-how-to-fix-them/
  - GitGuardian：Remediating SMTP Credential leaks - https://www.gitguardian.com/remediation/smtp-credential

- **项目参考：**
  - QQBot 实现：`src/claw_cron/channels/qqbot.py`
    - Token 管理：TokenInfo 类，提前刷新机制
    - 错误处理：区分速率限制和认证错误
    - 重试策略：指数退避，最多 3 次
    - 配置模式：pydantic_settings + 环境变量前缀

---
*Pitfalls research for: 邮件和飞书通知通道集成*
*Researched: 2026-04-17*
