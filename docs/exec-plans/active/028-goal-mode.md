# Exec Plan 028 - Goal Mode: Persistent Long-Running Autonomous Tasks

## Goal

Add a `/goal` command that runs persistent long tasks as a loop of plan, act, test, review, and iterate until completion criteria are met or a budget/stop condition triggers.

Goal Mode is the control plane for serious work. It lets Bolt preserve an objective, track evidence, self-correct, pause, resume, and stop safely.

## Why Now

The current agent loop is short-lived and step-limited. Real coding work often needs many iterations: inspect state, make changes, run tests, diagnose failures, repair, and verify again. Without Goal Mode, Bolt cannot reliably handle migrations, large bug fixes, broad test repair, or multi-file implementation work.

## Key Architecture Decisions

### Structured Goal

Represent each goal with:

- Objective.
- Completion criteria.
- Constraints.
- Step, cost, and wall-time budgets.
- Workspace.
- Allowed tools.
- Auto-approve flag, default off.

GoalBuilder helps turn vague requests into audit-ready goals. A goal is audit-ready only when Bolt can name what success means and how it will verify success.

### Goal Runner

GoalRunner owns the autonomous loop:

1. Check stop conditions.
2. Assess current state.
3. Check completion against evidence.
4. Plan the next action.
5. Execute through ToolExecutor and PermissionGate.
6. Record evidence.
7. Self-correct on failure.
8. Repeat until completed, paused, failed, or budget exhausted.

The runner must not declare success from model confidence alone. It must run or cite concrete checks relevant to the completion criteria.

### Evidence Log

Every step records immutable evidence:

- Step number.
- Action.
- Result.
- Relevant test or command output.
- Files changed.
- Timestamp.

Recent evidence is fed back into the model context. The full log remains available for audit.

### Lifecycle Commands

Add `/goal` commands:

- `/goal <objective>` creates and starts a goal.
- `/goal status` shows state, steps, cost, elapsed time, and evidence count.
- `/goal pause` pauses the current goal.
- `/goal resume` resumes a paused goal.
- `/goal clear` abandons the current goal.
- `/goal evidence` shows the evidence log.
- `/goal budget` shows budget usage.

### Persistence

Goals persist to disk under `~/.bolt/goals/{goal_id}/`. Saved state includes goal definition, step count, evidence log, memory snapshot or references, and enough context to resume safely.

On startup, Bolt detects unfinished goals and offers to resume. Resume should detect obvious file drift since the last save.

### System Prompt

Goal Mode uses a specialized prompt that includes the objective, completion criteria, constraints, current step, budget, recent evidence, and available tools. The prompt rules emphasize evidence, non-repetition of failed approaches, budget awareness, and blocker reporting.

### Integration Points

- CostTracker enforces goal budgets.
- AutoCompact preserves long-running context.
- PermissionGate remains mandatory.
- MemoryStore records durable findings.
- CheckpointManager can save periodic state.
- MoA may assist with hard planning steps after provider work is stable.
- Hooks can run after each goal step after M27.

## Scope

- `goal.py` for `Goal`, `GoalBuilder`, and audit-readiness checks.
- `goal_runner.py` for the persistent loop.
- `Evidence` and `EvidenceLog`.
- Goal lifecycle commands and API endpoints.
- Goal persistence and startup recovery.
- Desktop goal panel, evidence timeline, and pause/resume/clear controls.
- Tests for goal building, execution, self-correction, stop conditions, persistence, evidence, and lifecycle controls.

## Out of Scope

- Full provider registry work from M26.
- Full auto-compact implementation from M27.
- MoA-by-default planning.
- Remote gateway control.
- Subagent orchestration.
- Auto-approve as the default.
- Bypassing user confirmation for writes or shell commands.

## Safety Boundary

- Default `max_steps=100` prevents infinite loops.
- Default `max_cost=$5.00` prevents runaway spend.
- Default `max_wall_time=3600` prevents endless runtime.
- Completion requires evidence such as tests, grep results, command output, or inspected files.
- The same failed sub-problem cannot be retried indefinitely.
- PermissionGate still applies unless a separately approved auto-approve mode is enabled.
- The UI should warn before running a goal on `main` or `master`.
- Evidence entries are immutable.
- When budget is low, Bolt wraps up current work instead of starting a risky new branch of work.

## Verification

1. All existing tests pass.
2. New tests:
   - `test_goal_builder_structures_vague_objective`
   - `test_goal_builder_rejects_unauditably_vague_goal`
   - `test_goal_runner_completes_simple_goal`
   - `test_goal_runner_self_corrects_on_failure`
   - `test_goal_runner_stops_at_max_steps`
   - `test_goal_runner_stops_at_max_cost`
   - `test_goal_runner_stops_at_max_wall_time`
   - `test_goal_runner_checks_completion_with_evidence`
   - `test_goal_runner_pauses_and_resumes`
   - `test_goal_persistence_save_and_load`
   - `test_goal_persistence_detects_file_conflicts`
   - `test_evidence_log_records_each_step`
   - `test_evidence_log_summary_for_context`
   - `test_goal_lifecycle_create_pause_resume_clear`
3. `pnpm quality` passes.
4. Source files stay under 300 lines each.

## Acceptance Criteria

- [ ] `/goal <objective>` creates and starts a persistent autonomous loop.
- [ ] GoalRunner loops through plan, act, test, review, and iterate.
- [ ] Completion is evidence-based, not model guessing.
- [ ] Failed actions trigger re-planning with retry limits.
- [ ] `max_steps`, `max_cost`, and `max_wall_time` are enforced.
- [ ] `/goal status`, pause, resume, clear, evidence, and budget commands work.
- [ ] Goals persist to disk and can resume after interruption.
- [ ] Resume detects obvious workspace conflicts.
- [ ] Evidence log provides an immutable audit trail.
- [ ] GoalBuilder rejects or clarifies unauditably vague goals.
- [ ] Desktop UI shows objective, progress, current action, recent evidence, and controls.
- [ ] All tests pass and `pnpm quality` passes.
