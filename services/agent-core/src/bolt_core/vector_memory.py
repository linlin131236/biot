"""Vector memory: embedding-based semantic search.

Uses deterministic local hash embedding by default (no external deps).
Can be swapped for Ollama/OpenAI embedding providers.
"""

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Protocol


_SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
]


@dataclass(frozen=True)
class MemoryVector:
    memory_id: str
    content: str
    vector: list[float]
    metadata: dict
    score: float = 0.0


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float] | None: ...


class LocalHashEmbedding:
    """Deterministic hash-based embedding for testing/fallback."""

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    def embed(self, text: str) -> list[float] | None:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        result = []
        for i in range(self._dim):
            byte_val = h[i % len(h)]
            result.append((byte_val / 255.0) * 2.0 - 1.0)
        norm = math.sqrt(sum(x * x for x in result))
        if norm == 0:
            return result
        return [x / norm for x in result]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


class VectorMemoryStore:
    """In-memory vector store with optional embedding provider."""

    def __init__(self, embedding: EmbeddingProvider | None = None) -> None:
        self._embedding = embedding
        self._vectors: dict[str, MemoryVector] = {}

    def record(self, memory_id: str, content: str,
               metadata: dict) -> MemoryVector | None:
        if _contains_secret(content):
            return None
        if self._embedding is None:
            # Store without vector (search will be empty)
            mv = MemoryVector(memory_id=memory_id, content=content,
                              vector=[], metadata=metadata)
            self._vectors[memory_id] = mv
            return mv
        vector = self._embedding.embed(content)
        if vector is None:
            mv = MemoryVector(memory_id=memory_id, content=content,
                              vector=[], metadata=metadata)
            self._vectors[memory_id] = mv
            return mv
        mv = MemoryVector(memory_id=memory_id, content=content,
                          vector=vector, metadata=metadata)
        self._vectors[memory_id] = mv
        return mv

    def search(self, query: str, limit: int = 10) -> list[MemoryVector]:
        if self._embedding is None:
            return []
        query_vec = self._embedding.embed(query)
        if query_vec is None:
            return []
        scored = []
        for mv in self._vectors.values():
            if not mv.vector:
                continue
            sim = _cosine_similarity(query_vec, mv.vector)
            scored.append(MemoryVector(
                memory_id=mv.memory_id, content=mv.content,
                vector=mv.vector, metadata=mv.metadata, score=sim))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def delete(self, memory_id: str) -> None:
        self._vectors.pop(memory_id, None)
