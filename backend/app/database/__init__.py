"""Database package exposing session management, models, and repositories."""

from app.database.base import Base, TimestampMixin, utc_now
from app.database.session import get_db, get_engine, get_session_factory
from app.database.models import (
    AuditLog,
    Customer,
    Inventory,
    Invoice,
    Order,
    OrderItem,
    Permission,
    Product,
    Role,
    SupportTicket,
    User,
    role_permissions,
    user_roles,
)
from app.database.repositories import (
    AuditLogRepository,
    BaseRepository,
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    ProductRepository,
    SupportTicketRepository,
    UserRepository,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "utc_now",
    "get_db",
    "get_engine",
    "get_session_factory",
    # Models
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
    # Repositories
    "BaseRepository",
    "CustomerRepository",
    "OrderRepository",
    "ProductRepository",
    "InvoiceRepository",
    "SupportTicketRepository",
    "UserRepository",
    "AuditLogRepository",
]
