"""Unit and integration tests for Agent Orchestrator, personas, and HITL flows."""

import pytest
from sqlalchemy.orm import Session

from app.agent import AgentOrchestrator, AgentStatus
from app.database.models import User
from app.database.repositories.agent_session import AgentSessionRepository


@pytest.fixture
def orchestrator() -> AgentOrchestrator:
    """Fixture providing AgentOrchestrator."""
    return AgentOrchestrator()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Fixture providing a test user."""
    user = db_session.query(User).filter(User.email == "orchestrator.test@enterprise.ai").first()
    if not user:
        user = User(
            email="orchestrator.test@enterprise.ai",
            hashed_password="hashed_placeholder",
            full_name="Agent Tester",
            department="Operations",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_coordinator_workflow_customer_inquiry(orchestrator: AgentOrchestrator, db_session: Session, test_user: User):
    """Verify coordinator fulfills customer lookup and gathers facts into scratchpad."""
    state = await orchestrator.run_workflow(
        query="Please look up customer profile for Apex Global Logistics",
        user_id=test_user.id,
        persona_id="coordinator",
        db=db_session,
    )

    assert state.status == AgentStatus.COMPLETED
    assert "get_customer" in state.scratchpad
    cust_data = state.scratchpad["get_customer"]
    assert "Apex Global Logistics" in str(cust_data)
    assert state.final_answer is not None
    assert len(state.trace) >= 3

    # Verify DB persistence
    repo = AgentSessionRepository(db_session)
    saved = repo.get_by_id(state.session_id)
    assert saved is not None
    assert saved.status == "completed"
    assert len(saved.steps) >= 3


@pytest.mark.asyncio
async def test_logistics_workflow_order_and_inventory(orchestrator: AgentOrchestrator, db_session: Session, test_user: User):
    """Verify logistics persona executes order details and inventory stock checks."""
    state = await orchestrator.run_workflow(
        query="Verify shipment and inventory for order ORD-2026-9001 with SKU-SRV-01",
        user_id=test_user.id,
        persona_id="logistics",
        db=db_session,
    )

    assert state.status == AgentStatus.COMPLETED
    assert "get_order_details" in state.scratchpad or "check_inventory" in state.scratchpad
    assert state.final_answer is not None


@pytest.mark.asyncio
async def test_support_workflow_ticket_triage(orchestrator: AgentOrchestrator, db_session: Session, test_user: User):
    """Verify customer support persona inspects ticket details."""
    state = await orchestrator.run_workflow(
        query="Triage support ticket TCK-8801 for customer issue",
        user_id=test_user.id,
        persona_id="customer_support",
        db=db_session,
    )

    assert state.status == AgentStatus.COMPLETED
    assert "get_support_ticket" in state.scratchpad
    ticket_data = state.scratchpad["get_support_ticket"]
    assert "TCK-8801" in str(ticket_data) or "David Chen" in str(ticket_data)


@pytest.mark.asyncio
async def test_human_in_the_loop_pause_and_approval(orchestrator: AgentOrchestrator, db_session: Session, test_user: User):
    """Verify policy violation pauses workflow for HITL approval and resumes on approval."""
    # 1. Trigger workflow that triggers policy verification requiring approval
    paused_state = await orchestrator.run_workflow(
        query="Request a large refund of 1500 for damaged shipment",
        user_id=test_user.id,
        persona_id="coordinator",
        db=db_session,
    )

    assert paused_state.status == AgentStatus.WAITING_FOR_HUMAN
    assert paused_state.requires_human_approval is True

    # 2. Resume with approval
    resumed_state = await orchestrator.resume_workflow(
        session_id=paused_state.session_id,
        approved=True,
        feedback="Verified damaged goods report. Approved.",
        db=db_session,
    )

    assert resumed_state.status == AgentStatus.COMPLETED
    assert resumed_state.requires_human_approval is False
    assert resumed_state.human_approved is True
    assert resumed_state.final_answer is not None


@pytest.mark.asyncio
async def test_human_in_the_loop_rejection(orchestrator: AgentOrchestrator, db_session: Session, test_user: User):
    """Verify workflow records rejection when human supervisor denies action."""
    paused_state = await orchestrator.run_workflow(
        query="Execute cancel order request for customer account",
        user_id=test_user.id,
        persona_id="coordinator",
        db=db_session,
    )

    assert paused_state.status == AgentStatus.WAITING_FOR_HUMAN

    rejected_state = await orchestrator.resume_workflow(
        session_id=paused_state.session_id,
        approved=False,
        feedback="Order has already been loaded onto carrier freight.",
        db=db_session,
    )

    assert rejected_state.status == AgentStatus.COMPLETED
    assert rejected_state.human_approved is False
    assert "rejected" in rejected_state.final_answer.lower()
