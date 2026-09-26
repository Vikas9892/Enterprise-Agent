"""Seed script populating database with realistic enterprise demo data."""

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database.session import get_engine, get_session_factory
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
)


def seed_database(session: Session) -> None:
    """Populate database with comprehensive domain data."""
    # Check if already seeded
    if session.query(User).first():
        print("Database already contains data. Skipping seed.")
        return

    print("Seeding Enterprise Agentic Platform database...")

    # 1. Permissions
    permissions_data = [
        ("users:read", "users", "read", "View user accounts and profiles"),
        ("users:write", "users", "write", "Create and modify user accounts"),
        ("roles:manage", "roles", "manage", "Assign and modify security roles"),
        ("customers:read", "customers", "read", "View enterprise customer records"),
        ("customers:write", "customers", "write", "Create and modify customer accounts"),
        ("products:read", "products", "read", "View product catalog"),
        ("products:write", "products", "write", "Modify products and catalog"),
        ("inventory:manage", "inventory", "manage", "Update warehouse stock levels"),
        ("orders:read", "orders", "read", "View sales orders and items"),
        ("orders:write", "orders", "write", "Place and update sales orders"),
        ("invoices:read", "invoices", "read", "View invoices and payment receipts"),
        ("invoices:write", "invoices", "write", "Issue and settle customer invoices"),
        ("support:read", "support", "read", "View customer support tickets"),
        ("support:write", "support", "write", "Assign and resolve support tickets"),
        ("audit:read", "audit", "read", "Inspect compliance and action audit trail"),
    ]

    perms_by_name = {}
    for name, res, act, desc in permissions_data:
        perm = Permission(name=name, resource=res, action=act, description=desc)
        session.add(perm)
        perms_by_name[name] = perm

    session.flush()

    # 2. Roles
    admin_role = Role(
        name="SuperAdmin",
        description="Full system administrative privileges across all modules",
        is_system_role=True,
    )
    admin_role.permissions = list(perms_by_name.values())

    ops_role = Role(
        name="OperationsManager",
        description="Manages product catalog, warehouse inventory, and order fulfillment",
    )
    ops_role.permissions = [
        perms_by_name["products:read"],
        perms_by_name["products:write"],
        perms_by_name["inventory:manage"],
        perms_by_name["orders:read"],
        perms_by_name["orders:write"],
        perms_by_name["customers:read"],
    ]

    support_role = Role(
        name="CustomerSupport",
        description="Assigned to support tickets and responds to enterprise clients",
    )
    support_role.permissions = [
        perms_by_name["support:read"],
        perms_by_name["support:write"],
        perms_by_name["customers:read"],
        perms_by_name["orders:read"],
    ]

    sales_role = Role(
        name="SalesRepresentative",
        description="Manages customer accounts, initiates orders, and inspects invoices",
    )
    sales_role.permissions = [
        perms_by_name["customers:read"],
        perms_by_name["customers:write"],
        perms_by_name["orders:read"],
        perms_by_name["orders:write"],
        perms_by_name["products:read"],
        perms_by_name["invoices:read"],
    ]

    auditor_role = Role(
        name="ComplianceAuditor",
        description="Read-only visibility for security, compliance, and financial records",
    )
    auditor_role.permissions = [
        perms_by_name["audit:read"],
        perms_by_name["users:read"],
        perms_by_name["orders:read"],
        perms_by_name["invoices:read"],
    ]

    session.add_all([admin_role, ops_role, support_role, sales_role, auditor_role])
    session.flush()

    # 3. Users with distinct roles
    user_admin = User(
        email="admin@enterprise.ai",
        full_name="Alexander Vance",
        department="Engineering",
        is_superuser=True,
        roles=[admin_role],
    )
    user_ops = User(
        email="sarah.jenkins@enterprise.ai",
        full_name="Sarah Jenkins",
        department="Operations",
        roles=[ops_role],
    )
    user_support = User(
        email="mike.chen@enterprise.ai",
        full_name="Michael Chen",
        department="Customer Success",
        roles=[support_role],
    )
    user_sales = User(
        email="elena.rostova@enterprise.ai",
        full_name="Elena Rostova",
        department="Enterprise Sales",
        roles=[sales_role],
    )
    user_auditor = User(
        email="marcus.wright@enterprise.ai",
        full_name="Marcus Wright",
        department="Risk & Compliance",
        roles=[auditor_role],
    )

    session.add_all([user_admin, user_ops, user_support, user_sales, user_auditor])
    session.flush()

    # 4. Customers
    cust_acme = Customer(
        name="Acme Technologies Inc.",
        email="procurement@acme-tech.com",
        company="Acme Corporation",
        phone="+1-415-555-0101",
        tier="enterprise",
        address="100 Mission Street, Suite 2400",
        city="San Francisco",
        country="USA",
    )
    cust_nova = Customer(
        name="Nova Robotics Ltd.",
        email="ai-systems@novarobotics.de",
        company="Nova Robotics Europe",
        phone="+49-89-2000-4100",
        tier="enterprise",
        address="Industriestrasse 14",
        city="Munich",
        country="Germany",
    )
    cust_global = Customer(
        name="Global Logistics Partners",
        email="it@globallogistics.co.uk",
        company="Global Logistics Group",
        phone="+44-20-7946-0950",
        tier="premium",
        address="45 Canary Wharf Tower",
        city="London",
        country="UK",
    )
    cust_apex = Customer(
        name="Apex Healthcare Systems",
        email="digital@apexhealth.org",
        company="Apex Health Group",
        phone="+1-617-555-0188",
        tier="enterprise",
        address="300 Longwood Avenue",
        city="Boston",
        country="USA",
    )

    session.add_all([cust_acme, cust_nova, cust_global, cust_apex])
    session.flush()

    # 5. Products & Inventory
    now = datetime.now(timezone.utc)

    prod_h100 = Product(
        sku="GPU-H100-POD",
        name="NVIDIA H100 8-GPU Compute Pod",
        category="Hardware",
        unit_price=Decimal("285000.00"),
        description="Dedicated liquid-cooled 8x SXM5 H100 80GB enterprise training pod.",
    )
    session.add(prod_h100)
    session.flush()
    inv_h100 = Inventory(
        product_id=prod_h100.id,
        quantity_on_hand=8,
        quantity_reserved=2,
        reorder_threshold=3,
        warehouse_location="WH-WEST-01",
        last_restocked_at=now - timedelta(days=10),
    )

    prod_a100 = Product(
        sku="GPU-A100-POD",
        name="NVIDIA A100 8-GPU Inference Cluster",
        category="Hardware",
        unit_price=Decimal("165000.00"),
        description="High-throughput 8x A100 80GB inference pod for fine-tuned LLMs.",
    )
    session.add(prod_a100)
    session.flush()
    inv_a100 = Inventory(
        product_id=prod_a100.id,
        quantity_on_hand=15,
        quantity_reserved=4,
        reorder_threshold=5,
        warehouse_location="WH-EAST-02",
        last_restocked_at=now - timedelta(days=14),
    )

    prod_sw_license = Product(
        sku="SW-ENT-AGENT-100",
        name="Enterprise Agent Platform (100 Seat License)",
        category="Software",
        unit_price=Decimal("12500.00"),
        description="Annual enterprise subscription including LiteLLM proxy and LangSmith trace exports.",
    )
    session.add(prod_sw_license)
    session.flush()
    inv_sw = Inventory(
        product_id=prod_sw_license.id,
        quantity_on_hand=500,
        quantity_reserved=0,
        reorder_threshold=20,
        warehouse_location="WH-DIGITAL",
        last_restocked_at=now,
    )

    prod_mcp_appliance = Product(
        sku="APPL-MCP-GATEWAY-PRO",
        name="Model Context Protocol Edge Appliance",
        category="Hardware",
        unit_price=Decimal("9500.00"),
        description="1U rackmount secure MCP protocol proxy with local SQLite/Redis caching.",
    )
    session.add(prod_mcp_appliance)
    session.flush()
    inv_mcp = Inventory(
        product_id=prod_mcp_appliance.id,
        quantity_on_hand=40,
        quantity_reserved=5,
        reorder_threshold=10,
        warehouse_location="WH-WEST-01",
        last_restocked_at=now - timedelta(days=5),
    )

    session.add_all([inv_h100, inv_a100, inv_sw, inv_mcp])
    session.flush()

    # 6. Orders and OrderItems
    order1 = Order(
        order_number="ORD-2026-0001",
        customer_id=cust_acme.id,
        status="DELIVERED",
        total_amount=Decimal("297500.00"),
        currency="USD",
        notes="Expedited delivery to Sunnyvale Data Center.",
        placed_at=now - timedelta(days=20),
    )
    session.add(order1)
    session.flush()

    item1_1 = OrderItem(
        order_id=order1.id,
        product_id=prod_h100.id,
        quantity=1,
        unit_price=Decimal("285000.00"),
        subtotal=Decimal("285000.00"),
    )
    item1_2 = OrderItem(
        order_id=order1.id,
        product_id=prod_sw_license.id,
        quantity=1,
        unit_price=Decimal("12500.00"),
        subtotal=Decimal("12500.00"),
    )

    order2 = Order(
        order_number="ORD-2026-0002",
        customer_id=cust_nova.id,
        status="CONFIRMED",
        total_amount=Decimal("349000.00"),
        currency="USD",
        notes="Scheduled deployment for Frankfurt staging lab.",
        placed_at=now - timedelta(days=4),
    )
    session.add(order2)
    session.flush()

    item2_1 = OrderItem(
        order_id=order2.id,
        product_id=prod_a100.id,
        quantity=2,
        unit_price=Decimal("165000.00"),
        subtotal=Decimal("330000.00"),
    )
    item2_2 = OrderItem(
        order_id=order2.id,
        product_id=prod_mcp_appliance.id,
        quantity=2,
        unit_price=Decimal("9500.00"),
        subtotal=Decimal("19000.00"),
    )

    order3 = Order(
        order_number="ORD-2026-0003",
        customer_id=cust_apex.id,
        status="PROCESSING",
        total_amount=Decimal("22000.00"),
        currency="USD",
        notes="Clinical trial LLM deployment.",
        placed_at=now - timedelta(days=1),
    )
    session.add(order3)
    session.flush()

    item3_1 = OrderItem(
        order_id=order3.id,
        product_id=prod_sw_license.id,
        quantity=1,
        unit_price=Decimal("12500.00"),
        subtotal=Decimal("12500.00"),
    )
    item3_2 = OrderItem(
        order_id=order3.id,
        product_id=prod_mcp_appliance.id,
        quantity=1,
        unit_price=Decimal("9500.00"),
        subtotal=Decimal("9500.00"),
    )

    session.add_all([item1_1, item1_2, item2_1, item2_2, item3_1, item3_2])
    session.flush()

    # 7. Invoices
    inv1 = Invoice(
        invoice_number="INV-2026-0001",
        customer_id=cust_acme.id,
        order_id=order1.id,
        amount=Decimal("297500.00"),
        currency="USD",
        status="PAID",
        issued_at=now - timedelta(days=20),
        due_date=now + timedelta(days=10),
        paid_at=now - timedelta(days=12),
    )
    inv2 = Invoice(
        invoice_number="INV-2026-0002",
        customer_id=cust_nova.id,
        order_id=order2.id,
        amount=Decimal("349000.00"),
        currency="USD",
        status="ISSUED",
        issued_at=now - timedelta(days=4),
        due_date=now + timedelta(days=26),
    )
    inv3 = Invoice(
        invoice_number="INV-2026-0003",
        customer_id=cust_global.id,
        order_id=None,
        amount=Decimal("45000.00"),
        currency="USD",
        status="OVERDUE",
        issued_at=now - timedelta(days=45),
        due_date=now - timedelta(days=15),
    )

    session.add_all([inv1, inv2, inv3])
    session.flush()

    # 8. Support Tickets
    ticket1 = SupportTicket(
        ticket_number="TCK-2026-0001",
        customer_id=cust_acme.id,
        assigned_to_user_id=user_support.id,
        subject="Cluster latency spike during high-throughput inference batch",
        description="Observed P99 latency exceeding 450ms when batch size surpasses 128 on H100 pod.",
        status="RESOLVED",
        priority="CRITICAL",
        created_at=now - timedelta(days=8),
        resolved_at=now - timedelta(days=7),
    )
    ticket2 = SupportTicket(
        ticket_number="TCK-2026-0002",
        customer_id=cust_nova.id,
        assigned_to_user_id=user_support.id,
        subject="Requesting custom tool schema validation for MCP server",
        description="Need guidance configuring FastMCP endpoints to interface with our internal ROS2 node.",
        status="IN_PROGRESS",
        priority="HIGH",
        created_at=now - timedelta(days=2),
    )
    ticket3 = SupportTicket(
        ticket_number="TCK-2026-0003",
        customer_id=cust_global.id,
        assigned_to_user_id=None,
        subject="Billing inquiries for overdue retainer balance",
        description="Requesting remittance address verification for wire transfer.",
        status="OPEN",
        priority="MEDIUM",
        created_at=now - timedelta(hours=6),
    )

    session.add_all([ticket1, ticket2, ticket3])
    session.flush()

    # 9. Audit Logs
    audit1 = AuditLog(
        actor_id=user_admin.id,
        action="SYSTEM_INIT",
        entity_type="System",
        entity_id="ROOT",
        new_values='{"status": "provisioned", "environment": "development"}',
        ip_address="127.0.0.1",
        user_agent="SystemProvisioner/1.0",
        created_at=now - timedelta(days=30),
    )
    audit2 = AuditLog(
        actor_id=user_sales.id,
        action="ORDER_CREATE",
        entity_type="Order",
        entity_id=order1.order_number,
        new_values=f'{{"total": {order1.total_amount}, "customer_id": {cust_acme.id}}}',
        ip_address="192.168.1.45",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        created_at=order1.placed_at,
    )
    audit3 = AuditLog(
        actor_id=user_support.id,
        action="TICKET_RESOLVE",
        entity_type="SupportTicket",
        entity_id=ticket1.ticket_number,
        new_values='{"status": "RESOLVED", "resolution": "Kernel parameter tuning applied"}',
        ip_address="192.168.1.60",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        created_at=ticket1.resolved_at or now,
    )

    session.add_all([audit1, audit2, audit3])
    session.commit()

    print("Database successfully seeded with realistic enterprise records!")


if __name__ == "__main__":
    engine = get_engine()
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        seed_database(session)
