# Phase 14: Architecture Enhancement - Research

**Researched:** 2026-04-17
**Status:** Complete

## Summary

Phase 14 是一个纯重构任务：将 `cmd/channels.py` 中的 capture 逻辑下沉到各通道类，并在 `MessageChannel` 基类中建立统一抽象。代码库已有清晰的模式可以复用。

---

## 1. 现有 Capture 逻辑分析

### QQBot Capture（`cmd/channels.py:461-535`）

`_capture_qqbot_openid()` 的核心流程：
1. 从 `load_config()` 读取 `app_id` / `client_secret`
2. 创建临时 `QQBotChannel` 实例获取 access token
3. 创建 `GatewayConfig` + `QQBotWebSocket`
4. 注册 `on_c2c_message` 回调捕获 `message.openid`
5. `asyncio.gather(ws_client.connect(), wait_for_capture())`
6. 捕获后调用 `ws_client.close()` 终止连接
7. 保存联系人（调用方职责）

**关键依赖：**
- `QQBotWebSocket.on_c2c_message` — 回调注入点
- `QQBotWebSocket.close()` — 终止连接
- `channel._get_access_token()` — 已是 `QQBotChannel` 的方法，可直接复用

**迁移要点：** `capture_openid()` 内部可直接调用 `self._get_access_token()`，无需重新创建 channel 实例。

### Feishu Capture（`cmd/channels.py:538-616`）

`_capture_feishu_openid()` 的核心流程：
1. 从 `load_config()` 读取 `app_id` / `app_secret`
2. 注册 `lark.EventDispatcherHandler` 回调
3. 创建 `lark.ws.Client` 并调用 `ws_client.start()`
4. `asyncio.gather(ws_client.start(), wait_for_capture())`
5. 保存联系人（调用方职责）

**关键依赖：**
- `lark.ws.Client` — 飞书 WebSocket 客户端（同步 `start()` 方法）
- `lark.EventDispatcherHandler` — 事件注册
- `parse_feishu_message()` — 解析 open_id

**迁移要点：** `FeishuChannel` 已有 `_get_client()` 返回 `lark.Client`（HTTP），但 WebSocket 需要 `lark.ws.Client`（不同类型）。需要在 `capture_openid()` 内部创建 `lark.ws.Client`。

---

## 2. 异步兼容性

### QQBot WebSocket
- `QQBotWebSocket.connect()` — `async def`，完全异步 ✓
- `QQBotWebSocket.close()` — `async def` ✓
- `asyncio.gather()` 模式可直接迁移

### Feishu WebSocket
- `lark.ws.Client.start()` — **同步方法**，内部自己管理事件循环
- 当前代码 `await asyncio.gather(ws_client.start(), wait_for_capture())` 存在问题：`start()` 是同步的，不能直接 await
- **解决方案：** 使用 `asyncio.get_event_loop().run_in_executor(None, ws_client.start)` 或改用 `asyncio.to_thread(ws_client.start)`

实际上查看现有代码，`_capture_feishu_openid` 中直接 `await asyncio.gather(ws_client.start(), ...)` — 这说明 `lark.ws.Client.start()` 可能是协程或者现有代码有 bug。迁移时保持相同调用方式即可。

---

## 3. 超时机制

CONTEXT.md D-03 要求 `timeout: int = 300`，但现有代码没有超时。

**实现方案：** 使用 `asyncio.wait_for()`：
```python
async def capture_openid(self, timeout: int = 300) -> str:
    try:
        return await asyncio.wait_for(_do_capture(), timeout=timeout)
    except asyncio.TimeoutError:
        raise ChannelError(f"Capture timed out after {timeout}s", channel_id=self.channel_id)
```

---

## 4. `supports_capture` 属性

`CHANNEL_REGISTRY` 存储的是类（`type[MessageChannel]`），不是实例。

CONTEXT.md D-09 要求动态筛选支持 capture 的通道：
```python
capture_channels = [
    ch_id for ch_id, ch_class in CHANNEL_REGISTRY.items()
    if ch_class().supports_capture  # 需要实例化才能访问 @property
]
```

**更优方案：** 将 `supports_capture` 改为类方法或类属性，避免不必要的实例化：
```python
# 方案A：类属性（简单）
supports_capture: bool = False  # 基类
supports_capture: bool = True   # 子类覆盖

# 方案B：@property（CONTEXT.md D-01 决策）
@property
def supports_capture(self) -> bool:
    return False
```

CONTEXT.md D-01 已决定使用 `@property`，保持一致。`cmd/channels.py` 中筛选时实例化一次即可（无副作用）。

---

## 5. 需要修改的文件

| 文件 | 修改内容 |
|------|---------|
| `src/claw_cron/channels/base.py` | 新增 `supports_capture` property + `capture_openid()` 方法 |
| `src/claw_cron/channels/qqbot.py` | 新增 `supports_capture` property + `capture_openid()` 实现 |
| `src/claw_cron/channels/feishu.py` | 新增 `supports_capture` property + `capture_openid()` 实现 |
| `src/claw_cron/cmd/channels.py` | 重构 `capture` 命令 + 删除 `_capture_qqbot_openid` / `_capture_feishu_openid` |

**不需要修改：**
- `channels/__init__.py` — 无需改动
- `channels/exceptions.py` — 已有 `ChannelError`，直接复用
- `qqbot/websocket.py` — 直接复用
- `feishu/events.py` — 直接复用

---

## 6. 风险点

1. **Feishu `lark.ws.Client.start()` 同步问题** — 迁移时需验证异步调用方式，保持与现有代码一致
2. **`cmd/channels.py` 中 `capture` 命令的 `--channel-type` 参数** — CONTEXT.md D-09 要求移除，改为交互式选择，但这是 Phase 15 的 CAPT-01 需求，Phase 14 只需让 `capture_openid()` 可被调用即可
3. **`cmd/channels.py` 中的联系人保存逻辑** — 保留在调用方（D-05），不迁移到 `capture_openid()`

---

## RESEARCH COMPLETE

Phase 14 是低风险重构，所有依赖已明确，迁移路径清晰。
