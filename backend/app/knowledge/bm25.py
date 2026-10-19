"""Sparse BM25 Okapi lexical search index for exact keyword matching and hybrid retrieval."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from app.knowledge.models import DocumentChunk, SearchResult

# Standard English stop words
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "isn't", "it", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "shouldn't", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "were", "weren't", "what", "when", "where", "which",
    "while", "who", "whom", "why", "with", "won't", "would", "wouldn't", "you", "your", "yours",
    "yourself", "yourselves"
}


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alpha-numeric tokens, removing stop words."""
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


class BM25Index:
    """Okapi BM25 implementation optimized for enterprise chunk retrieval."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._chunks: Dict[str, DocumentChunk] = {}
        self._tokenized_corpus: Dict[str, List[str]] = {}
        self._doc_lengths: Dict[str, int] = {}
        self._doc_frequencies: Dict[str, int] = {}
        self._avg_doc_len: float = 0.0

    def add_chunks(self, chunks: List[DocumentChunk]) -> int:
        """Index a collection of document chunks."""
        added = 0
        for chunk in chunks:
            tokens = tokenize(chunk.content)
            self._chunks[chunk.chunk_id] = chunk
            self._tokenized_corpus[chunk.chunk_id] = tokens
            self._doc_lengths[chunk.chunk_id] = len(tokens)

            # Update document frequencies (unique terms per chunk)
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self._doc_frequencies[t] = self._doc_frequencies.get(t, 0) + 1
            added += 1

        self._recalculate_avgdl()
        return added

    def _recalculate_avgdl(self) -> None:
        """Update average document length across indexed corpus."""
        if self._doc_lengths:
            self._avg_doc_len = sum(self._doc_lengths.values()) / len(self._doc_lengths)
        else:
            self._avg_doc_len = 0.0

    def _idf(self, term: str) -> float:
        """Calculate standard Lucene-style Robertson-Spärck Jones IDF."""
        n_docs = len(self._tokenized_corpus)
        df = self._doc_frequencies.get(term, 0)
        if df == 0 or n_docs == 0:
            return 0.0
        # Smooth IDF: ln(1 + (N - df + 0.5) / (df + 0.5))
        return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Score indexed chunks against query terms using BM25 Okapi."""
        query_tokens = tokenize(query)
        if not query_tokens or not self._chunks:
            return []

        scores: List[Tuple[float, DocumentChunk]] = []

        for chunk_id, chunk in self._chunks.items():
            if filters and not self._matches_filter(chunk.metadata, filters):
                continue

            doc_tokens = self._tokenized_corpus[chunk_id]
            doc_len = self._doc_lengths[chunk_id]
            if doc_len == 0:
                continue

            # Calculate BM25 score
            score = 0.0
            term_counts: Dict[str, int] = {}
            for t in doc_tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for qt in query_tokens:
                if qt not in term_counts:
                    continue
                tf = term_counts[qt]
                idf = self._idf(qt)
                # BM25 tf saturation formula
                denom = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self._avg_doc_len or 1.0)))
                score += idf * (tf * (self.k1 + 1.0)) / denom

            if score > min_score:
                scores.append((score, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            return []

        # Normalize top score to 1.0
        max_score = scores[0][0] or 1.0
        results: List[SearchResult] = []

        for raw_score, chunk in scores[:top_k]:
            normalized_score = min(1.0, max(0.0, raw_score / max_score))
            doc_title = chunk.metadata.get("title") or chunk.metadata.get("source") or chunk.document_id
            results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=str(doc_title),
                    content=chunk.content,
                    score=round(normalized_score, 4),
                    match_type="bm25",
                    metadata=chunk.metadata,
                    citation=f"[{doc_title} - Chunk #{chunk.index}]",
                )
            )

        return results

    def _matches_filter(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Verify whether chunk metadata matches the filter dictionary."""
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
        """Remove chunks belonging to a document and update statistics."""
        to_del = [cid for cid, chk in self._chunks.items() if chk.document_id == document_id]
        for cid in to_del:
            tokens = self._tokenized_corpus.get(cid, [])
            for t in set(tokens):
                if t in self._doc_frequencies:
                    self._doc_frequencies[t] -= 1
                    if self._doc_frequencies[t] <= 0:
                        del self._doc_frequencies[t]
            self._chunks.pop(cid, None)
            self._tokenized_corpus.pop(cid, None)
            self._doc_lengths.pop(cid, None)

        self._recalculate_avgdl()
        return len(to_del)

    def count(self) -> int:
        """Total chunks in BM25 index."""
        return len(self._chunks)
