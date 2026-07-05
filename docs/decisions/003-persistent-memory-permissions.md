# Decision 003 - Persistent Memory and Permissions

Date: 2026-07-05

## Completed

- Added optional SQLite persistence to MemoryStore.
- Added pending permission queue.
- Added approve/reject state transitions in Harness.
- Added permission API endpoints.
- Added shared protocol types for pending permissions.
- Added desktop client/state support for pending permissions.

## Decision

Permission approval is not execution. Real file writes and shell commands remain blocked until a ToolExecutor milestone adds side-effect boundaries and tests.

## Next

- Persist harness runs and trace events.
- Add visible permission list UI with approve/reject buttons.
- Add ToolExecutor with fake executor tests first.
- Add real file write only after diff confirmation is complete.
