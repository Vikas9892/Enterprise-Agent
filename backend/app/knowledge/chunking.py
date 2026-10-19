"""Semantic and structural chunking strategies for enterprise documents."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.knowledge.models import DocumentChunk


def estimate_token_count(text: str) -> int:
    """Fast, accurate token count approximation (avg 4 characters per token)."""
    if not text:
        return 0
    words = len(text.split())
    char_estimate = len(text) // 4
    return max(words, char_estimate)


class FixedWindowChunker:
    """Splits text into chunks of fixed character length with configurable overlap."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, document_id: str, base_metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        if not text.strip():
            return []

        chunks: List[DocumentChunk] = []
        step = self.chunk_size - self.chunk_overlap
        idx = 0
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                metadata = dict(base_metadata or {})
                metadata.update({"start_char": start, "end_char": end, "strategy": "fixed_window"})
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        index=idx,
                        content=chunk_text,
                        token_count=estimate_token_count(chunk_text),
                        metadata=metadata,
                    )
                )
                idx += 1
            if end >= len(text):
                break
            start += step

        return chunks


class RecursiveCharacterChunker:
    """Splits text hierarchically using natural separators (paragraphs, newlines, sentences, words)."""

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def __init__(
        self,
        chunk_size: int = 600,
        chunk_overlap: int = 120,
        separators: Optional[List[str]] = None,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS

    def chunk(self, text: str, document_id: str, base_metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        if not text.strip():
            return []

        raw_pieces = self._split_recursive(text, self.separators)
        merged_chunks = self._merge_pieces(raw_pieces)

        chunks: List[DocumentChunk] = []
        for idx, piece in enumerate(merged_chunks):
            metadata = dict(base_metadata or {})
            metadata.update({"strategy": "recursive_character", "chunk_index": idx})
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    index=idx,
                    content=piece,
                    token_count=estimate_token_count(piece),
                    metadata=metadata,
                )
            )
        return chunks

    def _split_recursive(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size or not separators:
            return [text] if text else []

        sep = separators[0]
        remaining = separators[1:]

        if sep == "":
            return list(text)

        splits = text.split(sep)
        result: List[str] = []

        for s in splits:
            if not s.strip():
                continue
            if len(s) <= self.chunk_size:
                result.append(s.strip())
            else:
                result.extend(self._split_recursive(s, remaining))

        return result

    def _merge_pieces(self, pieces: List[str]) -> List[str]:
        merged: List[str] = []
        current: List[str] = []
        current_len = 0

        for piece in pieces:
            piece_len = len(piece)
            if current and (current_len + piece_len + 1 > self.chunk_size):
                chunk_str = " ".join(current).strip()
                if chunk_str:
                    merged.append(chunk_str)

                # Keep overlap pieces from the tail
                overlap_pieces: List[str] = []
                overlap_len = 0
                for prev in reversed(current):
                    if overlap_len + len(prev) + 1 <= self.chunk_overlap:
                        overlap_pieces.insert(0, prev)
                        overlap_len += len(prev) + 1
                    else:
                        break
                current = overlap_pieces
                current_len = overlap_len

            current.append(piece)
            current_len += piece_len + 1

        if current:
            chunk_str = " ".join(current).strip()
            if chunk_str:
                merged.append(chunk_str)

        return merged


class MarkdownHeaderChunker:
    """Splits markdown content based on header levels while preserving header hierarchy context."""

    def __init__(self, max_chunk_size: int = 800):
        self.max_chunk_size = max_chunk_size
        self.header_regex = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

    def chunk(self, text: str, document_id: str, base_metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        if not text.strip():
            return []

        lines = text.splitlines()
        sections: List[Dict[str, Any]] = []
        current_headers: Dict[int, str] = {}
        current_body: List[str] = []

        for line in lines:
            header_match = self.header_regex.match(line)
            if header_match:
                # Flush previous section if any content exists
                if current_body:
                    body_text = "\n".join(current_body).strip()
                    if body_text:
                        sections.append({
                            "headers": dict(current_headers),
                            "content": body_text,
                        })
                    current_body = []

                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                # Clear deeper header levels
                current_headers = {lvl: h for lvl, h in current_headers.items() if lvl < level}
                current_headers[level] = title
            else:
                current_body.append(line)

        if current_body:
            body_text = "\n".join(current_body).strip()
            if body_text:
                sections.append({
                    "headers": dict(current_headers),
                    "content": body_text,
                })

        # Convert sections into DocumentChunks, further splitting if exceeding max_chunk_size
        chunks: List[DocumentChunk] = []
        idx = 0
        recursive_fallback = RecursiveCharacterChunker(chunk_size=self.max_chunk_size, chunk_overlap=100)

        for section in sections:
            header_trail = " > ".join(section["headers"].values()) if section["headers"] else "Overview"
            section_content = section["content"]

            if len(section_content) > self.max_chunk_size:
                sub_chunks = recursive_fallback.chunk(section_content, document_id=document_id)
                for sc in sub_chunks:
                    meta = dict(base_metadata or {})
                    meta.update({
                        "header_path": header_trail,
                        "header_levels": section["headers"],
                        "strategy": "markdown_header",
                    })
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            index=idx,
                            content=f"[{header_trail}]\n{sc.content}",
                            token_count=estimate_token_count(sc.content),
                            metadata=meta,
                        )
                    )
                    idx += 1
            else:
                meta = dict(base_metadata or {})
                meta.update({
                    "header_path": header_trail,
                    "header_levels": section["headers"],
                    "strategy": "markdown_header",
                })
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        index=idx,
                        content=f"[{header_trail}]\n{section_content}",
                        token_count=estimate_token_count(section_content),
                        metadata=meta,
                    )
                )
                idx += 1

        return chunks


class SemanticSentenceChunker:
    """Groups full sentences together respecting semantic paragraph bounds and token limits."""

    def __init__(self, target_tokens: int = 150, overlap_sentences: int = 1):
        self.target_tokens = target_tokens
        self.overlap_sentences = overlap_sentences
        self.sentence_regex = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

    def chunk(self, text: str, document_id: str, base_metadata: Optional[Dict[str, Any]] = None) -> List[DocumentChunk]:
        if not text.strip():
            return []

        # Split into paragraphs first
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[DocumentChunk] = []
        idx = 0

        for p in paragraphs:
            sentences = self.sentence_regex.split(p)
            current_group: List[str] = []
            current_tokens = 0

            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                s_tokens = estimate_token_count(sent)

                if current_group and (current_tokens + s_tokens > self.target_tokens):
                    chunk_text = " ".join(current_group).strip()
                    meta = dict(base_metadata or {})
                    meta.update({"strategy": "semantic_sentence", "sentence_count": len(current_group)})
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            index=idx,
                            content=chunk_text,
                            token_count=estimate_token_count(chunk_text),
                            metadata=meta,
                        )
                    )
                    idx += 1

                    # Overlap with last N sentences
                    overlap = current_group[-self.overlap_sentences:] if self.overlap_sentences > 0 else []
                    current_group = list(overlap)
                    current_tokens = sum(estimate_token_count(s) for s in current_group)

                current_group.append(sent)
                current_tokens += s_tokens

            if current_group:
                chunk_text = " ".join(current_group).strip()
                meta = dict(base_metadata or {})
                meta.update({"strategy": "semantic_sentence", "sentence_count": len(current_group)})
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        index=idx,
                        content=chunk_text,
                        token_count=estimate_token_count(chunk_text),
                        metadata=meta,
                    )
                )
                idx += 1

        return chunks
