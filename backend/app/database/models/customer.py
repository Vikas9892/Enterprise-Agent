"""Customer model representing enterprise accounts and clients."""

from typing import List, Optional
from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """Customer entity representing external enterprise accounts."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(150), index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="standard", index=True, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_customer_company_tier", "company", "tier"),
    )

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, name='{self.name}', company='{self.company}', tier='{self.tier}')>"
