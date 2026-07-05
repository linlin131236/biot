# M15 Release Hardening

## Goal

Make Bolt reliably produce Windows release artifacts without enabling automatic publishing or auto-update.

## Completed Scope

- Split Windows packaging scripts into portable, NSIS, and unpacked directory targets.
- Added a release preflight for Electron Builder network requirements.
- Wrapped Electron Builder so packaging stalls fail with a documented error instead of hanging CI.
- Added manual Release workflow with channel and package target inputs.
- Added signing policy that supports unsigned builds and environment-provided certificates.
- Added Windows install and release checklist documentation.
- Added release policy checks to the quality gate.

## Safety Boundary

- No automatic GitHub release creation.
- No tag push.
- No artifact publishing through Electron Builder.
- No certificate or password committed to the repository.
- No auto-update checks or downloads at runtime.

## Verification

- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `services/agent-core/.venv/Scripts/python -I -m pytest`
- `pnpm --filter @bolt/desktop package:win:portable`
