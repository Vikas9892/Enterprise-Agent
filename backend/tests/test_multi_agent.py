"""Unit and integration tests for multi-agent swarm collaboration and supervisor orchestration."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agent.multi_agent import ENTERPRISE_SWARM_AGENTS, MultiAgentSwarm
from app.auth.security import create_access_token, hash_password
from app.database.models import User


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Create test user and return Authorization headers."""
    email = "swarm.tester@enterprise.ai"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("SwarmPass123!"),
            full_name="Swarm Tester",
            department="Operations",
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"email": user.email, "roles": ["Operator"], "permissions": []},
    )
    return {"Authorization": f"Bearer {token}"}


def test_swarm_agent_catalog():
    """Verify specialist agent definitions and domain coverage."""
    assert "support_agent" in ENTERPRISE_SWARM_AGENTS
    assert "logistics_agent" in ENTERPRISE_SWARM_AGENTS
    assert "compliance_agent" in ENTERPRISE_SWARM_AGENTS

    support = ENTERPRISE_SWARM_AGENTS["support_agent"]
    assert "customer_lookup" in support.capabilities
    assert support.persona_id == "customer_support"


def test_query_decomposition():
    """Verify supervisor accurately decomposes multi-domain query into specialist subtasks."""
    swarm = MultiAgentSwarm()
    query = (
        "Customer Apex Global requests freight tracking for order ORD-2026-9001 "
        "and a refund evaluation for damaged components."
    )
    assignments = swarm.decompose_query(query)
    assert len(assignments) == 3

    assigned_agents = [a.assigned_agent for a in assignments]
    assert "support_agent" in assigned_agents
    assert "logistics_agent" in assigned_agents
    assert "compliance_agent" in assigned_agents


@pytest.mark.asyncio
async def test_swarm_collaborative_execution():
    """Verify end-to-end multi-agent swarm execution, blackboard aggregation, and synthesis."""
    swarm = MultiAgentSwarm()
    query = "Look up customer Apex Global Logistics and check inventory stock for SKU-SRV-01"

    state = await swarm.execute_swarm(query)
    assert state.status == "completed"
    assert state.swarm_id.startswith("swarm-")
    assert len(state.assignments) >= 2

    # Verify findings are deposited in shared blackboard
    assert "support_agent" in state.blackboard or "logistics_agent" in state.blackboard
    assert len(state.consensus_notes) >= 1
    assert state.final_synthesis is not None
    assert len(state.delegation_trace) >= 2


@pytest.mark.asyncio
async def test_swarm_hitl_escalation():
    """Verify swarm halts when a specialist encounters a sensitive action requiring human approval."""
    swarm = MultiAgentSwarm()
    query = "Request a refund of 1500 for customer order ORD-2026-9001"

    state = await swarm.execute_swarm(query)
    assert state.requires_human_approval is True
    assert state.status == "waiting_for_human"
    assert state.pending_approval_action is not None


def test_swarm_api_endpoints(client: TestClient, auth_headers: dict):
    """Verify /api/v1/swarm/agents, /run, and /stream REST/SSE endpoints."""
    # 1. List specialist agents
    agents_resp = client.get("/api/v1/swarm/agents")
    assert agents_resp.status_code == status.HTTP_200_OK
    agents = agents_resp.json()
    assert isinstance(agents, list)
    assert len(agents) >= 3
    ids = [a["id"] for a in agents]
    assert "support_agent" in ids
    assert "logistics_agent" in ids
    assert "compliance_agent" in ids

    # 2. Run swarm task unauthorized
    unauth_resp = client.post("/api/v1/swarm/run", json={"query": "Triage inquiry"})
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Run swarm task authorized
    run_resp = client.post(
        "/api/v1/swarm/run",
        json={"query": "Inspect customer Apex Global Logistics profile and order tracking ORD-2026-9001"},
        headers=auth_headers,
    )
    assert run_resp.status_code == status.HTTP_200_OK
    data = run_resp.json()
    assert data["swarm_id"] is not None
    assert "assignments" in data
    assert len(data["assignments"]) >= 2
    assert "blackboard" in data
    assert data["final_synthesis"] is not None

    # 4. Stream swarm task
    stream_resp = client.post(
        "/api/v1/swarm/stream",
        json={"query": "Verify shipment for order ORD-2026-9001"},
        headers=auth_headers,
    )
    assert stream_resp.status_code == status.HTTP_200_OK
    assert "text/event-stream" in stream_resp.headers["content-type"]
    text = stream_resp.text
    assert "swarm_started" in text
    assert "supervisor_planned" in text
    assert "subtask_completed" in text
    assert "[DONE]" in text
