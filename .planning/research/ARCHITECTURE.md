# Architecture Research: 微信通道 & Capture 增强

**Domain:** Message Channel Extension
**Researched:** 2026-04-17
**Confidence:** HIGH

## 现有架构分析

### 系统概览

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLI Layer                               │
│  claw-cron channels [add|list|delete|capture|verify]             │
├─────────────────────────────────────────────────────────────────┤
│                      Command Layer                               │
│  src/claw_cron/cmd/channels.py                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ add()        │  │ capture()    │  │ verify()     │           │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘           │
│         │                 │                                      │
├─────────┴─────────────────┴──────────────────────────────────────┤
│                     Channel Abstraction                          │
│  src/claw_cron/channels/                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ MessageChannel (ABC)                                     │   │
│  │  - channel_id: str                                       │   │
│  │  - send_text(recipient, content) → MessageResult         │   │
│  │  - send_markdown(recipient, content) → MessageResult     │   │
│  │  - health_check() → bool                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│         ↑             ↑             ↑             ↑             │
│  ┌──────┴──────┐ ┌────┴─────┐ ┌─────┴──────┐ ┌────┴─────┐       │
│  │ IMessage    │ │ QQBot    │ │ Feishu     │ │ Email    │       │
│  │ Channel     │ │ Channel  │ │ Channel    │ │ Channel  │       │
│  └─────────────┘ └──────────┘ └────────────┘ └──────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ CHANNEL_REGISTRY: dict[str, type[MessageChannel]]        │   │
│  │ get_channel(channel_id) → MessageChannel instance        │   │
│  │ get_channel_status(channel_id) → (icon, text)           │   │
│  └──────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Configuration Layer                          │
│  ~/.config/claw-cron/config.yaml                                 │
│  channels:                                                       │
│    qqbot: { app_id, client_secret, enabled, created_at }        │
│    feishu: { app_id, app_secret, enabled, created_at }          │
│    wechat: { corp_id, agent_id, secret, enabled, created_at }   │
├─────────────────────────────────────────────────────────────────┤
│                        Storage Layer                             │
│  ~/.config/claw-cron/contacts.yaml                               │
│  contacts:                                                       │
│    me: { openid, channel, alias, created }                      │
└─────────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 职责 | 实现方式 |
|------|------|----------|
| `MessageChannel` | 通道抽象接口，定义统一发送 API | ABC + @abstractmethod |
| `CHANNEL_REGISTRY` | 通道注册表，支持动态发现 | dict[channel_id, channel_class] |
| `get_channel()` | 通道工厂函数 | 根据 channel_id 实例化通道 |
| `get_channel_status()` | 配置状态检查 | 读取 config.yaml，验证必填字段 |
| `channels.py` | CLI 命令组 | Click + InquirerPy 交互 |
| `prompt_channel_select()` | 通道选择交互 | 从 CHANNEL_REGISTRY 构建选项列表 |

## 1. WechatChannel 实现要点

### 1.1 继承 MessageChannel 的方法

**必须实现:**
```python
class WechatChannel(MessageChannel):
    @property
    def channel_id(self) -> str:
        return "wechat"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        # 企业微信消息发送 API
        pass

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        # 企业微信支持 markdown，直接发送
        pass
```

**可选实现:**
```python
    async def health_check(self) -> bool:
        # 验证 access_token 是否有效
        pass
```

### 1.2 新增配置项

**WechatConfig (企业微信应用):**
```python
class WechatConfig(BaseSettings, ChannelConfig):
    corp_id: str | None = Field(
        default=None,
        description="企业 ID from work.weixin.qq.com"
    )
    agent_id: str | None = Field(
        default=None,
        description="应用 AgentId"
    )
    secret: str | None = Field(
        default=None,
        description="应用 Secret"
    )

    class Config:
        env_prefix = "CLAW_CRON_WECHAT_"
```

**config.yaml 结构:**
```yaml
channels:
  wechat:
    corp_id: "ww1234567890abcdef"
    agent_id: "1000001"
    secret: "abc123..."
    enabled: true
    created_at: "2026-04-17T10:00:00"
```

### 1.3 Recipient 格式

**企业微信用户标识:**
- `touser`: 成员 UserID（企业通讯录中的账号）
- 格式: 直接使用 UserID，如 `"wxnacy"`
- 或使用别名: `"c2c:wxnacy"` (与其他通道保持一致)

**与 QQ/Feishu 的差异:**
| 通道 | 用户标识 | 来源 |
|------|---------|------|
| QQ Bot | openid (bot-specific) | 需 WebSocket 捕获 |
| Feishu | open_id (bot-specific) | 需 WebSocket 捕获 |
| Wechat | UserID (企业通讯录) | **已知，无需捕获** |

**关键差异:** 企业微信不需要 capture 流程！UserID 在企业通讯录中已知。

### 1.4 Token 管理

**企业微信 access_token:**
```python
@dataclass
class WechatTokenInfo:
    access_token: str
    expires_at: float  # 7200s 有效期

async def _get_access_token(self) -> str:
    # 缓存逻辑类似 QQBot
    # API: https://qyapi.weixin.qq.com/cgi-bin/gettoken
    #      ?corpid=CORPID&corpsecret=SECRET
    pass
```

### 1.5 消息发送 API

**企业微信发送消息:**
```python
async def send_text(self, recipient: str, content: str) -> MessageResult:
    token = await self._get_access_token()
    # API: https://qyapi.weixin.qq.com/cgi-bin/message/send
    payload = {
        "touser": recipient,
        "msgtype": "text",
        "agentid": self.config.agent_id,
        "text": {"content": content}
    }
    # POST with access_token parameter
    pass
```

## 2. Capture 交互改进

### 2.1 现有 Capture 流程分析

**QQ Bot Capture:**
```
channels capture --channel-type qqbot --alias me
    ↓
WebSocket 连接 → 等待用户发消息 → 提取 openid → 保存为 Contact
```

**Feishu Capture:**
```
channels capture --channel-type feishu --alias me
    ↓
lark.ws.Client → 等待用户发消息 → 提取 open_id → 保存为 Contact
```

**iMessage/Email:** 无需 capture (已知标识)

### 2.2 统一不同通道的 Capture 流程

**方案 A: 通道声明 capture 能力 (推荐)**

```python
class MessageChannel(ABC):
    @property
    def supports_capture(self) -> bool:
        """通道是否支持 capture 流程"""
        return False

    async def capture_openid(self, alias: str) -> str | None:
        """捕获用户 openid (仅支持 capture 的通道实现)"""
        raise NotImplementedError(
            f"{self.channel_id} does not support capture"
        )
```

**实现示例:**
```python
class QQBotChannel(MessageChannel):
    @property
    def supports_capture(self) -> bool:
        return True

    async def capture_openid(self, alias: str) -> str | None:
        # WebSocket capture 逻辑
        pass

class IMessageChannel(MessageChannel):
    @property
    def supports_capture(self) -> bool:
        return False  # iMessage 使用电话号码/邮箱，无需 capture

class WechatChannel(MessageChannel):
    @property
    def supports_capture(self) -> bool:
        return False  # 企业微信使用已知 UserID，无需 capture
```

**capture 命令改进:**
```python
@channels.command()
@click.option("--channel-type", type=click.Choice(["qqbot", "feishu"]))
@click.option("--alias", default="me")
def capture(channel_type: str, alias: str) -> None:
    channel = get_channel(channel_type)

    if not channel.supports_capture:
        console.print(f"[yellow]{channel_type} 不需要 capture 流程[/yellow]")
        console.print(f"[dim]直接使用已知标识符发送消息[/dim]")
        return

    openid = await channel.capture_openid(alias)
    if openid:
        save_contact(Contact(openid=openid, channel=channel_type, alias=alias))
```

### 2.3 验证后自动触发 Capture

**当前 add 命令流程:**
```python
@channels.command()
@click.option("--capture-openid", is_flag=True)
def add(capture_openid: bool) -> None:
    # 1. 选择通道类型
    # 2. 输入凭证
    # 3. 验证凭证
    # 4. 保存配置
    if capture_openid:
        # 手动触发 capture
        asyncio.run(_capture_qqbot_openid(alias="me"))
```

**改进方案:**

**方案 B: 验证成功后自动询问 (推荐)**

```python
@channels.command()
@click.option("--capture-openid", is_flag=True, default=None)
def add(capture_openid: bool | None) -> None:
    # ... 验证凭证并保存 ...

    # 检查通道是否需要 capture
    channel = get_channel(channel_type)

    if channel.supports_capture:
        if capture_openid is None:
            # 未指定 --capture-openid，询问用户
            do_capture = prompt_confirm(
                "是否立即获取用户 OpenID?",
                default=True
            )
        else:
            do_capture = capture_openid

        if do_capture:
            console.print("\n[bold]步骤 2: 获取用户 OpenID[/bold]\n")
            asyncio.run(_capture_openid(channel_type, alias="me"))
    else:
        console.print(f"[dim]{channel_type} 无需 capture，直接使用已知标识符[/dim]")
```

**优化点:**
1. 自动判断是否需要 capture (`channel.supports_capture`)
2. 未指定 flag 时询问用户，而非强制手动指定
3. 不支持 capture 的通道给出友好提示

### 2.4 Capture 实现统一接口

**重构 capture 实现:**

```python
async def _capture_openid(channel_type: str, alias: str) -> None:
    """统一的 capture 入口"""
    config = load_config()
    channel_config = config.get("channels", {}).get(channel_type, {})

    channel = get_channel(channel_type, config=channel_config)

    try:
        openid = await channel.capture_openid(alias)
        if openid:
            contact = Contact(
                openid=openid,
                channel=channel_type,
                alias=alias,
                created=datetime.now().isoformat(),
            )
            save_contact(contact)
            console.print(f"[green]✓ Contact saved as '[bold]{alias}[/bold]'[/green]")
    except NotImplementedError:
        console.print(f"[yellow]{channel_type} 不支持 capture[/yellow]")
    except Exception as e:
        console.print(f"[red]Capture failed: {e}[/red]")
        raise SystemExit(1)
```

**通道特定实现移入 Channel 类:**
```python
class QQBotChannel(MessageChannel):
    async def capture_openid(self, alias: str) -> str | None:
        # 原 _capture_qqbot_openid 逻辑
        # WebSocket 连接 → 等待消息 → 返回 openid
        pass

class FeishuChannel(MessageChannel):
    async def capture_openid(self, alias: str) -> str | None:
        # 原 _capture_feishu_openid 逻辑
        # lark.ws.Client → 等待消息 → 返回 openid
        pass
```

## 3. 建议的实现顺序

### Phase 1: 架构增强 (新建基础)

**优先级:** 高 (为后续功能提供基础)

**任务:**
1. **MessageChannel 增加 capture 支持**
   - 新增 `supports_capture` 属性
   - 新增 `capture_openid()` 方法 (默认 raise NotImplementedError)

2. **重构现有通道实现**
   - QQBotChannel 实现 `capture_openid()`
   - FeishuChannel 实现 `capture_openid()`
   - IMessageChannel/EmailChannel 设置 `supports_capture = False`

3. **统一 capture 命令逻辑**
   - 提取 `_capture_openid()` 为通用入口
   - 移除通道特定的 `_capture_qqbot_openid` / `_capture_feishu_openid`

**文件修改:**
- `src/claw_cron/channels/base.py` (新增属性和方法)
- `src/claw_cron/channels/qqbot.py` (实现 capture_openid)
- `src/claw_cron/channels/feishu.py` (实现 capture_openid)
- `src/claw_cron/channels/imessage.py` (设置 supports_capture)
- `src/claw_cron/channels/email.py` (设置 supports_capture)
- `src/claw_cron/cmd/channels.py` (统一 capture 逻辑)

**测试验证:**
- 验证 `channels capture --channel-type qqbot` 仍然工作
- 验证 `channels capture --channel-type feishu` 仍然工作

### Phase 2: Capture 交互改进 (修改现有)

**优先级:** 中 (UX 优化)

**任务:**
1. **add 命令增加自动询问逻辑**
   - 验证成功后检查 `channel.supports_capture`
   - 未指定 `--capture-openid` 时询问用户
   - 不支持 capture 的通道给出提示

2. **capture 命令增加友好提示**
   - 对不支持 capture 的通道提示"无需 capture"
   - 显示该通道应使用的标识符类型

**文件修改:**
- `src/claw_cron/cmd/channels.py` (add 和 capture 命令)

**测试验证:**
- 验证 `channels add` 后自动询问 capture
- 验证 `channels capture --channel-type imessage` 提示无需 capture

### Phase 3: WechatChannel 实现 (新建组件)

**优先级:** 高 (核心功能)

**任务:**
1. **新建 wechat.py**
   - 实现 `WechatConfig` 配置类
   - 实现 `WechatChannel` 类
   - 实现 token 管理 (类似 QQBot)
   - 实现 `send_text()` 和 `send_markdown()`

2. **注册通道**
   - 在 `__init__.py` 中导入并注册
   - 更新 `get_channel_status()` 增加 wechat 验证逻辑

3. **add 命令增加 wechat 配置流程**
   - 交互式输入 corp_id, agent_id, secret
   - 验证凭证 (调用 gettoken API)
   - 保存配置

4. **verify 命令增加 wechat 验证**
   - 验证 access_token 获取
   - 显示企业信息

**文件新建:**
- `src/claw_cron/channels/wechat.py`

**文件修改:**
- `src/claw_cron/channels/__init__.py` (注册 wechat)
- `src/claw_cron/cmd/channels.py` (add 和 verify 命令)

**测试验证:**
- 验证 `channels add` 能选择 wechat
- 验证凭证验证正确
- 验证 `channels verify wechat` 工作
- 验证 `send_text()` 发送消息成功

### Phase 4: 飞书 Capture 交互增强 (修改现有)

**优先级:** 中 (需求要求)

**任务:**
1. **飞书 capture 交互式列表选择**
   - 获取用户最近联系人列表
   - InquirerPy 列表选择
   - 保存选中的联系人

**注意:** 飞书 API 是否支持获取联系人列表需要调研。

**文件修改:**
- `src/claw_cron/channels/feishu.py` (增加获取联系人方法)
- `src/claw_cron/cmd/channels.py` (capture 命令增加交互)

**测试验证:**
- 验证飞书 capture 显示联系人列表
- 验证选择后正确保存

### Phase 5: 版本升级 (修改配置)

**优先级:** 低 (收尾工作)

**任务:**
1. 更新 `pyproject.toml` 版本号到 0.2.1
2. 更新 `PROJECT.md` 里程碑状态

**文件修改:**
- `pyproject.toml`
- `.planning/PROJECT.md`

## 依赖关系图

```
Phase 1 (架构增强)
    ↓
    ├──→ Phase 2 (Capture 交互改进)
    │        ↓
    └──→ Phase 3 (WechatChannel 实现)
             ↓
         Phase 4 (飞书 Capture 增强)
             ↓
         Phase 5 (版本升级)
```

**并行可能性:**
- Phase 2 和 Phase 3 可以并行进行 (都依赖 Phase 1，但相互独立)
- Phase 4 需要等待 Phase 3 完成 (可能复用交互逻辑)
- Phase 5 最后执行

## 新建 vs 修改清单

### 新建文件

| 文件 | 用途 | Phase |
|------|------|-------|
| `src/claw_cron/channels/wechat.py` | 企业微信通道实现 | Phase 3 |

### 修改文件

| 文件 | 修改内容 | Phase |
|------|---------|-------|
| `src/claw_cron/channels/base.py` | 新增 `supports_capture` 属性和 `capture_openid()` 方法 | Phase 1 |
| `src/claw_cron/channels/qqbot.py` | 实现 `capture_openid()` | Phase 1 |
| `src/claw_cron/channels/feishu.py` | 实现 `capture_openid()`，增强联系人获取 | Phase 1, 4 |
| `src/claw_cron/channels/imessage.py` | 设置 `supports_capture = False` | Phase 1 |
| `src/claw_cron/channels/email.py` | 设置 `supports_capture = False` | Phase 1 |
| `src/claw_cron/channels/__init__.py` | 注册 wechat 通道 | Phase 3 |
| `src/claw_cron/cmd/channels.py` | 统一 capture 逻辑，增加自动询问，增加 wechat 配置 | Phase 1, 2, 3 |
| `pyproject.toml` | 版本号升级 | Phase 5 |
| `.planning/PROJECT.md` | 更新里程碑状态 | Phase 5 |

## 关键决策点

### D-01: WechatChannel 是否需要 capture?

**决策:** NO

**原因:**
- 企业微信使用企业通讯录中的 UserID
- UserID 是已知标识，不需要通过消息捕获
- 与 QQ/Feishu 的 bot-specific openid 机制不同

**影响:**
- `WechatChannel.supports_capture = False`
- add 命令配置完成后提示"直接使用 UserID 发送消息"

### D-02: Capture 逻辑是否移入 Channel 类?

**决策:** YES (推荐)

**原因:**
- 封装通道特定逻辑到对应类
- 统一 capture 命令入口
- 便于后续扩展新通道

**影响:**
- 需要 Phase 1 架构重构
- QQBotChannel 和 FeishuChannel 增加 `capture_openid()` 方法

### D-03: 企业微信使用哪个 API?

**决策:** 企业微信应用消息 API (非机器人)

**原因:**
- 项目定位为"通知工具"，不需要机器人对话能力
- 应用消息 API 更简单，支持全员推送
- 与 QQ Bot/Feishu Bot 定位一致

**API 端点:**
- 获取 token: `https://qyapi.weixin.qq.com/cgi-bin/gettoken`
- 发送消息: `https://qyapi.weixin.qq.com/cgi-bin/message/send`

## Sources

- 企业微信 API 文档: https://developer.work.weixin.qq.com/document/path/90236
- QQ Bot API 文档: https://bot.q.qq.com/wiki/develop/api/
- 飞书开放平台: https://open.feishu.cn/document/client-docs/bot-v3/events

---
*Architecture research for: 微信通道 & Capture 增强*
*Researched: 2026-04-17*
