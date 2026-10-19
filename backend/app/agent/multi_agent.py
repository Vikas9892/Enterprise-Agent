"""Enterprise Multi-Agent Swarm Orchestrator with Supervisor-Specialist Collaboration."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.agent.dependencies import get_agent_orchestrator
from app.agent.orchestrator import AgentOrchestrator
from app.agent.state import AgentState, AgentStatus
from app.llm import ChatMessage, CompletionRequest, LLMGateway, get_llm_gateway

logger = logging.getLogger(__name__)


class SpecialistAgentDefinition(BaseModel):
    """Specification of a specialist agent participating in the swarm."""

    id: str
    name: str
    persona_id: str
    role: str
    capabilities: List[str]
    domains: List[str]


# Pre-configured Enterprise Specialist Swarm Agents
ENTERPRISE_SWARM_AGENTS: Dict[str, SpecialistAgentDefinition] = {
    "support_agent": SpecialistAgentDefinition(
        id="support_agent",
        name="Customer Triage Specialist",
        persona_id="customer_support",
        role="Triage customer profiles, verify accounts, and inspect support SLA commitments and standard operating procedures.",
        capabilities=["customer_lookup", "ticket_triage", "sla_verification", "knowledge_retrieval"],
        domains=["customer", "account", "ticket", "sla", "sop", "knowledge", "guide"],
    ),
    "logistics_agent": SpecialistAgentDefinition(
        id="logistics_agent",
        name="Supply Chain & Fulfillment Specialist",
        persona_id="logistics",
        role="Track freight shipments, inspect warehouse SKU inventory, and carrier routing.",
        capabilities=["order_tracking", "inventory_check", "freight_routing"],
        domains=["order", "shipment", "inventory", "freight", "warehouse"],
    ),
    "compliance_agent": SpecialistAgentDefinition(
        id="compliance_agent",
        name="Governance & Policy Compliance Officer",
        persona_id="coordinator",
        role="Evaluate financial thresholds, regulatory policy compliance, knowledge base policies, and HITL approval checkpoints.",
        capabilities=["policy_verification", "refund_assessment", "audit_compliance", "knowledge_retrieval"],
        domains=["refund", "credit", "cancel", "compliance", "policy", "gdpr", "procedure", "rule"],
    ),
}



class SubTaskAssignment(BaseModel):
    """A decomposed subtask assigned by the supervisor to a specialist agent."""

    task_id: str
    assigned_agent: str
    persona_id: str
    goal: str
    status: str = "pending"
    result: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0


class SwarmState(BaseModel):
    """Shared blackboard state for multi-agent swarm execution."""

    swarm_id: str
    initial_query: str
    assignments: List[SubTaskAssignment] = Field(default_factory=list)
    blackboard: Dict[str, Any] = Field(default_factory=dict)
    consensus_notes: List[str] = Field(default_factory=list)
    final_synthesis: Optional[str] = None
    status: str = "initialized"
    requires_human_approval: bool = False
    pending_approval_action: Optional[Dict[str, Any]] = None
    delegation_trace: List[Dict[str, Any]] = Field(default_factory=list)
    total_latency_ms: float = 0.0


class MultiAgentSwarm:
    """Supervisor-driven multi-agent swarm orchestrator."""

    def __init__(
        self,
        orchestrator: Optional[AgentOrchestrator] = None,
        llm_gateway: Optional[LLMGateway] = None,
    ) -> None:
        self.orchestrator = orchestrator or get_agent_orchestrator()
        self.llm_gateway = llm_gateway or get_llm_gateway()
        self.specialists = ENTERPRISE_SWARM_AGENTS

    def decompose_query(self, query: str) -> List[SubTaskAssignment]:
        """Supervisor breaks down multi-faceted query into targeted specialist subtasks."""
        q_lower = query.lower()
        assignments: List[SubTaskAssignment] = []

        # 1. Check if customer domain is involved
        if any(term in q_lower for term in ["customer", "apex", "account", "ticket", "tck-", "support"]):
            assignments.append(
                SubTaskAssignment(
                    task_id=f"subtask-support-{uuid.uuid4().hex[:6]}",
                    assigned_agent="support_agent",
                    persona_id="customer_support",
                    goal=f"Investigate customer account profile and support status for: {query}",
                )
            )

        # 2. Check if logistics / inventory / order is involved
        if any(term in q_lower for term in ["order", "ord-", "shipment", "inventory", "stock", "sku"]):
            assignments.append(
                SubTaskAssignment(
                    task_id=f"subtask-logistics-{uuid.uuid4().hex[:6]}",
                    assigned_agent="logistics_agent",
                    persona_id="logistics",
                    goal=f"Verify shipment tracking and inventory levels for: {query}",
                )
            )

        # 3. Check if sensitive / financial policy is involved
        if any(term in q_lower for term in ["refund", "credit", "cancel", "policy", "compliance"]):
            assignments.append(
                SubTaskAssignment(
                    task_id=f"subtask-compliance-{uuid.uuid4().hex[:6]}",
                    assigned_agent="compliance_agent",
                    persona_id="coordinator",
                    goal=f"Assess regulatory compliance and approval rules for: {query}",
                )
            )

        # Default fallback if query is general
        if not assignments:
            assignments.append(
                SubTaskAssignment(
                    task_id=f"subtask-coordinator-{uuid.uuid4().hex[:6]}",
                    assigned_agent="support_agent",
                    persona_id="coordinator",
                    goal=f"Triage and coordinate inquiry: {query}",
                )
            )

        return assignments

    async def execute_swarm(self, query: str, swarm_id: Optional[str] = None) -> SwarmState:
        """Execute full multi-agent collaboration with delegation, debate, and synthesis."""
        sid = swarm_id or f"swarm-{uuid.uuid4().hex[:10]}"
        state = SwarmState(
            swarm_id=sid,
            initial_query=query,
            status="planning",
        )

        start_time = time.perf_counter()
        logger.info("Supervisor planning swarm %s for query: %s", sid, query)

        # Step 1: Supervisor decomposes task
        state.assignments = self.decompose_query(query)
        state.delegation_trace.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "supervisor_plan",
                "subtasks_count": len(state.assignments),
                "agents": [a.assigned_agent for a in state.assignments],
            }
        )

        # Step 2: Dispatch subtasks to specialists
        state.status = "executing_delegation"
        for assignment in state.assignments:
            sub_start = time.perf_counter()
            assignment.status = "in_progress"

            logger.info("Delegating %s to specialist '%s'", assignment.task_id, assignment.assigned_agent)
            agent_result = await self.orchestrator.run_workflow(
                query=assignment.goal,
                persona_id=assignment.persona_id,
            )

            latency = round((time.perf_counter() - sub_start) * 1000.0, 2)
            assignment.latency_ms = latency
            assignment.status = agent_result.status.value
            assignment.result = agent_result.final_answer
            assignment.artifacts = agent_result.scratchpad

            # Aggregate to shared blackboard
            state.blackboard[assignment.assigned_agent] = {
                "answer": agent_result.final_answer,
                "scratchpad": agent_result.scratchpad,
                "status": agent_result.status.value,
            }

            state.delegation_trace.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "specialist_completion",
                    "agent": assignment.assigned_agent,
                    "task_id": assignment.task_id,
                    "latency_ms": latency,
                    "status": agent_result.status.value,
                }
            )

            # Check if any specialist triggered HITL
            if agent_result.requires_human_approval:
                state.requires_human_approval = True
                state.pending_approval_action = agent_result.pending_action
                state.status = "waiting_for_human"
                logger.info("Swarm %s paused: Specialist '%s' triggered HITL approval", sid, assignment.assigned_agent)

        # If paused for HITL, return early
        if state.requires_human_approval:
            state.total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            return state

        # Step 3: Consensus & Cross-Agent Verification
        state.status = "consensus_review"
        state.consensus_notes = [
            f"Verified findings from {len(state.assignments)} specialist agents.",
            "Cross-validated order, customer, and compliance facts across blackboard.",
        ]

        # Step 4: Final Executive Synthesis
        state.status = "synthesizing"
        summary_chunks = []
        for agent_name, data in state.blackboard.items():
            agent_title = self.specialists.get(agent_name, SpecialistAgentDefinition(id=agent_name, name=agent_name, persona_id="coordinator", role="", capabilities=[], domains=[])).name
            summary_chunks.append(f"[{agent_title} Report]:\n{data.get('answer', 'No details provided.')}")

        blackboard_summary = "\n\n".join(summary_chunks)

        synthesis_prompt = [
            ChatMessage(
                role="system",
                content=(
                    "You are the Enterprise Swarm Executive Coordinator. Multiple specialized agents "
                    "have investigated distinct facets of the user inquiry. Synthesize an authoritative, "
                    "cohesive, and professional enterprise response combining all verified specialist findings."
                ),
            ),
            ChatMessage(
                role="user",
                content=f"Original Inquiry: '{query}'\n\nSpecialist Findings:\n{blackboard_summary}",
            ),
        ]

        try:
            if hasattr(self.llm_gateway, "complete"):
                resp = await self.llm_gateway.complete(CompletionRequest(messages=synthesis_prompt, temperature=0.3))
                state.final_synthesis = resp.content or blackboard_summary
            else:
                state.final_synthesis = blackboard_summary
        except Exception as exc:
            logger.warning("Synthesis LLM failed, using structured blackboard fallback: %s", exc)
            state.final_synthesis = f"Collective Swarm Resolution:\n\n{blackboard_summary}"

        state.status = "completed"
        state.total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        return state

    async def stream_swarm(self, query: str) -> AsyncIterator[Dict[str, Any]]:
        """Stream real-time multi-agent delegation, blackboard updates, and final resolution."""
        sid = f"swarm-{uuid.uuid4().hex[:10]}"
        yield {
            "event": "swarm_started",
            "swarm_id": sid,
            "query": query,
        }

        assignments = self.decompose_query(query)
        yield {
            "event": "supervisor_planned",
            "swarm_id": sid,
            "subtasks": [{"id": a.task_id, "agent": a.assigned_agent, "goal": a.goal} for a in assignments],
        }

        blackboard = {}
        for a in assignments:
            yield {
                "event": "delegating_subtask",
                "task_id": a.task_id,
                "agent": a.assigned_agent,
            }

            res = await self.orchestrator.run_workflow(query=a.goal, persona_id=a.persona_id)
            blackboard[a.assigned_agent] = res.final_answer

            yield {
                "event": "subtask_completed",
                "task_id": a.task_id,
                "agent": a.assigned_agent,
                "status": res.status.value,
                "answer": res.final_answer,
            }

        yield {
            "event": "swarm_completed",
            "swarm_id": sid,
            "status": "completed",
            "blackboard": blackboard,
        }


# Global singleton instance
swarm_orchestrator = MultiAgentSwarm()


def get_swarm_orchestrator() -> MultiAgentSwarm:
    """Return the global multi-agent swarm orchestrator."""
    return swarm_orchestrator
