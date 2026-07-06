# Decision 046: Controlled Execution Handoff

## Decision
Add a controlled execution handoff layer after queue approval. A handoff is an audit record and UI instruction for manual action; it does not execute the action.

## Rationale
M45 made pending actions visible, but approval still needed a safe next step. Separating queue approval from handoff keeps the human boundary explicit: the system can describe what to do next without running commands, approving permissions, creating goals, or starting loops.

## Rules
- Queue approval is not execution.
- Handoff creation is not execution.
- Verification commands are copied as manual terminal suggestions only.
- Permission handoffs direct the user to the original permission panel and do not call PermissionGate approve.
- Goal-input handoffs create only draft objective text and do not call createGoal or runAgentLoop.
- A queue item must be `approved` before handoff creation.
- The same queue item cannot create duplicate handoff records.

## Safety
The handoff service and API do not call Harness.submit_tool_request, approve_permission, run_agent_loop, shell, push, release, or delete. Desktop renderer code only calls typed handoff endpoints and does not add ipcRenderer, fs, shell, or process access.