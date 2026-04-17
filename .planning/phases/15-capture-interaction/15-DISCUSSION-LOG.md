# Phase 15: Capture Interaction - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 15-capture-interaction
**Areas discussed:** Capture 命令交互, Add 后自动 Capture, Capture 状态反馈, 不支持 Capture 的提示

---

## Capture 命令交互

| Option | Description | Selected |
|--------|-------------|----------|
| 交互式列表 | 类似 prompt_channel_select()，只列出支持 capture 的通道，无 --channel-type | ✓ |
| 混合模式 | 保留 --channel-type 可选参数，不传时弹出交互选择 | |

**User's choice:** 混合模式（后续确认移除 --channel-type，等价于纯交互式）

| Option | Description | Selected |
|--------|-------------|----------|
| 仅显示支持 capture 的 | 列表仅显示 supports_capture=True，无需判断 | ✓ |
| 显示全部通道 | 所有通道都显示，不支持的选择后给友好提示 | |

**User's choice:** 仅显示支持 capture 的

| Option | Description | Selected |
|--------|-------------|----------|
| 单通道执行 | 每次选一个通道执行 capture | ✓ |
| 多通道批量执行 | 可选多个，依次执行 | |

**User's choice:** 单通道执行

| Option | Description | Selected |
|--------|-------------|----------|
| 移除 --channel-type | 简化接口，交互选择已足够 | ✓ |
| 保留但隐藏 | 供脚本/高级用户使用 | |

**User's choice:** 移除 --channel-type

---

## Add 后自动 Capture

| Option | Description | Selected |
|--------|-------------|----------|
| 自动询问 | add 成功后弹确认框，用户确认后执行，移除 --capture-openid | ✓ |
| 默认执行 | 默认自动执行，用 --no-capture 跳过 | |

**User's choice:** 自动询问

| Option | Description | Selected |
|--------|-------------|----------|
| 仅支持 capture 的通道询问 | supports_capture=True 才询问，其他直接完成 | ✓ |
| 所有通道都询问 | 不支持的显示友好提示后结束 | |

**User's choice:** 仅支持 capture 的通道询问

| Option | Description | Selected |
|--------|-------------|----------|
| 简洁提示 | "是否立即获取用户 ID (capture)?" | ✓ |
| 详细解释 | 解释 capture 作用和好处 | |

**User's choice:** 简洁提示

| Option | Description | Selected |
|--------|-------------|----------|
| 移除 --capture-openid | 自动询问已覆盖功能 | ✓ |
| 保留但调整用途 | 用于跳过询问直接执行 | |

**User's choice:** 移除 --capture-openid

---

## Capture 状态反馈

| Option | Description | Selected |
|--------|-------------|----------|
| Rich spinner 动态提示 | console.status() 动态显示等待，捕获后切换成功消息 | ✓ |
| 静态文字提示 | "正在等待消息..." 无动画 | |

**User's choice:** Rich spinner 动态提示

| Option | Description | Selected |
|--------|-------------|----------|
| 包含通道名的提示 | "请向你的 {channel_name} 机器人发送任意消息" | ✓ |
| 通用提示 | "请发送消息以完成 capture" | |

**User's choice:** 包含通道名的提示

| Option | Description | Selected |
|--------|-------------|----------|
| 超时+重试建议 | "Capture 超时（5 分钟），请确认机器人在线后重试" | ✓ |
| 简洁超时提示 | "Capture 超时" | |

**User's choice:** 超时+重试建议

| Option | Description | Selected |
|--------|-------------|----------|
| 捕获+自动保存 | 显示结果并自动保存联系人，与现有行为一致 | ✓ |
| 捕获+询问保存 | 显示结果，询问是否保存 | |

**User's choice:** 捕获+自动保存

---

## 不支持 Capture 的提示

| Option | Description | Selected |
|--------|-------------|----------|
| 简洁提示 | "此通道不需要 capture" | |
| 带原因解释 | "此通道不需要 capture。iMessage 使用手机号直接发送，无需获取用户 ID" | ✓ |

**User's choice:** 带原因解释

| Option | Description | Selected |
|--------|-------------|----------|
| 不会出现 | 交互列表只显示支持 capture 的通道，此场景不会出现 | ✓ |
| 保留防御性检查 | 以防代码调用出错 | |

**User's choice:** 不会出现（交互式列表筛选后此场景不存在，但保留带原因的防御性检查）

---

## Claude's Discretion

- 交互式列表的显示样式
- 通道显示名映射的维护方式
- add 中询问的触发时机
- alias 参数默认值和提示
- 错误提示措辞

## Deferred Ideas

None
