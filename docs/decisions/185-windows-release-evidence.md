# Decision 185: Windows Release Evidence Vertical Slice

- Date: 2026-07-11
- Branch: feat/safe-controlled-beta
- Commit: 57a0cb68028b80a295cde2a0ac91f55f4d80f14d
- Product version: 0.1.0

## Summary

Implemented the Windows release-evidence vertical slice design and plan:

- package config/version gate
- packaged smoke checks
- signature verification gate (blocked without certificate material)
- fail-closed update service (production channel blocked by default)
- local diagnostics + redacted feedback
- artifact secret scan + SHA-256 + SBOM summary
- clean Windows E2E runbook/script (blocked on developer machine)

## Verification evidence (non-secret)

| Gate | Result |
|------|--------|
| node release script tests | 12 passed |
| architecture gate | exit 0 |
| packaged smoke | passed |
| signature verify | blocked (`release_signing_blocked`) |
| Desktop full vitest | 64 files / 461 passed |
| Desktop P0 focused | 12 files / 87 passed |
| Desktop build | passed |
| Backend pytest | 1776 passed, 2 skipped |
| git diff --check | exit 0 |
| package:win:dir | passed earlier in slice; runtime resources present |
| artifact secret-scan | passed on win-unpacked (shell scan) |
| clean_windows_e2e | blocked on current host (node/python/uv present) |

## Artifact snapshot

- Path role: `apps/desktop/release/win-unpacked/Bolt.exe`
- Size bytes: 235706880
- SHA-256: `c542c4f81de8ffc3413d919f2fa861cb1c0bc73c3d7fbb4d033122b6e2121c1d`
- Signing: not verified (no CSC_LINK/CSC_KEY_PASSWORD)

## Go / No-Go

| Scenario | Decision |
|----------|----------|
| Local development | Go |
| Team internal validation | Go |
| Player limited beta | **No-Go** |
| Public beta | **No-Go** |

### Blockers remaining for player limited beta

1. `release_signing_blocked` — need trusted code-signing certificate and `signtool verify /pa` pass
2. `clean_windows_e2e_blocked` — need clean Windows Sandbox/VM/standard-user run
3. Production update channel not enabled — local fixture update tests pass, production channel remains blocked by design
4. Full NSIS install/uninstall GUI E2E and real model-call evidence still require authorized human/clean-host execution
5. Final distribution still requires explicit user authorization (agent must not upload/publish)

## 8-dimension adversarial review

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Package integrity | Green | layout smoke + sha256 inventory |
| Signing & update supply chain | Red/Yellow | signing blocked; update fail-closed but production channel blocked |
| Electron/Main/Renderer/Core boundary | Green | no regression to P0/UI gate |
| Credentials & log redaction | Green | diagnostics redaction tests pass |
| Install/update/rollback/uninstall consistency | Yellow | unit/fixture covered; clean host install/uninstall not yet green |
| Clean environment runnability | Red | blocked on current machine; script provided |
| Crash/feedback privacy & recovery | Green | local-only default, no auto upload |
| Release claims match evidence | Green | player beta remains No-Go |

## External inputs still required from user

- Code signing certificate via protected `CSC_LINK` / `CSC_KEY_PASSWORD`
- Clean Windows environment (Sandbox/VM/new user)
- Authorization before any player distribution
- Optional production update host + trust secret once channel policy is approved
