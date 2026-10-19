"""Centralized enterprise knowledge service managing ingestion, indexing, and hybrid search."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.knowledge.models import (
    ContentType,
    Document,
    DocumentMetadata,
    SearchResult,
)
from app.knowledge.ingestion import DocumentIngestionPipeline
from app.knowledge.hybrid_search import HybridSearchEngine
from app.knowledge.reranker import ContextReranker
from app.knowledge.grounding import GroundingGuardrail

logger = logging.getLogger("enterprise_agent.knowledge.service")


class KnowledgeService:
    """Enterprise Knowledge Service singleton orchestrator."""

    def __init__(self):
        self.hybrid_engine = HybridSearchEngine()
        self.pipeline = DocumentIngestionPipeline(vector_store=self.hybrid_engine.vector_store)
        self.reranker = ContextReranker()
        self.guardrail = GroundingGuardrail()
        self._seed_default_documents()

    def _seed_default_documents(self) -> None:
        """Seed the knowledge base with canonical enterprise policies and guides."""
        seed_docs = [
            {
                "title": "Enterprise Refund & Return Policy",
                "category": "finance",
                "content_type": ContentType.MARKDOWN,
                "content": (
                    "# Enterprise Customer Refund & Return Policy\n\n"
                    "## 1. General Provisions\n"
                    "Enterprise customers in Gold and Platinum tiers are entitled to full refund processing within 30 days "
                    "of product receipt. Returns initiated due to freight damage or hardware defect qualify for 100% credit "
                    "including expedited return logistics paid by the platform.\n\n"
                    "## 2. Approval Limits and Thresholds\n"
                    "- Refunds under $1,000.00: Automatically approved by Autonomous Support Agents without human intervention.\n"
                    "- Refunds between $1,000.00 and $10,000.00: Require Human-In-The-Loop (HITL) approval from Logistics or Support Lead.\n"
                    "- Refunds exceeding $10,000.00: Must be escalated to the Finance Director and accompanied by carrier inspection photos."
                ),
            },
            {
                "title": "Global Shipping and Logistics SLA",
                "category": "logistics",
                "content_type": ContentType.MARKDOWN,
                "content": (
                    "# Global Freight Shipping SLA & Tracking\n\n"
                    "## 1. Delivery Schedules\n"
                    "- Priority Air Freight: Delivered within 24 to 48 hours for North American hubs.\n"
                    "- Standard Ground Transport: Delivered within 3 to 5 business days.\n"
                    "- Expedited Ocean Freight: 14 to 21 calendar days with customs clearance.\n\n"
                    "## 2. Transit Tracking and Incident Management\n"
                    "All shipments contain RFID sensor telemetry. If temperature or shock sensors trip, carriers are mandated "
                    "to issue an automated incident report within 2 hours. Replacement units are dispatched immediately from regional hubs."
                ),
            },
            {
                "title": "Enterprise GDPR and Data Governance",
                "category": "compliance",
                "content_type": ContentType.MARKDOWN,
                "content": (
                    "# Enterprise GDPR & Compliance Standards\n\n"
                    "## 1. PII Redaction Policy\n"
                    "All agent conversations, external tool payloads, and logging outputs must sanitize Personally Identifiable "
                    "Information (PII). Specifically: Credit card numbers, Social Security Numbers (SSN), taxpayer identification, "
                    "and employee personal contact numbers must be redacted into [REDACTED] tokens before persistence.\n\n"
                    "## 2. Retention Mandate\n"
                    "Chat trajectories and telemetry metrics are retained for 90 days in compliance with ISO/IEC 27001 audit standards."
                ),
            },
        ]

        for s in seed_docs:
            doc = self.pipeline.ingest_text(
                title=s["title"],
                content=s["content"],
                content_type=s["content_type"],
                metadata=DocumentMetadata(
                    category=s["category"],
                    source="enterprise_seed",
                    author="Enterprise Compliance Board",
                ),
            )
            # Ensure chunks are also indexed in BM25
            self.hybrid_engine.bm25_index.add_chunks(doc.chunks)
            logger.info("Seeded document %s (%s)", doc.title, doc.document_id)

    def query(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        category: Optional[str] = None,
        tenant_id: Optional[str] = None,
        use_mmr: bool = True,
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Execute hybrid search with re-ranking and grounding context generation."""
        filters = {}
        if category:
            filters["category"] = category
        if tenant_id:
            filters["tenant_id"] = tenant_id

        # Retrieve candidates
        candidates = self.hybrid_engine.search(
            query=query,
            top_k=top_k * 2 if use_mmr else top_k,
            alpha=alpha,
            filters=filters or None,
            min_score=min_score,
        )

        # Apply header boost and MMR diversity
        boosted = self.reranker.boost_headers(query, candidates)
        if use_mmr and len(boosted) > top_k:
            final_results = self.reranker.rerank_mmr(query, boosted, top_k=top_k)
        else:
            final_results = boosted[:top_k]

        grounded_context = self.guardrail.format_grounded_context(final_results)

        return {
            "query": query,
            "count": len(final_results),
            "results": [r.model_dump() for r in final_results],
            "grounded_context": grounded_context,
            "citations": [
                {
                    "index": idx + 1,
                    "title": r.title,
                    "document_id": r.document_id,
                    "chunk_id": r.chunk_id,
                    "score": r.score,
                    "match_type": r.match_type,
                }
                for idx, r in enumerate(final_results)
            ],
        }

    def ingest_document(
        self,
        title: str,
        content: str,
        content_type: ContentType = ContentType.TEXT,
        metadata: Optional[DocumentMetadata] = None,
    ) -> Document:
        """Ingest document, chunk it, and index into both vector and BM25 stores."""
        doc = self.pipeline.ingest_text(
            title=title,
            content=content,
            content_type=content_type,
            metadata=metadata,
        )
        if doc.status == "completed":
            self.hybrid_engine.bm25_index.add_chunks(doc.chunks)
        return doc

    def list_documents(self, tenant_id: Optional[str] = None) -> List[Document]:
        return self.pipeline.list_documents(tenant_id=tenant_id)

    def get_document(self, document_id: str) -> Optional[Document]:
        return self.pipeline.get_document(document_id)

    def delete_document(self, document_id: str) -> bool:
        doc = self.pipeline.get_document(document_id)
        if doc:
            self.pipeline.delete_document(document_id)
            self.hybrid_engine.delete_by_document(document_id)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        docs = self.pipeline.list_documents()
        total_chunks = sum(d.chunk_count for d in docs)
        categories = {}
        for d in docs:
            cat = d.metadata.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_documents": len(docs),
            "total_chunks": total_chunks,
            "categories": categories,
            "vector_store_count": self.hybrid_engine.vector_store.count(),
            "bm25_index_count": self.hybrid_engine.bm25_index.count(),
        }


# Global singleton instance
knowledge_service = KnowledgeService()
