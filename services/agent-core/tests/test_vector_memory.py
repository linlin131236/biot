from bolt_core.vector_memory import (
    EmbeddingProvider, LocalHashEmbedding, VectorMemoryStore, MemoryVector,
)


def test_local_hash_embedding_deterministic():
    embedder = LocalHashEmbedding()
    v1 = embedder.embed("hello world")
    v2 = embedder.embed("hello world")
    assert v1 == v2


def test_local_hash_embedding_different_text():
    embedder = LocalHashEmbedding()
    v1 = embedder.embed("hello")
    v2 = embedder.embed("goodbye")
    assert v1 != v2


def test_local_hash_embedding_dimension():
    embedder = LocalHashEmbedding(dim=64)
    v = embedder.embed("test")
    assert len(v) == 64


def test_vector_store_record_and_search():
    store = VectorMemoryStore(embedding=LocalHashEmbedding(dim=32))
    store.record("mem_1", "authentication bug in login", {"source": "test"})
    store.record("mem_2", "database connection timeout", {"source": "test"})
    store.record("mem_3", "CSS layout issue on mobile", {"source": "test"})

    results = store.search("login authentication error", limit=3)
    assert len(results) == 3
    # Hash embedding is deterministic but not semantically meaningful
    assert all(r.score != 0.0 for r in results)
    ids = [r.memory_id for r in results]
    assert "mem_1" in ids


def test_vector_store_delete():
    store = VectorMemoryStore(embedding=LocalHashEmbedding(dim=32))
    store.record("mem_1", "test content", {})
    store.delete("mem_1")
    results = store.search("test content")
    assert all(r.memory_id != "mem_1" for r in results)


def test_vector_store_metadata_preserved():
    store = VectorMemoryStore(embedding=LocalHashEmbedding(dim=32))
    store.record("mem_1", "test", {"source": "api", "scope": "session"})
    results = store.search("test")
    assert len(results) >= 1
    assert results[0].metadata["source"] == "api"


def test_vector_store_no_secret_ingestion():
    store = VectorMemoryStore(embedding=LocalHashEmbedding(dim=32))
    # Content with API key pattern should be rejected
    result = store.record("mem_secret", "my api key is sk-abc123def456ghi789jkl012mno", {})
    assert result is None


def test_vector_store_search_has_source_and_score():
    store = VectorMemoryStore(embedding=LocalHashEmbedding(dim=32))
    store.record("mem_1", "python testing best practices", {"source": "docs"})
    results = store.search("testing")
    assert len(results) >= 1
    assert hasattr(results[0], "score")
    assert "source" in results[0].metadata


def test_vector_store_fallback_on_no_embedding():
    """Without embedding provider, store should still work with empty search."""
    store = VectorMemoryStore(embedding=None)
    store.record("mem_1", "test content", {"source": "test"})
    results = store.search("test")
    assert results == []  # No vector search possible without embedding
