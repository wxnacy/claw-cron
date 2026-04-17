# Phase 11: UX Improvements - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

改进 channels 命令的交互体验：
1. **channels add** — 使用 InquirerPy 列表选择通道类型，显示配置状态
2. **channels list** — 显示详细的配置状态信息
3. **channels verify** — 新增校验命令，验证通道凭证有效性

不包括：添加新的通道类型（Phase 12-13）、消息发送功能（已实现）。

</domain>

<decisions>
## Implementation Decisions

### 通道选择交互

- **D-01:** `channels add` 使用 `prompt_select()` 显示所有支持的通道类型
  - 列表显示：imessage、qqbot、feishu、email（Phase 12-13 添加后两者）
  - 已配置的通道显示 ✓ 状态图标
- **D-02:** 选择已配置通道时，提示确认是否覆盖
  - 确认后进入配置流程，覆盖原配置
  - 取消则退出命令

### 配置状态展示

- **D-03:** 定义四种配置状态：
  - **已配置** ✓ — config.yaml 中有完整配置（绿色）
  - **配置不完整** ⚠ — 必填字段缺失（黄色）
  - **凭证无效** ✗ — API 验证失败（红色）
  - **未配置** ○ — 无配置记录（灰色）
- **D-04:** 状态使用 Unicode 图标 + Rich 颜色双重展示

### channels list 详细信息

- **D-05:** 显示四列信息：
  - Channel — 通道名称 + 状态图标
  - Status — 配置状态文字（已配置/配置不完整/凭证无效/未配置）
  - Config — 关键配置值（app_id 前8位、邮箱地址等）
  - Contacts — 联系人数量
  - Created — 配置创建时间
- **D-06:** 配置新增 `created_at` 字段
  - 已存在的配置迁移时默认使用当前时间

### 配置校验行为

- **D-07:** `channels add` 保存前校验凭证
  - 校验通过才保存
  - 校验失败显示错误信息，不保存
- **D-08:** 新增 `channels verify <channel_type>` 命令
  - 校验指定通道的凭证有效性
  - 输出校验结果（成功/失败+原因）
- **D-09:** `channels list` 不执行 API 校验
  - 仅检查配置完整性（字段是否存在）
  - 不调用外部 API，保证响应速度

### Claude's Discretion

- `prompt.py` 中新增 `prompt_channel_select()` 函数的具体实现
- `channels list` 表格布局细节（列宽、对齐方式）
- 迁移脚本处理已有配置的方式

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 已实现的模块（直接依赖）
- `src/claw_cron/cmd/channels.py` — 现有 channels 命令实现
- `src/claw_cron/channels/__init__.py` — CHANNEL_REGISTRY 通道注册表
- `src/claw_cron/channels/base.py` — MessageChannel 抽象基类
- `src/claw_cron/prompt.py` — InquirerPy 交互封装
- `src/claw_cron/config.py` — 配置加载/保存

### 项目规范
- `.planning/PROJECT.md` — 技术栈约束
- `.planning/REQUIREMENTS.md` — UX-01, UX-02, UX-03

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `prompt.prompt_select()` — 可直接用于通道选择，需要扩展显示状态图标
- `prompt.prompt_confirm()` — 用于覆盖确认
- `CHANNEL_REGISTRY` — 获取所有注册的通道类型
- `Rich Table` — 现有 `list_channels()` 已使用，可扩展列

### Established Patterns
- InquirerPy Choice 对象 — `prompt_cron()` 已展示 Choice(name=描述, value=值) 模式
- Rich 颜色标记 — `[green]`, `[yellow]`, `[red]` 等
- Click 命令参数 — `@click.option` + `prompt=True` 模式

### Integration Points
- `cmd/channels.py:add()` — 需重构为交互式列表选择
- `cmd/channels.py:list_channels()` — 需扩展列和状态检查
- `config.py` — 需新增 `created_at` 字段处理
- `channels/__init__.py` — 新增通道需注册到 CHANNEL_REGISTRY

</code_context>

<specifics>
## Specific Ideas

- 通道列表显示示例：
  ```
  选择通道类型:
  > qqbot (已配置 ✓)
    imessage
    feishu (未配置 ○)
    email (配置不完整 ⚠)
  ```
- `channels list` 输出示例：
  ```
  ┏━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
  ┃ Channel  ┃ Status       ┃ Config         ┃ Contacts ┃ Created  ┃
  ┡━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
  │ qqbot    │ ✓ 已配置     │ 12345678...    │ 2        │ 2026-04-16 │
  │ feishu   │ ○ 未配置     │ -              │ 0        │ -        │
  │ email    │ ⚠ 配置不完整 │ smtp.qq.com    │ 0        │ -        │
  └──────────┴──────────────┴────────────────┴──────────┴──────────┘
  ```

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-ux-improvements*
*Context gathered: 2026-04-17*
