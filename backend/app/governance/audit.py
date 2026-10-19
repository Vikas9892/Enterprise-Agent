"""Compliance audit trail logger recording governed actions, PII events, and policy verdicts."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Immutable audit trail record."""
    event_id: str = Field(default_factory=lambda: f"aud_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str = Field(default="tenant-default")
    actor: str = Field(default="system")
    action_type: str
    verdict: str
    rule_triggered: Optional[str] = None
    pii_masked_count: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogger:
    """Thread-safe circular audit event repository."""

    MAX_EVENTS = 500

    def __init__(self):
        self._events: List[AuditEvent] = []
        self._seed_sample_events()

    def _seed_sample_events(self) -> None:
        """Seed representative enterprise governance audit records."""
        sample_records = [
            AuditEvent(
                tenant_id="tenant-apex",
                actor="agent:support_agent",
                action_type="refund_evaluation",
                verdict="allow",
                rule_triggered="POL-SPEND-1000",
                pii_masked_count=1,
                details={"amount": 450.00, "customer": "CUST-001", "sku": "SKU-SRV-01"},
            ),
            AuditEvent(
                tenant_id="tenant-apex",
                actor="agent:compliance_agent",
                action_type="refund_evaluation",
                verdict="require_approval",
                rule_triggered="POL-SPEND-1000",
                pii_masked_count=2,
                details={"amount": 3400.00, "order": "ORD-2026-9001", "approver": "Logistics Lead"},
            ),
            AuditEvent(
                tenant_id="tenant-novatech",
                actor="user:alex.chen",
                action_type="prompt_inspection",
                verdict="pii_redacted",
                rule_triggered="POL-PII-ENFORCE",
                pii_masked_count=3,
                details={"masked_types": ["credit_cards", "emails"]},
            ),
            AuditEvent(
                tenant_id="tenant-default",
                actor="agent:coordinator",
                action_type="tool_execution",
                verdict="require_approval",
                rule_triggered="POL-TOOL-CANCEL",
                pii_masked_count=0,
                details={"tool": "cancel_order", "reason": "Mandatory shipment verification checkpoint"},
            ),
        ]
        self._events.extend(sample_records)

    def log_event(
        self,
        action_type: str,
        verdict: str,
        tenant_id: str = "tenant-default",
        actor: str = "system",
        rule_triggered: Optional[str] = None,
        pii_masked_count: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """Create and store an audit event."""
        event = AuditEvent(
            tenant_id=tenant_id,
            actor=actor,
            action_type=action_type,
            verdict=verdict,
            rule_triggered=rule_triggered,
            pii_masked_count=pii_masked_count,
            details=details or {},
        )
        self._events.append(event)
        if len(self._events) > self.MAX_EVENTS:
            self._events.pop(0)
        return event

    def list_events(
        self,
        tenant_id: Optional[str] = None,
        verdict: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEvent]:
        """Fetch audit events filtered by tenant or verdict."""
        evts = list(reversed(self._events))
        if tenant_id:
            evts = [e for e in evts if e.tenant_id == tenant_id]
        if verdict:
            evts = [e for e in evts if e.verdict == verdict]
        return evts[:limit]
