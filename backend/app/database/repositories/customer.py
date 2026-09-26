"""Customer repository containing enterprise customer query and command logic."""

from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.models.customer import Customer
from app.database.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Data access operations for Customer entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Customer, session)

    def get_by_email(self, email: str) -> Optional[Customer]:
        """Fetch customer by unique email address."""
        stmt = select(Customer).where(Customer.email == email.strip().lower())
        return self.session.scalars(stmt).first()

    def search(self, query: str, skip: int = 0, limit: int = 50) -> List[Customer]:
        """Search customers by name, company, or email."""
        pattern = f"%{query}%"
        stmt = (
            select(Customer)
            .where(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.company.ilike(pattern),
                    Customer.email.ilike(pattern),
                )
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def get_with_orders(self, customer_id: int) -> Optional[Customer]:
        """Retrieve customer including eager-loaded orders."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.orders))
        )
        return self.session.scalars(stmt).first()

    def get_with_invoices(self, customer_id: int) -> Optional[Customer]:
        """Retrieve customer including eager-loaded invoices."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.invoices))
        )
        return self.session.scalars(stmt).first()

    def get_with_tickets(self, customer_id: int) -> Optional[Customer]:
        """Retrieve customer including eager-loaded support tickets."""
        stmt = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.support_tickets))
        )
        return self.session.scalars(stmt).first()

    def list_by_tier(self, tier: str) -> List[Customer]:
        """Filter active customers by tier (e.g., enterprise, premium)."""
        stmt = select(Customer).where(Customer.tier == tier, Customer.is_active.is_(True))
        return list(self.session.scalars(stmt).all())
