"""Centralized governance service orchestrating guardrails, policy engine, and audit logging."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from app.governance.guardrails import (
    PIIMasker,
    PromptInjectionDetector,
    HarmfulContentFilter,
)
from app.governance.policy_engine import (
    PolicyEngine,
    PolicyRule,
    PolicyDecision,
    PolicyVerdict,
)
from app.governance.audit import AuditLogger, AuditEvent


class GovernanceService:
    """Enterprise governance gateway orchestrator."""

    def __init__(self):
        self.pii_masker = PIIMasker()
        self.injection_detector = PromptInjectionDetector()
        self.harm_filter = HarmfulContentFilter()
        self.policy_engine = PolicyEngine()
        self.audit_logger = AuditLogger()

    def inspect_text(self, text: str, tenant_id: str = "tenant-default") -> Dict[str, Any]:
        """Inspect and sanitize input or output text."""
        # 1. PII Redaction
        masked_text, pii_tally = self.pii_masker.mask(text)
        total_pii = sum(pii_tally.values())

        # 2. Prompt Injection Assessment
        injection_result = self.injection_detector.inspect(text)

        # 3. Harm Assessment
        harm_result = self.harm_filter.check(text)

        # Log audit if sensitive items were detected
        if total_pii > 0 or injection_result["is_suspicious"] or not harm_result["is_safe"]:
            self.audit_logger.log_event(
                action_type="guardrail_inspection",
                verdict="threat_detected" if injection_result["is_suspicious"] else "pii_redacted",
                tenant_id=tenant_id,
                rule_triggered="POL-PII-ENFORCE" if total_pii > 0 else "ADVERSARIAL_DEFENSE",
                pii_masked_count=total_pii,
                details={
                    "pii_tally": pii_tally,
                    "injection": injection_result,
                    "harm": harm_result,
                },
            )

        return {
            "original_length": len(text),
            "masked_text": masked_text,
            "pii_detected": total_pii > 0,
            "pii_tally": pii_tally,
            "total_redactions": total_pii,
            "injection_assessment": injection_result,
            "content_safety": harm_result,
        }

    def evaluate_financial_action(
        self,
        action_type: str,
        amount: float,
        tenant_id: str = "tenant-default",
        user_role: str = "support_agent",
        actor: str = "system",
    ) -> PolicyDecision:
        """Evaluate a financial action against active policy rules and audit."""
        decision = self.policy_engine.evaluate_financial_action(
            action_type=action_type,
            amount=amount,
            user_role=user_role,
        )

        self.audit_logger.log_event(
            action_type=action_type,
            verdict=decision.verdict.value,
            tenant_id=tenant_id,
            actor=actor,
            rule_triggered=decision.rule_id,
            details={"amount": amount, "reason": decision.reason},
        )
        return decision

    def evaluate_tool(
        self,
        tool_name: str,
        tenant_id: str = "tenant-default",
        user_role: str = "operator",
        actor: str = "system",
    ) -> PolicyDecision:
        """Evaluate tool execution safety and audit."""
        decision = self.policy_engine.evaluate_tool(tool_name, user_role=user_role)
        if decision.verdict != PolicyVerdict.ALLOW:
            self.audit_logger.log_event(
                action_type=f"tool:{tool_name}",
                verdict=decision.verdict.value,
                tenant_id=tenant_id,
                actor=actor,
                rule_triggered=decision.rule_id,
                details={"reason": decision.reason},
            )
        return decision


# Global singleton instance
governance_service = GovernanceService()
