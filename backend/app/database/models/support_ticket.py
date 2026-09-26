"""SupportTicket model for customer issues, SLA tracking, and ticket assignment."""

from typing import Optional
from datetime import datetime
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class SupportTicket(Base, TimestampMixin):
    """Customer support case or incident ticket."""

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    assigned_to_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    subject: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="OPEN",
        index=True,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="MEDIUM",
        index=True,
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="support_tickets")
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_tickets",
        foreign_keys=[assigned_to_user_id],
    )

    __table_args__ = (
        Index("idx_ticket_customer_status", "customer_id", "status"),
        Index("idx_ticket_priority_status", "priority", "status"),
    )

    def __repr__(self) -> str:
        return f"<SupportTicket(id={self.id}, number='{self.ticket_number}', priority='{self.priority}', status='{self.status}')>"
