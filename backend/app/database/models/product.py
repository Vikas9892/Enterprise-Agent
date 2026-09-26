"""Product and Inventory models for catalog and warehouse tracking."""

from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean,
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


class Product(Base, TimestampMixin):
    """Product catalog item offered by the enterprise platform."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Relationships
    inventory: Mapped[Optional["Inventory"]] = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
    )

    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="chk_product_unit_price_positive"),
        Index("idx_product_category_active", "category", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}', price={self.unit_price})>"


class Inventory(Base):
    """Inventory levels and warehouse allocations for a product."""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    warehouse_location: Mapped[str] = mapped_column(String(100), default="WH-MAIN-01", nullable=False)
    last_restocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    product: Mapped[Product] = relationship(
        Product,
        back_populates="inventory",
    )

    __table_args__ = (
        CheckConstraint("quantity_on_hand >= 0", name="chk_inventory_qoh_nonnegative"),
        CheckConstraint("quantity_reserved >= 0", name="chk_inventory_reserved_nonnegative"),
        Index("idx_inventory_product_warehouse", "product_id", "warehouse_location"),
    )

    @property
    def quantity_available(self) -> int:
        """Calculate unreserved available inventory."""
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    def __repr__(self) -> str:
        return f"<Inventory(product_id={self.product_id}, on_hand={self.quantity_on_hand}, reserved={self.quantity_reserved})>"
