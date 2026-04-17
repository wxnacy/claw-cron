# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2026-04-17

### Added
- 企业微信应用消息通知通道 (WeChat Work / 企业微信)
  - 支持文本消息和 Markdown 消息
  - 自动管理 access_token 生命周期（获取、缓存、到期前刷新）
  - 支持通过 `channels capture` 获取企业微信 userid
- `channels capture` 交互式列表选择通道类型（替代 `--channel-type` 参数）
- `channels add` 验证成功后自动询问是否执行 capture
- capture 流程实时状态反馈（Rich console.status）
- capture 流程 5 分钟超时机制，超时后给出明确错误提示
- `MessageChannel.supports_capture` 属性标识通道是否支持 capture
- `MessageChannel.capture_openid()` 抽象方法，支持通道特定 capture 实现

### Changed
- `channels capture` 移除 `--channel-type` 参数，改为交互式选择
- `channels add` 移除 `--capture-openid` 参数，改为 add 成功后自动询问

## [0.1.0] - 2026-04-16

### Added
- 初始版本：iMessage、QQ Bot、飞书、邮件通道
- `channels add/list/delete/verify/capture` 命令
- 联系人别名管理 (`channels contacts`)
- AI 驱动的定时任务配置
