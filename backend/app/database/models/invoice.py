"""Invoice model for billing, payment records, and accounts receivable."""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, utc_now


class Invoice(Base, TimestampMixin):
    """Customer invoice issued against an account or specific order."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="ISSUED",
        index=True,
        nullable=False,
    )
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="invoices")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="invoices")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_invoice_amount_positive"),
        Index("idx_invoice_customer_status", "customer_id", "status"),
        Index("idx_invoice_due_date_status", "due_date", "status"),
    )

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', amount={self.amount}, status='{self.status}')>"
