"""Database models package aggregating all domain entities and associations."""

from app.database.base import Base, TimestampMixin, utc_now
from app.database.models.user import (
    Permission,
    Role,
    User,
    role_permissions,
    user_roles,
)
from app.database.models.customer import Customer
from app.database.models.product import Inventory, Product
from app.database.models.order import Order, OrderItem
from app.database.models.invoice import Invoice
from app.database.models.support_ticket import SupportTicket
from app.database.models.audit_log import AuditLog

__all__ = [
    "Base",
    "TimestampMixin",
    "utc_now",
    "User",
    "Role",
    "Permission",
    "user_roles",
    "role_permissions",
    "Customer",
    "Product",
    "Inventory",
    "Order",
    "OrderItem",
    "Invoice",
    "SupportTicket",
    "AuditLog",
]
