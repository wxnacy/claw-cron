# Pitfalls Research

**Domain:** 微信通道 & Capture 增强
**Researched:** 2026-04-17
**Confidence:** MEDIUM (基于官方文档和社区实践，部分 WebSearch 未验证)

---

## Critical Pitfalls

### Pitfall 1: 个人微信封号风险

**What goes wrong:**
使用个人微信机器人方案（如 wechat-bridge、Hook、逆向协议）发送定时任务通知，导致账号被风控或封禁。

**Why it happens:**
- 个人微信 API 不是官方开放接口，腾讯严厉打击自动化行为
- 定时高频发送消息触发风控系统（批量营销特征）
- 2026年3月虽然官方开放了 iLink 协议，但仍有限制：
  - 仅限特定场景（AI 助理对话）
  - 不适合定时任务通知（单向推送）

**How to avoid:**
- **必须使用企业微信应用机器人**（官方 API，合规稳定）
- 不使用任何 Hook、协议破解、RPA 工具
- 如需个人微信，仅用于测试，频率控制在每日 < 5 条

**Warning signs:**
- 账号收到"账号异常"警告
- 发送消息延迟严重（风控拦截）
- 好友无法收到消息（已被限流）

**Phase to address:**
**Phase 14 (微信通道实现)** — 架构设计阶段就确定使用企业微信，不提供个人微信选项

---

### Pitfall 2: 企业微信群机器人 vs 应用机器人选择错误

**What goes wrong:**
选择企业微信群机器人 webhook 实现通知功能，发现：
- 无法发送私聊消息（仅群聊）
- 无法获取用户 open_id（无 WebSocket 事件）
- 消息类型受限（不支持卡片、文件等）
- 外部客户群推送受限（仅内部群）

**Why it happens:**
混淆了两种机器人类型：

| 特性 | 群机器人 | 应用机器人 |
|-----|---------|-----------|
| **通信方式** | Webhook（单向推送） | API + WebSocket（双向） |
| **私聊支持** | ❌ 不支持 | ✅ 支持 |
| **open_id 获取** | ❌ 无法获取 | ✅ 通过 WebSocket 事件 |
| **消息类型** | 文本、Markdown、图片 | 全类型（卡片、文件、模板） |
| **适用场景** | 群通知广播 | 个人定时提醒 |

**How to avoid:**
- **定时任务通知场景 → 必须使用应用机器人**
- 群机器人仅用于测试或"推送到群"场景
- 在 `channels add` 流程中明确区分：
  - `wechat-work-app` — 企业微信应用（推荐）
  - `wechat-work-webhook` — 群机器人（受限场景）

**Warning signs:**
- 用户问"如何发送私聊" → 选错了机器人类型
- capture 流程无法获取 open_id → 群机器人不支持

**Phase to address:**
**Phase 14 (微信通道实现)** — 只实现应用机器人，群机器人标记为 "future work"

---

### Pitfall 3: API 频率限制未处理导致通知丢失

**What goes wrong:**
定时任务批量执行时（如每分钟提醒 10 个用户），企业微信 API 返回 45009 错误（频率限制），通知丢失。

**Why it happens:**
企业微信 API 有限制：
- access_token 有效期 2 小时，需提前刷新
- 消息发送频率限制（具体 QPS 未公开，实测约 30 次/分钟）
- 单个用户接收频率限制（防骚扰）

**How to avoid:**
**分级超时 + 熔断降级策略**（参考微信 API 最佳实践）：

```python
# 超时配置
WECHAT_TIMEOUTS = {
    "get_token": {"connect": 1.0, "read": 2.0},
    "send_message": {"connect": 2.0, "read": 10.0},
    "default": {"connect": 3.0, "read": 5.0},
}

# 熔断配置（参考 Resilience4j）
CIRCUIT_BREAKER = {
    "failure_rate_threshold": 50,  # 失败率 > 50% 开启熔断
    "wait_duration": 30,           # 熔断后等待 30 秒
    "sliding_window_size": 10,     # 最近 10 次调用
    "minimum_calls": 5,            # 至少 5 次才计算
}

# 降级策略
async def send_with_fallback(recipient: str, content: str):
    try:
        return await wechat_channel.send_text(recipient, content)
    except RateLimitError:
        # 降级到备用通道（如 QQ Bot）
        return await fallback_channel.send_text(recipient, content)
    except CircuitBreakerOpen:
        # 记录到队列，稍后重试
        await retry_queue.add({"recipient": recipient, "content": content})
        return MessageResult(success=True, error="Queued for retry")
```

**关键预防措施：**
1. **Token 缓存 + 预刷新**：提前 30 秒刷新 access_token
2. **指数退避重试**：失败后 1s → 2s → 4s → 8s（最多 3 次）
3. **降级通道**：企业微信失败 → 降级到 QQ Bot 或邮件
4. **异步队列**：高并发时不直接调用 API，先入队再处理

**Warning signs:**
- 日志中出现大量 45009 错误
- 消息延迟超过 1 分钟
- 用户反馈"没收到提醒"

**Phase to address:**
**Phase 14 (微信通道实现)** — 在 `WeChatWorkChannel` 中实现完整的重试、熔断、降级逻辑

---

### Pitfall 4: Capture 流程用户不知道下一步该做什么

**What goes wrong:**
用户执行 `claw-cron channels capture --channel-type wechat-work` 后：
- 看到提示 "Waiting for message..."
- 不知道要打开企业微信发送消息给机器人
- 以为程序卡死，直接 Ctrl+C 退出
- capture 失败，无法保存 contact

**Why it happens:**
- 提示信息不明确，缺少操作指引
- 用户不了解 WebSocket 工作原理
- 没有进度反馈（如倒计时、状态更新）

**How to avoid:**
**改进 capture 交互流程**（参考 QQ Bot 现有实现，进一步优化）：

```python
async def _capture_wechat_work_openid(alias: str):
    # 1. 清晰的分步指引
    console.print("\n[bold cyan]步骤 1/2: 启动消息监听[/bold cyan]")
    console.print("[dim]正在连接企业微信 WebSocket...[/dim]\n")
    
    # 2. 显式的操作说明（带示例）
    console.print("[bold yellow]步骤 2/2: 发送消息给机器人[/bold yellow]")
    console.print("[green]请按以下步骤操作：[/green]")
    console.print("  1. 打开 [bold]企业微信[/bold] 手机 App 或桌面客户端")
    console.print("  2. 找到机器人应用（名称：claw-cron）")
    console.print("  3. 发送任意消息（如：[dim]test[/dim]）")
    console.print("\n[dim]示例：在机器人对话框输入 'capture' 或 'hello'[/dim]\n")
    
    # 3. 实时状态反馈
    with console.status("[bold green]等待消息中... (Ctrl+C 取消)[/bold green]"):
        # WebSocket 监听逻辑
    
    # 4. 超时提醒（可选）
    if timeout > 300:  # 5 分钟
        console.print("[yellow]⏱ 等待时间较长，请检查：[/yellow]")
        console.print("  - 机器人是否已添加到通讯录")
        console.print("  - 企业微信网络是否正常")
```

**优化要点：**
1. **分步指引**：明确当前步骤和下一步操作
2. **带示例的操作说明**：降低理解门槛
3. **实时状态**：显示 spinner + 等待时间
4. **超时提示**：长时间无响应时给出诊断建议

**Warning signs:**
- 用户反馈 "capture 一直卡住"
- capture 成功率低（< 50%）
- 用户多次执行 capture（之前失败了）

**Phase to address:**
**Phase 15 (自动 capture 流程)** — 在 `channels add` 成功后自动触发 capture，提供更好的指引

---

### Pitfall 5: 不同通道 capture 流程不一致导致混淆

**What goes wrong:**
用户配置了 QQ Bot 和企业微信两个通道，capture 流程差异大：
- QQ Bot：需要扫码授权 → 发送消息
- 企业微信：需要添加机器人到通讯录 → 发送消息
- 飞书：需要搜索机器人 → 发送消息

用户在不同通道间混淆操作步骤，浪费时间。

**Why it happens:**
- 各通道的 WebSocket 实现不同（QQ Bot 自建，飞书用 lark-oapi，企业微信用企业微信 SDK）
- 提示信息没有统一模板
- 没有提供通道差异对比表

**How to avoid:**
**统一 capture 流程模板 + 通道差异说明**：

```python
# 统一的 capture 模板
CAPTURE_TEMPLATES = {
    "qqbot": {
        "step1": "添加 QQ Bot 为好友",
        "step1_detail": "在 QQ 搜索 Bot ID: {app_id}",
        "step2": "发送任意消息给 Bot",
        "timeout_hint": "如果 5 分钟未响应，请检查 Bot 是否在线",
    },
    "wechat-work": {
        "step1": "添加机器人到通讯录",
        "step1_detail": "在企业微信通讯录中搜索 'claw-cron'",
        "step2": "发送任意消息给机器人",
        "timeout_hint": "如果 5 分钟未响应，请检查机器人是否已启用",
    },
    "feishu": {
        "step1": "搜索机器人",
        "step1_detail": "在飞书搜索栏输入机器人名称",
        "step2": "发送任意消息",
        "timeout_hint": "确保机器人已启用并分配了权限",
    },
}

async def capture_with_template(channel_type: str, config: dict):
    template = CAPTURE_TEMPLATES[channel_type]
    
    console.print(f"\n[bold cyan]配置通道: {channel_type}[/bold cyan]\n")
    
    # Step 1
    console.print(f"[bold yellow]步骤 1: {template['step1']}[/bold yellow]")
    console.print(f"  {template['step1_detail'].format(**config)}\n")
    
    # Step 2
    console.print(f"[bold yellow]步骤 2: {template['step2']}[/bold yellow]")
    console.print(f"  [dim]示例：发送 'test' 或任意文字[/dim]\n")
    
    # Timeout hint (动态显示)
    console.print(f"[dim]💡 提示: {template['timeout_hint']}[/dim]\n")
```

**额外优化：**
- 在 `channels list` 输出中显示各通道的 capture 状态
- 提供帮助命令：`claw-cron channels capture --help-wechat-work`

**Phase to address:**
**Phase 15 (自动 capture 流程)** — 重构所有通道的 capture 流程，使用统一模板

---

### Pitfall 6: 网络超时导致 capture 失败

**What goes wrong:**
WebSocket 连接建立后，企业微信服务器响应慢或网络抖动，导致：
- 连接建立超时（> 30 秒）
- 消息事件丢失（用户发了消息但没捕获到）
- capture 永远等待（没有超时机制）

**Why it happens:**
- WebSocket 是长连接，默认无超时
- 网络不稳定（如公司内网限制 WebSocket）
- 企业微信服务器高峰期响应慢

**How to avoid:**
**WebSocket 超时 + 重连 + 降级策略**（参考 webhook best practices）：

```python
async def capture_with_timeout(channel_type: str, alias: str, timeout: int = 300):
    """带超时和重试的 capture 流程"""
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        console.print(f"\n[cyan]尝试 {attempt}/{max_attempts}[/cyan]")
        
        try:
            # 设置总超时（5 分钟）
            async with asyncio.timeout(timeout):
                result = await _do_capture(channel_type, alias)
                if result:
                    return result
                    
        except TimeoutError:
            console.print(f"[yellow]⏱ 超时 ({timeout}s)，尝试重连...[/yellow]")
            
            # 提供诊断建议
            if attempt == max_attempts:
                console.print("\n[red]多次超时，可能原因：[/red]")
                console.print("  1. 网络限制 WebSocket 连接（尝试切换网络）")
                console.print("  2. 企业微信服务不可用（查看官方状态页）")
                console.print("  3. 机器人未正确配置（运行 `channels verify`）")
                raise CaptureTimeoutError(f"Capture failed after {max_attempts} attempts")
                
        except ConnectionError as e:
            console.print(f"[red]连接失败: {e}[/red]")
            await asyncio.sleep(5 * attempt)  # 指数退避
            
    raise CaptureError("All attempts failed")

async def _do_capture(channel_type: str, alias: str) -> str | None:
    """实际的 capture 逻辑（带心跳检测）"""
    
    ws_client = create_websocket_client(channel_type)
    captured_openid = None
    
    # 心跳检测（每 30 秒）
    async def heartbeat():
        while not captured_openid:
            await asyncio.sleep(30)
            if ws_client.is_connected:
                console.print("[dim]💓 WebSocket 连接正常[/dim]")
            else:
                console.print("[yellow]⚠ 连接已断开[/yellow]")
                break
    
    async def on_message(message):
        nonlocal captured_openid
        captured_openid = message.openid
        console.print(f"[green]✓ OpenID: {message.openid}[/green]")
    
    ws_client.on_message = on_message
    
    # 并发执行：WebSocket 连接 + 心跳 + 等待捕获
    await asyncio.gather(
        ws_client.connect(),
        heartbeat(),
        wait_for_capture(lambda: captured_openid),
    )
    
    return captured_openid
```

**关键预防措施：**
1. **总超时限制**：5 分钟（可配置）
2. **自动重连**：最多 3 次，指数退避
3. **心跳检测**：每 30 秒检查连接状态
4. **诊断建议**：失败时提供可能原因和解决方法

**Warning signs:**
- capture 执行时间超过 5 分钟
- 日志中频繁出现 "Connection lost"
- 用户反馈"发了消息但没反应"

**Phase to address:**
**Phase 15 (自动 capture 流程)** — 在 capture 实现中加入超时、重连、心跳机制

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **直接调用企业微信 API，不缓存 token** | 减少代码复杂度 | 频繁获取 token 触发限流，性能下降 | **Never** — 必须实现 token 缓存 |
| **capture 无超时限制** | 简化实现 | 用户不知道何时失败，浪费时间 | **Never** — 必须设置超时（默认 5 分钟） |
| **只用一种通道（如 QQ Bot）** | 开发快，测试简单 | 无法降级，单点故障 | **MVP only** — 生产环境需多通道降级 |
| **忽略 webhook 签名验证** | 减少配置步骤 | 安全漏洞，可能被伪造消息攻击 | **测试环境 only** — 生产必须验证签名 |
| **日志只记录成功/失败** | 日志量少 | 无法诊断问题根因 | **Never** — 必须记录详细上下文（recipient, error_code, latency） |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **企业微信应用** | 混淆 AgentId 和 CorpId | CorpId 在企业信息页，AgentId 在应用详情页 |
| **企业微信 token** | 不刷新，导致 2 小时后失效 | 缓存 token，提前 30 秒刷新（expires_in - 60s） |
| **企业微信 open_id** | 以为 open_id 跨应用通用 | open_id 是机器人维度的，不同应用 open_id 不同 |
| **WebSocket 连接** | 不处理断线重连 | 实现心跳检测 + 自动重连（指数退避） |
| **消息发送频率** | 批量发送不间隔 | 高频场景使用队列 + 限流（如 10 条/分钟） |
| **错误码处理** | 只判断 HTTP 状态码 | 企业微信返回的是业务错误码（如 45009），需解析 JSON |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **单线程发送消息** | 定时任务多时延迟严重 | 使用异步队列 + 并发发送 | > 10 个任务/分钟 |
| **同步验证凭证** | `channels add` 卡顿 | 验证请求设置 5s 超时，后台异步验证 | 网络慢时明显 |
| **capture 无并发限制** | 多个 capture 同时运行耗尽连接 | 限制同时运行的 capture 数量（如 3 个） | > 5 个并发 capture |
| **不限制消息长度** | 长消息导致 API 超时 | 消息长度限制（如 2048 字符），超出截断或分多条 | 消息 > 4KB |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **企业微信 Secret 明文存储** | 泄露后可伪造机器人发送消息 | 使用环境变量或加密存储（如 keyring） |
| **open_id 直接暴露在日志** | 用户隐私泄露 | 日志脱敏（open_id 只显示前 8 位） |
| **capture 流程无防重放** | 恶意用户重复 capture 消耗资源 | capture 成功后记录，短时间内拒绝重复 capture |
| **WebSocket 连接无鉴权** | 任何人可连接获取 open_id | 验证连接来源（检查 IP 白名单或 token） |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **capture 提示不明确** | 用户不知道下一步操作 | 分步指引 + 示例 + 进度反馈 |
| **错误信息只有错误码** | 用户无法自行解决 | 错误码 + 可能原因 + 解决建议 |
| **通道选择无状态显示** | 用户不知道哪些通道可用 | `channels list` 显示配置状态（✓ 已配置 / ○ 未配置） |
| **capture 失败无重试** | 用户需重新执行整个流程 | 提供"重试"选项，保留之前输入的 alias |
| **多通道操作混淆** | 用户在不同通道间重复操作 | 显示当前操作的通道类型（如 `[qqbot] Waiting...`） |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **企业微信通道：** 往往只实现 `send_text`，缺少 `send_markdown` 和降级逻辑 — 验证 markdown 失败时是否 fallback
- [ ] **capture 流程：** 往往只实现 WebSocket 连接，缺少超时和重连 — 验证 5 分钟后是否自动退出
- [ ] **token 刷新：** 往往只在启动时获取一次，缺少后台刷新 — 验证运行 2 小时后是否仍可用
- [ ] **错误处理：** 往往只捕获异常，缺少错误码解析 — 验证频率限制时是否返回具体错误信息
- [ ] **日志记录：** 往往只记录成功/失败，缺少上下文 — 验证日志是否包含 recipient、error_code、latency
- [ ] **降级通道：** 往往只实现一个通道，缺少降级 — 验证企业微信失败时是否降级到 QQ Bot

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **个人微信被封** | HIGH（无法恢复） | 1. 申诉解封（成功率低）<br>2. 注册新号，使用企业微信 |
| **企业微信 token 失效** | LOW | 1. 重新运行 `channels add`<br>2. 检查网络和权限配置 |
| **capture 超时失败** | LOW | 1. 检查网络（切换 Wi-Fi/热点）<br>2. 运行 `channels verify` 验证配置<br>3. 重试 capture |
| **频率限制触发** | MEDIUM | 1. 等待 1 分钟后重试<br>2. 实现队列限流<br>3. 添加降级通道 |
| **WebSocket 连接断开** | LOW | 1. 自动重连（已实现）<br>2. 用户无需操作 |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **个人微信封号风险** | Phase 14 (微信通道实现) | 只提供企业微信选项，文档明确警告个人微信风险 |
| **企业微信群 vs 应用选择错误** | Phase 14 (微信通道实现) | 架构设计时选择应用机器人，不实现群机器人 |
| **API 频率限制未处理** | Phase 14 (微信通道实现) | 实现完整的重试、熔断、降级逻辑，测试限流场景 |
| **capture 用户不知道下一步** | Phase 15 (自动 capture 流程) | 用户测试：首次使用用户能否独立完成 capture |
| **不同通道 capture 不一致** | Phase 15 (自动 capture 流程) | 统一模板，对比测试 3 个通道的 capture 流程 |
| **网络超时导致 capture 失败** | Phase 15 (自动 capture 流程) | 模拟弱网环境测试，验证超时和重连机制 |

---

## Sources

- **微信 API 超时与熔断降级：** https://blog.csdn.net/ling_76539446/article/details/156560331 (MEDIUM confidence - 实践经验总结)
- **企业微信群机器人限制：** https://blog.csdn.net/2501_94198109/article/details/155856070 (HIGH confidence - 官方文档确认)
- **Webhook 重试最佳实践：** https://dev.to/henry_hang/webhook-best-practices-retry-logic-idempotency-and-error-handling-27i3 (HIGH confidence - 行业标准)
- **微信封号规则 2026：** https://www.zhanghaobang.cn/policy/wechat-ban-rules-2026 (MEDIUM confidence - 第三方总结，非官方)
- **个人微信 vs 企业微信对比：** WebSearch 结果未验证（LOW confidence，建议查阅官方文档）
- **现有实现参考：** `src/claw_cron/channels/qqbot.py` (HIGH confidence - 已验证代码)

---

*Pitfalls research for: 微信通道 & Capture 增强*  
*Researched: 2026-04-17*
