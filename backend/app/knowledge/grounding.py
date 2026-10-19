"""Grounding guardrails, citation attribution, and hallucination verification."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple
from app.knowledge.models import SearchResult


class GroundingGuardrail:
    """Verifies that agent responses are grounded in retrieved source context and generates citations."""

    def __init__(self, min_grounding_threshold: float = 0.35):
        self.min_grounding_threshold = min_grounding_threshold

    def format_grounded_context(self, search_results: List[SearchResult]) -> str:
        """Format retrieved search results into a clean, structured context block with citations."""
        if not search_results:
            return "No enterprise knowledge documents found matching the query."

        context_lines: List[str] = [
            "### ENTERPRISE GROUNDED KNOWLEDGE BASE CONTEXT ###",
            "Use ONLY the factual information provided below. Cite sources using [Doc #] notations.",
            "",
        ]

        for idx, res in enumerate(search_results, start=1):
            source_tag = f"[Doc {idx}: {res.title} | Chunk #{res.metadata.get('index', 0)}]"
            context_lines.append(f"{source_tag}")
            context_lines.append(f"Content: {res.content.strip()}")
            context_lines.append(f"Relevance: {res.score} | Match: {res.match_type}")
            context_lines.append("-" * 40)

        return "\n".join(context_lines)

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract significant informative words, ignoring common syntax."""
        # Find capitalized words, acronyms, and alphanumeric terms
        words = re.findall(r"\b[a-zA-Z0-9_\-\$]{3,}\b", text.lower())
        # Filter obvious conversational words
        filter_words = {
            "the", "and", "this", "that", "with", "from", "have", "been", "were", "what",
            "when", "where", "which", "will", "would", "could", "should", "there", "their"
        }
        return {w for w in words if w not in filter_words and not w.isdigit()}

    def verify_grounding(
        self,
        answer: str,
        retrieved_context: List[SearchResult],
    ) -> Dict[str, Any]:
        """Evaluate how well an LLM generated answer is grounded in retrieved documents.

        Returns:
            Dict containing:
                - is_grounded: bool
                - confidence_score: float (0.0 to 1.0)
                - matched_terms: List[str]
                - ungrounded_terms: List[str]
                - citations: List[Dict[str, str]]
        """
        if not retrieved_context:
            return {
                "is_grounded": False,
                "confidence_score": 0.0,
                "matched_terms": [],
                "ungrounded_terms": list(self.extract_keywords(answer)),
                "citations": [],
                "warning": "No source context was provided to ground this answer.",
            }

        combined_source_text = " ".join([res.content for res in retrieved_context]).lower()
        answer_keywords = self.extract_keywords(answer)

        if not answer_keywords:
            return {
                "is_grounded": True,
                "confidence_score": 1.0,
                "matched_terms": [],
                "ungrounded_terms": [],
                "citations": [],
            }

        matched: List[str] = []
        ungrounded: List[str] = []

        for kw in answer_keywords:
            if kw in combined_source_text:
                matched.append(kw)
            else:
                ungrounded.append(kw)

        confidence = len(matched) / len(answer_keywords)
        is_grounded = confidence >= self.min_grounding_threshold

        citations = [
            {
                "index": idx + 1,
                "title": res.title,
                "document_id": res.document_id,
                "chunk_id": res.chunk_id,
                "score": res.score,
            }
            for idx, res in enumerate(retrieved_context)
        ]

        result = {
            "is_grounded": is_grounded,
            "confidence_score": round(confidence, 3),
            "matched_terms_count": len(matched),
            "ungrounded_terms_count": len(ungrounded),
            "matched_sample": matched[:10],
            "ungrounded_sample": ungrounded[:10],
            "citations": citations,
        }

        if not is_grounded:
            result["warning"] = "Potential hallucination detected: answer contains terms not found in source context."

        return result
