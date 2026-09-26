"""Product repository managing catalog items and stock levels."""

from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.base import utc_now
from app.database.models.product import Inventory, Product
from app.database.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """Data access operations for Product and Inventory entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Product, session)

    def get_by_sku(self, sku: str) -> Optional[Product]:
        """Lookup a product by unique SKU with its inventory."""
        stmt = (
            select(Product)
            .where(Product.sku == sku.upper().strip())
            .options(selectinload(Product.inventory))
        )
        return self.session.scalars(stmt).first()

    def get_with_inventory(self, product_id: int) -> Optional[Product]:
        """Fetch product with eager loaded inventory."""
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.inventory))
        )
        return self.session.scalars(stmt).first()

    def list_active(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """List all active products in the catalog."""
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .options(selectinload(Product.inventory))
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_by_category(self, category: str) -> List[Product]:
        """List products by category."""
        stmt = (
            select(Product)
            .where(Product.category == category, Product.is_active.is_(True))
            .options(selectinload(Product.inventory))
        )
        return list(self.session.scalars(stmt).all())

    def create_with_inventory(
        self,
        sku: str,
        name: str,
        category: str,
        unit_price: Decimal,
        initial_stock: int = 0,
        warehouse_location: str = "WH-MAIN-01",
        description: Optional[str] = None,
    ) -> Product:
        """Create a product and initialize its inventory record atomically."""
        product = Product(
            sku=sku.upper().strip(),
            name=name,
            category=category,
            unit_price=unit_price,
            description=description,
            is_active=True,
        )
        self.session.add(product)
        self.session.flush()

        inventory = Inventory(
            product_id=product.id,
            quantity_on_hand=initial_stock,
            quantity_reserved=0,
            reorder_threshold=10,
            warehouse_location=warehouse_location,
            last_restocked_at=utc_now() if initial_stock > 0 else None,
        )
        self.session.add(inventory)
        self.session.flush()

        return product

    def update_stock(self, product_id: int, quantity_delta: int) -> Optional[Inventory]:
        """Adjust physical stock level by a delta value."""
        stmt = select(Inventory).where(Inventory.product_id == product_id)
        inventory = self.session.scalars(stmt).first()
        if inventory:
            new_qty = inventory.quantity_on_hand + quantity_delta
            if new_qty < 0:
                raise ValueError(f"Insufficient stock for product ID {product_id}")
            inventory.quantity_on_hand = new_qty
            if quantity_delta > 0:
                inventory.last_restocked_at = utc_now()
            self.session.flush()
        return inventory
