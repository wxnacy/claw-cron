# 消息通道研究报告

**项目**: claw-cron
**研究日期**: 2026-04-16
**研究模式**: Ecosystem

---

## 执行摘要

本报告研究了 OpenClaw 的消息通道 API 设计，以及如何为 claw-cron 实现 iMessage 和 QQ 的消息通知功能。研究发现：

1. **iMessage 集成**：推荐使用 `macpymessenger` 库（现代、类型安全、积极维护），而非已停止维护的 `py-iMessage`
2. **QQ 集成**：OpenClaw 已内置 QQ Bot 支持，可直接利用其 Channel Plugin 架构
3. **通道抽象设计**：参考 OpenClaw 的 14 个 Adapter 接口和 agent-summary 的 Provider 模式，建议采用"最小接口 + 渐进增强"策略

---

## 一、iMessage 集成方案

### 1.1 方案对比

| 方案 | 状态 | 推荐度 | 优势 | 劣势 |
|------|------|--------|------|------|
| **macpymessenger** | 积极维护 | ⭐⭐⭐⭐⭐ | 类型安全、模板支持、批量发送、无需禁用 SIP | 仅限 macOS |
| py-iMessage | 已停止维护 | ⭐⭐ | 支持消息状态查询 | 需禁用 SIP、仅 10 位号码、慢 |
| AppleScript 直接调用 | 可行 | ⭐⭐⭐ | 无依赖、完全控制 | 需自行处理错误、复杂消息难处理 |
| Shortcuts 自动化 | 可行 | ⭐⭐ | macOS 原生、可图形配置 | 调用复杂、不适合程序化控制 |

**推荐方案**: `macpymessenger` (v0.2.0+)

### 1.2 macpymessenger 详细分析

#### 安装要求

```bash
# 系统要求
- macOS
- Python 3.10+

# 安装
pip install macpymessenger
# 或
uv pip install macpymessenger
```

#### 核心 API

```python
from macpymessenger import IMessageClient, Configuration
from macpymessenger.exceptions import MessageSendError

# 初始化
config = Configuration()
client = IMessageClient(config)

# 发送单条消息
try:
    client.send("+8613812345678", "定时任务执行完成")
except MessageSendError as e:
    print(f"发送失败: {e}")

# 批量发送
numbers = ["+15551234567", "+15557654321"]
successful, failed = client.send_bulk(numbers, "系统告警通知")

# 使用模板发送
client.create_template("task_complete", "任务 {{ task_name }} 已完成，耗时 {{ duration }}")
client.send_template("+8613812345678", "task_complete", {
    "task_name": "数据备份",
    "duration": "5分钟"
})

# 从文件加载模板
from pathlib import Path
from macpymessenger import TemplateManager
manager = TemplateManager()
manager.load_directory(Path("./templates"))
```

#### 权限要求

- **无需禁用 SIP**：使用 AppleScript 与 Messages.app 交互，不需要访问 chat.db
- **首次运行**：macOS 会请求"辅助功能"权限，需用户批准
- **Messages.app 登录**：需确保 Messages.app 已登录 iMessage 账号

#### 限制

| 限制项 | 说明 |
|--------|------|
| 平台 | 仅 macOS，不支持 Windows/Linux |
| 消息数量 | Apple 限制每日数百条，大量营销消息会被封号 |
| 号码格式 | 支持国际格式 `+86...` 或本地格式 |
| 附件发送 | 实验性功能，暂未实现 |

### 1.3 备选方案：AppleScript 直接调用

如果不想依赖第三方库，可直接使用 AppleScript：

```python
import subprocess

def send_imessage(phone: str, message: str) -> bool:
    """通过 AppleScript 发送 iMessage"""
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = iMessage
        set targetBuddy to buddy "{phone}" of targetService
        send "{message}" to targetBuddy
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"AppleScript 错误: {e.stderr.decode()}")
        return False
```

**注意**: 此方法需要 Messages.app 已运行且已登录。

---

## 二、QQ 集成方案

### 2.1 OpenClaw 内置支持

OpenClaw 已内置 QQ Bot 插件，可直接复用其架构：

```json
// ~/.openclaw/openclaw.json
{
  "channels": {
    "qqbot": {
      "enabled": true,
      "appId": "YOUR_APP_ID",
      "clientSecret": "YOUR_CLIENT_SECRET"
    }
  }
}
```

### 2.2 QQ 开放平台 API

#### 认证方式

| 凭据 | 来源 | 用途 |
|------|------|------|
| AppID | QQ 开放平台创建机器人 | 应用标识 |
| AppSecret | 机器人设置页面 | 客户端密钥 |

#### 消息发送接口

**单聊消息**

```http
POST /v2/users/{openid}/messages
Content-Type: application/json

{
  "content": "定时任务执行完成",
  "msg_type": 0
}
```

**群聊消息**

```http
POST /v2/groups/{group_openid}/messages
Content-Type: application/json

{
  "content": "@所有人 系统维护通知",
  "msg_type": 0
}
```

**Markdown 消息**

```http
POST /v2/users/{openid}/messages
Content-Type: application/json

{
  "msg_type": 2,
  "markdown": {
    "content": "# 任务报告\n- 任务: **数据备份**\n- 状态: ✅ 成功"
  }
}
```

#### 消息类型

| msg_type | 类型 | 说明 |
|----------|------|------|
| 0 | 文本 | 纯文本消息 |
| 2 | Markdown | Markdown 格式 |
| 3 | Ark | Ark 卡片 |
| 4 | Embed | Embed 卡片 |
| 7 | 富媒体 | 图片、语音、视频、文件 |

#### 频率限制

| 场景 | 主动消息 | 被动消息 |
|------|----------|----------|
| 单聊 | 4 条/月/用户 | 60分钟有效，最多 5 次回复 |
| 群聊 | 4 条/月/群 | 5分钟有效，最多 5 次回复 |
| 文字子频道 | 20 条/天/子频道 | 5分钟有效 |

**重要**: 2025年4月21日起，QQ 已不再提供主动推送能力，被动消息需在用户交互后的时效内回复。

### 2.3 QQ Bot 集成代码示例

```python
import aiohttp
from dataclasses import dataclass

@dataclass
class QQBotConfig:
    app_id: str
    client_secret: str
    base_url: str = "https://api.sgroup.qq.com"

class QQBotClient:
    def __init__(self, config: QQBotConfig):
        self.config = config
        self._access_token: str | None = None
        self._session: aiohttp.ClientSession | None = None

    async def _get_access_token(self) -> str:
        """获取访问令牌"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.base_url}/v2/oauth2/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.client_secret,
                },
            ) as resp:
                data = await resp.json()
                return data["access_token"]

    async def send_private_message(self, openid: str, content: str) -> dict:
        """发送私聊消息"""
        if not self._access_token:
            self._access_token = await self._get_access_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.base_url}/v2/users/{openid}/messages",
                headers=headers,
                json={"content": content, "msg_type": 0},
            ) as resp:
                return await resp.json()

    async def send_group_message(self, group_openid: str, content: str) -> dict:
        """发送群聊消息"""
        if not self._access_token:
            self._access_token = await self._get_access_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.base_url}/v2/groups/{group_openid}/messages",
                headers=headers,
                json={"content": content, "msg_type": 0},
            ) as resp:
                return await resp.json()
```

---

## 三、消息通道抽象设计

### 3.1 OpenClaw Channel Plugin 架构

OpenClaw 采用 **14 个 Adapter 接口** 组合出完整的渠道能力：

```
ChannelPlugin
├── config: ChannelConfigAdapter        # ⭐ 必选 - 配置管理
├── outbound: ChannelOutboundAdapter    # ⭐ 必选 - 消息发送
├── setup: ChannelSetupAdapter          # 安装向导
├── security: ChannelSecurityAdapter    # 安全策略
├── group: ChannelGroupAdapter          # 群组策略
├── pairing: ChannelPairingAdapter      # 设备配对
├── status: ChannelStatusAdapter        # 状态监控
├── gateway: ChannelGatewayAdapter      # 网关生命周期
├── directory: ChannelDirectoryAdapter  # 联系人查询
├── resolver: ChannelResolverAdapter    # 目标解析
├── auth: ChannelAuthAdapter            # 认证流程
├── threading: ChannelThreadingAdapter  # 线程支持
├── streaming: ChannelStreamingAdapter  # 流式回复
└── heartbeat: ChannelHeartbeatAdapter  # 心跳检测
```

**设计哲学**:
- **组合优于继承**: 通过多个 Adapter 组合能力
- **最小实现**: 只需 `config` + `outbound` 即可运行
- **渐进增强**: 根据平台特性添加更多 Adapter

### 3.2 agent-summary Provider 模式

agent-summary 采用简化的 Provider 模式：

```python
# base.py - 抽象基类
from abc import ABC, abstractmethod

class BaseProvider(ABC):
    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    def summarize(self, content: str, system_prompt: str) -> SummarizeResult:
        ...

# __init__.py - 工厂函数
def get_provider(provider_name: str, api_key: str, model: str, base_url: str | None = None) -> BaseProvider:
    providers = {
        "openai": OpenAIProvider,
        "claude": AnthropicProvider,
    }
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")
    return providers[provider_name](api_key=api_key, model=model, base_url=base_url)
```

### 3.3 推荐设计：claw-cron 消息通道基类

结合两种模式的优点，建议为 claw-cron 设计如下：

```python
# src/claw_cron/channels/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

@dataclass
class MessageResult:
    """消息发送结果"""
    success: bool
    message_id: str | None = None
    error: str | None = None
    timestamp: int | None = None

@dataclass
class ChannelConfig:
    """通道配置基类"""
    enabled: bool = True

class MessageChannel(ABC):
    """消息通道抽象基类"""

    def __init__(self, config: ChannelConfig):
        self.config = config

    @property
    @abstractmethod
    def channel_id(self) -> str:
        """通道唯一标识 (如 'imessage', 'qq', 'telegram')"""
        ...

    @abstractmethod
    async def send_text(self, recipient: str, content: str) -> MessageResult:
        """发送文本消息

        Args:
            recipient: 接收者标识 (电话号码、OpenID、用户ID等)
            content: 消息内容
        """
        ...

    @abstractmethod
    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        """发送 Markdown 消息（如平台支持）"""
        ...

    async def send_template(
        self, recipient: str, template_id: str, variables: dict[str, str]
    ) -> MessageResult:
        """发送模板消息（可选实现）"""
        raise NotImplementedError(f"{self.channel_id} does not support templates")

    async def health_check(self) -> bool:
        """健康检查（可选实现）"""
        return True
```

```python
# src/claw_cron/channels/imessage.py
from .base import MessageChannel, ChannelConfig, MessageResult
from macpymessenger import IMessageClient, Configuration

class IMessageConfig(ChannelConfig):
    """iMessage 配置"""
    pass  # macpymessenger 使用系统配置，无需额外参数

class IMessageChannel(MessageChannel):
    """iMessage 消息通道"""

    def __init__(self, config: IMessageConfig | None = None):
        super().__init__(config or IMessageConfig())
        self._client = IMessageClient(Configuration())

    @property
    def channel_id(self) -> str:
        return "imessage"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        try:
            self._client.send(recipient, content)
            return MessageResult(success=True)
        except Exception as e:
            return MessageResult(success=False, error=str(e))

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        # iMessage 不支持 Markdown，作为纯文本发送
        return await self.send_text(recipient, content)
```

```python
# src/claw_cron/channels/qq.py
from .base import MessageChannel, ChannelConfig, MessageResult
import aiohttp

class QQBotConfig(ChannelConfig):
    """QQ Bot 配置"""
    app_id: str
    client_secret: str
    base_url: str = "https://api.sgroup.qq.com"

class QQBotChannel(MessageChannel):
    """QQ Bot 消息通道"""

    def __init__(self, config: QQBotConfig):
        super().__init__(config)
        self._access_token: str | None = None

    @property
    def channel_id(self) -> str:
        return "qq"

    async def _get_access_token(self) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.config.base_url}/v2/oauth2/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.client_secret,
                },
            ) as resp:
                data = await resp.json()
                return data["access_token"]

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        if not self._access_token:
            self._access_token = await self._get_access_token()

        headers = {"Authorization": f"Bearer {self._access_token}"}
        # recipient 格式: "c2c:OPENID" 或 "group:GROUP_OPENID"
        parts = recipient.split(":", 1)
        if len(parts) != 2:
            return MessageResult(success=False, error="Invalid recipient format")

        msg_type, openid = parts
        endpoint = f"{self.config.base_url}/v2/"
        if msg_type == "c2c":
            endpoint += f"users/{openid}/messages"
        elif msg_type == "group":
            endpoint += f"groups/{openid}/messages"
        else:
            return MessageResult(success=False, error=f"Unknown message type: {msg_type}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                headers=headers,
                json={"content": content, "msg_type": 0},
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    return MessageResult(
                        success=True,
                        message_id=data.get("id"),
                        timestamp=data.get("timestamp"),
                    )
                return MessageResult(success=False, error=str(data))

    async def send_markdown(self, recipient: str, content: str) -> MessageResult:
        # 类似 send_text，但 msg_type=2
        ...
```

```python
# src/claw_cron/channels/__init__.py
from .base import MessageChannel, ChannelConfig, MessageResult
from .imessage import IMessageChannel, IMessageConfig
from .qq import QQBotChannel, QQBotConfig

CHANNEL_REGISTRY: dict[str, type[MessageChannel]] = {
    "imessage": IMessageChannel,
    "qq": QQBotChannel,
}

def get_channel(channel_id: str, config: ChannelConfig) -> MessageChannel:
    """获取消息通道实例"""
    if channel_id not in CHANNEL_REGISTRY:
        raise ValueError(f"Unknown channel: {channel_id}. Available: {list(CHANNEL_REGISTRY.keys())}")
    return CHANNEL_REGISTRY[channel_id](config)
```

### 3.4 与 claw-cron 任务执行集成

```python
# src/claw_cron/notifier.py
from .channels import get_channel, MessageResult

async def notify_task_complete(task_name: str, result: str, recipients: list[str], channel_id: str):
    """任务完成后发送通知"""
    channel = get_channel(channel_id, load_channel_config(channel_id))
    content = f"✅ 任务 `{task_name}` 执行完成\n\n结果: {result}"

    for recipient in recipients:
        msg_result = await channel.send_text(recipient, content)
        if not msg_result.success:
            print(f"通知发送失败 [{recipient}]: {msg_result.error}")
```

```yaml
# ~/.config/claw-cron/tasks.yaml
- name: daily_backup
  cron: "0 2 * * *"
  type: command
  script: ./backup.sh
  notify:
    channel: imessage  # 或 qq
    recipients:
      - "+8613812345678"       # iMessage 电话号码
      # - "c2c:USER_OPENID"    # QQ 私聊
```

---

## 四、未来扩展通道

### 4.1 已知可用平台

| 平台 | 难度 | API 类型 | 推荐库 |
|------|------|----------|--------|
| Telegram | 简单 | Bot API HTTP | `python-telegram-bot` |
| Discord | 简单 | WebSocket Gateway | `discord.py` |
| Slack | 中等 | Web API + Socket Mode | `slack_sdk` |
| 微信 | 复杂 | 企业微信 API / 个人号逆向 | `wechaty` |
| 飞书 | 中等 | 开放平台 API | `lark-oapi` |
| 钉钉 | 中等 | 开放平台 API | `dingtalk-sdk` |

### 4.2 扩展设计

新增通道只需：

1. 创建配置类继承 `ChannelConfig`
2. 创建通道类继承 `MessageChannel`
3. 实现 `send_text` 和 `send_markdown` 方法
4. 注册到 `CHANNEL_REGISTRY`

```python
# src/claw_cron/channels/telegram.py
class TelegramChannel(MessageChannel):
    @property
    def channel_id(self) -> str:
        return "telegram"

    async def send_text(self, recipient: str, content: str) -> MessageResult:
        # 使用 python-telegram-bot 发送
        ...

# 注册
CHANNEL_REGISTRY["telegram"] = TelegramChannel
```

---

## 五、实施建议

### 5.1 分阶段实施

| 阶段 | 目标 | 工作量 |
|------|------|--------|
| **Phase 1** | 实现 `MessageChannel` 基类 + `IMessageChannel` | 1-2 天 |
| **Phase 2** | 与 Task 执行流程集成，支持 YAML 配置 | 1 天 |
| **Phase 3** | 实现 `QQBotChannel` | 1-2 天 |
| **Phase 4** | 扩展 Telegram/Discord/Slack 等通道 | 每个 1 天 |

### 5.2 依赖安装

```bash
# requirements.txt 或 pyproject.toml
macpymessenger>=0.2.0  # iMessage 支持
aiohttp>=3.9.0         # QQ Bot HTTP 客户端
```

### 5.3 配置文件格式

```yaml
# ~/.config/claw-cron/config.yaml
channels:
  imessage:
    enabled: true

  qq:
    enabled: true
    app_id: ${QQ_BOT_APP_ID}
    client_secret: ${QQ_BOT_CLIENT_SECRET}

  telegram:
    enabled: false
    bot_token: ${TELEGRAM_BOT_TOKEN}
```

---

## 六、来源与置信度

### 高置信度来源 (Context7/官方文档)

| 内容 | 来源 | 置信度 |
|------|------|--------|
| macpymessenger API | [官方文档](https://macpymessenger.readthedocs.io/) | HIGH |
| QQ Bot API 规范 | [QQ 机器人文档](https://bot.q.qq.com/) | HIGH |
| OpenClaw 架构设计 | [官方文档](https://docs.clawdbot.org.cn/) | HIGH |

### 中置信度来源 (WebSearch 验证)

| 内容 | 来源 | 置信度 |
|------|------|--------|
| py-iMessage 用法 | [GitHub](https://github.com/Rolstenhouse/py-iMessage) | MEDIUM |
| OpenClaw Adapter 架构 | [CSDN 分析](https://blog.csdn.net/weixin_41120248/article/details/158836972) | MEDIUM |

### 低置信度来源 (WebSearch 单源)

| 内容 | 来源 | 置信度 |
|------|------|--------|
| AppleScript 直接调用方法 | [CSDN 教程](https://blog.csdn.net/weixin_36296444/article/details/143607729) | LOW |

---

## 七、开放问题

1. **iMessage 批量发送限制**: Apple 具体的日发送限制是多少？需要进一步测试或联系 Apple 开发者支持
2. **QQ Bot OpenID 获取**: 如何在用户首次交互时获取并存储 OpenID？可能需要实现 QQ Bot 的消息接收回调
3. **多账号支持**: 是否需要支持同一通道的多个账号（如多个 QQ Bot）？

---

## 八、参考链接

- [macpymessenger 官方文档](https://macpymessenger.readthedocs.io/)
- [macpymessenger GitHub](https://github.com/ethan-wickstrom/macpymessenger)
- [py-iMessage GitHub](https://github.com/Rolstenhouse/py-iMessage)
- [QQ 机器人官方文档](https://bot.q.qq.com/)
- [QQ 开放平台](https://q.qq.com/)
- [OpenClaw 文档](https://docs.clawdbot.org.cn/)
- [OpenClaw Channel Plugin 架构分析](https://blog.csdn.net/weixin_41120248/article/details/158836972)
- [OpenClaw IM 消息通道逻辑架构](https://www.cnblogs.com/LexLuc/p/19675584)
