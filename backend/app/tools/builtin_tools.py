"""Standard local built-in enterprise tools."""

from datetime import datetime, timezone
import math
from typing import Any, Dict


def get_current_datetime() -> Dict[str, Any]:
    """Retrieve current enterprise server UTC timestamp and formatted date."""
    now = datetime.now(timezone.utc)
    return {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S UTC"),
        "timestamp": int(now.timestamp()),
    }


def calculate(expression: str) -> Dict[str, Any]:
    """Safely evaluate mathematical expressions for financial/operational calculation."""
    safe_dict = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        "math": math,
        "sqrt": math.sqrt,
        "ceil": math.ceil,
        "floor": math.floor,
    }
    cleaned = expression.strip()
    forbidden = ["__", "import", "open", "exec", "eval", "globals", "locals", "sys", "os"]
    if any(f in cleaned for f in forbidden):
        return {"error": "Expression contains prohibited identifiers", "is_error": True}

    try:
        res = eval(cleaned, {"__builtins__": {}}, safe_dict)
        return {"expression": expression, "result": res, "is_error": False}
    except Exception as exc:
        return {"error": f"Evaluation error: {str(exc)}", "is_error": True}


def verify_policy_compliance(action_type: str, amount: float = 0.0) -> Dict[str, Any]:
    """Verify enterprise policy compliance for sensitive operations (refunds, escalations)."""
    action = action_type.strip().lower()
    if "refund" in action or "credit" in action:
        if amount > 1000.00:
            return {
                "compliant": False,
                "requires_human_approval": True,
                "reason": f"Refund of ${amount:.2f} exceeds automatic approval threshold ($1,000.00).",
                "recommended_approver": "Finance Director",
            }
        return {
            "compliant": True,
            "requires_human_approval": False,
            "reason": f"Refund of ${amount:.2f} within automatic processing limits.",
        }

    if "cancel" in action:
        return {
            "compliant": False,
            "requires_human_approval": True,
            "reason": "Order cancellations require customer verification checkpoint.",
            "recommended_approver": "Logistics Lead",
        }

    return {"compliant": True, "requires_human_approval": False, "reason": "Standard operational action."}


def get_customer(customer_id: str = "cust-001") -> Dict[str, Any]:
    """Look up enterprise customer profile and account details."""
    customers = {
        "cust-001": {
            "customer_id": "cust-001",
            "name": "Apex Global Logistics",
            "tier": "Enterprise Gold",
            "status": "active",
            "sla": "24/7 Priority",
            "contact_email": "operations@apexlogistics.com",
        },
        "cust-002": {
            "customer_id": "cust-002",
            "name": "NovaTech Dynamics",
            "tier": "Enterprise Platinum",
            "status": "active",
            "sla": "15-minute SLA",
            "contact_email": "support@novatech.io",
        },
        "cust-003": {
            "customer_id": "cust-003",
            "name": "Quantum Enterprises",
            "tier": "Commercial Tier 1",
            "status": "active",
            "sla": "Standard 4-hour SLA",
            "contact_email": "admin@quantumenterprises.com",
        },
    }
    return customers.get(
        customer_id.lower(),
        {
            "customer_id": customer_id,
            "name": "Apex Global Logistics",
            "tier": "Enterprise Gold",
            "status": "active",
            "sla": "24/7 Priority",
        },
    )


def get_order_details(order_number: str = "ORD-2026-9001") -> Dict[str, Any]:
    """Look up enterprise order tracking and shipment line items."""
    return {
        "order_number": order_number,
        "status": "in_transit",
        "carrier": "FedEx Freight",
        "tracking_code": "TRK-9876543210",
        "destination": "Chicago Logistics Hub, IL",
        "items": [
            {"sku": "SKU-SRV-01", "name": "Enterprise Server Node", "quantity": 5, "unit_price": 2850.00}
        ],
        "total_amount": 14250.00,
    }


def check_inventory(sku: str = "SKU-SRV-01") -> Dict[str, Any]:
    """Check inventory stock levels, warehouse, and availability."""
    return {
        "sku": sku,
        "product_name": "Enterprise High-Density Compute Node",
        "in_stock": True,
        "quantity_available": 142,
        "safety_threshold": 25,
        "warehouse": "Chicago Distribution Center Hub 2",
    }


def get_support_ticket(ticket_number: str = "TCK-8801") -> Dict[str, Any]:
    """Look up enterprise customer support ticket history and SLA."""
    return {
        "ticket_number": ticket_number,
        "customer": "David Chen",
        "organization": "Apex Global Logistics",
        "priority": "high",
        "issue": "Delayed Freight Delivery for Server Hardware",
        "status": "investigating",
        "assigned_agent": "Support Specialist Sarah Connor",
    }
