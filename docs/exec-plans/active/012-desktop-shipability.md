# M12 Desktop Shipability

## Goal

Make Bolt usable by a normal Windows user after installation: first run, workspace setup, visible agent state, recoverable last task, and clear user documentation.

## Completed Scope

- First-run wizard with non-sensitive local session persistence.
- State-driven desktop workbench for workspace, core URL, last run, trace, permissions, memory, and perception.
- User-readable error banner for failed Agent Core calls.
- Pending permission diff preview.
- Desktop packaging configuration and user guide.

## Safety Boundary

- API keys are not stored in browser localStorage.
- Permission approvals still flow through Agent Core and `PermissionGate`.
- Packaging does not add auto-update, signing, push, or release publishing.
- Crash recovery is limited to local UI session restoration.

## Verification

- `services/agent-core/.venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
- `pnpm --filter @bolt/desktop package:win`
