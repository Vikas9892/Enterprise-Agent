"""Repository for agent session management and step trace persistence."""

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.database.models.agent_session import AgentSession, AgentSessionStep
from app.database.repositories.base import BaseRepository


class AgentSessionRepository(BaseRepository[AgentSession]):
    """Repository handling CRUD and queries for autonomous agent sessions and step traces."""

    def __init__(self, db: Session):
        super().__init__(AgentSession, db)
        self.db = db

    def create_session(
        self,
        session_id: str,
        input_query: str,
        user_id: Optional[int] = None,
        persona: str = "coordinator",
        status: str = "initialized",
        state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> AgentSession:
        """Create and persist a new agent session checkpoint."""
        session = AgentSession(
            id=session_id,
            user_id=user_id,
            persona=persona,
            status=status,
            input_query=input_query,
            state_snapshot=state_snapshot or {},
            iterations=0,
            requires_human_approval=False,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: str) -> Optional[AgentSession]:
        """Fetch session by ID with joined steps."""
        return self.db.query(AgentSession).filter(AgentSession.id == session_id).first()

    def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        final_answer: Optional[str] = None,
        state_snapshot: Optional[Dict[str, Any]] = None,
        iterations: Optional[int] = None,
        requires_human_approval: Optional[bool] = None,
        pending_action: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentSession]:
        """Update session state checkpoint."""
        session = self.get_by_id(session_id)
        if not session:
            return None

        if status is not None:
            session.status = status
        if final_answer is not None:
            session.final_answer = final_answer
        if state_snapshot is not None:
            session.state_snapshot = state_snapshot
        if iterations is not None:
            session.iterations = iterations
        if requires_human_approval is not None:
            session.requires_human_approval = requires_human_approval
        if pending_action is not None:
            session.pending_action = pending_action

        self.db.commit()
        self.db.refresh(session)
        return session

    def add_step(
        self,
        session_id: str,
        step_number: int,
        node_name: str,
        action: Optional[str] = None,
        observation: Optional[str] = None,
        reflection: Optional[str] = None,
        latency_ms: float = 0.0,
    ) -> AgentSessionStep:
        """Record an execution node step trace."""
        step = AgentSessionStep(
            session_id=session_id,
            step_number=step_number,
            node_name=node_name,
            action=action,
            observation=observation,
            reflection=reflection,
            latency_ms=latency_ms,
        )
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def list_user_sessions(
        self, user_id: int, skip: int = 0, limit: int = 20
    ) -> List[AgentSession]:
        """List past sessions initiated by a specific user."""
        return (
            self.db.query(AgentSession)
            .filter(AgentSession.user_id == user_id)
            .order_by(AgentSession.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
