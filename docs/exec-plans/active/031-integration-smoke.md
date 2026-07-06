# M31 Integration Smoke

## Goal

Prove that the autonomous platform baseline has a working end-to-end smoke path across Agent Core routes, desktop client methods, permission flow, checkpoints, review gate, and trace timeline.

## Scope

- Add a backend integration smoke test that creates a run and goal, records conversation input, reads a workspace file, proposes and approves a patch, creates and loads a checkpoint, evaluates a review gate, runs a bounded agent loop, and reads the timeline.
- Wire the existing `CheckpointService` through `/checkpoints` and `/checkpoints/{checkpoint_id}`.
- Wire the existing `ReviewGate` through `/review/evaluate`.
- Update the desktop autonomy client so checkpoint and review methods call real endpoints.
- Keep unwired surfaces explicit when the backend has no route.
- Add M31 docs to the docs quality gate.

## Out of Scope

- New model behavior, planner behavior, skills execution, delegation execution, or MoA behavior.
- Real release packaging, publishing, signing, or auto-update.
- New `/skills` API behavior.
- Refactoring Harness, AgentLoop, or provider internals.

## Smoke Path

1. Create a harness run with a workspace.
2. Create a persistent goal.
3. Create a conversation and append a user message.
4. Execute `file.read` without permission.
5. Queue `file.patch`, approve it, and verify the file changed.
6. Create and load a checkpoint for the changed file.
7. Evaluate a review checklist with an intentional failure.
8. Run a bounded agent loop and verify timeline trace events.

## Verification

- `cd services/agent-core && .venv/Scripts/python -I -m pytest tests/test_integration_smoke.py`
- `pnpm --filter @bolt/desktop exec vitest run src/harnessClientAutonomy.test.ts`
- `cd services/agent-core && .venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
