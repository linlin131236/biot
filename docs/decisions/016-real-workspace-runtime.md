# 016 Real Workspace Runtime

## Context

Earlier milestones used a development-machine workspace path in tests and CI compatibility shims. That was acceptable while the harness and desktop workflow were being built, but it made the runtime look tied to one checkout location.

Bolt needs each harness run to execute against the workspace selected by the desktop user, while CI and tests run in their actual checkout directories.

## Decision

M16 makes workspace selection a run-level contract:

- Desktop passes the selected workspace path when creating a harness run.
- Agent Core stores `workspace` on each run and returns it in the run response.
- Permission evaluation, tool execution, perception capture, and document gardening resolve against the run workspace.
- Agent Core defaults to the service process working directory only when a client does not provide a workspace.
- CI no longer creates a legacy development-machine junction for tests.
- Tests use temporary workspaces or neutral example paths instead of the original development-machine path.

## Consequences

Users can point Bolt at a real project directory without rebuilding or changing server code. Permission and execution boundaries now follow the active run instead of a single harness-wide executor.

Future multi-workspace features should continue to treat workspace as explicit runtime state and avoid hidden machine-specific defaults.
