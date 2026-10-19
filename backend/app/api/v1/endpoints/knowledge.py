"""API v1 endpoints for Enterprise Knowledge Retrieval & RAG."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.knowledge.models import (
    ContentType,
    Document,
    DocumentMetadata,
    SearchQuery,
)
from app.knowledge.service import knowledge_service

router = APIRouter()


class IngestRequest(BaseModel):
    title: str = Field(..., description="Document title or file identifier")
    content: str = Field(..., description="Raw text, markdown, CSV, or JSON document content")
    content_type: ContentType = Field(default=ContentType.TEXT, description="Content format type")
    category: str = Field(default="general", description="Department or knowledge classification")
    tenant_id: str = Field(default="default", description="Tenant workspace identifier")
    source: str = Field(default="manual_upload", description="Source or origin file")
    author: Optional[str] = Field(default=None, description="Author or system origin")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata key-values")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Search query or question")
    top_k: int = Field(default=4, ge=1, le=50, description="Max passages to retrieve")
    alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="0=BM25, 1=Vector, 0.5=Hybrid")
    category: Optional[str] = Field(default=None, description="Filter by category")
    tenant_id: Optional[str] = Field(default=None, description="Filter by tenant")
    use_mmr: bool = Field(default=True, description="Enable Maximal Marginal Relevance diversity")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum relevance score cutoff")


@router.post(
    "/ingest",
    response_model=Document,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and index a document into knowledge base",
)
async def ingest_document(req: IngestRequest) -> Document:
    meta = DocumentMetadata(
        source=req.source,
        author=req.author,
        category=req.category,
        tenant_id=req.tenant_id,
        extra=req.extra,
    )
    doc = knowledge_service.ingest_document(
        title=req.title,
        content=req.content,
        content_type=req.content_type,
        metadata=meta,
    )
    if doc.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to ingest document: {doc.error_message}",
        )
    return doc


@router.post(
    "/query",
    summary="Execute hybrid search and grounding retrieval",
)
async def query_knowledge(req: QueryRequest) -> Dict[str, Any]:
    return knowledge_service.query(
        query=req.query,
        top_k=req.top_k,
        alpha=req.alpha,
        category=req.category,
        tenant_id=req.tenant_id,
        use_mmr=req.use_mmr,
        min_score=req.min_score,
    )


@router.get(
    "/documents",
    response_model=List[Document],
    summary="List all indexed knowledge documents",
)
async def list_documents(tenant_id: Optional[str] = Query(None, description="Filter by tenant ID")) -> List[Document]:
    return knowledge_service.list_documents(tenant_id=tenant_id)


@router.get(
    "/documents/{document_id}",
    response_model=Document,
    summary="Retrieve an ingested document by ID",
)
async def get_document(document_id: str) -> Document:
    doc = knowledge_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an ingested document and its indexed chunks",
)
async def delete_document(document_id: str) -> Dict[str, Any]:
    deleted = knowledge_service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return {"message": "Document successfully deleted", "document_id": document_id}


@router.get(
    "/stats",
    summary="Retrieve knowledge base corpus statistics",
)
async def get_stats() -> Dict[str, Any]:
    return knowledge_service.get_stats()
