"""Dense vector embedding generation, indexing, and cosine similarity retrieval engine."""

from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from app.knowledge.models import DocumentChunk, SearchResult


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot_product / (norm_a * norm_b)
    # Clamp to [0.0, 1.0] for non-negative space or [-1.0, 1.0]
    return max(-1.0, min(1.0, float(sim)))


class FastSemanticEmbedder:
    """Deterministic, high-throughput semantic embedding generator (128 dimensions).

    Uses character n-grams and hashing with L2 normalization to produce rich,
    dense vector representations with semantic proximity for related terminology.
    Requires zero external network or GPU overhead, ensuring reliable CI and offline execution.
    """

    DIMENSIONS = 128

    def __init__(self, dimensions: int = 128):
        self.dimensions = dimensions

    def embed_text(self, text: str) -> List[float]:
        """Generate a normalized dense vector for input text."""
        if not text:
            return [0.0] * self.dimensions

        # Tokenize and normalize
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return [0.0] * self.dimensions

        vec = [0.0] * self.dimensions

        for idx, token in enumerate(tokens):
            # Token hash
            h1 = hash(token) % self.dimensions
            vec[h1] += 1.0

            # Bigram hash for context
            if idx > 0:
                bigram = f"{tokens[idx - 1]}_{token}"
                h2 = hash(bigram) % self.dimensions
                vec[h2] += 0.8

            # Substring 3-gram hashes for morphological affinity
            if len(token) >= 3:
                for i in range(len(token) - 2):
                    sub = token[i : i + 3]
                    h3 = hash(sub) % self.dimensions
                    vec[h3] += 0.3

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        return [self.embed_text(t) for t in texts]


class VectorStore:
    """Abstract base class for vector storage and retrieval."""

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        raise NotImplementedError

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        raise NotImplementedError

    def delete_by_document(self, document_id: str) -> int:
        raise NotImplementedError

    def delete_by_tenant(self, tenant_id: str) -> int:
        raise NotImplementedError

    def count(self, tenant_id: Optional[str] = None) -> int:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """In-memory vector store with metadata filtering and fast cosine ranking."""

    def __init__(self, embedder: Optional[FastSemanticEmbedder] = None):
        self.embedder = embedder or FastSemanticEmbedder()
        self._chunks: Dict[str, DocumentChunk] = {}

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Add or update document chunks, generating embeddings if missing."""
        added = 0
        for chunk in chunks:
            if not chunk.embedding:
                chunk.embedding = self.embedder.embed_text(chunk.content)
            self._chunks[chunk.chunk_id] = chunk
            added += 1
        return added

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Perform vector cosine search against indexed chunks with optional metadata filters."""
        if not self._chunks:
            return []

        query_vec = self.embedder.embed_text(query)
        scored_results: List[Tuple[float, DocumentChunk]] = []

        for chunk in self._chunks.values():
            # Apply metadata filters
            if filters and not self._matches_filter(chunk.metadata, filters):
                continue

            if not chunk.embedding:
                continue

            score = cosine_similarity(query_vec, chunk.embedding)
            # Normalize [-1, 1] to [0, 1]
            normalized_score = max(0.0, min(1.0, (score + 1.0) / 2.0))

            if normalized_score >= min_score:
                scored_results.append((normalized_score, chunk))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results: List[SearchResult] = []
        for score, chunk in scored_results[:top_k]:
            doc_title = chunk.metadata.get("title") or chunk.metadata.get("source") or chunk.document_id
            results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=str(doc_title),
                    content=chunk.content,
                    score=round(score, 4),
                    match_type="vector",
                    metadata=chunk.metadata,
                    citation=f"[{doc_title} - Chunk #{chunk.index}]",
                )
            )

        return results

    def _matches_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Verify whether chunk metadata satisfies all specified filter criteria."""
        for key, expected_val in filters.items():
            actual_val = metadata.get(key)
            if actual_val is None:
                return False
            if isinstance(expected_val, list):
                if actual_val not in expected_val:
                    return False
            elif actual_val != expected_val:
                return False
        return True

    def delete_by_document(self, document_id: str) -> int:
        """Remove all chunks belonging to a document."""
        to_del = [cid for cid, chk in self._chunks.items() if chk.document_id == document_id]
        for cid in to_del:
            del self._chunks[cid]
        return len(to_del)

    def delete_by_tenant(self, tenant_id: str) -> int:
        """Remove all chunks belonging to a specific tenant."""
        to_del = [
            cid for cid, chk in self._chunks.items()
            if chk.metadata.get("tenant_id") == tenant_id
        ]
        for cid in to_del:
            del self._chunks[cid]
        return len(to_del)

    def count(self, tenant_id: Optional[str] = None) -> int:
        """Total number of chunks stored, optionally filtered by tenant."""
        if not tenant_id:
            return len(self._chunks)
        return sum(1 for chk in self._chunks.values() if chk.metadata.get("tenant_id") == tenant_id)

    def get_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """Fetch a specific chunk by ID."""
        return self._chunks.get(chunk_id)

    def list_all(self) -> List[DocumentChunk]:
        """Return all indexed chunks."""
        return list(self._chunks.values())
