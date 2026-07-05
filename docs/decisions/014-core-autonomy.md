# Decision 014: Core Autonomy

## Status

Accepted.

## Context

Bolt can run individual agent steps and expose them in the desktop workflow. The next risk is letting autonomous behavior proceed without clear stop conditions, verifier semantics, or tool allowlists.

## Decision

M14 adds conservative autonomy. The Agent Core supports bounded loops, but stops on pending permission, denial, rejection, or failure. Unknown tools and unsupported operations are denied before execution. Planner context includes trace, memory, failure, and perception summaries.

## Consequences

- Agent Core can execute bounded loops without adding background workers.
- PermissionGate remains the execution boundary.
- Unknown model tool requests fail closed instead of fake succeeding.
- Multi-step replanning beyond failure remains future work.
