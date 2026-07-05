# Decision 001 - Harness Foundation

Date: 2026-07-05

## Completed

- Converted `AGENTS.md` into an agent-readable repository map.
- Added required knowledge-map documents under `docs/`.
- Added documentation and boundary quality gates.
- Added Python Agent Core harness modules:
  - `tool_protocol.py`
  - `permission_gate.py`
  - `trace.py`
  - `harness.py`
- Added harness API endpoints for runs, tool requests, traces, and P0 context.
- Added `@bolt/shared` protocol package.
- Added desktop harness client and harness state handling.
- Added UI panels for Harness Trace and Pending Permissions.

## Verification

```text
Python pytest: 19 passed
pnpm quality: passed
Desktop build: passed
```

## Design Decision

Bolt harness engineering starts with protocol and feedback loops before real side effects. Shell execution and file writes remain unimplemented until permission, trace, and failure memory flows are stable.

## Next

- Persist harness runs and failure memory.
- Add pending permission API and desktop confirmation UI.
- Add workspace selection and file read/search tool requests.
