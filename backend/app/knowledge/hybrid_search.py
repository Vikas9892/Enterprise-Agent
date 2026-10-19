"""Hybrid search engine combining dense vector similarity with sparse BM25 keyword matching via Reciprocal Rank Fusion (RRF)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.knowledge.models import DocumentChunk, SearchQuery, SearchResult
from app.knowledge.vector_store import VectorStore, InMemoryVectorStore
from app.knowledge.bm25 import BM25Index

logger = logging.getLogger("enterprise_agent.knowledge.hybrid")


class HybridSearchEngine:
    """Enterprise hybrid retrieval engine blending semantic embeddings and exact lexical matching."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        bm25_index: Optional[BM25Index] = None,
        rrf_constant: int = 60,
    ):
        self.vector_store = vector_store or InMemoryVectorStore()
        self.bm25_index = bm25_index or BM25Index()
        self.rrf_constant = rrf_constant

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Add chunks to both dense vector store and sparse BM25 index."""
        v_added = self.vector_store.add_chunks(chunks)
        b_added = self.bm25_index.add_chunks(chunks)
        logger.debug("Indexed %d chunks in vector store and %d in BM25 index", v_added, b_added)
        return v_added

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Perform hybrid retrieval combining vector and BM25 scores.

        Args:
            query: User search text or query question.
            top_k: Number of ranked chunks to return.
            alpha: Weight for dense vector search (1.0 = dense only, 0.0 = BM25 only, 0.5 = balanced).
            filters: Metadata attribute filters (e.g. tenant_id, category).
            min_score: Minimum relevance cutoff.
        """
        if not query.strip():
            return []

        # If alpha == 1.0: pure vector search
        if alpha >= 0.999:
            return self.vector_store.search(query, top_k=top_k, min_score=min_score, filters=filters)

        # If alpha == 0.0: pure BM25 search
        if alpha <= 0.001:
            return self.bm25_index.search(query, top_k=top_k, min_score=min_score, filters=filters)

        # Retrieve candidates from both sources with wider candidate window (2x top_k)
        candidate_k = max(top_k * 3, 20)
        vector_results = self.vector_store.search(query, top_k=candidate_k, filters=filters)
        bm25_results = self.bm25_index.search(query, top_k=candidate_k, filters=filters)

        # Map ranks (1-indexed)
        vector_ranks: Dict[str, Tuple[int, SearchResult]] = {
            res.chunk_id: (idx + 1, res) for idx, res in enumerate(vector_results)
        }
        bm25_ranks: Dict[str, Tuple[int, SearchResult]] = {
            res.chunk_id: (idx + 1, res) for idx, res in enumerate(bm25_results)
        }

        all_chunk_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
        if not all_chunk_ids:
            return []

        # Reciprocal Rank Fusion calculation
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, SearchResult] = {}

        w_dense = alpha
        w_sparse = 1.0 - alpha

        for cid in all_chunk_ids:
            score = 0.0
            if cid in vector_ranks:
                vrank, res = vector_ranks[cid]
                score += w_dense * (1.0 / (self.rrf_constant + vrank))
                chunk_map[cid] = res

            if cid in bm25_ranks:
                brank, res = bm25_ranks[cid]
                score += w_sparse * (1.0 / (self.rrf_constant + brank))
                if cid not in chunk_map:
                    chunk_map[cid] = res

            fused_scores[cid] = score

        # Sort descending by fused score
        sorted_cids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        if not sorted_cids:
            return []

        # Theoretical maximum RRF score occurs at rank 1 in both:
        max_possible_rrf = (w_dense / (self.rrf_constant + 1)) + (w_sparse / (self.rrf_constant + 1))
        results: List[SearchResult] = []

        for cid in sorted_cids[:top_k]:
            raw_score = fused_scores[cid]
            normalized = min(1.0, max(0.0, raw_score / max_possible_rrf))
            if normalized < min_score:
                continue

            base = chunk_map[cid]
            is_in_vec = cid in vector_ranks
            is_in_bm25 = cid in bm25_ranks
            match_mode = "hybrid" if (is_in_vec and is_in_bm25) else ("vector" if is_in_vec else "bm25")

            results.append(
                SearchResult(
                    chunk_id=base.chunk_id,
                    document_id=base.document_id,
                    title=base.title,
                    content=base.content,
                    score=round(normalized, 4),
                    match_type=match_mode,
                    metadata=base.metadata,
                    citation=base.citation,
                )
            )

        return results

    def delete_by_document(self, document_id: str) -> int:
        """Purge chunks belonging to a document from both indices."""
        v = self.vector_store.delete_by_document(document_id)
        b = self.bm25_index.delete_by_document(document_id)
        return max(v, b)

    def count(self) -> int:
        """Total chunks indexed."""
        return self.vector_store.count()
