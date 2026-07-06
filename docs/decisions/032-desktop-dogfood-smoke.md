# M32 Desktop Dogfood Smoke

## Status

Accepted.

## Context

M31 proved that the backend route wiring works end-to-end through an integration smoke test. However, the desktop product layer had no test or UI entry for the full dogfood path. The App toolbar had corrupted button labels, and the workflow client only covered harness-level operations.

## Decision

M32 adds focused dogfood smoke tests at both the backend and desktop levels, wires the workflow client to the autonomy API surface, and adds minimal UI entries for goal, timeline, and review. The Dogfood panel in the workbench surface shows goal status, review results, and timeline event count.

Unwired surfaces (`/skills`, `/delegation/tasks`) continue to return 404 or throw explicitly. M32 does not fake their existence.

## Consequences

The desktop product now has a verifiable dogfood workflow. Future phases that add new autonomy surfaces must also add entries to the Dogfood panel or the appropriate workflow area.

M32 does not add new autonomous behavior, release packaging, signing, or online updates.
