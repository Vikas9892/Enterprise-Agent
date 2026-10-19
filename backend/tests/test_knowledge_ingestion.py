"""Unit and integration tests for document ingestion, chunking, and vector store."""

import pytest
from app.knowledge.models import ContentType, DocumentMetadata
from app.knowledge.chunking import (
    FixedWindowChunker,
    RecursiveCharacterChunker,
    MarkdownHeaderChunker,
    SemanticSentenceChunker,
    estimate_token_count,
)
from app.knowledge.vector_store import (
    FastSemanticEmbedder,
    InMemoryVectorStore,
    cosine_similarity,
)
from app.knowledge.ingestion import DocumentIngestionPipeline


def test_estimate_token_count():
    assert estimate_token_count("") == 0
    text = "Enterprise Agentic AI Platform"
    count = estimate_token_count(text)
    assert count >= 4


def test_fixed_window_chunker():
    chunker = FixedWindowChunker(chunk_size=50, chunk_overlap=10)
    text = "The enterprise agent processes complex asynchronous tasks with high reliability and zero downtime."
    chunks = chunker.chunk(text, document_id="doc_1")
    assert len(chunks) > 1
    for c in chunks:
        assert c.document_id == "doc_1"
        assert len(c.content) <= 50
        assert c.metadata["strategy"] == "fixed_window"


def test_recursive_character_chunker():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    text = (
        "First section introduces the supervisor agent.\n\n"
        "Second section details specialist agents including support, logistics, and compliance.\n\n"
        "Third section explains the consensus mechanism and shared blackboard memory."
    )
    chunks = chunker.chunk(text, document_id="doc_2")
    assert len(chunks) >= 2
    for c in chunks:
        assert c.document_id == "doc_2"
        assert c.token_count > 0


def test_markdown_header_chunker():
    chunker = MarkdownHeaderChunker(max_chunk_size=300)
    md = (
        "# Enterprise Architecture\n\n"
        "Overview of the core microservices and gateway.\n\n"
        "## Agent Orchestrator\n\n"
        "State graph engine with cyclical reflection loops and human-in-the-loop validation.\n\n"
        "### Tool Registry\n\n"
        "Dynamic tool execution and sandboxing."
    )
    chunks = chunker.chunk(md, document_id="doc_md")
    assert len(chunks) >= 2
    assert any("Enterprise Architecture" in c.content for c in chunks)
    assert any("Agent Orchestrator" in c.content for c in chunks)


def test_semantic_sentence_chunker():
    chunker = SemanticSentenceChunker(target_tokens=20, overlap_sentences=1)
    text = (
        "Enterprise workflows require compliance checking. Every transaction over $10,000 must be audited. "
        "Logistics agents verify shipping schedules. Support agents manage customer tickets efficiently."
    )
    chunks = chunker.chunk(text, document_id="doc_sent")
    assert len(chunks) >= 1
    assert chunks[0].metadata["strategy"] == "semantic_sentence"


def test_fast_semantic_embedder():
    embedder = FastSemanticEmbedder(dimensions=128)
    vec1 = embedder.embed_text("enterprise customer support refund policy")
    vec2 = embedder.embed_text("customer refund guidelines and support tickets")
    vec3 = embedder.embed_text("quantum physics astrophysical astrophysics equations")

    assert len(vec1) == 128
    sim_related = cosine_similarity(vec1, vec2)
    sim_unrelated = cosine_similarity(vec1, vec3)

    assert sim_related > sim_unrelated


def test_in_memory_vector_store():
    store = InMemoryVectorStore()
    pipeline = DocumentIngestionPipeline(vector_store=store)

    doc = pipeline.ingest_text(
        title="GDPR Compliance Guide",
        content="Personal identifiable information (PII) must be encrypted and redacted before storing.",
        content_type=ContentType.TEXT,
        metadata=DocumentMetadata(category="compliance", tenant_id="tenant_a"),
    )

    assert doc.status == "completed"
    assert doc.chunk_count > 0

    # Search with matching query
    results = store.search(query="PII encryption and privacy redaction", top_k=2)
    assert len(results) > 0
    assert results[0].document_id == doc.document_id
    assert results[0].score > 0.0

    # Search with filter
    filtered_results = store.search(
        query="privacy",
        filters={"tenant_id": "tenant_b"},
    )
    assert len(filtered_results) == 0

    # Delete
    deleted = store.delete_by_document(doc.document_id)
    assert deleted > 0
    assert store.count() == 0


def test_ingestion_pipeline_csv_and_json():
    pipeline = DocumentIngestionPipeline()

    # Ingest JSON
    json_data = '[{"product": "Server Blade", "price": 1200}, {"product": "Rack Switch", "price": 450}]'
    doc_json = pipeline.ingest_text(
        title="Hardware Catalog",
        content=json_data,
        content_type=ContentType.JSON,
    )
    assert doc_json.status == "completed"
    assert doc_json.chunk_count > 0

    # Ingest CSV
    csv_data = "id,name,role\n1,Alice,Admin\n2,Bob,Operator\n"
    doc_csv = pipeline.ingest_text(
        title="Personnel Roster",
        content=csv_data,
        content_type=ContentType.CSV,
    )
    assert doc_csv.status == "completed"
    assert doc_csv.chunk_count > 0
