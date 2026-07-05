# M14 Core Autonomy

## Goal

Add conservative autonomous control flow to Agent Core: bounded loops, fail-closed tools, actionable verifier statuses, and richer planning context.

## Completed Scope

- Verifier distinguishes complete, permission pause, terminal failure, recoverable failure, and replan states.
- Unknown tools and unsupported operations fail closed before execution.
- Backend exposes bounded agent loop execution with clear trace stop reasons.
- Planner prompt includes recent trace, memory tags/scopes, failure constraints, and perception metadata summaries.
- Desktop protocol/client can call the loop endpoint without changing the main UI flow.

## Safety Boundary

- No automatic approval.
- No background loop or streaming worker.
- No infinite retries.
- No commit, push, publish, or PR creation.
- All tool requests still pass through `PermissionGate` and trace recording.

## Verification

- `services/agent-core/.venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
