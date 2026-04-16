# Requirements: v2.1 - 通道管理命令

**Created:** 2026-04-16
**Milestone:** v2.1 Channel Management
**Status:** Draft

---

## Overview

添加 `channels` 命令，支持交互式管理消息通道配置，并通过 WebSocket 连接自动捕获用户 OpenID，简化定时任务的 recipient 配置。

---

## CHAN-MGMT-01: channels 命令组

**Priority:** P0
**Phase:** 9

**描述：**
创建顶层 `channels` 命令组，支持 add/delete/list 子命令。

**验收标准：**
- [ ] `claw-cron channels` 显示帮助信息
- [ ] `claw-cron channels add` 启动交互式配置
- [ ] `claw-cron channels delete <name>` 删除指定通道
- [ ] `claw-cron channels list` 列出已配置通道

**技术细节：**
- 使用 Click.group() 创建命令组
- 将现有 `config channels` 命令迁移到新结构

---

## CHAN-MGMT-02: 交互式添加通道

**Priority:** P0
**Phase:** 9

**描述：**
`channels add` 命令提供交互式界面，引导用户配置通道。

**验收标准：**
- [ ] 提示用户选择通道类型（当前仅 qqbot）
- [ ] 提示输入 AppID
- [ ] 提示输入 AppSecret（隐藏输入）
- [ ] 验证凭据有效性（调用 QQ 开放平台 API）
- [ ] 配置保存到 `~/.config/claw-cron/config.yaml`

**交互流程：**
```
$ claw-cron channels add
? Channel type: qqbot
? AppID: 123456789
? AppSecret: ********
✓ Credentials validated
? Connect now to capture openid? (Y/n)
```

---

## CHAN-MGMT-03: WebSocket 连接管理

**Priority:** P0
**Phase:** 9

**描述：**
实现 QQ Bot WebSocket 客户端，用于接收消息事件并捕获用户 OpenID。

**验收标准：**
- [ ] 连接 QQ 开放平台 WebSocket 网关
- [ ] 完成认证流程（Identify + Resume）
- [ ] 维护心跳连接
- [ ] 接收 C2C 消息事件
- [ ] 从消息事件中提取用户 openid

**技术细节：**
- WebSocket URL: `wss://api.sgroup.qq.com/websocket/`
- 认证 Token 格式: `Bot {appid}.{access_token}`
- 心跳间隔: 从 Hello 事件获取

---

## CHAN-MGMT-04: OpenID 捕获与存储

**Priority:** P0
**Phase:** 9

**描述：**
当用户发送消息给机器人时，自动捕获 openid 并存储为联系人。

**验收标准：**
- [ ] 从消息事件中提取 `author.id` (openid)
- [ ] 可选：提示用户输入联系人别名
- [ ] 存储到 `~/.config/claw-cron/contacts.yaml`
- [ ] `remind` 命令支持使用别名作为 recipient

**存储格式：**
```yaml
# ~/.config/claw-cron/contacts.yaml
contacts:
  me:
    openid: "ABC123DEF456"
    channel: qqbot
    created: "2026-04-16T10:00:00Z"
    last_message: "2026-04-16T10:00:00Z"
```

---

## CHAN-MGMT-05: 通道状态显示

**Priority:** P1
**Phase:** 9

**描述：**
`channels list` 命令显示已配置通道的详细状态。

**验收标准：**
- [ ] 显示通道名称、类型、状态
- [ ] 显示 WebSocket 连接状态
- [ ] 显示已捕获的联系人数量
- [ ] 支持 JSON 输出格式

**输出示例：**
```
Channel: qqbot
Status: Connected
AppID: 123456789
WebSocket: Connected (45s heartbeat)
Contacts: 2 captured
```

---

## CHAN-MGMT-06: 通道删除

**Priority:** P1
**Phase:** 9

**描述：**
`channels delete` 命令删除通道配置。

**验收标准：**
- [ ] 删除前确认提示
- [ ] 从 config.yaml 移除配置
- [ ] 可选：断开 WebSocket 连接
- [ ] 可选：保留或删除联系人数据

---

## CHAN-MGMT-07: remind 命令集成

**Priority:** P0
**Phase:** 9

**描述：**
`remind` 命令支持使用联系人别名作为 recipient。

**验收标准：**
- [ ] `--recipient` 支持别名（如 `--recipient me`）
- [ ] 自动解析别名为 `c2c:OPENID` 格式
- [ ] 别名不存在时提示可用联系人

**使用示例：**
```bash
# 使用别名
claw-cron remind --name morning \
    --cron "0 8 * * *" \
    --message "早安！" \
    --channel qqbot \
    --recipient me

# 自动解析为 c2c:ABC123DEF456
```

---

## Coverage Summary

| ID | Priority | Phase | Plan |
|----|----------|-------|------|
| CHAN-MGMT-01 | P0 | 9 | 09-01 |
| CHAN-MGMT-02 | P0 | 9 | 09-01 |
| CHAN-MGMT-03 | P0 | 9 | 09-02 |
| CHAN-MGMT-04 | P0 | 9 | 09-02 |
| CHAN-MGMT-05 | P1 | 9 | 09-01 |
| CHAN-MGMT-06 | P1 | 9 | 09-01 |
| CHAN-MGMT-07 | P0 | 9 | 09-02 |

**Total:** 7 requirements

---

## OpenClaw 流程对比

| 特性 | OpenClaw | claw-cron (本里程碑) |
|------|----------|---------------------|
| 配置方式 | CLI + 配置文件 | CLI 交互式 |
| WebSocket | 内置，自动连接 | 按需连接 |
| OpenID 获取 | 自动记录 | 提示用户发消息捕获 |
| 联系人管理 | 无 | 支持别名 |

**关键差异：**
- OpenClaw 是完整机器人框架，WebSocket 持续运行
- claw-cron 是定时任务工具，按需连接捕获 openid

---

*Created: 2026-04-16*
