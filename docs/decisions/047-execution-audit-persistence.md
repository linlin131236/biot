# Decision 047: Execution Audit Persistence

## Decision
Persist execution queue items and execution handoff records as local audit JSON so they can be restored after app restart.

## Rationale
M45 made execution queue items explicit, and M46 added controlled handoff records. Both were still memory-only, so a restart could lose approved queue state and handoff results. M47 stores that audit trail before any real execution bridge exists, so future execution work starts from recoverable records rather than transient UI state.

## Why Persistence Before Real Execution
Persistent audit records are safer to introduce before real execution because they do not expand capability. They make intent, approval state, and manual completion results recoverable without granting the app permission to run commands or approve requests.

## Rules
- Queue approve still means only queue item approval; it is not command execution.
- Queue approve still does not approve PermissionGate requests.
- Handoff still means only a manual-action record; it is not execution.
- Handoff still does not call shell, Harness.submit_tool_request, approve_permission, createGoal, or runAgentLoop.
- Persistence is audit recovery only, not execution authorization.
- Damaged audit JSON must fail loudly instead of being silently overwritten.
- M48 is the earliest milestone that may consider a PermissionGate-bound execution bridge, and it must not start without explicit approval from 爸爸.

## Safety
The store writes only queue and handoff dictionaries to UTF-8 JSON using an atomic tmp-file replace. It does not store token, certificate, environment, cache, or virtual environment material, and it does not expose renderer capabilities.
