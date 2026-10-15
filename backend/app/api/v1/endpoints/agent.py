"""API endpoints for autonomous agent execution, streaming, checkpoints, and personas."""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.dependencies import get_agent_orchestrator
from app.agent.orchestrator import AgentOrchestrator
from app.agent.personas import PersonaConfig, list_all_personas
from app.agent.state import AgentState
from app.auth.dependencies import get_current_user
from app.database.models.user import User
from app.database.repositories.agent_session import AgentSessionRepository
from app.database.session import get_db

router = APIRouter()


class AgentRunRequest(BaseModel):
    """Payload to launch an autonomous agent task."""

    query: str = Field(..., min_length=2, description="Instruction or operational inquiry for the agent")
    persona: str = Field(default="coordinator", description="Agent persona ('coordinator', 'customer_support', 'logistics')")
    session_id: Optional[str] = Field(default=None, description="Optional custom session identifier")


class AgentResumeRequest(BaseModel):
    """Payload to approve or reject a human-in-the-loop checkpoint."""

    approved: bool = Field(..., description="Whether to approve or reject the pending action")
    feedback: Optional[str] = Field(default=None, description="Optional guidance or steering feedback for the agent")


class AgentStepResponse(BaseModel):
    """Trace details of a single execution step."""

    step_number: int
    node_name: str
    action: Optional[str] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    latency_ms: float = 0.0


class AgentSessionResponse(BaseModel):
    """Snapshot of agent execution session state."""

    session_id: str
    persona: str
    status: str
    input_query: str
    final_answer: Optional[str] = None
    iterations: int = 0
    requires_human_approval: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    plan: List[str] = Field(default_factory=list)
    scratchpad: Dict[str, Any] = Field(default_factory=dict)
    steps: List[AgentStepResponse] = Field(default_factory=list)


@router.post(
    "/run",
    response_model=AgentSessionResponse,
    summary="Execute Agent Task",
    description="Run state-machine agent with cyclical reflection, automated tool calling, and HITL checkpoints.",
)
async def run_agent(
    request: AgentRunRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    """Execute autonomous agent workflow."""
    final_state: AgentState = await orchestrator.run_workflow(
        query=request.query,
        session_id=request.session_id,
        user_id=current_user.id,
        persona_id=request.persona,
        db=db,
    )

    steps = [
        AgentStepResponse(
            step_number=t.step_number,
            node_name=t.node_name,
            action=t.action,
            observation=t.observation,
            reflection=t.reflection,
            latency_ms=t.latency_ms,
        )
        for t in final_state.trace
    ]

    return AgentSessionResponse(
        session_id=final_state.session_id,
        persona=final_state.persona,
        status=final_state.status.value,
        input_query=final_state.input_query,
        final_answer=final_state.final_answer,
        iterations=final_state.iterations,
        requires_human_approval=final_state.requires_human_approval,
        pending_action=final_state.pending_action,
        plan=final_state.plan,
        scratchpad=final_state.scratchpad,
        steps=steps,
    )


@router.post(
    "/stream",
    summary="Stream Agent Workflow",
    description="Stream real-time state machine node transitions, tool calls, and completion via SSE.",
)
async def stream_agent(
    request: AgentRunRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream agent execution events over Server-Sent Events (SSE)."""

    async def event_generator():
        try:
            async for event in orchestrator.stream_workflow(
                query=request.query,
                session_id=request.session_id,
                user_id=current_user.id,
                persona_id=request.persona,
                db=db,
            ):
                payload = json.dumps(event, default=str)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            err = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/sessions/{session_id}",
    response_model=AgentSessionResponse,
    summary="Inspect Agent Session",
    description="Retrieve execution history, trace steps, and checkpoint state for a session.",
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    """Fetch session details by ID."""
    repo = AgentSessionRepository(db)
    session_obj = repo.get_by_id(session_id)
    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent session '{session_id}' not found.",
        )

    steps = [
        AgentStepResponse(
            step_number=s.step_number,
            node_name=s.node_name,
            action=s.action,
            observation=s.observation,
            reflection=s.reflection,
            latency_ms=s.latency_ms,
        )
        for s in session_obj.steps
    ]

    snapshot = session_obj.state_snapshot or {}

    return AgentSessionResponse(
        session_id=session_obj.id,
        persona=session_obj.persona,
        status=session_obj.status,
        input_query=session_obj.input_query,
        final_answer=session_obj.final_answer,
        iterations=session_obj.iterations,
        requires_human_approval=session_obj.requires_human_approval,
        pending_action=session_obj.pending_action,
        plan=snapshot.get("plan", []),
        scratchpad=snapshot.get("scratchpad", {}),
        steps=steps,
    )


@router.post(
    "/sessions/{session_id}/resume",
    response_model=AgentSessionResponse,
    summary="Resume Paused Agent Workflow",
    description="Submit Human-In-The-Loop approval or rejection to steer a paused agent session.",
)
async def resume_session(
    session_id: str,
    request: AgentResumeRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentSessionResponse:
    """Resume execution of a paused agent session."""
    try:
        final_state = await orchestrator.resume_workflow(
            session_id=session_id,
            approved=request.approved,
            feedback=request.feedback,
            db=db,
        )

        steps = [
            AgentStepResponse(
                step_number=t.step_number,
                node_name=t.node_name,
                action=t.action,
                observation=t.observation,
                reflection=t.reflection,
                latency_ms=t.latency_ms,
            )
            for t in final_state.trace
        ]

        return AgentSessionResponse(
            session_id=final_state.session_id,
            persona=final_state.persona,
            status=final_state.status.value,
            input_query=final_state.input_query,
            final_answer=final_state.final_answer,
            iterations=final_state.iterations,
            requires_human_approval=final_state.requires_human_approval,
            pending_action=final_state.pending_action,
            plan=final_state.plan,
            scratchpad=final_state.scratchpad,
            steps=steps,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/personas",
    response_model=List[PersonaConfig],
    summary="List Agent Personas",
    description="Return available specialized agent operational personas and capabilities.",
)
async def get_personas() -> List[PersonaConfig]:
    """List operational agent personas."""
    return list_all_personas()
