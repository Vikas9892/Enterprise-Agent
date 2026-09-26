"""Audit log repository for immutable event recording and compliance auditing."""

import json
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLog
from app.database.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Data access operations for immutable AuditLog entries."""

    def __init__(self, session: Session) -> None:
        super().__init__(AuditLog, session)

    def log_event(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[int] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Create and persist an immutable audit log entry."""
        log_entry = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_values=json.dumps(old_values, default=str) if old_values else None,
            new_values=json.dumps(new_values, default=str) if new_values else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        self.session.flush()
        return log_entry

    def list_by_entity(self, entity_type: str, entity_id: str) -> List[AuditLog]:
        """Fetch audit trail for a specific domain entity."""
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == str(entity_id),
            )
            .order_by(AuditLog.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_actor(self, actor_id: int, limit: int = 100) -> List[AuditLog]:
        """Fetch recent actions performed by a specific user."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())
