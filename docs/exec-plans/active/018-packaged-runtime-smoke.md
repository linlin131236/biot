# M18 Packaged Runtime Smoke

## Goal

Prove that a Windows packaged desktop artifact carries the Agent Core resources needed by the packaged runtime path.

## Scope

- Add packaged-mode fail-closed validation before spawning Agent Core.
- Add a desktop package runtime smoke script.
- Run the smoke script after `package:win:dir`.
- Include the smoke script in the default quality gate in config-only mode.
- Document the packaged runtime expectation in release and install docs.

## Out of Scope

- Bundling a standalone Python runtime.
- Creating GitHub releases or tags.
- Enabling auto-update.
- Changing Agent Core behavior.

## Verification

- `pnpm --filter @bolt/desktop test -- electron/agentCoreRuntime.test.ts`
- `pnpm lint:release`
- `pnpm lint:package-runtime`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `cd services/agent-core && .venv/Scripts/python -I -m pytest`

`pnpm --filter @bolt/desktop package:win:dir` should run the post-package runtime smoke when Electron Builder can complete in the local network environment.
