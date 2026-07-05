# Decision 002 - Memory Layer Foundation

Date: 2026-07-05

## Completed

- Added `MemoryStore` as Bolt's local memory abstraction.
- Upgraded failure memory into the memory layer.
- Kept `/context/p0` compatible while adding `/memory` and `/memory/p0`.
- Added shared protocol types for memory snapshots.
- Added desktop memory snapshot client/state and Memory panel.
- Documented Mem0 as a future adapter.

## Decision

Bolt owns the memory contract. Mem0 is a candidate backend, not the product abstraction.

## Next

- Add persistent SQLite storage.
- Add session/project/user/tool memory scopes.
- Add memory list/delete UI.
- Add optional Mem0 adapter after local-only mode is proven.
