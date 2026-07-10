# Decision 186: Windows Release Chain Repair After Audit

- Date: 2026-07-11
- Branch: `feat/safe-controlled-beta`
- Final product rebuild commit: `7f3d9916dbeb842aa4c95eba8b333c95dc38133e`
- Product version: `0.1.0`

## Audit acceptance

Independent review correctly rejected earlier claims of completion, including residual sender-trust prefix grants.

Correct ongoing status:

> Packaged/dev sender and navigation trust now require exact entry URLs only.
> Desktop suite is green and packages were rebuilt from this exact-trust commit.
> Signing and clean Windows full E2E remain No-Go. Player beta remains forbidden.

## Latest critical fix

Removed remaining weak URL grants:

- No `endsWith('/dist/index.html')`
- No `includes('/dist/index.html')`
- No `startsWith(devServerUrl)`

Packaged mode accepts only the normalized exact path:

`file:///<appPath>/dist/index.html`

with no query, hash, or userinfo.

Dev mode accepts only exact `URL.origin` plus allowlisted pathnames (`/`, `/index.html`).

`will-navigate` and all IPC (Agent Core / diagnostics / update) share the same validator.

Attack tests cover:

- `file:///C:/Temp/dist/index.html`
- `index.html.evil`
- similar dev ports/hosts
- userinfo / fragment / iframe parent / non-top frames
- packaged query strings

## Final rebuild evidence (non-secret)

| Item | Value |
|------|-------|
| Git commit | `7f3d9916dbeb842aa4c95eba8b333c95dc38133e` |
| Desktop full vitest | **67 files / 469 passed** |
| Desktop build / architecture | passed |
| Worktree evidence gate | clean |
| `win-unpacked/Bolt.exe` SHA-256 | `ab4f30da93e189f68ec5370c6b16cb667160e34868597a2a07b4ed55986c36f6` |
| `Bolt.exe` size | 235706880 bytes |
| `Bolt Setup 0.1.0.exe` SHA-256 | `6da5cb352129b58f88b40ddfe7bd01db0286b1c4e9896f5022223a29a576b517` |
| Setup size | 132007699 bytes |
| package layout smoke | passed |
| artifact secret-scan / asar content | passed (`asar=present`) |
| weak URL grants in electron sources | none |
| `signing.verify` | blocked (`signtool_not_found`) |
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

> The last sender-trust Critical is fixed with exact-entry validation and attack tests.
> Packages were rebuilt after the Main change.
> Player beta remains forbidden until signing and clean Windows E2E pass.
