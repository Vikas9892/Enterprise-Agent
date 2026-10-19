"""Tests for Knowledge Base API endpoints and builtin tool integration."""

import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.tools.builtin_tools import search_knowledge_base
from app.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_knowledge_ingest_and_query_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest document
        ingest_payload = {
            "title": "Data Retention & Encryption Standards",
            "content": (
                "# Encryption and Backup Procedures\n\n"
                "All customer telemetry databases must be encrypted at rest with AES-256 keys. "
                "Disaster recovery backups are executed every 6 hours and stored in multi-region cold vaults."
            ),
            "content_type": "text/markdown",
            "category": "compliance",
            "tenant_id": "tenant_enterprise",
            "source": "api_test",
        }
        res_ingest = await client.post("/api/v1/knowledge/ingest", json=ingest_payload)
        assert res_ingest.status_code == 201
        data = res_ingest.json()
        assert data["title"] == "Data Retention & Encryption Standards"
        assert data["chunk_count"] > 0
        doc_id = data["document_id"]

        # 2. Query document
        query_payload = {
            "query": "AES-256 encryption keys and backup recovery",
            "top_k": 2,
            "alpha": 0.5,
            "category": "compliance",
        }
        res_query = await client.post("/api/v1/knowledge/query", json=query_payload)
        assert res_query.status_code == 200
        qdata = res_query.json()
        assert qdata["count"] > 0
        assert len(qdata["citations"]) > 0
        assert "AES-256" in qdata["grounded_context"]

        # 3. Retrieve document by ID
        res_doc = await client.get(f"/api/v1/knowledge/documents/{doc_id}")
        assert res_doc.status_code == 200
        assert res_doc.json()["document_id"] == doc_id

        # 4. List documents
        res_list = await client.get("/api/v1/knowledge/documents")
        assert res_list.status_code == 200
        assert len(res_list.json()) >= 1

        # 5. Stats endpoint
        res_stats = await client.get("/api/v1/knowledge/stats")
        assert res_stats.status_code == 200
        sdata = res_stats.json()
        assert sdata["total_documents"] >= 1
        assert sdata["total_chunks"] >= 1

        # 6. Delete document
        res_del = await client.delete(f"/api/v1/knowledge/documents/{doc_id}")
        assert res_del.status_code == 200


def test_builtin_tool_search_knowledge_base():
    # Call directly
    tool_res = search_knowledge_base(query="customer refund policy damaged shipment", top_k=2)
    assert tool_res["count"] > 0
    assert len(tool_res["citations"]) > 0
    assert "Refund" in tool_res["context"]

    # Verify registration in ToolRegistry
    registry = ToolRegistry(register_defaults=True)
    tool = registry.get_tool("search_knowledge_base")
    assert tool is not None
    assert tool.source == "local"
    assert "query" in tool.parameters["properties"]
