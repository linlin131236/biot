# Decision 049: Execution Result Evidence Ingestion

## Decision
Ingest ToolResult values returned by the existing PermissionGate approval/rejection endpoints into execution handoff records, execution queue items, and task closure command evidence.

## Rationale
M48 creates a pending permission but deliberately does not execute. Once a user manually approves or rejects that pending permission through the existing PermissionGate flow, the result must be reflected in the audit trail. M49 closes that evidence loop without creating any new execution entry point.

## Rules
- Only ToolResult.request_id values mapped to a handoff.permission_request_id are handled.
- Unknown request_id values are ignored.
- executed completes the handoff and queue item, and records verification command output as task closure evidence.
- failed, denied, and rejected fail the handoff and queue item.
- rejected and denied do not create command evidence.
- Terminal handoffs are not rewritten by repeated ingestion.
- M49 does not call approve_permission, shell execution, createGoal, or runAgentLoop.

## Safety
Execution still happens only inside the existing Harness.approve_permission path after a user approves a pending permission. Ingestion receives the resulting ToolResult and records evidence; it does not grant permission or execute tools.
