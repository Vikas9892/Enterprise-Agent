"""Order and OrderItem models representing enterprise purchase transactions."""

from typing import List, Optional
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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, utc_now


class Order(Base, TimestampMixin):
    """Customer sales order."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("customers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        index=True,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="order",
    )

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_order_total_amount_positive"),
        Index("idx_order_customer_status", "customer_id", "status"),
    )

    def calculate_total(self) -> Decimal:
        """Compute the sum of line items."""
        total = sum((item.subtotal for item in self.items), Decimal("0.00"))
        self.total_amount = total
        return total

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, number='{self.order_number}', status='{self.status}', total={self.total_amount})>"


class OrderItem(Base):
    """Individual line item within an order."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items", lazy="joined")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_order_item_qty_positive"),
        CheckConstraint("unit_price >= 0", name="chk_order_item_price_positive"),
        CheckConstraint("subtotal >= 0", name="chk_order_item_subtotal_positive"),
        Index("idx_order_item_order_product", "order_id", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, qty={self.quantity})>"
