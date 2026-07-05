# Security

Bolt treats local files and commands as privileged operations.

## Defaults

- Read workspace files only when needed for the task.
- Write operations require a change set and confirmation.
- Shell commands require confirmation.
- Destructive commands are denied by default.
- Secret paths are denied by default.
- Network upload of local content is high risk.

## Harness Rule

Every tool request must have a permission decision and a trace event before it can produce a side effect.

Approval is not real system execution. Current approved tool requests only run through FakeToolExecutor, which has no shell, file, delete, or network side effects.
