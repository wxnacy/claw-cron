# Phase 17: Verification & Release - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 17-verification-release
**Areas discussed:** 验证策略, 文档更新范围, 发布流程

---

## 验证策略

### 验证方式

| Option | Description | Selected |
|--------|-------------|----------|
| 手动端到端测试 | 手动运行 CLI 命令逐个通道验证，覆盖真实 API 调用，更可靠但依赖环境 | |
| 自动化测试 | 编写 pytest 集成测试用例，mock 外部 API，可重复但可能覆盖不到真实问题 | |
| 混合：核心流程手动 + 边界情况自动 | 关键路径（add + send）手动验证，错误处理和边界情况写自动化测试 | ✓ |

**User's choice:** 混合：核心流程手动 + 边界情况自动

### 验证范围

| Option | Description | Selected |
|--------|-------------|----------|
| 全流程验证 | 每个通道都跑 add → capture → send → verify → delete 全流程，最彻底 | ✓ |
| 核心路径验证 | 只跑 add → send 核心流程，跳过 capture/verify/delete | |
| 仅新增功能验证 | 只验证 Phase 14-16 新增功能（capture 交互、企业微信），已验证的通道跳过 | |

**User's choice:** 全流程验证

### 自动化测试范围

| Option | Description | Selected |
|--------|-------------|----------|
| 重点边界测试 | 写 1-2 个测试文件，覆盖核心边界（错误处理、超时、不支持 capture 的通道、收件人解析） | ✓ |
| 全面测试套件 | 为每个通道写完整测试套件，mock 所有 API 调用 | |

**User's choice:** 重点边界测试

**Notes:** 现有项目没有测试目录，从头写起。聚焦最容易出问题的边界，不追求全面覆盖。

---

## 文档更新范围

| Option | Description | Selected |
|--------|-------------|----------|
| README + 版本号 | 更新 README.md（新增通道使用示例 + 配置说明），更新 pyproject.toml 版本号 | |
| 仅版本号 | 仅更新 pyproject.toml 版本号，不改文档 | |
| 全量文档更新 | README + CHANGELOG + 版本号，完整记录所有变更 | ✓ |

**User's choice:** 全量文档更新

---

## 发布流程

| Option | Description | Selected |
|--------|-------------|----------|
| 版本号 + Git Tag | 升级版本号 + git tag v0.2.1，不发布到 PyPI | |
| 完整发布（含 PyPI） | 版本号 + git tag + 发布到 PyPI | |
| 仅版本号 | 仅升级 pyproject.toml 版本号 | ✓ |

**User's choice:** 仅版本号

**Notes:** 不创建 git tag，不发布到 PyPI。

---

## Claude's Discretion

- 手动验证的具体步骤和顺序
- 自动化测试的测试框架配置和 fixture 设计
- README 文档的具体结构和措辞
- CHANGELOG 的分组方式

## Deferred Ideas

None
