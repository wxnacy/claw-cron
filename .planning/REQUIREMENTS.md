# Requirements: claw-cron v2.4

**Defined:** 2026-04-17
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## v2.4 Requirements

### Version

- [ ] **VERS-01**: 软件版本号升级到 0.2.1

### Architecture

- [ ] **ARCH-01**: MessageChannel 新增 `supports_capture` 属性标识通道是否支持 capture
- [ ] **ARCH-02**: MessageChannel 新增 `capture_openid()` 方法，支持通道特定的 capture 实现
- [ ] **ARCH-03**: QQBotChannel 实现 `capture_openid()` 方法，封装现有 WebSocket 逻辑
- [ ] **ARCH-04**: FeishuChannel 实现 `capture_openid()` 方法，封装现有 open_id 获取逻辑

### Capture Enhancement

- [ ] **CAPT-01**: capture 命令支持交互式列表选择通道类型（替代 --channel-type 参数）
- [ ] **CAPT-02**: capture 命令对不支持 capture 的通道给出友好提示
- [ ] **CAPT-03**: channels add 验证成功后自动询问用户是否执行 capture
- [ ] **CAPT-04**: capture 流程添加实时状态反馈（Rich console.status）
- [ ] **CAPT-05**: capture 流程添加 5 分钟超时机制

### WeChat Channel

- [ ] **WECHAT-01**: 用户可配置企业微信应用凭证 (corp_id, agent_id, secret)
- [ ] **WECHAT-02**: 用户可通过企业微信应用发送私聊文本消息
- [ ] **WECHAT-03**: 用户可通过企业微信应用发送私聊 Markdown 消息
- [ ] **WECHAT-04**: 系统自动管理 access_token 生命周期（获取、缓存、刷新）
- [ ] **WECHAT-05**: 用户可通过 capture 流程获取企业微信 userid

## v2 Requirements (Deferred)

### WeChat Personal

- **WECHAT-P01**: 支持个人微信消息发送（风险：封号风险高，需监控 iLink API 可用性）

### WeChat Webhook

- **WECHAT-W01**: 支持企业微信群机器人 Webhook（简单但仅支持群通知）

## Out of Scope

| Feature | Reason |
|---------|--------|
| 个人微信 API | 封号风险极高，需等待微信官方 iLink API 开放申请 |
| 企业微信群机器人 | 仅支持群广播，不符合私聊通知场景 |
| 微信图片/文件消息 | 增加复杂度，v2.4 聚焦文本通知 |
| 多企业微信应用 | 多租户场景，暂无需求 |
| 微信模板卡片消息 | 需要设计模板结构，复杂度高 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 14 | Pending |
| ARCH-02 | Phase 14 | Pending |
| ARCH-03 | Phase 14 | Pending |
| ARCH-04 | Phase 14 | Pending |
| CAPT-01 | Phase 15 | Pending |
| CAPT-02 | Phase 15 | Pending |
| CAPT-03 | Phase 15 | Pending |
| CAPT-04 | Phase 15 | Pending |
| CAPT-05 | Phase 15 | Pending |
| WECHAT-01 | Phase 16 | Pending |
| WECHAT-02 | Phase 16 | Pending |
| WECHAT-03 | Phase 16 | Pending |
| WECHAT-04 | Phase 16 | Pending |
| WECHAT-05 | Phase 16 | Pending |
| VERS-01 | Phase 17 | Pending |

**Coverage:**
- v2.4 requirements: 15 total
- Mapped to phases: 15 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-17*
*Last updated: 2026-04-17 after initial definition*
