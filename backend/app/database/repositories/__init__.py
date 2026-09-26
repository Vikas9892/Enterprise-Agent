"""Repositories package aggregating all domain data access layers."""

from app.database.repositories.base import BaseRepository
from app.database.repositories.customer import CustomerRepository
from app.database.repositories.order import OrderRepository
from app.database.repositories.product import ProductRepository
from app.database.repositories.invoice import InvoiceRepository
from app.database.repositories.support_ticket import SupportTicketRepository
from app.database.repositories.user import UserRepository
from app.database.repositories.audit_log import AuditLogRepository

__all__ = [
    "BaseRepository",
    "CustomerRepository",
    "OrderRepository",
    "ProductRepository",
    "InvoiceRepository",
    "SupportTicketRepository",
    "UserRepository",
    "AuditLogRepository",
]
