# Phase 14: Architecture Enhancement - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

建立统一的 capture 抽象层，支持各通道实现特定的 capture 逻辑，包括：
1. **MessageChannel 扩展** — 新增 `supports_capture` 属性和 `capture_openid()` 方法
2. **QQBotChannel 重构** — 将现有 WebSocket capture 逻辑封装到 `capture_openid()` 方法
3. **FeishuChannel 重构** — 将现有飞书 capture 逻辑封装到 `capture_openid()` 方法
4. **capture 命令改进** — 支持交互式通道选择，动态发现支持 capture 的通道

不包括：新的 capture 功能（如批量捕获、自动重试）、UI 增强（Phase 15）、微信 capture（Phase 16）。

</domain>

<decisions>
## Implementation Decisions

### supports_capture 属性设计

- **D-01:** 使用 `@property` 方法实现 `supports_capture`
  - 基类默认返回 `False`
  - 子类覆盖该方法返回 `True` 表示支持 capture
  - 更语义化、类型安全，避免子类忘记设置类属性
- **D-02:** 不支持 capture 的通道无需任何特殊处理
  - IMessageChannel、EmailChannel 保持默认实现即可

### capture_openid() 方法签名

- **D-03:** 方法签名：`async def capture_openid(timeout: int = 300) -> str`
  - 返回捕获的 open_id 字符串
  - timeout 参数控制等待超时，默认 300 秒（5 分钟）
  - 简单通用，调用方根据返回值保存联系人
- **D-04:** 方法只负责捕获逻辑，不处理 UI 显示
  - UI 层（Rich console 状态显示）由 cmd/channels.py 处理
  - 关注点分离，便于测试
- **D-05:** 方法不直接保存联系人
  - 只捕获并返回 open_id
  - 由调用方决定是否保存、如何保存
  - 更灵活，支持临时捕获场景

### 错误处理

- **D-06:** 不支持 capture 的通道调用时抛出 `NotImplementedError`
  - 基类 `capture_openid()` 实现：`raise NotImplementedError(f"{self.channel_id} does not support capture")`
  - 明确告知调用方该通道不支持此功能
- **D-07:** 缺少配置时抛出 `ChannelConfigError`
  - 调用方在调用前检查配置
  - capture_openid() 假设配置已就绪，未配置时抛出异常
  - 复用现有异常体系
- **D-08:** capture 超时或失败抛出 `ChannelError`
  - 使用通道模块已有的异常类
  - 错误消息包含具体失败原因（超时、连接失败等）

### capture 命令改进

- **D-09:** 移除硬编码的 `--channel-type` 参数
  - 改为交互式选择通道
  - 从 `CHANNEL_REGISTRY` 动态筛选 `supports_capture == True` 的通道
  - 支持未来新增通道自动发现
- **D-10:** 不支持 capture 的通道在列表中显示友好提示
  - 如果用户尝试 capture 不支持的通道，显示 "This channel doesn't require capture"
  - 与 Phase 15 的 CAPT-02 需求对应

### Claude's Discretion

- WebSocket 连接管理的具体实现细节
- capture_openid() 内部的错误消息格式
- 测试用例的覆盖范围
- 是否需要 capture 进度回调（目前不需要）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，MessageResult, ChannelConfig
- `src/claw_cron/channels/qqbot.py` — QQBotChannel 实现，包含 WebSocket 逻辑
- `src/claw_cron/channels/feishu.py` — FeishuChannel 实现
- `src/claw_cron/channels/email.py` — EmailChannel 实现（不需要 capture）
- `src/claw_cron/channels/imessage.py` — IMessageChannel 实现（不需要 capture）
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY 注册表
- `src/claw_cron/channels/exceptions.py` — 通道异常类
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, capture, verify）
- `src/claw_cron/qqbot/websocket.py` — QQ Bot WebSocket 客户端
- `src/claw_cron/feishu/events.py` — 飞书事件处理

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — ARCH-01 至 ARCH-04

### 相关阶段上下文
- `.planning/phases/12-feishu-channel/12-CONTEXT.md` — 飞书通道实现，capture 交互流程
- `.planning/phases/13-email-channel/13-CONTEXT.md` — 邮件通道实现，不需要 capture

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MessageChannel` 抽象基类 — 已有 send_text/send_markdown 接口模式
- `QQBotWebSocket` — QQ Bot WebSocket 连接管理
- `lark-oapi` SDK — 飞书 WebSocket 事件监听
- `CHANNEL_REGISTRY` — 通道注册表，可动态遍历
- `ChannelConfigError` — 配置错误异常类
- `ChannelError` — 通用通道错误异常类

### Established Patterns
- `@property` 方法 — 已在 channel_id 等属性使用
- `async/await` — 所有通道方法都是异步的
- `NotImplementedError` — 已用于 send_template 等可选方法
- pydantic-settings 配置类 — 所有通道配置类都继承 ChannelConfig
- Rich console 状态显示 — cmd/channels.py 中已有模式

### Integration Points
- `channels/base.py` — 新增 `supports_capture` 属性和 `capture_openid()` 方法
- `channels/qqbot.py` — 重构现有 capture 逻辑到 `capture_openid()` 方法
- `channels/feishu.py` — 重构现有 capture 逻辑到 `capture_openid()` 方法
- `cmd/channels.py:capture()` — 重构为交互式通道选择，调用 channel.capture_openid()
- `channels/__init__.py` — 无需修改（通道已在注册表中）

### Current Capture Implementation
- `_capture_qqbot_openid()` (cmd/channels.py:461-535) — QQ Bot capture 逻辑
- `_capture_feishu_openid()` (cmd/channels.py:538-616) — 飞书 capture 逻辑
- 两处实现都包含：配置加载、WebSocket 连接、消息监听、联系人保存

</code_context>

<specifics>
## Specific Ideas

### MessageChannel 基类扩展示例
```python
class MessageChannel(ABC):
    @property
    def supports_capture(self) -> bool:
        """Whether this channel supports openid capture."""
        return False

    async def capture_openid(self, timeout: int = 300) -> str:
        """Capture user openid by waiting for user message.

        Args:
            timeout: Timeout in seconds (default: 300s / 5 min).

        Returns:
            Captured openid string.

        Raises:
            NotImplementedError: If channel doesn't support capture.
            ChannelConfigError: If channel is not configured.
            ChannelError: If capture fails or times out.
        """
        raise NotImplementedError(
            f"{self.channel_id} does not support capture"
        )
```

### QQBotChannel 实现示例
```python
class QQBotChannel(MessageChannel):
    @property
    def supports_capture(self) -> bool:
        return True

    async def capture_openid(self, timeout: int = 300) -> str:
        self._validate_config()
        # ... WebSocket 连接和消息监听逻辑
        return captured_openid
```

### capture 命令改进示例
```python
@channels.command()
@click.option("--alias", default="me", help="Alias name for the captured contact")
def capture(alias: str) -> None:
    """Capture openid from interactive channel selection."""
    # 动态筛选支持 capture 的通道
    capture_channels = [
        ch_id for ch_id, ch_class in CHANNEL_REGISTRY.items()
        if ch_class().supports_capture
    ]

    if not capture_channels:
        console.print("[yellow]No channels support capture[/yellow]")
        return

    # 交互式选择通道
    channel_type = prompt_channel_select(capture_channels)

    # 调用 channel 的 capture_openid 方法
    channel = get_channel(channel_type)
    try:
        with console.status(f"[bold green]Waiting for message from {channel_type}..."):
            openid = await channel.capture_openid()
        console.print(f"[green]✓ OpenID captured: {openid}[/green]")

        # 保存联系人
        contact = Contact(openid=openid, channel=channel_type, alias=alias, ...)
        save_contact(contact)
    except ChannelError as e:
        console.print(f"[red]Capture failed: {e}[/red]")
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-architecture-enhancement*
*Context gathered: 2026-04-17*
