# M17 Desktop Runtime Orchestration

## Goal

Make the desktop app own the local Agent Core runtime so Bolt opens as a usable desktop agent instead of requiring a separately started backend.

## Completed Scope

- Added an Electron Agent Core runtime resolver.
- Added an Electron supervisor that health-checks before spawning and stops the child process on quit.
- Wired Electron main process startup to ensure Agent Core is available before opening the window.
- Added workbench health refresh so the sidebar reports `ok` or `down`.
- Added Electron Builder resources for Agent Core source files.
- Added tests for runtime resolution, supervisor spawn behavior, and renderer health status.

## Safety Boundary

- No new autonomous agent capability.
- No remote binding; Agent Core stays on `127.0.0.1`.
- No bundled certificates, secrets, or Python virtual environments.
- No automatic update or release publishing changes.

## Verification

- `pnpm --filter @bolt/desktop test -- electron/agentCoreRuntime.test.ts src/App.test.tsx`
- `pnpm --filter @bolt/desktop build`
- `pnpm quality`
- `services/agent-core/.venv/Scripts/python -I -m pytest`
