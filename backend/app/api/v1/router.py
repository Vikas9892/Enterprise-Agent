"""API v1 master router aggregating version 1 endpoints."""

from fastapi import APIRouter
from app.api.v1.endpoints.agent import router as agent_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.llm import router as llm_router
from app.api.v1.endpoints.mcp import router as mcp_router
from app.api.v1.endpoints.observability import router as observability_router
from app.api.v1.endpoints.evaluation import router as evaluation_router
from app.api.v1.endpoints.swarm import router as swarm_router
from app.api.v1.endpoints.knowledge import router as knowledge_router
from app.api.v1.endpoints.governance import router as governance_router

v1_router = APIRouter()

# Register endpoint routers
v1_router.include_router(health_router)
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(llm_router, prefix="/llm", tags=["LLM Gateway"])
v1_router.include_router(mcp_router, prefix="/mcp", tags=["Model Context Protocol"])
v1_router.include_router(agent_router, prefix="/agent", tags=["Agent Orchestrator"])
v1_router.include_router(observability_router, prefix="/observability", tags=["Observability & Telemetry"])
v1_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation & Benchmarks"])
v1_router.include_router(swarm_router, prefix="/swarm", tags=["Multi-Agent Swarm Collaboration"])
v1_router.include_router(knowledge_router, prefix="/knowledge", tags=["Enterprise Knowledge & RAG"])
v1_router.include_router(governance_router, prefix="/governance", tags=["Governance & Policy Engine"])


