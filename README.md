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

### 任务管理

```bash
claw-cron list                # 列出所有任务（含通道信息和 CWD）
claw-cron info <name>         # 查看单个任务的详细信息（竖向表格）
claw-cron info                # 不传 name，交互式 fuzzy 选择任务
claw-cron add --name test --cron "0 8 * * *" --type command --script "echo hello"
claw-cron add --name test --cron "0 8 * * *" --type command --script "./run.sh" --cwd /path/to/project
claw-cron command --name backup --cron "0 2 * * *" --script "./backup.sh" --cwd /path/to/project
claw-cron delete <name>       # 删除任务（先展示详情，再确认）
claw-cron delete              # 不传 name，交互式 fuzzy 选择任务
claw-cron delete <name> -y    # 跳过确认直接删除
claw-cron run <name>          # 立即执行某个任务
```

> `--cwd`：指定任务执行时的工作目录，使脚本中的相对路径在 `run` 和 `server` 模式下表现一致。不指定时继承当前进程的工作目录。

### AI 聊天管理

```bash
claw-cron chat                          # 交互式 AI 聊天（默认 claude）
claw-cron chat --agent codebuddy        # 使用 codebuddy  provider
claw-cron chat -a openai -m gpt-4o-mini # 使用 openai 并指定模型
```

支持通过自然语言执行：列出任务、添加任务、删除任务、运行任务、启用/禁用任务。

### 启动调度服务

```bash
claw-cron server              # 前台启动调度服务
claw-cron server --daemon     # 后台守护进程启动
claw-cron server --stop       # 停止守护进程
claw-cron server --restart    # 重启守护进程
claw-cron server --status     # 查看守护进程状态
claw-cron server --pid        # 输出守护进程 PID（未运行时不输出）
```

> 环境变量：守护进程模式会自动加载 login shell 的环境变量（如 `.zshrc`、`.bash_profile` 中定义的变量），确保任务脚本中的自定义变量在 `run` 和 `server` 模式下表现一致。

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
