# Phase 15: Capture Interaction - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

改进 capture 交互体验，自动化 capture 流程，包括：
1. **Capture 命令交互改进** — 移除 `--channel-type` 参数，改为交互式列表选择通道
2. **Add 后自动 Capture** — 移除 `--capture-openid` 参数，在 add 成功后自动询问是否执行 capture
3. **Capture 状态反馈** — 使用 Rich spinner 动态显示等待状态，包含通道名的引导提示
4. **超时机制** — 5 分钟超时，带重试建议的错误提示
5. **不支持 Capture 的处理** — 交互式列表仅显示支持 capture 的通道，保留防御性检查

不包括：新增 capture 功能（如批量捕获、自动重试）、微信 capture（Phase 16）、新的通道实现。

</domain>

<decisions>
## Implementation Decisions

### Capture 命令交互

- **D-01:** 移除 `--channel-type` 参数，改为纯交互式列表选择通道
  - 使用 InquirerPy select 组件（和 `prompt_channel_select()` 一致）
  - 仅显示 `supports_capture=True` 的通道，从 `CHANNEL_REGISTRY` 动态筛选
  - 不再需要用户记忆通道名称
- **D-02:** 交互式列表仅显示支持 capture 的通道
  - 从 `CHANNEL_REGISTRY` 中筛选 `supports_capture == True` 的通道
  - 列表带有配置状态图标（复用 `get_channel_status()`）
  - 无需用户判断通道是否支持 capture
- **D-03:** 每次只执行单个通道的 capture
  - 用户从列表选择一个通道后执行
  - 不支持多通道批量 capture

### Add 后自动 Capture

- **D-04:** 移除 `add` 命令的 `--capture-openid` 参数
  - 自动询问机制已覆盖其功能
  - 简化命令接口
- **D-05:** 仅对 `supports_capture=True` 的通道在 add 验证成功后自动询问
  - 使用 InquirerPy confirm 组件
  - 提示语简洁："是否立即获取用户 ID (capture)?"
  - 用户拒绝则正常结束 add 流程
  - 不支持 capture 的通道（imessage, email）直接完成，不询问

### Capture 状态反馈

- **D-06:** 使用 Rich `console.status()` spinner 动态显示等待状态
  - 状态文字格式："等待来自 {channel_name} 的消息..."
  - 捕获成功后切换为成功消息
  - 与现有 add/verify 中的 `console.status()` 模式一致
- **D-07:** 等待时显示包含通道名的引导提示
  - 提示格式："请向你的 {channel_name} 机器人发送任意消息"
  - channel_name 使用友好的通道显示名（如 "QQ Bot"、"飞书"）
  - 同时提示 "按 Ctrl+C 取消"
- **D-08:** 超时后显示带重试建议的错误提示
  - 错误消息："Capture 超时（5 分钟），请确认机器人在线后重试"
  - 包含具体的超时时长和重试建议
- **D-09:** Capture 成功后自动保存为联系人
  - 与现有 capture 行为一致：捕获 openid → 创建 Contact → save_contact
  - 显示 "✓ OpenID 已捕获: {openid}" 和 "✓ 联系人已保存为 '{alias}'"
  - alias 默认为 "me"（保留 `--alias` 参数）

### 不支持 Capture 的处理

- **D-10:** 交互式列表仅显示支持 capture 的通道，正常使用时此场景不会出现
  - 保留防御性检查：如果代码路径错误调用了不支持 capture 的通道，显示带原因解释的友好提示
  - 提示格式："此通道不需要 capture。{reason}"
  - reason 示例：iMessage → "iMessage 使用手机号直接发送，无需获取用户 ID"；email → "邮件使用邮箱地址直接发送"

### Claude's Discretion

- 交互式列表的显示样式（是否带描述文字）
- 通道显示名的映射（channel_id → 中文名）如何维护
- add 中自动询问的触发时机（验证成功后立即询问还是保存配置后询问）
- alias 参数的默认值和提示方式
- 错误提示的具体措辞

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类，supports_capture, capture_openid()
- `src/claw_cron/channels/qqbot.py` — QQBotChannel 实现，supports_capture=True
- `src/claw_cron/channels/feishu.py` — FeishuChannel 实现，supports_capture=True
- `src/claw_cron/channels/email.py` — EmailChannel 实现，supports_capture=False
- `src/claw_cron/channels/imessage.py` — IMessageChannel 实现，supports_capture=False
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY, get_channel(), get_channel_status()
- `src/claw_cron/channels/exceptions.py` — ChannelError, ChannelConfigError
- `src/claw_cron/cmd/channels.py` — channels 命令实现（add, capture, verify）
- `src/claw_cron/prompt.py` — prompt_channel_select(), prompt_confirm()
- `src/claw_cron/contacts.py` — Contact, save_contact()
- `src/claw_cron/config.py` — load_config(), save_config()

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — CAPT-01 至 CAPT-05

### 相关阶段上下文
- `.planning/phases/14-architecture-enhancement/14-CONTEXT.md` — Capture 抽象层设计
- `.planning/phases/13-email-channel/13-CONTEXT.md` — 邮件通道（不需要 capture 的参考）
- `.planning/phases/12-feishu-channel/12-CONTEXT.md` — 飞书通道 capture 流程

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prompt_channel_select()` — 已有带状态图标的交互式通道选择，可参考创建仅筛选 capture 通道的版本
- `prompt_confirm()` — 已有确认提示工具，可直接用于 add 后的 capture 询问
- `InquirerPy` — 项目已使用，支持 select/confirm/text 等交互
- `console.status()` — Rich spinner 已在 add/verify 中使用
- `CHANNEL_REGISTRY` — 通道注册表，可动态遍历筛选
- `get_channel_status()` — 状态检查函数，可复用
- `Contact` / `save_contact()` — 联系人保存机制已存在

### Established Patterns
- InquirerPy 交互式选择 — `prompt_channel_select()` 模式
- Rich console.status — 状态显示模式
- `asyncio.run()` — 在 Click 命令中运行异步方法
- `@property supports_capture` — 判断通道是否支持 capture
- `capture_openid(timeout=300)` — 异步 capture 方法

### Integration Points
- `cmd/channels.py:capture()` — 移除 `--channel-type` 参数，改为交互式选择
- `cmd/channels.py:add()` — 移除 `--capture-openid` 参数，添加自动询问逻辑
- `prompt.py` — 新增 `prompt_capture_channel_select()` 函数（仅显示支持 capture 的通道）
- `channels/__init__.py` — 无需修改

### Current Capture Command
- `capture()` (cmd/channels.py:447-502) — 当前使用 `--channel-type` 参数
- 支持 qqbot 和 feishu 两种通道
- 已有 `console.status()` 等待显示和错误处理
- 已有自动保存联系人逻辑

### Current Add Command
- `add()` (cmd/channels.py:39-217) — 当前有 `--capture-openid` 标志
- qqbot 和 feishu 各自有 capture_openid 分支逻辑（代码重复）
- 两条路径逻辑相同：获取 channel → capture_openid → save_contact

</code_context>

<specifics>
## Specific Ideas

### 改进后的 capture 命令流程
```
$ claw-cron channels capture
选择通道类型: (仅显示支持 capture 的通道)
  qqbot (已配置 ✓)
  feishu (未配置 ○)

Save as contact alias [me]:

请向你的 QQ Bot 机器人发送任意消息
按 Ctrl+C 取消

⠋ 等待来自 QQ Bot 的消息...

✓ OpenID 已捕获: ABC123DEF456
✓ 联系人已保存为 'me'
```

### 改进后的 add 命令流程（capture 部分）
```
✓ 通道 'qqbot' 配置完成

是否立即获取用户 ID (capture)? [Y/n]: y

请向你的 QQ Bot 机器人发送任意消息
按 Ctrl+C 取消

⠋ 等待来自 QQ Bot 的消息...

✓ OpenID 已捕获: ABC123DEF456
✓ 联系人已保存为 'me'
```

### 超时场景
```
⠋ 等待来自飞书的消息...

✗ Capture 超时（5 分钟），请确认机器人在线后重试
```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-capture-interaction*
*Context gathered: 2026-04-17*
