# Decision 048: PermissionGate-Bound Execution Bridge

## Decision
Add a request-only bridge that turns an approved manual_verification handoff into a PermissionGate pending permission. The bridge constructs a shell.execute ToolRequest and evaluates it with PermissionGate, but it never calls Harness.submit_tool_request and never executes the command.

## Rationale
M45 queue approval and M46 handoff are intent records, not execution permission. M48 adds the next boundary explicitly: a handoff can ask the existing PermissionGate panel for human approval. This keeps queue approval separate from real execution authorization and prevents allowed requests from running immediately through Harness.submit_tool_request.

## Rules
- Only manual_verification handoffs can request execution permission.
- The command must come from the handoff record.
- The workdir must come from the app/harness workspace.
- PermissionGate denied means the handoff fails and no permission is queued.
- Non-denied decisions are always queued as pending_permission for later human approval.
- Repeated request-permission calls return the existing handoff and do not duplicate permission requests.
- The bridge does not approve permissions, run shell, create goals, or start Agent Loop.

## Safety
The bridge writes only audit metadata back to the handoff record: permission_request_id, permission_status, and bridge_error. Desktop receives no node capabilities and only calls the request-permission API.
