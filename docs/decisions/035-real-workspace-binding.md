# M35 Real Workspace File Picker + Safe Workspace Binding

## Status

Accepted.

## Context

M33/M34 completed Chinese UI and quality gates, but all file operations used absolute paths and there was no UI to change the workspace after first run. The backend _is_inside_workspace used startswith which had a sibling prefix vulnerability.

## Decision

1. Fix _is_inside_workspace to use Path.relative_to (no prefix confusion)
2. Resolve relative paths against workspace in PathGuard (ws / target before resolve)
3. Add workspace picker UI with selectWorkspace adapter (preload bridge ready)
4. Disable start/goal when no workspace selected
5. All file ops remain bound to workspace; backend is the final security boundary

## Consequences

- Relative paths like README.md now work correctly inside workspace
- Sibling prefix attack (project_evil vs project) is correctly denied
- Users can change workspace from the sidebar without re-running the wizard
- preload.ts can be wired to Electron dialog.showOpenDialog later
