# M16 Real Workspace Runtime

## Goal

Remove development-machine workspace assumptions so Bolt can run against the workspace selected in the desktop app and validated by Agent Core.

## Completed Scope

- Added `workspace` to harness runs and shared protocol validation.
- Desktop run creation now posts the selected workspace to Agent Core.
- Agent Core run creation accepts an optional workspace and reports the stored workspace.
- Permission gate, read-only executor, perception capture, file-write proposals, and document gardener now use the run workspace.
- Fake model gateway derives tool paths from planner workspace metadata instead of a hardcoded checkout path.
- Removed CI legacy workspace junction creation.
- Updated tests to use temporary workspaces or neutral sample paths.

## Safety Boundary

- No new agent capability beyond workspace routing.
- No broad project manager or multi-root UX.
- No automatic workspace discovery beyond the existing first-run field and Agent Core process cwd fallback.
- No permission relaxation; outside-workspace access remains denied or failed.

## Verification

- `services/agent-core/.venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
