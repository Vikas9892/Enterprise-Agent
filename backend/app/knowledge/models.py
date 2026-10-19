"""Data models and schemas for Enterprise Knowledge Retrieval & RAG."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Supported content types for document ingestion."""
    TEXT = "text/plain"
    MARKDOWN = "text/markdown"
    JSON = "application/json"
    CSV = "text/csv"
    PDF = "application/pdf"
    CODE = "text/x-code"


class IngestionStatus(str, Enum):
    """Document processing and ingestion states."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    """Metadata attributes associated with an ingested enterprise document."""
    source: str = Field(default="direct_upload", description="Source file name, URI, or system origin")
    author: Optional[str] = Field(default=None, description="Author or system owner")
    category: str = Field(default="general", description="Department, topic, or document domain")
    tags: List[str] = Field(default_factory=list, description="Descriptive classification tags")
    tenant_id: str = Field(default="default", description="Multi-tenant isolation boundary identifier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    extra: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain-specific metadata")


class DocumentChunk(BaseModel):
    """A granular chunk of an ingested document used for indexing and vector retrieval."""
    chunk_id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:12]}")
    document_id: str = Field(description="Parent document identifier")
    index: int = Field(description="Zero-indexed sequence position within document")
    content: str = Field(description="Textual payload for this chunk")
    token_count: int = Field(default=0, description="Approximate or exact token count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Inherited and chunk-specific metadata")
    embedding: Optional[List[float]] = Field(default=None, description="Dense vector embedding")


class Document(BaseModel):
    """An ingested enterprise document entity."""
    document_id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:12]}")
    title: str = Field(description="Human-readable title or file name")
    content: str = Field(description="Raw original document content")
    content_type: ContentType = Field(default=ContentType.TEXT)
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    status: IngestionStatus = Field(default=IngestionStatus.PENDING)
    chunks: List[DocumentChunk] = Field(default_factory=list)
    chunk_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class SearchResult(BaseModel):
    """Retrieved document chunk with relevance scoring and attribution metadata."""
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float = Field(description="Normalized relevance score between 0.0 and 1.0")
    match_type: str = Field(default="vector", description="Match algorithm: vector, bm25, or hybrid")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    citation: Optional[str] = Field(default=None, description="Formatted citation reference")


class SearchQuery(BaseModel):
    """Query parameters for knowledge retrieval."""
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="0.0 = BM25 only, 1.0 = Vector only, 0.5 = Balanced hybrid")
    tenant_id: Optional[str] = Field(default=None, description="Filter results by tenant")
    category: Optional[str] = Field(default=None, description="Filter results by category")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance threshold")
