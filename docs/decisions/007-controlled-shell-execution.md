# Decision 007 - Controlled Shell Execution

## Status

Accepted.

## Context

Bolt needs command execution for tests, builds, and project inspection, but shell commands are higher risk than read-only tools and file writes. They must stay behind the same harness, permission, and trace boundaries.

## Decision

Introduce `shell.execute` as the controlled command tool:

- Submission evaluates command risk and queues permission for allowed command classes.
- Approval executes the command in a workspace-contained working directory.
- Destructive commands and pipe-to-shell install patterns are denied before queuing.
- Command execution captures stdout and stderr, enforces timeout, and truncates large output.
- Execution success and failure use the existing `ToolResult`, trace, and failure-memory flow.

## Consequences

M8 can ask the harness to run tests and build commands through a permissioned shell path. Interactive PTY and live WebSocket streaming remain future polish beyond this foundation, but the safety and execution boundary is now in place.
