# Exec Plan 021 - Vector Memory

## Goal

Replace string-matching `MemoryStore.search` with semantic vector search so Bolt can retrieve relevant memories by meaning, not just by keyword.

## Why Now

Plans 019-020 make Bolt functional, but its memory is blind. `MemoryStore.search` does `needle in content.lower()` — if you search for "authentication bug" it won't find a memory stored as "login token validation failed". Real agents need semantic retrieval.

## Architecture

```
User query / Agent context
    ↓
MemoryStore.search(query)
    ↓
Embed query → nomic-embed-text (Ollama, local, free)
    ↓
Search Qdrant (local, file-based) → top-k results
    ↓
Fallback: string match (if embedding service down)
    ↓
Return MemoryRecord list
```

## Scope

### 1. Add embedding dependency

File: `services/agent-core/pyproject.toml`

```
dependencies = [
  # ... existing ...
  "openai>=1.50",
  "qdrant-client>=1.11",
  "ollama>=0.4"
]
```

### 2. Create embedding service

New file: `services/agent-core/src/bolt_core/embedding.py`

```python
class EmbeddingService:
    def __init__(self, model="nomic-embed-text", base_url="http://localhost:11434"):
        # Uses ollama client
        # Fallback: if Ollama not running, return None
        # Caches embeddings in memory (LRU, max 1000)
    
    def embed(self, text: str) -> list[float] | None:
        # Call Ollama /api/embeddings
        # Return 768-dim vector or None on failure
    
    def embed_batch(self, texts: list[str]) -> list[list[float] | None]:
        # Batch embed for indexing
```

### 3. Create vector store

New file: `services/agent-core/src/bolt_core/vector_store.py`

```python
class VectorStore:
    def __init__(self, path: str, dim: int = 768):
        # Qdrant local mode, storage at {path}/qdrant/
        # Collection: "bolt_memories"
    
    def upsert(self, memory_id: str, vector: list[float], metadata: dict):
        # Insert or update embedding
    
    def search(self, vector: list[float], limit: int = 10) -> list[ScoredMemory]:
        # Cosine similarity search
    
    def delete(self, memory_id: str):
        # Remove embedding
```

### 4. Update MemoryStore

File: `services/agent-core/src/bolt_core/memory_store.py`

- Add optional `embedding_service` and `vector_store` params.
- On `record()`: embed content, upsert to vector store (async, non-blocking on failure).
- On `search()`: try vector search first; if embedding service unavailable, fall back to current string match.
- On `resolve()`: delete from vector store too.

### 5. Wire through Harness

File: `services/agent-core/src/bolt_core/harness.py`

- Pass embedding service to MemoryStore constructor if Ollama is available.
- Add health check: `GET /memory/embedding-status` → {available: bool, model: str}.

## Safety Boundary

- Embedding runs locally via Ollama (no data leaves the machine).
- Qdrant stores locally (file-based, no cloud).
- Vector search is additive: if embedding fails, string search still works.
- No external API calls for embedding.

## Verification

1. All existing tests pass (vector search is optional, tests without it still work).
2. New tests with mocked Ollama:
   - `test_embedding_service_embeds_text`
   - `test_embedding_service_returns_none_when_ollama_down`
   - `test_vector_store_upsert_and_search`
   - `test_memory_store_uses_vector_search_when_available`
   - `test_memory_store_falls_back_to_string_match`
3. `pnpm quality` passes.
4. Source files under 300 lines.

## Acceptance Criteria

- [ ] `EmbeddingService` with Ollama nomic-embed-text, graceful fallback.
- [ ] `VectorStore` with Qdrant local mode.
- [ ] `MemoryStore.search` uses vector search when available, string match when not.
- [ ] New records auto-embedded and upserted.
- [ ] All tests pass. No new external network egress.
