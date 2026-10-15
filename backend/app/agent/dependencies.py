"""FastAPI dependencies for agent orchestrator and workflow sessions."""

from typing import Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from app.agent.orchestrator import AgentOrchestrator
from app.database.session import get_db
from app.llm import LLMGateway, get_llm_gateway
from app.tools import ToolRegistry, get_tool_registry

_orchestrator_instance: Optional[AgentOrchestrator] = None


def get_agent_orchestrator(
    llm_gateway: LLMGateway = Depends(get_llm_gateway),
    tool_registry: ToolRegistry = Depends(get_tool_registry),
) -> AgentOrchestrator:
    """Dependency provider for AgentOrchestrator."""
    global _orchestrator_instance
    resolved_gateway = get_llm_gateway() if getattr(llm_gateway, "__class__", None).__name__ == "Depends" else llm_gateway
    resolved_registry = get_tool_registry() if getattr(tool_registry, "__class__", None).__name__ == "Depends" else tool_registry

    if _orchestrator_instance is None:
        _orchestrator_instance = AgentOrchestrator(
            llm_gateway=resolved_gateway,
            tool_registry=resolved_registry,
        )
    return _orchestrator_instance
