"""Agent session and execution step database models."""

from typing import List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.base import Base, TimestampMixin


class AgentSession(Base, TimestampMixin):
    """Persistent storage for autonomous agent execution sessions and checkpoints."""

    __tablename__ = "agent_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    persona: Mapped[str] = mapped_column(String(50), default="coordinator", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="initialized", nullable=False, index=True)
    input_query: Mapped[str] = mapped_column(Text, nullable=False)
    final_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state_snapshot: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pending_action: Mapped[Optional[dict]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    steps: Mapped[List["AgentSessionStep"]] = relationship(
        "AgentSessionStep", back_populates="session", cascade="all, delete-orphan", order_by="AgentSessionStep.step_number"
    )

    def __repr__(self) -> str:
        return f"<AgentSession id={self.id} status={self.status} persona={self.persona}>"


class AgentSessionStep(Base, TimestampMixin):
    """Detailed trace step executed during an agent session."""

    __tablename__ = "agent_session_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    session: Mapped["AgentSession"] = relationship("AgentSession", back_populates="steps")

    def __repr__(self) -> str:
        return f"<AgentSessionStep session_id={self.session_id} step={self.step_number} node={self.node_name}>"
