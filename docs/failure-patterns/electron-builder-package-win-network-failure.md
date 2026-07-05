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

## Root Cause

The local environment cannot resolve or reach `release-assets.githubusercontent.com`. The Vite and TypeScript build steps complete, so the failure is outside the application build itself.

## Repair

Retry packaging when DNS/network access to GitHub release assets is available. Keep the `electron-builder` config and pnpm package extension in place.

## Do Not Repeat

Do not treat this as a TypeScript or desktop source failure. Verify network access before retrying installer packaging.

## Source

M12 package verification.
