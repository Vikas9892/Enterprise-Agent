"""Support ticket repository managing customer support cases, SLA, and ticket assignment."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.base import utc_now
from app.database.models.support_ticket import SupportTicket
from app.database.repositories.base import BaseRepository


class SupportTicketRepository(BaseRepository[SupportTicket]):
    """Data access operations for SupportTicket entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(SupportTicket, session)

    def get_by_ticket_number(self, ticket_number: str) -> Optional[SupportTicket]:
        """Fetch ticket by formatted ticket identifier."""
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.ticket_number == ticket_number)
            .options(joinedload(SupportTicket.customer), joinedload(SupportTicket.assigned_to))
        )
        return self.session.scalars(stmt).first()

    def list_by_customer(self, customer_id: int) -> List[SupportTicket]:
        """Fetch all tickets submitted by a customer."""
        stmt = (
            select(SupportTicket)
            .where(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_status(self, status: str) -> List[SupportTicket]:
        """Filter tickets by status (e.g., OPEN, IN_PROGRESS, RESOLVED)."""
        stmt = select(SupportTicket).where(SupportTicket.status == status).order_by(SupportTicket.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_by_priority(self, priority: str) -> List[SupportTicket]:
        """Filter tickets by priority (e.g., CRITICAL, HIGH)."""
        stmt = select(SupportTicket).where(SupportTicket.priority == priority).order_by(SupportTicket.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def assign_ticket(self, ticket: SupportTicket, user_id: int) -> SupportTicket:
        """Assign ticket to a support representative."""
        ticket.assigned_to_user_id = user_id
        if ticket.status == "OPEN":
            ticket.status = "IN_PROGRESS"
        self.session.flush()
        return ticket

    def resolve_ticket(self, ticket: SupportTicket) -> SupportTicket:
        """Mark ticket as resolved with timestamp."""
        ticket.status = "RESOLVED"
        ticket.resolved_at = utc_now()
        self.session.flush()
        return ticket
