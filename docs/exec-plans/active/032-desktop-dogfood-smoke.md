# M32 Desktop Dogfood Smoke

## Goal

Verify that the Bolt desktop product can complete a real dogfood workflow: create a run, set a goal, send a conversation message, read and patch a workspace file through the permission gate, checkpoint the result, evaluate a review gate, and read the timeline.

## Scope

- Add desktop and backend dogfood smoke tests covering the full product path.
- Wire workflow client helpers for goal, conversation, checkpoint, review, and timeline.
- Add minimal UI entries (Create Goal, Timeline, Review buttons; Dogfood panel).
- Fix corrupted button labels in the existing App toolbar.
- Add M32 docs to the docs quality gate.

## Out of Scope

- New agent intelligence, planner behavior, or model integration.
- Release packaging, signing, or auto-update (M15/M18).
- New `/skills` API behavior.
- Large UI redesign or new design system.

## Dogfood Path

1. Create a harness run with a workspace.
2. Create a goal.
3. Create a conversation and add a user message.
4. `file.read` — executed immediately without permission.
5. `file.patch` → pending_permission → approve → file changes.
6. Create and load a checkpoint for the changed file.
7. Evaluate a review checklist.
8. Fetch the run timeline.

## Verification

- `cd services/agent-core && .venv/Scripts/python -I -m pytest tests/test_dogfood_smoke.py`
- `pnpm --filter @bolt/desktop exec vitest run src/dogfoodSmoke.test.ts`
- `cd services/agent-core && .venv/Scripts/python -I -m pytest`
- `pnpm quality`
- `pnpm --filter @bolt/desktop build`
