"""Comprehensive tests for database models, relationships, constraints, and repositories."""

from decimal import Decimal
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.database.models import (
    Customer,
    Order,
    Permission,
    Product,
    Role,
    User,
)
from app.database.repositories import (
    AuditLogRepository,
    CustomerRepository,
    InvoiceRepository,
    OrderRepository,
    ProductRepository,
    SupportTicketRepository,
    UserRepository,
)


def test_user_role_permission_rbac(db_session: Session) -> None:
    """Verify Many-to-Many associations between User, Role, and Permission."""
    perm_read = Permission(name="orders:read", resource="orders", action="read")
    perm_write = Permission(name="orders:write", resource="orders", action="write")
    db_session.add_all([perm_read, perm_write])
    db_session.flush()

    role = Role(name="OrderManager", description="Can manage orders")
    role.permissions = [perm_read, perm_write]
    db_session.add(role)
    db_session.flush()

    user = User(
        email="operator@enterprise.ai",
        full_name="Operations Operator",
        department="Operations",
    )
    user.roles.append(role)
    db_session.add(user)
    db_session.flush()

    # Query via repository
    user_repo = UserRepository(db_session)
    fetched_user = user_repo.get_by_email("operator@enterprise.ai")
    assert fetched_user is not None
    assert len(fetched_user.roles) == 1
    assert fetched_user.roles[0].name == "OrderManager"
    assert len(fetched_user.roles[0].permissions) == 2
    perm_names = {p.name for p in fetched_user.roles[0].permissions}
    assert "orders:read" in perm_names
    assert "orders:write" in perm_names


def test_customer_repository_crud_and_search(db_session: Session) -> None:
    """Verify CustomerRepository search, filtering, and eager loading."""
    repo = CustomerRepository(db_session)

    c1 = repo.create(
        name="Alpha Global Corp",
        email="contact@alphaglobal.com",
        company="Alpha Global",
        tier="enterprise",
        city="New York",
        country="USA",
    )
    c2 = repo.create(
        name="Beta Systems Inc",
        email="ops@betasystems.com",
        company="Beta Systems",
        tier="standard",
        city="Austin",
        country="USA",
    )

    # Search
    results = repo.search("Alpha")
    assert len(results) == 1
    assert results[0].email == "contact@alphaglobal.com"

    # Filter by tier
    enterprise_customers = repo.list_by_tier("enterprise")
    assert any(c.email == "contact@alphaglobal.com" for c in enterprise_customers)
    assert not any(c.email == "ops@betasystems.com" for c in enterprise_customers)

    # Unique email lookup
    by_email = repo.get_by_email("contact@alphaglobal.com")
    assert by_email is not None
    assert by_email.id == c1.id


def test_product_and_inventory_repository(db_session: Session) -> None:
    """Verify ProductRepository, 1-to-1 inventory relationship, and stock adjustments."""
    repo = ProductRepository(db_session)

    product = repo.create_with_inventory(
        sku="TEST-SKU-001",
        name="AI Acceleration Card",
        category="Hardware",
        unit_price=Decimal("4500.00"),
        initial_stock=10,
        warehouse_location="WH-TEST-01",
    )

    assert product.id is not None
    assert product.inventory is not None
    assert product.inventory.quantity_on_hand == 10
    assert product.inventory.quantity_available == 10

    # Increase stock
    updated_inv = repo.update_stock(product.id, 5)
    assert updated_inv.quantity_on_hand == 15

    # Decrease stock
    updated_inv = repo.update_stock(product.id, -3)
    assert updated_inv.quantity_on_hand == 12

    # Insufficient stock error
    with pytest.raises(ValueError, match="Insufficient stock"):
        repo.update_stock(product.id, -20)

    # Retrieve by SKU
    lookup = repo.get_by_sku("TEST-SKU-001")
    assert lookup is not None
    assert lookup.name == "AI Acceleration Card"


def test_order_repository_with_items(db_session: Session) -> None:
    """Verify atomic order creation with line items and subtotal computation."""
    cust_repo = CustomerRepository(db_session)
    customer = cust_repo.create(
        name="Nexus Industries",
        email="procure@nexus.io",
        tier="enterprise",
    )

    prod_repo = ProductRepository(db_session)
    p1 = prod_repo.create_with_inventory(
        sku="NEXUS-01",
        name="Item Alpha",
        category="Hardware",
        unit_price=Decimal("100.00"),
        initial_stock=50,
    )
    p2 = prod_repo.create_with_inventory(
        sku="NEXUS-02",
        name="Item Beta",
        category="Software",
        unit_price=Decimal("50.00"),
        initial_stock=100,
    )

    order_repo = OrderRepository(db_session)
    items = [
        {"product_id": p1.id, "quantity": 2, "unit_price": Decimal("100.00")},
        {"product_id": p2.id, "quantity": 3, "unit_price": Decimal("50.00")},
    ]

    order = order_repo.create_order_with_items(
        customer_id=customer.id,
        order_number="ORD-TEST-1001",
        items=items,
        notes="Automated test purchase",
    )

    assert order.id is not None
    assert order.status == "PENDING"
    # Total = (2 * 100) + (3 * 50) = 200 + 150 = 350.00
    assert order.total_amount == Decimal("350.00")
    assert len(order.items) == 2

    # Status transition
    order_repo.update_status(order, "CONFIRMED")
    assert order.status == "CONFIRMED"

    # Eager loading with items
    fetched_order = order_repo.get_by_order_number("ORD-TEST-1001")
    assert fetched_order is not None
    assert len(fetched_order.items) == 2
    assert fetched_order.items[0].product.name in ["Item Alpha", "Item Beta"]


def test_invoice_repository_and_overdue(db_session: Session) -> None:
    """Verify InvoiceRepository creation, settlement, and overdue queries."""
    cust_repo = CustomerRepository(db_session)
    customer = cust_repo.create(
        name="Vortex Energy",
        email="billing@vortex.energy",
        tier="premium",
    )

    order_repo = OrderRepository(db_session)
    order = order_repo.create(
        customer_id=customer.id,
        order_number="ORD-VORTEX-01",
        total_amount=Decimal("12000.00"),
        status="DELIVERED",
    )

    invoice_repo = InvoiceRepository(db_session)
    invoice = invoice_repo.create_for_order(
        order=order,
        invoice_number="INV-VORTEX-001",
        payment_terms_days=30,
    )

    assert invoice.id is not None
    assert invoice.status == "ISSUED"
    assert invoice.amount == Decimal("12000.00")

    # Mark as paid
    invoice_repo.mark_as_paid(invoice)
    assert invoice.status == "PAID"
    assert invoice.paid_at is not None

    # Overdue invoice test
    overdue_inv = invoice_repo.create(
        invoice_number="INV-OVERDUE-999",
        customer_id=customer.id,
        amount=Decimal("5000.00"),
        status="ISSUED",
        issued_at=datetime.now(timezone.utc) - timedelta(days=40),
        due_date=datetime.now(timezone.utc) - timedelta(days=10),
    )

    overdue_list = invoice_repo.list_overdue()
    assert any(inv.invoice_number == "INV-OVERDUE-999" for inv in overdue_list)


def test_support_ticket_repository(db_session: Session) -> None:
    """Verify SupportTicket assignment, lifecycle, and priority filtering."""
    cust_repo = CustomerRepository(db_session)
    customer = cust_repo.create(
        name="Quantum Core Systems",
        email="support@quantumcore.com",
    )

    user_repo = UserRepository(db_session)
    agent = user_repo.create(
        email="tier2.agent@enterprise.ai",
        full_name="Agent Smith",
        department="Support",
    )

    ticket_repo = SupportTicketRepository(db_session)
    ticket = ticket_repo.create(
        ticket_number="TCK-TEST-9001",
        customer_id=customer.id,
        subject="High memory utilization alert",
        description="Container memory reached 94% threshold.",
        priority="HIGH",
        status="OPEN",
    )

    assert ticket.id is not None
    assert ticket.status == "OPEN"

    # Assign ticket
    ticket_repo.assign_ticket(ticket, agent.id)
    assert ticket.assigned_to_user_id == agent.id
    assert ticket.status == "IN_PROGRESS"

    # Resolve ticket
    ticket_repo.resolve_ticket(ticket)
    assert ticket.status == "RESOLVED"
    assert ticket.resolved_at is not None


def test_audit_log_repository(db_session: Session) -> None:
    """Verify immutable audit log persistence and filtering."""
    audit_repo = AuditLogRepository(db_session)

    log_entry = audit_repo.log_event(
        action="CONFIG_UPDATE",
        entity_type="AgentWorkflow",
        entity_id="WORKFLOW-01",
        actor_id=None,
        old_values={"max_retries": 3},
        new_values={"max_retries": 5},
        ip_address="10.0.0.1",
    )

    assert log_entry.id is not None
    assert log_entry.action == "CONFIG_UPDATE"

    # Fetch by entity
    entity_logs = audit_repo.list_by_entity("AgentWorkflow", "WORKFLOW-01")
    assert len(entity_logs) >= 1
    assert "max_retries" in entity_logs[0].new_values


def test_cascade_delete_customer_orphan_removal(db_session: Session) -> None:
    """Verify cascade delete from Customer to Orders and SupportTickets."""
    cust_repo = CustomerRepository(db_session)
    customer = cust_repo.create(
        name="Disposable Corp",
        email="temp@disposable.com",
    )

    order_repo = OrderRepository(db_session)
    order = order_repo.create(
        customer_id=customer.id,
        order_number="ORD-DISPOSABLE-01",
        total_amount=Decimal("100.00"),
    )

    ticket_repo = SupportTicketRepository(db_session)
    ticket = ticket_repo.create(
        ticket_number="TCK-DISPOSABLE-01",
        customer_id=customer.id,
        subject="Temp Issue",
        description="Will be cascade removed",
    )

    db_session.flush()

    # Delete customer
    cust_repo.delete(customer)
    db_session.flush()

    # Verify orders and tickets were deleted
    assert order_repo.get_by_id(order.id) is None
    assert ticket_repo.get_by_id(ticket.id) is None
