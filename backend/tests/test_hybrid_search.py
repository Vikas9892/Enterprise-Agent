"""Unit and integration tests for BM25, Hybrid Search (RRF), Context Reranker, and Grounding Guardrails."""

import pytest
from app.knowledge.models import DocumentChunk
from app.knowledge.bm25 import BM25Index, tokenize
from app.knowledge.hybrid_search import HybridSearchEngine
from app.knowledge.vector_store import InMemoryVectorStore
from app.knowledge.reranker import ContextReranker
from app.knowledge.grounding import GroundingGuardrail


def test_bm25_tokenization():
    tokens = tokenize("Enterprise Agentic AI with PostgreSQL and Redis!")
    assert "enterprise" in tokens
    assert "postgresql" in tokens
    assert "redis" in tokens
    assert "with" not in tokens  # Stop word removed
    assert "and" not in tokens  # Stop word removed


def test_bm25_indexing_and_search():
    index = BM25Index()

    chunks = [
        DocumentChunk(
            document_id="doc_policy",
            index=0,
            content="Enterprise refund policy states that items damaged during transit are eligible for 100% refund.",
            metadata={"category": "finance", "title": "Refund Policy"},
        ),
        DocumentChunk(
            document_id="doc_shipping",
            index=0,
            content="Standard delivery takes 3 to 5 business days using priority carrier trucks.",
            metadata={"category": "logistics", "title": "Shipping SLA"},
        ),
        DocumentChunk(
            document_id="doc_security",
            index=0,
            content="OAuth2 JWT tokens expire after 60 minutes and require HTTPS encryption.",
            metadata={"category": "security", "title": "Security Protocols"},
        ),
    ]

    index.add_chunks(chunks)
    assert index.count() == 3

    # Exact keyword search
    results = index.search(query="damaged transit refund policy", top_k=2)
    assert len(results) > 0
    assert results[0].document_id == "doc_policy"
    assert results[0].match_type == "bm25"
    assert results[0].score > 0.0

    # Test metadata filter
    filtered = index.search(query="policy", filters={"category": "security"})
    assert len(filtered) == 0

    # Delete
    deleted = index.delete_by_document("doc_policy")
    assert deleted == 1
    assert index.count() == 2


def test_hybrid_search_reciprocal_rank_fusion():
    vstore = InMemoryVectorStore()
    bm25 = BM25Index()
    engine = HybridSearchEngine(vector_store=vstore, bm25_index=bm25, rrf_constant=60)

    chunks = [
        DocumentChunk(
            document_id="doc_k8s",
            index=0,
            content="Kubernetes manifests configure HorizontalPodAutoscaler with CPU threshold of 75 percent.",
            metadata={"title": "K8s Deployment", "tenant_id": "tenant_1"},
        ),
        DocumentChunk(
            document_id="doc_fastapi",
            index=0,
            content="FastAPI gateway provides asynchronous REST and Server-Sent Events SSE streaming endpoints.",
            metadata={"title": "FastAPI Architecture", "tenant_id": "tenant_1"},
        ),
        DocumentChunk(
            document_id="doc_db",
            index=0,
            content="PostgreSQL relational database handles transactions with ACID isolation and foreign keys.",
            metadata={"title": "Database Setup", "tenant_id": "tenant_2"},
        ),
    ]

    engine.add_chunks(chunks)
    assert engine.count() == 3

    # Hybrid search (alpha = 0.5)
    results = engine.search(query="Kubernetes HorizontalPodAutoscaler CPU scaling", top_k=2, alpha=0.5)
    assert len(results) > 0
    assert results[0].document_id == "doc_k8s"
    assert results[0].score > 0.0

    # Pure vector mode (alpha = 1.0)
    vec_results = engine.search(query="streaming SSE endpoints", top_k=1, alpha=1.0)
    assert len(vec_results) == 1
    assert vec_results[0].match_type == "vector"

    # Pure BM25 mode (alpha = 0.0)
    bm25_results = engine.search(query="PostgreSQL ACID transactions", top_k=1, alpha=0.0)
    assert len(bm25_results) == 1
    assert bm25_results[0].match_type == "bm25"


def test_context_reranker_mmr_and_header_boost():
    reranker = ContextReranker()
    engine = HybridSearchEngine()

    chunks = [
        DocumentChunk(
            document_id="doc_1",
            index=0,
            content="Enterprise pricing tier includes unlimited API tokens and dedicated support line.",
            metadata={"title": "Pricing Plans", "header_path": "Enterprise > Pricing"},
        ),
        DocumentChunk(
            document_id="doc_1",
            index=1,
            content="Enterprise pricing tier includes unlimited API tokens and 24/7 dedicated phone line.",
            metadata={"title": "Pricing Plans", "header_path": "Enterprise > Support"},
        ),
        DocumentChunk(
            document_id="doc_2",
            index=0,
            content="Community tier provides basic open source features and community forum help.",
            metadata={"title": "Community Edition", "header_path": "Community > Free"},
        ),
    ]

    engine.add_chunks(chunks)
    candidates = engine.search(query="enterprise pricing support tier", top_k=3, alpha=0.5)

    # MMR should diversify candidates
    diversified = reranker.rerank_mmr(
        query="enterprise pricing tier",
        candidates=candidates,
        top_k=2,
        lambda_param=0.5,
    )
    assert len(diversified) == 2

    # Header boost
    boosted = reranker.boost_headers(query="Enterprise Pricing", results=candidates)
    assert boosted[0].score >= candidates[0].score


def test_grounding_guardrail_citations_and_hallucination():
    guardrail = GroundingGuardrail(min_grounding_threshold=0.3)
    engine = HybridSearchEngine()

    chunks = [
        DocumentChunk(
            document_id="doc_warranty",
            index=0,
            content="Enterprise hardware servers have a 36-month warranty covering replacement parts and on-site repair.",
            metadata={"title": "Server Hardware Warranty"},
        )
    ]
    engine.add_chunks(chunks)
    search_results = engine.search(query="hardware warranty duration", top_k=1)

    # 1. Format grounded context
    formatted = guardrail.format_grounded_context(search_results)
    assert "Server Hardware Warranty" in formatted
    assert "36-month warranty" in formatted

    # 2. Grounded answer check
    grounded_answer = "The hardware servers come with a 36-month warranty covering replacement parts."
    grounding_eval = guardrail.verify_grounding(grounded_answer, search_results)
    assert grounding_eval["is_grounded"] is True
    assert grounding_eval["confidence_score"] >= 0.3
    assert len(grounding_eval["citations"]) == 1

    # 3. Hallucination check
    hallucinated_answer = "The quantum teleportation gateway requires antimatter batteries and kryptonite fuel."
    hallucination_eval = guardrail.verify_grounding(hallucinated_answer, search_results)
    assert hallucination_eval["is_grounded"] is False
    assert hallucination_eval["confidence_score"] < 0.2
    assert "warning" in hallucination_eval
