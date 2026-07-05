# Mem0 Reference

Mem0 (`mem0ai/mem0`) is an Apache-2.0 universal memory layer for AI agents.

## Bolt Decision

Bolt will not bind directly to Mem0 as its memory abstraction. Bolt owns `MemoryStore`; Mem0 can be added later as `Mem0MemoryStore`.

## Why

- Desktop memory may contain private user and project data.
- Mem0 defaults can use cloud LLM and embedding providers.
- Bolt needs local-first behavior by default.
- Adapter boundaries keep the product replaceable.

## Future Adapter

A future adapter may map:

```text
MemoryStore.record -> mem0.add
MemoryStore.search -> mem0.search
MemoryStore.delete -> mem0.delete
```

The adapter must support local-only configuration before it becomes a default option.
