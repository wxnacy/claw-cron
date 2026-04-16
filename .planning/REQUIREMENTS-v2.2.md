# Requirements: v2.2 - 交互式命令改进

**Created:** 2026-04-17
**Milestone:** v2.2 Interactive Commands
**Status:** Draft

---

## Overview

改进 CLI 交互体验，使用 InquirerPy 库实现统一的交互式界面。为 `remind` 和新增的 `command` 命令提供命令行直接模式和交互式模式两种使用方式。

---

## INTERACT-01: 采用 InquirerPy 作为交互式库

**Priority:** P0
**Phase:** 10

**描述：**
引入 InquirerPy 库作为统一的交互式 CLI 解决方案，替换现有的 Click prompt/confirm 调用。

**验收标准：**
- [ ] 项目依赖添加 InquirerPy
- [ ] 创建交互式辅助模块 `claw_cron/prompt.py`
- [ ] 封装常用的交互式操作（文本输入、选择、确认）
- [ ] 支持实时校验和错误提示

**技术细节：**
- InquirerPy 版本：>= 0.3.3
- 使用替代语法 `inquirer.text()` 而非经典语法
- 支持样式自定义（与 Rich 风格一致）

---

## INTERACT-02: remind 命令交互式模式

**Priority:** P0
**Phase:** 10

**描述：**
`remind` 命令不传必选参数时进入交互式模式，引导用户填写 name、cron、message、channel、recipient。

**验收标准：**
- [ ] `claw-cron remind` 无参数进入交互模式
- [ ] 分步骤引导用户填写各字段
- [ ] channel 从已配置通道列表选择
- [ ] recipient 支持选择联系人或手动输入
- [ ] cron 表达式支持常用预设选择或自定义输入
- [ ] 最终确认后创建任务

**技术细节：**
- 多步骤表单流程
- channel 选择时显示可用通道
- recipient 选择时显示已保存联系人
- 预览最终配置后再确认

---

## INTERACT-03: 新增 command 命令

**Priority:** P0
**Phase:** 10

**描述：**
新增 `command` 命令，专门用于创建 command 类型的定时任务。与 `remind` 类似，支持命令行直接模式和交互式模式。

**验收标准：**
- [ ] `claw-cron command` 无参数进入交互模式
- [ ] `claw-cron command --name x --cron "0 8 * * *" --script "echo hi"` 直接创建
- [ ] 交互模式引导填写 name、cron、script
- [ ] 可选填写 notify 配置
- [ ] 创建类型为 `command` 的 Task

**技术细节：**
- 参数：`--name`、`--cron`、`--script`（必填）
- 可选参数：`--channel`、`--recipient`（通知配置）
- script 内容支持多行输入

---

## INTERACT-04: 替换现有交互式调用

**Priority:** P1
**Phase:** 10

**描述：**
将项目中现有的 `click.prompt`、`click.confirm` 调用替换为 InquirerPy 实现，保持统一的交互风格。

**验收标准：**
- [ ] `delete` 命令的确认提示使用 InquirerPy
- [ ] `channels delete` 命令的确认提示使用 InquirerPy
- [ ] `channels contacts delete` 命令的确认提示使用 InquirerPy
- [ ] `chat` 命令的用户输入使用 InquirerPy
- [ ] `agent.py` 中的 prompt 调用使用 InquirerPy

**技术细节：**
- 确认提示使用 `inquirer.confirm()`
- 文本输入使用 `inquirer.text()`
- 选择使用 `inquirer.select()`
- 保持 Rich 显示与 InquirerPy 输入的视觉一致性

---

## INTERACT-05: 交互式 Cron 表达式辅助

**Priority:** P1
**Phase:** 10

**描述：**
提供 Cron 表达式的交互式选择，降低用户记忆 cron 语法的门槛。

**验收标准：**
- [ ] 提供常用 cron 预设（每小时、每天8点、每周一等）
- [ ] 显示每个预设的人类可读描述
- [ ] 支持选择"自定义"后手动输入
- [ ] 自定义输入时显示格式提示

**技术细节：**
- 预设列表：
  - "每分钟" → `* * * * *`
  - "每小时整点" → `0 * * * *`
  - "每天早上8点" → `0 8 * * *`
  - "每天中午12点" → `0 12 * * *`
  - "每天晚上6点" → `0 18 * * *`
  - "每周一早上9点" → `0 9 * * 1`
  - "工作日早上9点" → `0 9 * * 1-5`
  - "每月1号" → `0 0 1 * *`
  - "自定义" → 手动输入

---

## INTERACT-06: SKILL.md 更新

**Priority:** P2
**Phase:** 10

**描述：**
更新 `skills/claw-cron/SKILL.md` 文档，添加交互式命令的使用说明。

**验收标准：**
- [ ] 添加 `command` 命令使用说明
- [ ] 更新 `remind` 命令交互式模式说明
- [ ] 添加交互式流程示例

---

## Technical Notes

### InquirerPy 选型理由

| 特性 | InquirerPy | python-inquirer |
|------|------------|-----------------|
| 交互类型 | 9 种 | 5 种 |
| 模糊搜索 | ✅ | ❌ |
| 样式自定义 | ✅ 丰富 | ⚠️ 有限 |
| 类型提示 | ✅ 替代语法 | ⚠️ 部分 |
| 最新更新 | 2022-02 | 2025-08 |
| Stars | 459 | ~500 |

选择 InquirerPy 因为：
1. 更丰富的交互类型，特别是模糊搜索
2. 替代语法支持完整的类型提示
3. 样式自定义更灵活，易于与 Rich 配合
4. API 设计更现代化

### 交互模式触发逻辑

```python
# remind 命令示例
@click.command()
@click.option("--name", default=None)
@click.option("--cron", default=None)
# ... 其他参数
def remind(name, cron, ...):
    # 有必填参数缺失时进入交互模式
    if not all([name, cron, message, channel, recipients]):
        return _remind_interactive()
    # 否则直接创建
    _remind_direct(name, cron, ...)
```
