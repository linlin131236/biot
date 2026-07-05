# Exec Plan 007 - Controlled Shell Execution

## Goal

Complete Milestone 7 so Bolt can run shell commands only after explicit permission approval.

## Completed Scope

- Added `shell.execute` for controlled command execution.
- Enforced command workdir inside the configured workspace.
- Added command risk classification with known commands, unknown commands, and denied destructive patterns.
- Enforced default timeout and stdout/stderr output size limit.
- Routed `shell.execute` through the permission queue before execution.
- Approval executes the command and records execution trace events.
- Failures record failure memory and surface command errors.
- Shared TypeScript protocol now includes `ShellCommandPayload`.
- Desktop client and state tests cover shell permission requests.

## Safety Boundary

Commands never run at submission time. `shell.execute` requests require approval, must use a workspace-contained workdir, and are denied when they match destructive command patterns or shell-pipe install patterns.

## Verification

- Python pytest passes.
- pnpm quality passes.
- desktop build passes.
