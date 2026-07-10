# Windows 发布证据纵向切片实施计划

> **For agentic workers:** 按 Task 顺序执行。每 Task：RED → 确认失败 → 最小实现 → focused GREEN → 审查 → 显式 add 本 Task 文件 → commit → 下一 Task。

**Goal:** 完成 Windows 发布证据纵向切片，使 Bolt 具备玩家小范围内测的技术条件（最终分发仍须用户授权）。

**Design:** `docs/superpowers/specs/2026-07-11-windows-release-evidence-design.md`  
**Supersedes conflicts in:** `docs/superpowers/plans/2026-07-10-release-evidence-windows.md`（schema/store/check IDs 仍复用）

**Branch:** `feat/safe-controlled-beta`（原地继续；禁止 reset/clean/add -A/push）

**Tech Stack:** Electron Builder、Node scripts、Vitest、pytest、PowerShell smoke、signtool（可选）

---

### Task A: 可重复 Windows 打包 hardening

**Files:**
- Create: `scripts/check-desktop-package-config.test.mjs`
- Modify: `scripts/check-desktop-package-runtime.mjs`（必要时）
- Modify: `apps/desktop/electron-builder.json`（asarUnpack / 版本一致性如需）
- Create: `scripts/assert-single-version.mjs` + test
- Modify: `apps/desktop/package.json` / root scripts 如需挂接

- [ ] RED: 配置测试断言 portable+nsis、extraResources、publish null、version 一致、agent-core 不进 asar
- [ ] GREEN: 最小补齐配置与检查
- [ ] 运行 `package:win:dir` 并记录产物
- [ ] Commit: `feat(release): harden windows package config and version gate`

### Task B: 安装与运行验证脚本

**Files:**
- Create: `scripts/windows-packaged-smoke.mjs` (+ test)
- Create: `scripts/windows-install-smoke.ps1`（可选包装）
- Modify: docs runbook 片段

验证：dir 启动路径、Core 资源存在、exit 清理策略文档化；真实 GUI 安装记入证据。

- [ ] Commit: `feat(release): add packaged windows smoke checks`

### Task C: 代码签名验证入口

**Files:**
- Create: `scripts/verify-windows-signature.mjs` (+ test)
- Modify: `docs/release/release-checklist.md`

- [ ] 无证书 → blocked，不伪造
- [ ] 有签名 → signtool verify /pa
- [ ] Commit: `feat(release): add windows signature verification gate`

### Task D: 自动更新与回滚（默认关闭生产检查）

**Files:**
- Create: `apps/desktop/electron/updateService.ts` (+ test)
- Create: `scripts/local-update-fixture-server.mjs` (+ attack fixtures test)
- Modify: main 窄集成（默认不自动 check）

- [ ] HTTPS only、host allowlist、sha256、拒绝篡改、失败不破坏当前版
- [ ] Commit: `feat(desktop): add fail-closed update service with local fixtures`

### Task E: 崩溃记录与用户反馈

**Files:**
- Create: `apps/desktop/electron/diagnosticsStore.ts` (+ test)
- Create: `apps/desktop/src/DiagnosticsFeedbackPanel.tsx` (+ test)
- Modify: main IPC / settings 挂载（最小）

- [ ] 本地诊断、脱敏、复制、打开目录、默认不上传
- [ ] Commit: `feat(desktop): add local diagnostics and redacted feedback`

### Task F: 产物安全检查

**Files:**
- Create: `scripts/scan-release-artifacts.mjs` (+ test)
- Create: `scripts/create-release-evidence.mjs` (+ test) — 可合并旧计划 Task 3

- [ ] 禁 .env/secret/dev server/coreUrl；生成 sha256 + sbom 摘要
- [ ] Commit: `feat(release): scan artifacts and write evidence hashes`

### Task G: 干净 Windows 验收

**Files:**
- Create: `scripts/clean-windows-e2e.ps1`
- Create: `docs/release/clean-windows-e2e-runbook.md`

- [ ] 本机可跑则跑；否则 `clean_windows_e2e_blocked` + 一键脚本
- [ ] Commit: `docs(release): add clean windows e2e runbook and script`

### Task H: Release Evidence + 最终门禁

**Files:**
- Create/Update: `docs/release/evidence-check-catalog.json`
- Create: `docs/release/safe-beta-acceptance-runbook.md`（若缺）
- Generate: `release-evidence/...`（不提交密钥）
- Create: `docs/decisions/185-windows-release-evidence.md`

- [ ] 全量测试命令与真实结果
- [ ] 8 维审查
- [ ] Go/No-Go
- [ ] Commit docs only: `docs(release): record windows release evidence decision`

---

## 最终命令门禁

```bash
node --test scripts/check-architecture.test.mjs
node scripts/check-architecture.mjs
pnpm.cmd --filter @bolt/desktop test -- --run
pnpm.cmd --filter @bolt/desktop build
# backend
uv run pytest -q
# P0 desktop suite (12 files)
git diff --check
# package + scan + signature + update fixtures + evidence
```

## 工作区规则（重申）

- 每次 `git add` 仅本 Task 文件
- 禁止 `git add -A` / reset / clean / push / 公开 Release
- 证书与 secret 永不入库
