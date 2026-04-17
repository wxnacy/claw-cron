# Phase 14: Architecture Enhancement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 14-architecture-enhancement
**Areas discussed:** 属性设计, 方法签名, 错误处理, 超时机制, UI层分离, 参数设计, 配置依赖, 异常类型, capture命令接口

---

## supports_capture 属性设计

| Option | Description | Selected |
|--------|-------------|----------|
| @property 方法 | 更语义化、类型安全，子类只需覆盖方法返回 True/False。基类默认返回 False。 | ✓ |
| 类属性 | 简单直接，但需要子类显式设置类属性，容易被遗忘。 | |

**User's choice:** @property 方法
**Notes:** 更符合 Python 风格，避免子类忘记设置属性的问题

---

## capture_openid() 方法签名

| Option | Description | Selected |
|--------|-------------|----------|
| async def capture_openid() -> str | 简单通用，capture 输出通过控制台打印，返回捕获的 open_id 字符串。 | ✓ |
| async def capture_openid(alias: str) -> dict | 更灵活，可以返回 alias 等额外信息，但调用方需要处理 dict。 | |

**User's choice:** async def capture_openid() -> str
**Notes:** 保持方法签名简单，调用方负责保存联系人

---

## 不支持 capture 的通道处理

| Option | Description | Selected |
|--------|-------------|----------|
| 抛出 NotImplementedError | 基类默认抛出 NotImplementedError，明确告知该通道不支持 capture。 | ✓ |
| 返回 None | 不抛异常，调用方需先检查 supports_capture 属性。 | |

**User's choice:** 抛出 NotImplementedError
**Notes:** 与 MessageChannel 其他可选方法（如 send_template）保持一致

---

## 超时机制实现位置

| Option | Description | Selected |
|--------|-------------|----------|
| 在 capture_openid() 方法参数中设置 | 每个通道可以根据平台特性设置不同的超时时间。 | ✓ |
| 在 capture 命令层面统一设置 | 所有通道统一超时时间，简单但不够灵活。 | |

**User's choice:** 在 capture_openid() 方法参数中设置
**Notes:** 提供更好的灵活性，不同通道可以有不同的默认超时时间

---

## UI 层分离

| Option | Description | Selected |
|--------|-------------|----------|
| capture_openid() 只负责捕获逻辑 | capture_openid() 返回纯数据，UI 显示由 cmd/channels.py 负责。更清晰的关注点分离。 | ✓ |
| capture_openid() 内部处理 UI 显示 | capture_openid() 内部使用 Rich console 显示进度，简化调用方代码，但耦合度更高。 | |

**User's choice:** capture_openid() 只负责捕获逻辑
**Notes:** 更好的关注点分离，便于单元测试

---

## capture_openid() 参数设计

| Option | Description | Selected |
|--------|-------------|----------|
| 只捕获并返回 open_id | 保持方法简单，只返回 open_id，由调用方负责保存。更灵活，职责更清晰。 | ✓ |
| 捕获并直接保存联系人 | 方法内部保存联系人，减少调用方代码，但增加了耦合。 | |

**User's choice:** 只捕获并返回 open_id
**Notes:** 保持方法职责单一，调用方决定如何处理捕获结果

---

## 配置依赖处理

| Option | Description | Selected |
|--------|-------------|----------|
| 抛出 ChannelConfigError | 调用方在调用前检查配置，capture_openid() 假设配置已就绪。更简单的错误处理。 | ✓ |
| 方法内部加载配置 | 方法内部加载并验证配置，更健壮但增加了重复逻辑。 | |

**User's choice:** 抛出 ChannelConfigError
**Notes:** 复用现有异常体系，避免重复的配置检查逻辑

---

## 超时参数默认值

| Option | Description | Selected |
|--------|-------------|----------|
| 默认 300 秒（5分钟） | 平衡用户体验和安全性，飞书和 QQ Bot 都适合这个超时时间。 | ✓ |
| 默认 600 秒（10分钟） | 更长的等待时间，适合网络不稳定的环境。 | |

**User's choice:** 默认 300 秒（5分钟）
**Notes:** 5 分钟是合理的等待时间，足够用户完成操作

---

## capture 异常类型

| Option | Description | Selected |
|--------|-------------|----------|
| 抛出 ChannelError | 使用通道模块已有的异常类，一致性更好。 | ✓ |
| 创建新的 CaptureError 异常类 | 创建专用的 CaptureError 异常类，更精确的错误类型。 | |

**User's choice:** 抛出 ChannelError
**Notes:** 复用现有异常体系，避免创建过多异常类

---

## capture 命令接口改进

| Option | Description | Selected |
|--------|-------------|----------|
| 交互式选择通道 | 移除硬编码的 --channel-type，改为从 CHANNEL_REGISTRY 动态生成支持 capture 的通道列表。 | ✓ |
| 保持现有模式 | 保持现有 --channel-type 参数，但扩展支持更多通道。 | |

**User's choice:** 交互式选择通道
**Notes:** 动态发现支持 capture 的通道，支持未来新增通道自动发现

---

## Claude's Discretion

- WebSocket 连接管理的具体实现细节
- capture_openid() 内部的错误消息格式
- 测试用例的覆盖范围
- 是否需要 capture 进度回调（目前不需要）

## Deferred Ideas

None — discussion stayed within phase scope
