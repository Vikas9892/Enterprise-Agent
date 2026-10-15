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

    if "cancel_order" in action:
        return {
            "compliant": False,
            "requires_human_approval": True,
            "reason": "Order cancellations require customer verification checkpoint.",
            "recommended_approver": "Logistics Lead",
        }

    return {"compliant": True, "requires_human_approval": False, "reason": "Standard operational action."}
