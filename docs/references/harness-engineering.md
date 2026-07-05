# Harness Engineering Reference

This note converts the OpenAI harness engineering article into Bolt rules.

## Principles

- Humans set intent; agents execute inside a designed environment.
- When the agent fails, improve the harness instead of blindly retrying.
- Repository knowledge must live in files, not memory or chat history.
- AGENTS.md is a map, not a full manual.
- Quality, architecture, and taste must be mechanically checked.
- Every tool request needs traceability and feedback.
- Failure memory must become a constraint for the next run.

## Bolt Implementation

- `docs/` stores product, architecture, quality, and execution plans.
- `services/agent-core` owns harness state and failure constraints.
- `apps/desktop` displays pending permissions and trace events.
- `scripts/` enforces documentation, size, and boundary checks.
