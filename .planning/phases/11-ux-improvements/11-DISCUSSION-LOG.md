# Phase 11: UX Improvements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 11-ux-improvements
**Areas discussed:** 通道选择交互, 配置状态展示, list 详细信息, 配置校验行为

---

## 通道选择交互

| Option | Description | Selected |
|--------|-------------|----------|
| 显示所有 + 状态图标 | 列表显示所有支持通道（imessage/qqbot/feishu/email），已配置显示 ✓ 图标 | ✓ |
| 仅显示未配置 | 只显示未配置的通道，已配置的不在列表中出现 | |
| 显示所有，无状态 | 显示所有通道，无状态标识，用户可重复配置覆盖 | |

**User's choice:** 显示所有 + 状态图标

| Option | Description | Selected |
|--------|-------------|----------|
| 确认后覆盖 | 选择已配置通道后提示是否覆盖，确认后重新配置 | ✓ |
| 进入编辑模式 | 选择已配置通道时自动跳转到编辑模式，显示当前值作为默认值 | |
| 禁用已配置项 | 已配置通道显示在列表中但禁用选择（灰色） | |

**User's choice:** 确认后覆盖

**Notes:** 列表显示所有支持通道，已配置的显示 ✓ 图标，选择时确认后覆盖

---

## 配置状态展示

| Option | Description | Selected |
|--------|-------------|----------|
| 已配置 | 在 config.yaml 中有该通道的配置 | ✓ |
| 配置不完整 | 配置项缺失或必填字段为空 | ✓ |
| 凭证无效 | 调用 API 验证凭证失败（如 app_id/client_secret 错误） | ✓ |

**User's choice:** 全部选择

| Option | Description | Selected |
|--------|-------------|----------|
| Unicode 图标 | ✓ 已配置 / ⚠ 配置不完整 / ✗ 凭证无效 / ○ 未配置 | |
| 颜色标签 | 绿色/黄色/红色/灰色文字标签 | |
| 纯文字 | enabled/invalid/... 文字状态 | |

**User's choice:** Unicode + 颜色两种都要

**Notes:** 四种状态：已配置(✓绿)、配置不完整(⚠黄)、凭证无效(✗红)、未配置(○灰)

---

## list 详细信息

| Option | Description | Selected |
|--------|-------------|----------|
| 通道 + 状态 | 通道名称和配置状态（当前已有） | ✓ |
| 关键配置值 | 如 app_id、邮箱地址等（当前已有部分） | ✓ |
| 联系人数量 | 该通道下的联系人数量（当前已有） | ✓ |
| 创建时间 | 配置创建的时间（需新增字段） | ✓ |

**User's choice:** 全部选择

| Option | Description | Selected |
|--------|-------------|----------|
| 新增字段 | 在配置中新增 created_at 字段，已存在的配置默认为当前时间 | ✓ |
| 使用文件时间 | 不在配置中存储，使用文件修改时间 | |
| 暂不实现 | 先不做，等后续需求明确 | |

**User's choice:** 新增字段

**Notes:** channels list 显示五列：Channel, Status, Config, Contacts, Created

---

## 配置校验行为

| Option | Description | Selected |
|--------|-------------|----------|
| 每次 list 都校验 | 每次 list 命令执行时验证所有通道（可能较慢） | |
| 独立 verify 命令 | 提供 channels verify 命令手动校验 | ✓ |
| 仅 add 时校验 | add 时校验，list 时仅检查配置完整性（不调 API） | |

**User's choice:** add / verify 时做校验，list 只展示不操作

| Option | Description | Selected |
|--------|-------------|----------|
| 验证全部 | 验证所有已配置的通道，输出每个通道的状态 | |
| 验证指定通道 | 验证指定通道：channels verify qqbot | ✓ |
| 全部 + 单个可选 | 默认全部，支持指定单个 | |

**User's choice:** 验证指定通道

**Notes:** 新增 channels verify <channel_type> 命令，校验指定通道凭证

---

## Claude's Discretion

- `prompt.py` 中新增 `prompt_channel_select()` 函数的具体实现
- `channels list` 表格布局细节（列宽、对齐方式）
- 迁移脚本处理已有配置的方式

## Deferred Ideas

None — discussion stayed within phase scope
