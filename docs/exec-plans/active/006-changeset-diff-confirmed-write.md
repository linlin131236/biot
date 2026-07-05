# Exec Plan 006 - ChangeSet Diff Confirmed Write

## Goal

Complete Milestone 6 so Bolt can propose file writes as change sets, show a diff payload, and only apply after user approval.

## Completed Scope

- Added `apply_change_set` with base-hash verification before writing.
- Added `file.write` proposal flow that creates a `ChangeSet` and queues it for permission review.
- Pending write permissions carry `change_set` payload data for Desktop diff rendering.
- Approving a write applies the change set and records `change.applied` or `change.failed`.
- Rejecting a write leaves the file untouched and records `change.rejected`.
- Base-hash mismatches reject the write and record failure memory.
- Shared TypeScript protocol now includes `ChangeSet`.
- Desktop state and harness client tests cover diff-review payloads.

## Safety Boundary

Writes are only allowed for paths accepted by `PathGuard`. Workspace-external paths and secret paths are denied. A write never applies during proposal; approval re-checks the file base hash before writing.

## Verification

- Python pytest passes.
- pnpm quality passes.
- desktop build passes.
