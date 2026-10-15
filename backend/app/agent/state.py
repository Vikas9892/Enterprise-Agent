"""Data models and contracts representing Agent state and execution trace."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.llm.schemas import ChatMessage


class AgentStatus(str, Enum):
    """Execution status for the state-machine agent."""

    INITIALIZED = "initialized"
    PLANNING = "planning"
    EXECUTING_TOOL = "executing_tool"
    REFLECTING = "reflecting"
    WAITING_FOR_HUMAN = "waiting_for_human"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStepTrace(BaseModel):
    """Detailed trace record of an individual node step."""

    step_number: int
    node_name: str
    action: Optional[str] = None
    observation: Optional[str] = None
    reflection: Optional[str] = None
    latency_ms: float = 0.0
    status: AgentStatus = AgentStatus.INITIALIZED


class AgentState(BaseModel):
    """Complete asynchronous state passed between workflow graph nodes."""

    session_id: str = Field(..., description="Unique session ID")
    user_id: Optional[int] = Field(default=None, description="Requesting user ID")
    persona: str = Field(default="coordinator", description="Agent operational persona")
    input_query: str = Field(..., description="Initial user task or query")
    messages: List[ChatMessage] = Field(default_factory=list, description="Conversational context")
    plan: List[str] = Field(default_factory=list, description="Decomposed execution plan steps")
    current_step: int = Field(default=0, description="Current plan step index")
    scratchpad: Dict[str, Any] = Field(default_factory=dict, description="Working memory of facts gathered")
    pending_tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="Tools queued for execution")
    last_tool_results: List[Dict[str, Any]] = Field(default_factory=list, description="Outputs from latest tool calls")
    status: AgentStatus = Field(default=AgentStatus.INITIALIZED, description="Current workflow state")
    requires_human_approval: bool = Field(default=False, description="True if workflow paused for HITL approval")
    pending_action: Optional[Dict[str, Any]] = Field(default=None, description="Sensitive action awaiting user approval")
    human_approved: Optional[bool] = Field(default=None, description="Decision provided by user")
    human_feedback: Optional[str] = Field(default=None, description="Optional steering feedback from human")
    final_answer: Optional[str] = Field(default=None, description="Final formulated agent response")
    iterations: int = Field(default=0, description="Total cyclical iterations completed")
    max_iterations: int = Field(default=8, description="Safety guardrail ceiling for cycles")
    trace: List[AgentStepTrace] = Field(default_factory=list, description="Chronological node execution trace")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional tracking metadata")
