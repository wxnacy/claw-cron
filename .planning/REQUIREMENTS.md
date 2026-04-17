# Requirements: claw-cron v3.1

**Defined:** 2026-04-18
**Core Value:** 用自然语言描述定时任务，AI 帮你配置并按时执行，并通过消息通道通知你。

## v3.1 Requirements

增加 update 命令，支持修改已有任务的字段，版本升级到 0.3.1。

### Update Command (任务修改)

- [ ] **UPD-01**: update 子命令入口 — 用户可通过 `claw-cron update <name>` 调用，name 为必传参数定位目标任务
- [ ] **UPD-02**: 修改 cron 字段 — 通过 `--cron` 选项修改任务的 cron 表达式
- [ ] **UPD-03**: 修改 enabled 字段 — 通过 `--enabled` 选项启用/禁用任务（布尔值）
- [ ] **UPD-04**: 修改 message 字段 — 通过 `--message` 选项修改通知消息模板
- [ ] **UPD-05**: 修改 script 字段 — 通过 `--script` 选项修改 command 类型任务的脚本内容
- [ ] **UPD-06**: 修改 prompt 字段 — 通过 `--prompt` 选项修改 chat 类型任务的 prompt 内容

### Version (版本)

- [ ] **VER-02**: 版本号升级到 0.3.1

## Future Requirements

### Batch Update

- **BUPD-01**: 批量修改 — 支持同时修改多个任务的相同字段
- **BUPD-02**: 按条件批量修改 — 按 cron 模式或类型筛选后批量修改

## Out of Scope

| Feature | Reason |
|---------|--------|
| 修改任务类型 | 类型变更涉及配置结构变化，应删除重建 |
| 修改任务名称 | 名称为主键，变更影响上下文文件路径等关联数据，应删除重建 |
| 修改通知通道 | 通道配置结构复杂，未来单独处理 |
| 修改环境变量/上下文配置 | env/context 属于高级配置，v3.1 聚焦常用字段 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UPD-01 | — | Pending |
| UPD-02 | — | Pending |
| UPD-03 | — | Pending |
| UPD-04 | — | Pending |
| UPD-05 | — | Pending |
| UPD-06 | — | Pending |
| VER-02 | — | Pending |

**Coverage:**
- v3.1 requirements: 7 total
- Mapped to phases: 0
- Unmapped: 7

---
*Requirements defined: 2026-04-18*
