"""Invoice repository managing billing records, overdue tracking, and collections."""

from datetime import timedelta
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.base import utc_now
from app.database.models.invoice import Invoice
from app.database.models.order import Order
from app.database.repositories.base import BaseRepository


class InvoiceRepository(BaseRepository[Invoice]):
    """Data access operations for Invoice entities."""

    def __init__(self, session: Session) -> None:
        super().__init__(Invoice, session)

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Lookup an invoice by invoice reference number."""
        stmt = (
            select(Invoice)
            .where(Invoice.invoice_number == invoice_number)
            .options(joinedload(Invoice.customer), joinedload(Invoice.order))
        )
        return self.session.scalars(stmt).first()

    def list_by_customer(self, customer_id: int) -> List[Invoice]:
        """Fetch all invoices for a given customer."""
        stmt = (
            select(Invoice)
            .where(Invoice.customer_id == customer_id)
            .order_by(Invoice.issued_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_by_status(self, status: str) -> List[Invoice]:
        """Filter invoices by payment/issuance status."""
        stmt = select(Invoice).where(Invoice.status == status).order_by(Invoice.due_date.asc())
        return list(self.session.scalars(stmt).all())

    def list_overdue(self) -> List[Invoice]:
        """Query unpaid invoices past their due date."""
        now = utc_now()
        stmt = (
            select(Invoice)
            .where(
                Invoice.due_date < now,
                Invoice.status.in_(["ISSUED", "OVERDUE", "PARTIAL"]),
            )
            .order_by(Invoice.due_date.asc())
        )
        return list(self.session.scalars(stmt).all())

    def mark_as_paid(self, invoice: Invoice) -> Invoice:
        """Mark invoice as paid and record settlement timestamp."""
        invoice.status = "PAID"
        invoice.paid_at = utc_now()
        self.session.flush()
        return invoice

    def create_for_order(self, order: Order, invoice_number: str, payment_terms_days: int = 30) -> Invoice:
        """Issue an invoice for a completed or confirmed sales order."""
        now = utc_now()
        invoice = Invoice(
            invoice_number=invoice_number,
            customer_id=order.customer_id,
            order_id=order.id,
            amount=order.total_amount,
            currency=order.currency,
            status="ISSUED",
            issued_at=now,
            due_date=now + timedelta(days=payment_terms_days),
        )
        self.session.add(invoice)
        self.session.flush()
        return invoice
