"""Context re-ranking and Maximal Marginal Relevance (MMR) diversity optimization."""

from __future__ import annotations

import re
from typing import List, Optional
from app.knowledge.models import SearchResult
from app.knowledge.vector_store import FastSemanticEmbedder, cosine_similarity


class ContextReranker:
    """Re-ranks retrieved candidates for maximum relevance, diversity (MMR), and coverage."""

    def __init__(self, embedder: Optional[FastSemanticEmbedder] = None):
        self.embedder = embedder or FastSemanticEmbedder()

    def rerank_mmr(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
        lambda_param: float = 0.7,
    ) -> List[SearchResult]:
        """Apply Maximal Marginal Relevance to balance relevance and information diversity.

        Args:
            query: The search query.
            candidates: Initial retrieved candidate results.
            top_k: Number of final results to retain.
            lambda_param: 1.0 = Pure relevance, 0.0 = Pure diversity, 0.7 = Standard balanced.
        """
        if not candidates or top_k <= 0:
            return []

        if len(candidates) <= top_k:
            return candidates

        # Precompute embeddings
        query_vec = self.embedder.embed_text(query)
        doc_vecs = [self.embedder.embed_text(c.content) for c in candidates]

        selected_indices: List[int] = []
        unselected_indices = list(range(len(candidates)))

        # First item is the one with highest relevance to query
        best_first = -1
        best_sim = -1.0
        for idx in unselected_indices:
            sim = cosine_similarity(query_vec, doc_vecs[idx])
            if sim > best_sim:
                best_sim = sim
                best_first = idx

        if best_first != -1:
            selected_indices.append(best_first)
            unselected_indices.remove(best_first)

        # Iteratively select items that maximize MMR
        while unselected_indices and len(selected_indices) < top_k:
            best_mmr = -float("inf")
            best_cand = -1

            for idx in unselected_indices:
                rel = cosine_similarity(query_vec, doc_vecs[idx])
                # Max similarity to any already selected document
                max_redundancy = max(cosine_similarity(doc_vecs[idx], doc_vecs[s]) for s in selected_indices)

                mmr = lambda_param * rel - (1.0 - lambda_param) * max_redundancy
                if mmr > best_mmr:
                    best_mmr = mmr
                    best_cand = idx

            if best_cand != -1:
                selected_indices.append(best_cand)
                unselected_indices.remove(best_cand)
            else:
                break

        return [candidates[i] for i in selected_indices]

    def boost_headers(self, query: str, results: List[SearchResult]) -> List[SearchResult]:
        """Apply a contextual relevance multiplier when document headers match query keywords."""
        query_terms = set(re.findall(r"\w+", query.lower()))
        if not query_terms:
            return results

        boosted: List[SearchResult] = []
        for res in results:
            header_path = str(res.metadata.get("header_path", "")).lower()
            title = res.title.lower()

            matches = sum(1 for t in query_terms if t in header_path or t in title)
            if matches > 0:
                boost_multiplier = 1.0 + min(0.3, matches * 0.1)
                new_score = min(1.0, res.score * boost_multiplier)
                res.score = round(new_score, 4)

            boosted.append(res)

        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted
