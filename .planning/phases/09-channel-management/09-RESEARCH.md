# Phase 9: Channel Management Commands - Research

**Researched:** 2026-04-16
**Domain:** QQ Bot WebSocket API, Interactive CLI, Contact Management
**Confidence:** HIGH

## Summary

Phase 9 涉及三个核心技术领域：QQ Bot WebSocket 连接与事件处理、交互式 CLI 配置流程、以及联系人管理系统。研究发现 QQ 开放平台提供了完整的 WebSocket Gateway API，OpenClaw 项目已有成熟的实现可供参考，Python websockets 库（v16.0）支持开箱即用的心跳和重连机制，Click 框架提供了完善的交互式提示功能。

**Primary recommendation:** 采用 websockets 库建立 WebSocket 客户端，使用 Click 的 password_option 和 prompt 实现交互式配置，参考 OpenClaw 的消息处理流程实现 OpenID 自动捕获。

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| websockets | 16.0 | WebSocket 客户端 | Python 标准 WebSocket 库，支持 asyncio/threading 双模式，内置 ping/pong |
| click | ^8.0 | CLI 框架 | 项目已使用，提供 prompt、password_option 等交互功能 |
| rich | 14.3.3 | 终端美化 | 项目已使用，提供 status spinner 和彩色输出 |
| pyyaml | ^6.0 | 配置存储 | 项目已使用，存储通道配置和联系人数据 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | ^0.27 | HTTP 客户端 | 已在 qqbot.py 中使用，获取 Gateway URL 和 access_token |
| pydantic-settings | ^2.0 | 配置验证 | 已使用，验证通道配置结构 |
| asyncio | stdlib | 异步运行时 | WebSocket 连接的异步基础 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| websockets | websocket-client | websockets 支持 asyncio，更符合 Python 异步最佳实践 |
| websockets | aiohttp WebSocket | websockets 库更轻量，专注于 WebSocket 协议 |
| Click prompt | inquirer | Click 已集成，无需引入额外依赖 |

**Installation:**
```bash
# 已安装依赖，无需额外安装
# websockets 已在环境中 (v16.0)
# rich 已在项目依赖中 (v14.3.3)
# click 已在项目依赖中
```

**Version verification:**
- websockets: 16.0 (已验证)
- rich: 14.3.3 (已验证)
- click: 已在 pyproject.toml 中

## Architecture Patterns

### Recommended Project Structure
```
src/claw_cron/
├── cmd/
│   └── channels.py          # channels 命令组
├── qqbot/
│   ├── __init__.py          # 导出
│   ├── websocket.py         # WebSocket 客户端
│   └── events.py            # 事件类型定义
├── contacts.py              # 联系人管理
└── config.py                # 扩展配置（channels 部分）
```

### Pattern 1: WebSocket 客户端架构

**What:** 基于 websockets 库的异步 WebSocket 客户端，支持心跳、重连、事件分发。

**When to use:** QQ Bot 连接，接收消息事件。

**Example:**
```python
# WebSocket 客户端核心结构
import asyncio
import websockets
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

class OpCode(Enum):
    DISPATCH = 0           # 事件分发
    HEARTBEAT = 1          # 心跳
    IDENTIFY = 2           # 鉴权
    HELLO = 10             # 服务端 Hello
    HEARTBEAT_ACK = 11     # 心跳响应

@dataclass
class GatewayConfig:
    app_id: str
    access_token: str
    intents: int = 1 << 25  # C2C_MESSAGE_CREATE

class QQBotWebSocket:
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.heartbeat_interval: int = 45000  # 默认 45 秒
        self.session_id: str | None = None
        self.seq: int | None = None
        
    async def connect(self, gateway_url: str) -> None:
        """建立 WebSocket 连接"""
        async with websockets.connect(
            gateway_url,
            ping_interval=None,  # 禁用内置 ping，使用 QQ 协议的心跳
            ping_timeout=None,
        ) as ws:
            self.ws = ws
            await self._receive_loop()
    
    async def _receive_loop(self) -> None:
        """消息接收循环"""
        async for message in self.ws:
            data = json.loads(message)
            op = data.get("op")
            self.seq = data.get("s")  # 记录序列号
            
            if op == OpCode.HELLO.value:
                # Hello 事件：获取心跳间隔
                self.heartbeat_interval = data["d"]["heartbeat_interval"]
                asyncio.create_task(self._heartbeat_loop())
                await self._identify()
            elif op == OpCode.DISPATCH.value:
                # 事件分发
                event_type = data.get("t")
                if event_type == "READY":
                    self.session_id = data["d"]["session_id"]
                elif event_type == "C2C_MESSAGE_CREATE":
                    await self._handle_c2c_message(data["d"])
            elif op == OpCode.HEARTBEAT_ACK.value:
                pass  # 心跳响应，无需处理
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            if self.ws:
                await self.ws.send(json.dumps({
                    "op": OpCode.HEARTBEAT.value,
                    "d": self.seq
                }))
    
    async def _identify(self) -> None:
        """发送鉴权请求"""
        await self.ws.send(json.dumps({
            "op": OpCode.IDENTIFY.value,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.access_token}",
                "intents": self.config.intents,
                "shard": [0, 1],
                "properties": {}
            }
        }))
    
    async def _handle_c2c_message(self, event_data: dict) -> None:
        """处理 C2C 消息事件"""
        openid = event_data["author"]["user_openid"]
        content = event_data.get("content", "")
        # 触发回调或事件
        if self.on_message:
            await self.on_message(openid, content)
```

**Source:** QQ Bot 官方文档 + OpenClaw 实现分析

### Pattern 2: Click 交互式配置

**What:** 使用 Click 的 prompt、password_option 实现交互式通道配置。

**When to use:** `claw-cron channels add` 命令。

**Example:**
```python
import click
from rich.console import Console
from rich.status import Status

console = Console()

@click.group()
def channels():
    """Manage message channels."""
    pass

@channels.command()
@click.option('--channel-type', 
              type=click.Choice(['qqbot'], case_sensitive=False),
              prompt='Channel type',
              help='Type of channel to configure')
@click.option('--app-id', 
              prompt='AppID',
              help='QQ Bot AppID from q.qq.com')
@click.option('--client-secret',
              prompt=True,
              hide_input=True,  # 隐藏输入
              confirmation_prompt=True,  # 确认密码
              help='QQ Bot Client Secret')
@click.option('--capture-openid', 
              is_flag=True,
              default=False,
              prompt='Connect now to capture openid?',
              help='Start WebSocket to capture user openid')
def add(channel_type: str, app_id: str, client_secret: str, capture_openid: bool):
    """Add a new message channel configuration."""
    # 验证凭据
    with console.status("[bold green]Validating credentials...") as status:
        try:
            token = validate_qqbot_credentials(app_id, client_secret)
            console.print("[green]✓ Credentials validated[/green]")
        except Exception as e:
            console.print(f"[red]✗ Validation failed: {e}[/red]")
            raise click.Abort()
    
    # 保存配置
    save_channel_config(channel_type, app_id, client_secret)
    console.print(f"[green]✓ Channel '{channel_type}' configured[/green]")
    
    # 可选：捕获 openid
    if capture_openid:
        asyncio.run(capture_user_openid(app_id, token))

def validate_qqbot_credentials(app_id: str, client_secret: str) -> str:
    """验证 QQ Bot 凭据并返回 access_token"""
    import httpx
    
    response = httpx.post(
        "https://bots.qq.com/app/getAppAccessToken",
        json={"appId": app_id, "clientSecret": client_secret}
    )
    data = response.json()
    if data.get("code", 0) != 0:
        raise ValueError(data.get("message", "Unknown error"))
    return data["access_token"]
```

**Source:** Click 官方文档 - Options Shortcut Decorators

### Pattern 3: 联系人管理

**What:** YAML 文件存储联系人别名与 openid 映射。

**When to use:** remind 命令使用别名代替 openid。

**Example:**
```python
# contacts.py
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
from typing import Any
import yaml

CONTACTS_FILE = Path.home() / ".config" / "claw-cron" / "contacts.yaml"

@dataclass
class Contact:
    openid: str
    channel: str
    alias: str
    created: str
    last_message: str | None = None

def load_contacts(path: Path = CONTACTS_FILE) -> dict[str, Contact]:
    """加载联系人"""
    if not path.exists():
        return {}
    
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    
    return {
        alias: Contact(**info) 
        for alias, info in data.get("contacts", {}).items()
    }

def save_contact(contact: Contact, path: Path = CONTACTS_FILE) -> None:
    """保存联系人"""
    contacts = load_contacts(path)
    contacts[contact.alias] = contact
    
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump({
            "contacts": {alias: asdict(c) for alias, c in contacts.items()}
        }, f, allow_unicode=True)

def resolve_recipient(recipient: str, channel: str) -> str:
    """解析收件人：别名 → openid 格式
    
    Args:
        recipient: 收件人标识（别名或 openid 格式）
        channel: 通道名称
    
    Returns:
        格式化的收件人字符串（如 "c2c:OPENID"）
    
    Raises:
        ValueError: 别名不存在
    """
    # 如果已经是 openid 格式，直接返回
    if recipient.startswith("c2c:") or recipient.startswith("group:"):
        return recipient
    
    # 尝试解析别名
    contacts = load_contacts()
    if recipient in contacts:
        contact = contacts[recipient]
        if contact.channel == channel:
            return f"c2c:{contact.openid}"
        raise ValueError(
            f"Contact '{recipient}' is for channel '{contact.channel}', "
            f"not '{channel}'"
        )
    
    # 别名不存在
    available = list(contacts.keys())
    raise ValueError(
        f"Contact alias '{recipient}' not found. "
        f"Available: {available}" if available else "No contacts saved."
    )
```

**Source:** 项目需求 + YAML 存储模式

### Anti-Patterns to Avoid

- **直接使用 `websockets.connect` 而不处理重连** — QQ 连接会因网络波动断开，必须实现 Resume 机制
- **忽略心跳间隔** — 必须从 Hello 事件获取 heartbeat_interval，不能硬编码
- **混用不同 bot 的 openid** — openid 与 appId 绑定，跨 bot 使用会导致 500 错误
- **在命令中直接使用 asyncio.run()** — 应使用 `anyio` 或 Click 的异步支持

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket 心跳 | 手写 ping/pong 循环 | websockets 内置 + QQ 协议心跳 | 协议细节复杂，容易出错 |
| 密码输入隐藏 | 自己实现终端控制 | Click password_option | 已处理终端兼容性 |
| YAML 配置解析 | 手写 YAML 读写 | pyyaml + pydantic | 类型验证和默认值处理 |
| 重连逻辑 | 简单 while 循环 | 指数退避 + session_id 恢复 | 避免服务器压力和无限重试 |

**Key insight:** QQ Bot WebSocket 协议已有成熟的实现模式（OpenClaw），应参考而非重新设计。

## Common Pitfalls

### Pitfall 1: OpenID 跨 Bot 使用

**What goes wrong:** 使用 Bot A 捕获的 openid 通过 Bot B 发送消息，导致 HTTP 500 错误。

**Why it happens:** QQ 开放平台的 openid 是 bot-specific 的，每个 bot 有独立的用户标识体系。

**How to avoid:** 
- 存储联系人时记录对应的 channel 和 app_id
- 发送消息前验证 openid 来源
- 提示用户使用正确的 bot 配置

**Warning signs:** 
- 错误日志中出现 HTTP 500
- 用户反馈消息发送失败
- 联系人配置中的 channel 与实际发送通道不匹配

### Pitfall 2: 心跳超时断连

**What goes wrong:** WebSocket 连接在运行一段时间后自动断开，不再接收消息。

**Why it happens:** 心跳未按协议要求发送，或序列号未正确更新。

**How to avoid:**
- 从 Hello 事件动态获取 heartbeat_interval
- 每次收到消息更新 seq 序列号
- 心跳发送时使用最新的 seq 值
- 实现断线重连和 Resume 机制

**Warning signs:**
- 连接在 45-60 秒后断开
- 日志中无心跳响应记录
- seq 值长时间未更新

### Pitfall 3: Resume 失败导致消息丢失

**What goes wrong:** 断线重连后无法恢复 session，丢失断线期间的消息。

**Why it happens:** Resume 需要正确的 session_id 和 seq，缺少任何一个都会创建新 session。

**How to avoid:**
- READY 事件时保存 session_id
- 断线前保存最新的 seq 值
- 重连时优先尝试 Resume（op=6）
- Resume 失败后回退到 Identify（op=2）

**Warning signs:**
- 重连后收到新的 READY 事件而非 RESUMED
- session_id 每次重连都变化
- 断线期间的消息未被投递

### Pitfall 4: 凭据验证失败但保存配置

**What goes wrong:** 用户输入错误的 AppID/Secret，配置被保存，后续使用一直失败。

**Why it happens:** 配置保存前未验证凭据有效性。

**How to avoid:**
- 保存前调用 `/app/getAppAccessToken` 验证
- 使用 Rich status 显示验证进度
- 验证失败时中断流程，不保存配置
- 提示用户检查 q.qq.com 上的配置

**Warning signs:**
- 配置保存成功但后续发送失败
- access_token 获取返回错误码
- 用户混淆 AppID 和其他标识

## Code Examples

### 获取 Gateway URL

```python
# Source: QQ Bot 官方文档
import httpx

async def get_gateway_url(access_token: str) -> str:
    """获取 WebSocket Gateway URL
    
    Args:
        access_token: OAuth2 access token
    
    Returns:
        WebSocket URL (如 "wss://api.sgroup.qq.com/websocket/")
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.sgroup.qq.com/gateway",
            headers={"Authorization": f"QQBot {access_token}"}
        )
        data = response.json()
        return data["url"]
```

### 从消息事件提取 OpenID

```python
# Source: QQ Bot 官方文档 + OpenClaw 分析
from dataclasses import dataclass
from datetime import datetime

@dataclass
class C2CMessage:
    openid: str           # author.user_openid
    union_openid: str     # author.union_openid (跨 bot 标识)
    content: str          # 消息文本内容
    message_id: str       # 平台消息 ID
    timestamp: datetime   # 消息时间

def parse_c2c_message(event_data: dict) -> C2CMessage:
    """解析 C2C_MESSAGE_CREATE 事件
    
    Event structure:
    {
        "author": {
            "user_openid": "E4F4AEA33253A2797FB897C50B81D7ED",
            "union_openid": "..."  # 可选
        },
        "content": "hello",
        "id": "ROBOT1.0_.b6nx.CVryAO0nR58RXuU6SC...",
        "timestamp": "2023-11-06T13:37:18+08:00"
    }
    """
    author = event_data["author"]
    return C2CMessage(
        openid=author["user_openid"],
        union_openid=author.get("union_openid", ""),
        content=event_data.get("content", ""),
        message_id=event_data["id"],
        timestamp=datetime.fromisoformat(event_data["timestamp"])
    )
```

### WebSocket 断线重连

```python
# Source: websockets 最佳实践 + QQ 协议
import asyncio
import websockets
from typing import Optional

class ReconnectingWebSocket:
    def __init__(self, gateway_url: str, config: GatewayConfig):
        self.gateway_url = gateway_url
        self.config = config
        self.session_id: Optional[str] = None
        self.seq: Optional[int] = None
        self.max_retries = 5
        self.retry_delay = 1  # 初始延迟（秒）
    
    async def connect(self) -> None:
        """建立连接，支持自动重连"""
        retries = 0
        while retries < self.max_retries:
            try:
                async with websockets.connect(
                    self.gateway_url,
                    ping_interval=None,
                    ping_timeout=None,
                ) as ws:
                    print("✓ Connected to QQ Bot Gateway")
                    retries = 0  # 重置重试计数
                    await self._handle_connection(ws)
            except Exception as e:
                retries += 1
                print(f"Connection lost: {e}. Retrying {retries}/{self.max_retries}")
                await asyncio.sleep(self.retry_delay * (2 ** (retries - 1)))  # 指数退避
    
    async def _handle_connection(self, ws) -> None:
        """处理连接生命周期"""
        hello_received = False
        
        async for message in ws:
            data = json.loads(message)
            op = data.get("op")
            self.seq = data.get("s")
            
            if op == 10:  # Hello
                hello_received = True
                self.heartbeat_interval = data["d"]["heartbeat_interval"]
                asyncio.create_task(self._heartbeat_loop(ws))
                
                # 尝试 Resume 或 Identify
                if self.session_id and self.seq:
                    await self._resume(ws)
                else:
                    await self._identify(ws)
            
            elif op == 0:  # Dispatch
                event_type = data.get("t")
                if event_type == "READY":
                    self.session_id = data["d"]["session_id"]
                    print("✓ Session established")
                elif event_type == "RESUMED":
                    print("✓ Session resumed")
                elif event_type == "C2C_MESSAGE_CREATE":
                    await self._handle_message(data["d"])
    
    async def _resume(self, ws) -> None:
        """恢复会话"""
        await ws.send(json.dumps({
            "op": 6,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.access_token}",
                "session_id": self.session_id,
                "seq": self.seq
            }
        }))
    
    async def _identify(self, ws) -> None:
        """新建会话"""
        await ws.send(json.dumps({
            "op": 2,
            "d": {
                "token": f"Bot {self.config.app_id}.{self.config.access_token}",
                "intents": 1 << 25,  # C2C_MESSAGE_CREATE
                "shard": [0, 1],
                "properties": {}
            }
        }))
```

### Rich Status Spinner

```python
# Source: Rich 官方文档
from rich.console import Console
import asyncio

console = Console()

async def capture_openid_with_spinner(app_id: str, token: str):
    """捕获 openid 并显示进度"""
    console.print("\n[bold]Step 2: Capture User OpenID[/bold]\n")
    
    with console.status(
        "[bold green]Connecting to QQ Bot WebSocket...",
        spinner="dots"
    ) as status:
        # 连接 WebSocket
        ws_client = await connect_to_gateway(app_id, token)
        status.update("[bold green]✓ Connected! Waiting for message...")
        
        # 等待用户发送消息
        openid = await wait_for_c2c_message(ws_client)
        status.update(f"[bold green]✓ OpenID captured: {openid}")
        
        console.print(f"\n[green]✓ OpenID captured: [bold]{openid}[/bold][/green]\n")
        
        # 提示保存别名
        alias = click.prompt("Save as contact alias", default="me")
        save_contact(Contact(
            openid=openid,
            channel="qqbot",
            alias=alias,
            created=datetime.now().isoformat()
        ))
        
        console.print(f"[green]✓ Contact saved as '{alias}'[/green]")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 手动编辑 config.yaml | 交互式 CLI 配置 | 本阶段 | 降低配置错误，提升用户体验 |
| 手动查找 openid | WebSocket 自动捕获 | 本阶段 | 无需访问开发者工具 |
| 直接使用 openid | 联系人别名系统 | 本阶段 | 简化 remind 命令使用 |
| 无连接管理 | WebSocket 心跳 + Resume | 本阶段 | 稳定的长连接，断线恢复 |

**Deprecated/outdated:**
- QQ Bot 主动推送 API（2025年4月后取消）→ 使用 WebSocket 接收消息
- botpy SDK → 直接使用 websockets 库（更灵活）

## Open Questions

1. **是否需要支持多个 QQ Bot 账号？**
   - What we know: OpenClaw 支持 accounts 配置，每个账号独立连接
   - What's unclear: 用户是否有多个 bot 的需求
   - Recommendation: 初期实现单账号，架构预留多账号扩展

2. **WebSocket 连接的生命周期管理？**
   - What we know: 需要在 channels add 后启动，捕获 openid 后关闭
   - What's unclear: 是否需要长期运行的 WebSocket 服务
   - Recommendation: 按需启动（capture_openid 时），任务完成后关闭

3. **联系人存储位置？**
   - What we know: 可放在 config.yaml 或独立的 contacts.yaml
   - What's unclear: 是否需要支持导入/导出
   - Recommendation: 使用独立的 contacts.yaml，便于管理和备份

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| websockets | WebSocket 客户端 | ✓ | 16.0 | — |
| click | 交互式 CLI | ✓ | ^8.0 (project) | — |
| rich | 终端美化 | ✓ | 14.3.3 | — |
| httpx | HTTP 请求 | ✓ | ^0.27 (project) | — |
| pyyaml | 配置存储 | ✓ | ^6.0 (project) | — |
| asyncio | 异步运行时 | ✓ | stdlib | — |

**Missing dependencies with no fallback:**
- None — 所有必需依赖已就绪

**Missing dependencies with fallback:**
- None — 无需备用方案

## Sources

### Primary (HIGH confidence)
- QQ Bot 官方文档 - WebSocket API reference: https://bot.q.qq.com/wiki/develop/api-v2/dev-prepare/interface-framework/reference.html
- QQ Bot 官方文档 - 事件类型: https://bot.q.qq.com/wiki/develop/api-v2/server-inter/message/send-receive/event.html
- Click 官方文档 - Options Shortcut Decorators: https://click.palletsprojects.com/en/stable/option-decorators/
- websockets 官方文档: https://websockets.readthedocs.io/

### Secondary (MEDIUM confidence)
- OpenClaw QQ Bot 插件: https://docs.openclaw.ai/zh-CN/channels/qqbot
- OpenClaw GitHub 仓库: https://github.com/tencent-connect/openclaw-qqbot
- OpenClaw C2C 消息处理: https://deepwiki.com/tencent-connect/openclaw-qqbot/7.1-c2c-private-messages

### Tertiary (LOW confidence)
- Rich Console 文档: https://rich.readthedocs.io/en/stable/console.html
- Python websockets 心跳实现: 多篇博客文章（已验证核心概念）

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - 所有库已安装并验证版本，项目已有使用经验
- Architecture: HIGH - QQ Bot API 官方文档完整，OpenClaw 提供实现参考
- Pitfalls: HIGH - 官方文档和社区实践已明确常见问题

**Research date:** 2026-04-16
**Valid until:** 90 days（QQ Bot API 相对稳定，但需关注平台更新）
