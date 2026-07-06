# Decision 044: Evidence-Based Task Verification

## Decision
Add a deterministic verification layer on top of TaskClosure evidence. The layer builds a plan, assesses recorded evidence, and updates next action/status only when the evidence is sufficient.

## Rationale
M43 can record real Agent Loop outcomes, but execution evidence is not the same as completion evidence. A conservative heuristic keeps completion decisions explainable without adding LLM judgment or shell execution.

## Rules
- Pending permission has highest priority and maps to `waiting_permission`.
- Stopped tasks remain stopped and require replanning or human handling.
- Failed tasks produce repair suggestions and do not complete.
- Missing evidence produces `missing_evidence` and lists missing checks.
- Passed assessment may set closure status to `completed`.

## Command Suggestions
Verification checks may include a command string, but it is only a suggestion. Backend does not execute it, and desktop UI shows it as text with `不执行命令`.

## Safety
No push, release, delete, automatic approval, shell execution, PermissionGate bypass, renderer dangerous API, `as any`, or `unknown as` is introduced by M44.
