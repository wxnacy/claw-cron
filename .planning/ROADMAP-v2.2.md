# Roadmap: claw-cron v2.2

**Created:** 2026-04-17
**Phases:** 1 (Phase 10, continuing from v2.1)
**Requirements:** 6 v2.2 requirements mapped

---

## Phase 10: 交互式命令改进

**Goal:** 使用 InquirerPy 统一交互式体验，为 remind 和新增的 command 命令提供交互式模式。

**Requirements:** INTERACT-01, INTERACT-02, INTERACT-03, INTERACT-04, INTERACT-05, INTERACT-06

**Plans:** 4 plans in 2 waves

**Success Criteria:**
1. `claw-cron remind` 无参数进入交互式模式
2. `claw-cron command` 命令可用，支持直接和交互两种模式
3. 现有交互式调用统一使用 InquirerPy
4. Cron 表达式提供预设选择

**UI hint:** no

**Key Files:**
- `src/claw_cron/prompt.py` — 交互式辅助模块
- `src/claw_cron/cmd/remind.py` — 更新支持交互模式
- `src/claw_cron/cmd/command.py` — 新增 command 命令
- `pyproject.toml` — 添加 InquirerPy 依赖

---

## Plan Breakdown

### Wave 1: 基础设施

| Plan | Objective | Requirements |
|------|-----------|--------------|
| 10-01 | InquirerPy 集成 & prompt 模块 | INTERACT-01, INTERACT-05 |
| 10-02 | 替换现有交互式调用 | INTERACT-04 |

### Wave 2: 命令实现

| Plan | Objective | Requirements |
|------|-----------|--------------|
| 10-03 | remind 交互式模式 | INTERACT-02 |
| 10-04 | command 命令实现 | INTERACT-03, INTERACT-06 |

---

## Plans

- [ ] 10-01-PLAN.md — InquirerPy 集成 & 创建 prompt.py 交互模块
- [ ] 10-02-PLAN.md — 替换现有 click.prompt/confirm 为 InquirerPy
- [ ] 10-03-PLAN.md — remind 命令交互式模式实现
- [ ] 10-04-PLAN.md — 新增 command 命令（直接+交互模式）

---

## Requirements Mapping

| Requirement | Plan | Priority |
|-------------|------|----------|
| INTERACT-01 | 10-01 | P0 |
| INTERACT-02 | 10-03 | P0 |
| INTERACT-03 | 10-04 | P0 |
| INTERACT-04 | 10-02 | P1 |
| INTERACT-05 | 10-01 | P1 |
| INTERACT-06 | 10-04 | P2 |

---

## Dependencies

```
10-01 (基础) ──┬──> 10-03 (remind 交互)
               └──> 10-04 (command 命令)
10-02 (替换) ──────> 可独立进行
```

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| InquirerPy 与 Rich 显示冲突 | 显示错乱 | 测试颜色配置一致性 |
| 交互式模式在 CI 环境失败 | 无法自动化测试 | 提供 `--no-input` 或环境检测 |
| Windows 兼容性 | 部分用户无法使用 | InquirerPy 基于 prompt_toolkit，跨平台支持良好 |

---

*Last updated: 2026-04-17*
