"""API integration tests for agent orchestrator endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password
from app.database.models import User


@pytest.fixture
def auth_headers(db_session: Session) -> dict:
    """Create test user and return Authorization headers."""
    email = "agent.api.tester@enterprise.ai"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("SecureAgentPass123!"),
            full_name="Agent API Tester",
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


def test_get_personas(client: TestClient):
    """Verify /api/v1/agent/personas returns available agent personas."""
    response = client.get("/api/v1/agent/personas")
    assert response.status_code == status.HTTP_200_OK
    personas = response.json()
    assert isinstance(personas, list)
    assert len(personas) >= 3
    ids = [p["id"] for p in personas]
    assert "coordinator" in ids
    assert "customer_support" in ids
    assert "logistics" in ids


def test_run_agent_unauthorized(client: TestClient):
    """Verify unauthenticated requests return 401."""
    payload = {"query": "Check status for customer Apex"}
    response = client.post("/api/v1/agent/run", json=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_run_agent_authorized(client: TestClient, auth_headers: dict):
    """Verify executing autonomous agent task via API."""
    payload = {
        "query": "Look up account profile for Apex Global Logistics",
        "persona": "coordinator",
    }
    response = client.post("/api/v1/agent/run", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["session_id"] is not None
    assert data["status"] == "completed"
    assert "Apex Global Logistics" in str(data["scratchpad"])
    assert data["final_answer"] is not None
    assert len(data["steps"]) >= 3


def test_stream_agent_workflow(client: TestClient, auth_headers: dict):
    """Verify /api/v1/agent/stream yields SSE transition events."""
    payload = {
        "query": "Track order ORD-2026-9001 and check warehouse status",
        "persona": "logistics",
    }
    response = client.post("/api/v1/agent/stream", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "session_started" in text
    assert "node_transition" in text
    assert "[DONE]" in text


def test_get_agent_session_detail(client: TestClient, auth_headers: dict):
    """Verify inspecting persisted agent session and step history."""
    # 1. Run agent task
    payload = {"query": "Check support ticket TCK-8801", "persona": "customer_support"}
    run_resp = client.post("/api/v1/agent/run", json=payload, headers=auth_headers)
    session_id = run_resp.json()["session_id"]

    # 2. Retrieve session details
    get_resp = client.get(f"/api/v1/agent/sessions/{session_id}", headers=auth_headers)
    assert get_resp.status_code == status.HTTP_200_OK
    data = get_resp.json()
    assert data["session_id"] == session_id
    assert data["status"] == "completed"
    assert len(data["steps"]) >= 3


def test_hitl_pause_and_resume_flow(client: TestClient, auth_headers: dict):
    """Verify end-to-end API lifecycle: pause on sensitive action -> resume on human approval."""
    # 1. Trigger sensitive action
    payload = {"query": "Request a refund of 1500 for damaged items", "persona": "coordinator"}
    run_resp = client.post("/api/v1/agent/run", json=payload, headers=auth_headers)
    assert run_resp.status_code == status.HTTP_200_OK
    init_data = run_resp.json()
    assert init_data["status"] == "waiting_for_human"
    assert init_data["requires_human_approval"] is True
    session_id = init_data["session_id"]

    # 2. Resume session with human approval
    resume_payload = {
        "approved": True,
        "feedback": "Approved refund of $1,500 after reviewing RMA documentation.",
    }
    resume_resp = client.post(
        f"/api/v1/agent/sessions/{session_id}/resume",
        json=resume_payload,
        headers=auth_headers,
    )
    assert resume_resp.status_code == status.HTTP_200_OK
    resumed_data = resume_resp.json()
    assert resumed_data["status"] == "completed"
    assert resumed_data["requires_human_approval"] is False
    assert resumed_data["final_answer"] is not None
