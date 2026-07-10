# Decision 186: Windows Release Chain Repair After Audit

- Date: 2026-07-11
- Branch: `feat/safe-controlled-beta`
- Final rebuild commit: `3c335c3b7da401b75dd23473399ba3ccb00434e7`
- Product version: `0.1.0`

## Audit acceptance

Independent review rejected “technical implementation complete.”

Correct ongoing status:

> 发布能力骨架已加固；关键 dirty 源码 / 未接入 / 假门禁问题已修；Desktop 全量测试已恢复全绿；签名与干净 Windows 完整 E2E 仍未过。玩家内测仍然禁止。

## What was repaired in this follow-up

1. **Desktop full suite restored**
   - Preload bridge security contract re-accepted for `diagnostics` / `update` narrow surfaces with fixed channels.
   - Task-closure dogfood stabilized by waiting for health + quiet network fan-out (not by blind timeout inflation).
   - Real Electron bridge integration hardened: compile preload first, parent/child watchdogs, one retry under suite load, assert diagnostics/update presence.
   - Final result: **66 files / 465 tests passed**.

2. **clean-worktree gate tightened**
   - Production `apps/desktop/src/assets/` is **not** ignored.
   - Untracked production assets make evidence packaging dirty/fail.
   - Brand SVG assets were committed; non-shipping previews moved out of production path.

3. **ASAR scan hardened**
   - Resolves `@electron/asar` (including pnpm path).
   - Lists asar entries and scans packaged JS/JSON/CSS/HTML content for secret patterns.
   - Invalid/unlistable asar is a **hard failure** (`asar_listing_unavailable`), not a soft pass.
   - Final scan: `asar=present`, secret-scan passed.

4. **Real crash/startup diagnostics wired**
   - `render-process-gone`, main `uncaughtException` / `unhandledRejection`, Agent Core/desktop startup failures write into local diagnostics store via `crashDiagnostics` helpers.
   - UI diagnostics panel remains available; default no auto-upload.

5. **Rebuild from clean final commit**
   - Worktree clean for product source.
   - Regenerated `win-unpacked` and **real NSIS** installer.
   - Package includes `diagnosticsIpc`, `crashDiagnostics`, `updateService` markers in `app.asar`.

## Final rebuild evidence (non-secret)

| Item | Value |
|------|-------|
| Git commit | `3c335c3b7da401b75dd23473399ba3ccb00434e7` |
| Desktop full vitest | **66 files / 465 passed** |
| Desktop build | passed |
| Architecture gate | passed (prior + unchanged) |
| Worktree evidence gate | clean |
| `win-unpacked/Bolt.exe` SHA-256 | `fbb3b9d731c91e02aee4fe288051c4d759f107379343c871c7f59f38211a9e52` |
| `Bolt.exe` size | 235706880 bytes |
| `Bolt Setup 0.1.0.exe` SHA-256 | `28cc1053397ca30e592d0da2add1b97f4d6a82272a25a7468e2997aaf268ace0` |
| Setup size | 132007604 bytes |
| `app.asar` mtime | 2026-07-11 04:46:11 +0800 |
| package layout smoke | passed |
| artifact secret-scan | passed |
| asar listing/content scan | present / passed |
| SBOM | `file_inventory_not_cyclonedx` (honest limitations) |
| `signing.verify` | blocked (`signtool_not_found` in this shell) |
| `signing.capability` | blocked (no CSC material) |
| `clean_windows_e2e` | blocked on developer host |
| NSIS install/uninstall GUI E2E | not_run |
| production update channel | blocked by design |

## Go / No-Go

| Scenario | Decision |
|----------|----------|
| Local development | Go |
| Team internal validation | Go |
| Player limited beta | **No-Go** |
| Public beta | **No-Go** |

### Remaining blockers for player limited beta

1. Trusted code signing certificate + successful `signtool verify /pa` on these exact artifacts
2. Clean Windows install/start/core/credentials/task/exit/uninstall evidence
3. Production update channel policy/host only if auto-update is required
4. Explicit user authorization before any player distribution

## Correct summary statement

> 内部发布链关键缺口已按审核意见修复，Desktop 全量全绿，且已从 clean commit 重新生成 EXE 与 NSIS。  
> 但这仍不等于可玩家内测：签名、干净 Windows 完整 E2E 与生产更新链仍未通过。
