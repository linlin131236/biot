# Decision 011: Harness Engineering

## Status

Accepted.

## Context

Bolt needs to evolve its own harness without creating privileged maintenance paths. The existing architecture requires permission gates, traces, and ChangeSet review before side effects.

## Decision

M11 adds mechanical architecture checks, golden principle docs, CI gates, and a manual document gardener. The gardener reads failure memory and proposes failure pattern Markdown through the existing `file.write` flow.

## Consequences

- Architecture violations fail `pnpm quality` and CI.
- `AGENTS.md` remains a short map; detailed rules live in docs.
- Self-maintenance can propose repository changes but cannot write, commit, push, or open PRs automatically.
- Failure patterns become durable files under `docs/failure-patterns/` after user approval.
