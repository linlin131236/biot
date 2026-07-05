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

## Root Cause

The local environment cannot resolve or reach `release-assets.githubusercontent.com`. The Vite and TypeScript build steps complete, so the failure is outside the application build itself.

## Repair

Retry packaging when DNS/network access to GitHub release assets is available. Keep the `electron-builder` config, split package scripts, and pnpm package extension in place.

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
