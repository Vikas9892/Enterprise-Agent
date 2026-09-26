"""Order repository managing sales orders, order items, and state transitions."""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.models.order import Order, OrderItem
from app.database.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Data access operations for Order and OrderItem entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Order, session)

    def get_by_order_number(self, order_number: str) -> Optional[Order]:
        """Find order by its unique alphanumeric reference."""
        stmt = (
            select(Order)
            .where(Order.order_number == order_number)
            .options(selectinload(Order.items).joinedload(OrderItem.product))
        )
        return self.session.scalars(stmt).first()

    def get_with_items(self, order_id: int) -> Optional[Order]:
        """Retrieve order along with line items and product details."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.items).joinedload(OrderItem.product))
        )
        return self.session.scalars(stmt).first()

    def list_by_customer(self, customer_id: int, skip: int = 0, limit: int = 50) -> List[Order]:
        """Fetch orders placed by a specific customer."""
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.placed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_status(self, status: str, skip: int = 0, limit: int = 50) -> List[Order]:
        """Fetch orders filtered by status."""
        stmt = (
            select(Order)
            .where(Order.status == status)
            .order_by(Order.placed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def create_order_with_items(
        self,
        customer_id: int,
        order_number: str,
        items: List[Dict[str, Any]],
        notes: Optional[str] = None,
        currency: str = "USD",
    ) -> Order:
        """Create an order and its associated line items atomically, computing totals."""
        order = Order(
            customer_id=customer_id,
            order_number=order_number,
            status="PENDING",
            currency=currency,
            notes=notes,
            total_amount=Decimal("0.00"),
        )
        self.session.add(order)
        self.session.flush()

        total = Decimal("0.00")
        for item_data in items:
            qty = int(item_data["quantity"])
            price = Decimal(str(item_data["unit_price"]))
            subtotal = qty * price
            total += subtotal

            line_item = OrderItem(
                order_id=order.id,
                product_id=int(item_data["product_id"]),
                quantity=qty,
                unit_price=price,
                subtotal=subtotal,
            )
            self.session.add(line_item)

        order.total_amount = total
        self.session.flush()
        return order

    def update_status(self, order: Order, new_status: str) -> Order:
        """Transition order to a new lifecycle state."""
        order.status = new_status
        self.session.flush()
        return order
