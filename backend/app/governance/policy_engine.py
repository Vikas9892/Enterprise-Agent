"""Dynamic enterprise policy rule engine for RBAC, financial thresholds, and tool governance."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyRuleType(str, Enum):
    FINANCIAL_SPEND = "financial_spend"
    TOOL_ACCESS = "tool_access"
    PII_MASKING = "pii_masking"
    HITL_APPROVAL = "hitl_approval"


class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REQUIRE_APPROVAL = "require_approval"


class PolicyRule(BaseModel):
    """Configurable enterprise policy rule."""
    rule_id: str
    name: str
    description: str
    rule_type: PolicyRuleType
    is_active: bool = True
    threshold_amount: Optional[float] = None
    allowed_roles: List[str] = Field(default_factory=list)
    restricted_tools: List[str] = Field(default_factory=list)
    approver_role: Optional[str] = None


class PolicyDecision(BaseModel):
    """The outcome of evaluating an action or tool against active enterprise policies."""
    verdict: PolicyVerdict
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    reason: str
    recommended_approver: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PolicyEngine:
    """Evaluates enterprise policy rules in real-time."""

    def __init__(self):
        self._rules: Dict[str, PolicyRule] = {}
        self._seed_default_rules()

    def _seed_default_rules(self) -> None:
        """Initialize standard enterprise governance rules."""
        rules = [
            PolicyRule(
                rule_id="POL-SPEND-1000",
                name="Tier 1 Financial Threshold Checkpoint",
                description="Refunds and credits between $1,000 and $10,000 require Human-In-The-Loop approval.",
                rule_type=PolicyRuleType.FINANCIAL_SPEND,
                is_active=True,
                threshold_amount=1000.0,
                approver_role="Logistics Lead / Support Manager",
            ),
            PolicyRule(
                rule_id="POL-SPEND-10000",
                name="Executive Financial Cap Policy",
                description="Financial actions exceeding $10,000 are blocked unless invoked by Finance Director.",
                rule_type=PolicyRuleType.FINANCIAL_SPEND,
                is_active=True,
                threshold_amount=10000.0,
                allowed_roles=["finance_director", "super_admin"],
                approver_role="Finance Director",
            ),
            PolicyRule(
                rule_id="POL-TOOL-CANCEL",
                name="Order Cancellation Safety Checkpoint",
                description="Direct cancellation of orders in transit requires operator checkpoint verification.",
                rule_type=PolicyRuleType.HITL_APPROVAL,
                is_active=True,
                restricted_tools=["cancel_order"],
                approver_role="Fulfillment Supervisor",
            ),
            PolicyRule(
                rule_id="POL-PII-ENFORCE",
                name="GDPR & CCPA Mandatory PII Redaction",
                description="Automatically redact credit cards, SSNs, phone numbers, and emails in telemetry and prompts.",
                rule_type=PolicyRuleType.PII_MASKING,
                is_active=True,
            ),
        ]
        for r in rules:
            self._rules[r.rule_id] = r

    def evaluate_financial_action(
        self,
        action_type: str,
        amount: float,
        user_role: str = "support_agent",
    ) -> PolicyDecision:
        """Evaluate a financial operation (refund, credit, invoice adjustment)."""
        clean_action = action_type.lower()
        is_financial = any(k in clean_action for k in ["refund", "credit", "payout", "reimbursement"])

        if not is_financial:
            return PolicyDecision(verdict=PolicyVerdict.ALLOW, reason="Non-financial action authorized.")

        # Check Executive Cap ($10,000)
        rule_exec = self._rules.get("POL-SPEND-10000")
        if rule_exec and rule_exec.is_active and amount > (rule_exec.threshold_amount or 10000.0):
            if user_role not in rule_exec.allowed_roles:
                return PolicyDecision(
                    verdict=PolicyVerdict.BLOCK,
                    rule_id=rule_exec.rule_id,
                    rule_name=rule_exec.name,
                    reason=f"Action amount (${amount:,.2f}) exceeds executive cap ($10,000.00). Restricted to Finance Director.",
                    recommended_approver=rule_exec.approver_role,
                )

        # Check Tier 1 Checkpoint ($1,000)
        rule_tier1 = self._rules.get("POL-SPEND-1000")
        if rule_tier1 and rule_tier1.is_active and amount > (rule_tier1.threshold_amount or 1000.0):
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                rule_id=rule_tier1.rule_id,
                rule_name=rule_tier1.name,
                reason=f"Action amount (${amount:,.2f}) exceeds autonomous limit ($1,000.00). Requires human approval.",
                recommended_approver=rule_tier1.approver_role,
            )

        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            reason=f"Financial action (${amount:,.2f}) within autonomous approval limits.",
        )

    def evaluate_tool(self, tool_name: str, user_role: str = "operator") -> PolicyDecision:
        """Evaluate tool execution safety and restrictions."""
        rule_cancel = self._rules.get("POL-TOOL-CANCEL")
        if rule_cancel and rule_cancel.is_active and tool_name in rule_cancel.restricted_tools:
            return PolicyDecision(
                verdict=PolicyVerdict.REQUIRE_APPROVAL,
                rule_id=rule_cancel.rule_id,
                rule_name=rule_cancel.name,
                reason=f"Execution of sensitive tool '{tool_name}' requires human operator confirmation.",
                recommended_approver=rule_cancel.approver_role,
            )

        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            reason=f"Tool '{tool_name}' cleared for execution.",
        )

    def list_rules(self) -> List[PolicyRule]:
        """List all policy rules."""
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        return self._rules.get(rule_id)

    def toggle_rule(self, rule_id: str, is_active: bool) -> Optional[PolicyRule]:
        """Activate or deactivate a policy rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.is_active = is_active
        return rule

    def update_rule_threshold(self, rule_id: str, new_threshold: float) -> Optional[PolicyRule]:
        """Modify numeric limit threshold for a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.threshold_amount = new_threshold
        return rule
