# Bolt Safe Controlled Beta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Bolt 分四个可独立验收的纵向切片推进到安全受控 Beta，并以真实 Windows Release Evidence 放行。

**Architecture:** Electron Desktop 是唯一用户界面；Renderer 通过窄 preload transport 调用 loopback Python Agent Core。Python 端以 Pydantic/OpenAPI 为关键 Desktop interface 的单一事实源，凭据进入 Windows DPAPI，模型供应商和第三方中转站由 Agent Core 安全访问。

**Tech Stack:** Electron 43、React 19、TypeScript 6、Vitest 4、Python 3.11+、FastAPI 0.115、Pydantic 2.8、pytest、OpenAI SDK、electron-builder/NSIS。

---

## 执行顺序

1. [`2026-07-10-safe-transport-credentials.md`](./2026-07-10-safe-transport-credentials.md)
   - 关闭 Agent Core 普通 fetch 回退。
   - 建立 Windows DPAPI CredentialStore。
   - 原子迁移旧明文密钥。
2. [`2026-07-10-provider-contracts.md`](./2026-07-10-provider-contracts.md)
   - 官方/自定义 OpenAI-compatible 供应商。
   - Endpoint/SSRF 防护和真实验证。
   - Pydantic/OpenAPI/TypeScript 生成客户端。
3. [`2026-07-10-desktop-settings.md`](./2026-07-10-desktop-settings.md)
   - 双栏模型设置 Desktop UI。
   - 会话模型选择。
   - 盘点并只接入 Bolt 真实设置能力，删除空壳入口。
4. [`2026-07-10-release-evidence-windows.md`](./2026-07-10-release-evidence-windows.md)
   - Release Evidence 生成和脱敏。
   - NSIS 安装/重启/权限/Diff/回滚/卸载验收。
   - 最终质量门。

## 共享约束

- 仓库已有未提交 UI/Electron 修改；执行前必须先用 `git status --short` 记录基线，不能覆盖或格式化无关文件。
- 当前分支：`feat/safe-controlled-beta`。如执行时不在此分支，停止并确认，不在 `main` 上实施。
- 每项生产修改先写失败测试。
- focused test 通过后才进入下一任务；同一失败最多修复三轮，之后重新设计。
- source file 不超过 300 行，函数不超过 30 行。
- 不在聊天、测试 fixture、日志、快照或 Git 中放真实 API Key。
- 真供应商 smoke 由用户在 Bolt Desktop 本地输入密钥；自动测试使用 fake/in-memory adapter。
- 每个子计划完成后单独运行该计划的验收命令并提交；不得把原有未提交变更一起 stage。

## 全局完成门

- [ ] 四个子计划的 focused tests 全部通过。
- [ ] `pnpm quality` 通过。
- [ ] `pnpm --filter @bolt/desktop build` 通过。
- [ ] `pnpm --filter @bolt/desktop package:win:dir` 通过。
- [ ] 本机隔离 Windows NSIS 验收完成。
- [ ] `release-evidence/<version>-<commit>-<timestamp>/checks.json` 无 `failed`、`blocked`、`not_run`。
- [ ] 对抗审查覆盖 DNS rebinding、重定向、迁移中断、并发保存/删除、超大响应和卸载残留。
