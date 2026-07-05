# Decision 006 - ChangeSet Diff Confirmed Write

## Status

Accepted.

## Context

Bolt needs write capability, but all file modifications must remain inspectable and reversible before application. M6 depends on the M5 harness, permission queue, trace log, and path guards.

## Decision

Implement `file.write` as a two-step operation:

1. Proposal builds a `ChangeSet` with path, base hash, proposed content, unified diff, and `pending_review` status.
2. Approval applies the change only if the current file hash still matches the proposal base hash.

Rejected changes are discarded by permission state and leave files untouched. Failed applies record failure memory and `change.failed` trace events.

## Consequences

M7 shell execution and M8 LLM integration can request writes without direct file mutation. Desktop can render diff payloads from pending permissions and call the existing approve/reject endpoints to apply or discard changes.
