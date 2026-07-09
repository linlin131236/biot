# electron-builder package win network failure

## Trigger

- Tool: `shell.execute`
- Operation: `pnpm --filter @bolt/desktop package:win`
- Failure class: `external_network_failure`

## Symptom

Electron Builder reaches the Windows packaging phase, then fails while downloading from GitHub release assets:

```text
getaddrinfo ENOTFOUND release-assets.githubusercontent.com
```

M15 also runs `scripts/release-preflight.mjs` before distributable packaging. If DNS or HTTPS access for the same host fails, the preflight exits before Electron Builder starts.

Another symptom is Electron Builder printing `downloaded label=electron progress=100%` and then stalling while it prepares Windows packaging helpers. `scripts/run-electron-builder.mjs` treats no-output stalls as failures and prints this file path. Treat that as the same external packaging dependency class unless source build or tests also fail.

On Windows, another confirmed variant is Electron Builder re-downloading `electron-v43.0.0-win32-x64.zip` during `--dir` packaging even though the app dependency already contains a valid local Electron installation. In slow or unstable network environments this leaves partial `%TEMP%\electron-download-*` zip files and never reaches `release\win-unpacked`.

## Root Cause

The local environment cannot resolve or reach `release-assets.githubusercontent.com`, or can reach it only too slowly for Electron Builder's internal artifact download/extract step. The Vite and TypeScript build steps complete, so the failure is outside the application build itself.

## Repair

Retry packaging when DNS/network access to GitHub release assets is available. Keep the `electron-builder` config, split package scripts, and pnpm package extension in place.

For the Windows `--dir` smoke path, prefer reusing the local Electron distribution by keeping this Electron Builder config:

```json
"electronDist": "node_modules/electron/dist"
```

If `node_modules/electron/dist/electron.exe` is missing, install or repair the Electron dependency first. Do not downgrade Electron or rewrite package versions just to avoid the download. If GitHub is slow, downloading the same official Electron zip through a trusted mirror is acceptable only when the SHA256 in `node_modules/electron/checksums.json` is verified before extraction.

The wrapper defaults are:

- `BOLT_BUILDER_IDLE_TIMEOUT_MS=60000`
- `BOLT_BUILDER_TOTAL_TIMEOUT_MS=600000`

Useful commands:

```text
pnpm --filter @bolt/desktop package:win:portable
pnpm --filter @bolt/desktop package:win:nsis
pnpm --filter @bolt/desktop package:win:dir
```

`package:win:dir` runs `scripts/check-desktop-package-runtime.mjs --require-output` after packaging. If the network stage succeeds but the smoke check fails, inspect `apps/desktop/release/win-unpacked/resources/agent-core` before retrying the package command.

## Do Not Repeat

Do not treat this as a TypeScript or desktop source failure. Verify network access before retrying installer packaging. Do not bypass `--publish never` while diagnosing the issue. Do not commit partially generated `release/` output.

## Source

M12 package verification.
