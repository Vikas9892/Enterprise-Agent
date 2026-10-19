"""Document ingestion pipeline processing multi-format enterprise text sources."""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional
from app.knowledge.models import (
    ContentType,
    Document,
    DocumentChunk,
    DocumentMetadata,
    IngestionStatus,
)
from app.knowledge.chunking import (
    FixedWindowChunker,
    MarkdownHeaderChunker,
    RecursiveCharacterChunker,
    SemanticSentenceChunker,
)
from app.knowledge.vector_store import VectorStore, InMemoryVectorStore

logger = logging.getLogger("enterprise_agent.knowledge.ingestion")


class DocumentIngestionPipeline:
    """Manages document parsing, chunking, enrichment, and vector store ingestion."""

    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or InMemoryVectorStore()
        self._documents: Dict[str, Document] = {}

        # Default chunkers
        self.markdown_chunker = MarkdownHeaderChunker(max_chunk_size=700)
        self.text_chunker = RecursiveCharacterChunker(chunk_size=600, chunk_overlap=100)
        self.semantic_chunker = SemanticSentenceChunker(target_tokens=150, overlap_sentences=1)
        self.fixed_chunker = FixedWindowChunker(chunk_size=500, chunk_overlap=80)

    def ingest_text(
        self,
        title: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        metadata: Optional[DocumentMetadata] = None,
        strategy: str = "auto",
    ) -> Document:
        """Parse raw content, decompose into chunks, and store into the vector index."""
        meta = metadata or DocumentMetadata()
        doc = Document(
            title=title,
            content=content,
            content_type=content_type,
            metadata=meta,
            status=IngestionStatus.PROCESSING,
        )

        try:
            # Normalize and extract content based on type
            clean_text, extracted_meta = self._preprocess_content(content, content_type)

            # Combine metadata
            base_meta = {
                "document_id": doc.document_id,
                "title": doc.title,
                "category": meta.category,
                "tenant_id": meta.tenant_id,
                "source": meta.source,
                "content_type": content_type.value,
                **extracted_meta,
                **meta.extra,
            }

            # Select chunking strategy
            chunks = self._chunk_content(clean_text, doc.document_id, content_type, strategy, base_meta)

            doc.chunks = chunks
            doc.chunk_count = len(chunks)

            # Index into vector store
            self.vector_store.add_chunks(chunks)

            doc.status = IngestionStatus.COMPLETED
            self._documents[doc.document_id] = doc
            logger.info("Successfully ingested document %s (%d chunks)", doc.document_id, len(chunks))

        except Exception as e:
            logger.error("Failed to ingest document %s: %s", doc.document_id, str(e), exc_info=True)
            doc.status = IngestionStatus.FAILED
            doc.error_message = str(e)
            self._documents[doc.document_id] = doc

        return doc

    def _preprocess_content(self, content: str, content_type: ContentType) -> tuple[str, Dict[str, Any]]:
        """Extract structured representation and metadata from different content types."""
        extracted: Dict[str, Any] = {}

        if content_type == ContentType.JSON:
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    # List of JSON objects
                    lines = [json.dumps(item, ensure_ascii=False) for item in data]
                    return "\n".join(lines), {"format": "json_records", "record_count": len(data)}
                elif isinstance(data, dict):
                    # Flat or nested dictionary
                    lines = [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in data.items()]
                    return "\n".join(lines), {"format": "json_object", "key_count": len(data)}
            except Exception:
                pass  # Fall back to raw string

        elif content_type == ContentType.CSV:
            try:
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                if rows:
                    header = rows[0]
                    lines = []
                    for row in rows[1:]:
                        pairs = [f"{h}: {val}" for h, val in zip(header, row) if val.strip()]
                        lines.append(" | ".join(pairs))
                    return "\n".join(lines), {"format": "csv_table", "row_count": len(lines)}
            except Exception:
                pass

        return content.strip(), extracted

    def _chunk_content(
        self,
        text: str,
        document_id: str,
        content_type: ContentType,
        strategy: str,
        base_meta: Dict[str, Any],
    ) -> List[DocumentChunk]:
        """Apply the specified or auto-detected chunker."""
        if strategy == "fixed":
            return self.fixed_chunker.chunk(text, document_id, base_meta)
        elif strategy == "semantic":
            return self.semantic_chunker.chunk(text, document_id, base_meta)
        elif strategy == "recursive":
            return self.text_chunker.chunk(text, document_id, base_meta)

        # Auto detection based on content type
        if content_type == ContentType.MARKDOWN:
            return self.markdown_chunker.chunk(text, document_id, base_meta)
        else:
            return self.text_chunker.chunk(text, document_id, base_meta)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Fetch ingested document by ID."""
        return self._documents.get(document_id)

    def list_documents(self, tenant_id: Optional[str] = None) -> List[Document]:
        """List all ingested documents, optionally filtered by tenant."""
        docs = list(self._documents.values())
        if tenant_id:
            docs = [d for d in docs if d.metadata.tenant_id == tenant_id]
        return docs

    def delete_document(self, document_id: str) -> bool:
        """Remove document and its indexed chunks."""
        if document_id in self._documents:
            del self._documents[document_id]
            self.vector_store.delete_by_document(document_id)
            return True
        return False
