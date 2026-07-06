# Decision 045: Human Approval Execution Queue

## Decision
Add an in-memory execution queue for suggested next actions. Queue items are records with risk and status; they do not execute commands or approve PermissionGate requests.

## Rationale
M44 can identify missing evidence and repair needs, but acting on those suggestions requires a human approval boundary. A separate queue makes pending actions visible and auditable without changing tool execution semantics.

## Rules
- Verification commands are stored as command suggestions only.
- Queue approval is not PermissionGate approval.
- Queue completion records a user-provided result and does not mutate closure evidence.
- Closure completion still requires recorded TaskClosure evidence plus assessment.
- Duplicate pending items for the same closure/kind/title/command are suppressed.

## Safety
The queue does not call Harness, shell, Agent Loop, push, release, delete, or PermissionGate approve. Renderer code only calls queue API endpoints and does not expose fs, shell, process, or ipcRenderer.
