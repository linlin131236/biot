# Exec Plan 003 - Persistent Memory and Permissions

## Goal

Persist MemoryStore records and add a permission approval loop without executing real tools.

## Completed Scope

- SQLite roundtrip for MemoryStore.
- PendingPermission model and queue.
- Harness pending, approve, and reject states.
- Permission API endpoints.
- Shared protocol permission types.
- Desktop pending permission client and state.

## Safety Boundary

Approve and reject only change state and trace events. They do not run shell commands or write files.

## Verification

- Python pytest passes.
- pnpm quality passes.
- desktop build passes.
