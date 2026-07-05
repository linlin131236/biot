# Exec Plan 002 - Memory Layer Foundation

## Goal

Create Bolt's own memory abstraction before integrating external engines such as Mem0.

## Steps

1. Add Python MemoryStore and tests.
2. Move Harness failure recall to MemoryStore.
3. Add memory snapshot and P0 API endpoints.
4. Add shared protocol memory types.
5. Add desktop memory client, state, and panel.
6. Document Mem0 as a future adapter, not the default abstraction.
7. Run full quality gates.

## Verification

- Python pytest passes.
- pnpm quality passes.
- desktop build passes.
