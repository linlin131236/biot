# Decision 009 - Memory System

## Status

Accepted.

## Context

Bolt already had a generic memory abstraction and failure memory. M9 needs layered memory without introducing cloud storage, vector databases, or unbounded model context.

## Decision

Extend `MemoryStore` as the product memory contract:

- Support session, project, user, tool, failure, and long-term memory kinds.
- Store metadata and timestamps locally in memory or SQLite.
- Add local substring search, status filtering, and resolve lifecycle operations.
- Keep failure memory feeding P0 context.
- Add deterministic consolidation for local session preferences and tool summaries.
- Inject a capped set of active non-failure memories into agent context.
- Expose memory management through Agent Core APIs and shared desktop protocol types.

## Consequences

Bolt can grow memory behavior locally before adopting external adapters. Mem0 and Chroma remain future adapter options behind the `MemoryStore` contract, not default dependencies.
