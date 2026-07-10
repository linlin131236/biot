# Decision 186: Windows Release Chain Repair After Audit

- Date: 2026-07-11
- Branch: `feat/safe-controlled-beta`
- Commit used for rebuild: `22a55304dd5a76cb0874ba02cd4a6f920c6c2f6b`
- Product version: `0.1.0`

## Audit acceptance

The previous claim that the Windows release-evidence vertical slice was "technically complete" is **rejected**.

Correct state before this repair:

- release capability skeleton existed
- multiple critical implementation/evidence gaps remained

## Repairs completed

1. Committed previously dirty P0 sources that ship inside packages:
   - Desktop transport/readiness/preload stack
   - Agent Core credential gate / Windows secret stack
2. Wired diagnostics and update modules into Electron Main + preload + Settings UI
3. Added dirty-worktree package evidence gate
4. Split `signing.verify` (signtool verify, no private key) from `signing.capability` (CSC material)
5. Stopped clean-E2E script from marking `clean_windows_e2e=passed` on 5-second launch smoke
6. Honest SBOM inventory limitations (`file_inventory_not_cyclonedx`)
7. Rebuilt package from clean product source and produced real NSIS installer

## Rebuild evidence (non-secret)

| Item | Value |
|------|-------|
| Git commit | `22a55304dd5a76cb0874ba02cd4a6f920c6c2f6b` |
| Worktree gate | clean for product source (non-shipping local drafts ignored) |
| `win-unpacked/Bolt.exe` SHA-256 | `ca80d9feb1bd836aabf85e0cd08521ea7ccc0191e9555c4ec61acfe0e68e9a4f` |
| `Bolt.exe` size | 235706880 bytes |
| `Bolt Setup 0.1.0.exe` SHA-256 | `24a48c6b267d90277a02361d9e2d2f581c1d23921dde3264ed316e0d5a5b1e1f` |
| Setup size | 132006970 bytes |
| `app.asar` mtime | 2026-07-11 04:15:23 +0800 (after wiring commits) |
| asar content markers | `diagnosticsIpc`, `updateService`, `updateIpc`, `diagnosticsStore` present |
| package layout smoke | passed |
| artifact secret-scan | passed (shell inventory; asar listing unavailable without `@electron/asar`) |
| SBOM | inventory only, not CycloneDX/SPDX |
| `signing.verify` | blocked (`signtool_not_found` in this shell) |
| `signing.capability` | blocked (no CSC material) |
| `clean_windows_e2e` | blocked on developer host |
| NSIS install/uninstall GUI E2E | not_run |
| production update channel | blocked by design |

## Focused verification after repair

- node release gate tests: passed
- desktop wiring/update/diagnostics focused vitest: 13 passed

## Go / No-Go

| Scenario | Decision |
|----------|----------|
| Local development | Go |
| Team internal validation | Go |
| Player limited beta | **No-Go** |
| Public beta | **No-Go** |

### Remaining blockers for player limited beta

1. Trusted code signing certificate + successful `signtool verify /pa` on final artifacts
2. Clean Windows install/start/core/credentials/task/exit/uninstall evidence
3. Production update channel policy/host if auto-update is required
4. Explicit user authorization before any player distribution

## Correct summary statement

> 发布能力骨架已加固，且关键 dirty 源码/接入/门禁问题已修复；但签名、干净 Windows 完整 E2E、安装卸载证据与生产更新链仍未通过。玩家内测仍然禁止。
