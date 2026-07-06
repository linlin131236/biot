# Decision 043: Bind Task Closure To Real Agent Loop

## Decision
Use one TaskClosureService instance per FastAPI app and inject it into both the task-closure router and Harness. Harness owns run lifecycle, so it records Agent Loop outcomes into a closure only when a closure is bound to the run.

## Rationale
M42 made closure a conservative evidence recorder. M43 keeps that boundary: closure records status and evidence, while Harness, PermissionGate, and tool executors keep their existing responsibilities. A single app-level service avoids the M42 global-router instance split where a closure could be created in one service and queried from another.

## Status Mapping
- loop start -> executing
- pending_permission / pause_for_permission -> waiting_permission
- max_steps_reached -> stopped
- denied / rejected / terminal_failure -> failed
- failed / recoverable_failure -> repairing or failed at terminal boundary
- completed -> completed

## Safety
TaskClosureService never executes shell, calls tool executors, approves permissions, deletes files, releases, or pushes. Pending permission remains queued until the user approves through the existing permission UI.
