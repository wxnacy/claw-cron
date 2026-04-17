# Requirements: claw-cron v2.3

**Defined:** 2026-04-17
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## v2.3 Requirements

### UX Improvements

- [x] **UX-01**: channels add 命令使用 InquirerPy 列表选择通道类型
- [x] **UX-02**: channels add 列表显示每个通道的配置状态
- [x] **UX-03**: channels list 显示每个通道的详细配置状态

### Feishu Channel

- [ ] **FEISHU-01**: 用户可以配置飞书应用凭证（app_id, app_secret）
- [ ] **FEISHU-02**: 用户可以发送私聊文本消息（通过 open_id）
- [ ] **FEISHU-03**: 系统自动管理 tenant_access_token 的获取和刷新
- [ ] **FEISHU-04**: 系统处理飞书 API 频率限制（5 QPS/用户）
- [ ] **FEISHU-05**: 用户可以通过交互获取自己的 open_id

### Email Channel

- [ ] **EMAIL-01**: 用户可以配置 SMTP 服务器（host, port, username, password, from_email）
- [ ] **EMAIL-02**: 用户可以发送纯文本邮件通知
- [ ] **EMAIL-03**: 用户可以发送 HTML 格式邮件通知
- [ ] **EMAIL-04**: 用户可以指定多个邮件收件人
- [ ] **EMAIL-05**: 用户可以在邮件中附加文件

## v2.x Requirements (Deferred)

### Email Channel Enhancements

- **EMAIL-F01**: Markdown 转 HTML 渲染
- **EMAIL-F02**: 邮件模板支持
- **EMAIL-F03**: 发送状态追踪

### Feishu Channel Enhancements

- **FEISHU-F01**: 富文本消息（Post 类型）
- **FEISHU-F02**: Markdown 消息支持
- **FEISHU-F03**: 文件/图片附件
- **FEISHU-F04**: 交互式卡片

## Out of Scope

| Feature | Reason |
|---------|--------|
| 微信通道 | 后续版本扩展 |
| 消息接收 | 仅支持发送通知，不接收用户消息 |
| 邮件定时发送 | 由 claw-cron 调度器处理时机 |
| 飞书群聊 | 聚焦私聊通知，群聊延后 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UX-01 | Phase 11 | Complete |
| UX-02 | Phase 11 | Complete |
| UX-03 | Phase 11 | Complete |
| FEISHU-01 | Phase 12 | Pending |
| FEISHU-02 | Phase 12 | Pending |
| FEISHU-03 | Phase 12 | Pending |
| FEISHU-04 | Phase 12 | Pending |
| FEISHU-05 | Phase 12 | Pending |
| EMAIL-01 | Phase 13 | Pending |
| EMAIL-02 | Phase 13 | Pending |
| EMAIL-03 | Phase 13 | Pending |
| EMAIL-04 | Phase 13 | Pending |
| EMAIL-05 | Phase 13 | Pending |

**Coverage:**
- v2.3 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-17*
*Last updated: 2026-04-17 after roadmap creation*
