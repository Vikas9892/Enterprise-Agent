"""API endpoints for multi-agent swarm collaboration and supervisor task delegation."""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.multi_agent import (
    ENTERPRISE_SWARM_AGENTS,
    MultiAgentSwarm,
    SpecialistAgentDefinition,
    SwarmState,
    get_swarm_orchestrator,
)
from app.auth.dependencies import get_current_user
from app.database.models.user import User

router = APIRouter()


class SwarmRunRequest(BaseModel):
    """Payload to initiate a collaborative multi-agent swarm task."""

    query: str = Field(..., min_length=3, description="Complex enterprise task to be solved by multi-agent swarm")
    swarm_id: Optional[str] = Field(default=None, description="Optional custom swarm session identifier")


@router.get(
    "/agents",
    response_model=List[SpecialistAgentDefinition],
    summary="List Swarm Specialist Agents",
    description="Retrieve catalog of specialist agents participating in collaborative swarms.",
)
async def list_swarm_agents() -> List[SpecialistAgentDefinition]:
    """Return available specialist swarm agents."""
    return list(ENTERPRISE_SWARM_AGENTS.values())


@router.post(
    "/run",
    response_model=SwarmState,
    summary="Execute Collaborative Swarm Task",
    description="Supervisor decomposes query, delegates to specialist agents, verifies consensus, and synthesizes output.",
)
async def run_swarm_task(
    request: SwarmRunRequest,
    swarm: MultiAgentSwarm = Depends(get_swarm_orchestrator),
    current_user: User = Depends(get_current_user),
) -> SwarmState:
    """Execute supervisor-driven multi-agent collaboration."""
    return await swarm.execute_swarm(query=request.query, swarm_id=request.swarm_id)


@router.post(
    "/stream",
    summary="Stream Swarm Delegation Events",
    description="Stream real-time subtask delegation, specialist agent handovers, and final resolution via SSE.",
)
async def stream_swarm_task(
    request: SwarmRunRequest,
    swarm: MultiAgentSwarm = Depends(get_swarm_orchestrator),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream real-time swarm execution events over Server-Sent Events (SSE)."""

    async def event_generator():
        try:
            async for event in swarm.stream_swarm(query=request.query):
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
