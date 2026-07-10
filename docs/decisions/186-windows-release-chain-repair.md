# Decision 186: Windows Release Chain Repair After Audit

- Date: 2026-07-11
- Branch: `feat/safe-controlled-beta`
- Final product rebuild commit: `b175e521a45d000f6c3363432dad1c2e284c11f3`
- Product version: `0.1.0`

## Audit acceptance

Independent review correctly rejected earlier claims of completion.

Correct ongoing status:

> 发布链关键缺口已按审核意见继续收紧；Desktop 全量全绿；ASAR 内容扫描已真实可读且 fixture 可抓 secret；sender trust 已提升到 frame/URL 级；fatal exception 使用 monitor 记录。
> 签名与干净 Windows 完整 E2E 仍未过。玩家内测仍然禁止。

## What was repaired after the latest audit

1. **ASAR content scan is real**
   - `normalizeAsarEntry()` strips leading separators and keeps the Windows path form required by `@electron/asar` (`dist-electron\main.js`).
   - Scannable JS/JSON/CSS/HTML entries hard-fail on `asar_read_failed` / `asar_read_empty`.
   - Fixture test creates a real asar containing `sk-...` and asserts detection.
   - Spot-check on rebuilt package: 20/20 sampled JS entries read non-zero bytes.
   - Final scan: `asar=present`, secret-scan passed.

2. **IPC sender trust hardened**
   - Shared `isTrustedDesktopSender()` requires:
     - matching trusted `webContents.id`
     - top-level frame only
     - exact dev-server origin, or packaged `.../dist/index.html` entry
   - Used by Agent Core, diagnostics, and update IPC.
   - `will-navigate` no longer allows arbitrary `file://` prefixes.

3. **Fatal exception handling**
   - Replaced swallowing `uncaughtException` listener with `uncaughtExceptionMonitor` so diagnostics are recorded without suppressing Electron's default fatal exit path.
   - `unhandledRejection` still recorded.

4. **Whitespace**
   - Decision/scanner trailing whitespace cleaned; `git diff --check` clean on product commits.

5. **Desktop suite**
   - Final result after this repair: **67 files / 470 tests passed**.

## Final rebuild evidence (non-secret)

| Item | Value |
|------|-------|
| Git commit | `b175e521a45d000f6c3363432dad1c2e284c11f3` |
| Desktop full vitest | **67 files / 470 passed** |
| Desktop build | passed |
| Worktree evidence gate | clean |
| `win-unpacked/Bolt.exe` SHA-256 | `79c76fc5e76b80b299b425926cc7a05d03acb2df54db0c765290c469890e1fe9` |
| `Bolt.exe` size | 235706880 bytes |
| `Bolt Setup 0.1.0.exe` SHA-256 | `712985fce2eee9d8a919045d9aada99fa8e896d4bc69701a3d94de31c696ca1e` |
| Setup size | 132007405 bytes |
| package layout smoke | passed |
| artifact secret-scan | passed |
| asar listing/content scan | present / passed (real non-zero reads) |
| SBOM | `file_inventory_not_cyclonedx` |
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

> 审核指出的 ASAR 假绿、弱 sender trust、fatal exception 处理与 whitespace 已修复，并已从 clean commit 重建 EXE/NSIS。
> 这仍不等于可玩家内测：签名与干净 Windows 完整 E2E 未通过。
