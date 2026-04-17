# claw-cron

AI-powered cron task manager. Describe tasks in natural language, let AI configure and run them on schedule.

## Installation

```bash
uv sync
```

## Usage

```bash
claw-cron -h          # 查看帮助
claw-cron -v          # 查看版本
claw-cron --version   # 查看版本
```

## Development

```bash
uv venv
uv sync
uv run claw-cron -h
```

## 企业微信通道 (WeChat Work)

### 配置

```bash
claw-cron channels add
# 选择 wecom，然后输入：
# Corp ID: 你的企业 ID（企业微信管理后台 → 我的企业 → 企业信息）
# Agent ID: 应用 ID（企业微信管理后台 → 应用管理 → 自建应用）
# Secret: 应用 Secret
```

### 获取用户 ID

```bash
claw-cron channels capture
# 选择 wecom，然后在企业微信管理后台查找你的 userid 并输入
```

### 发送消息

```bash
claw-cron remind "每天 9 点提醒我开会" --recipient me
```

## Capture 交互改进 (v0.2.1)

`channels capture` 现在支持交互式选择通道类型，无需记忆 `--channel-type` 参数：

```bash
claw-cron channels capture
# 交互式列表选择通道类型
# 对不支持 capture 的通道（iMessage、邮件）给出友好提示
```

`channels add` 验证成功后会自动询问是否执行 capture（适用于 QQ Bot、飞书、企业微信）。
