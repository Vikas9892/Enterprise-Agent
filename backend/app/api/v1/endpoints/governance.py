"""API v1 endpoints for Enterprise Governance, Guardrails, Policies, and Audit Logging."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from app.governance.policy_engine import PolicyRule
from app.governance.audit import AuditEvent
from app.governance.service import governance_service
from app.tenancy.manager import tenant_manager

router = APIRouter()


class InspectTextRequest(BaseModel):
    text: str = Field(..., description="Prompt or response text to sanitize and evaluate")
    tenant_id: str = Field(default="tenant-default", description="Associated tenant workspace")


class UpdatePolicyRequest(BaseModel):
    is_active: Optional[bool] = None
    threshold_amount: Optional[float] = None


class GenerateApiKeyRequest(BaseModel):
    tenant_id: str
    name: str
    workspace_id: Optional[str] = None
    scopes: List[str] = Field(default_factory=lambda: ["agent:run", "knowledge:read"])


@router.get(
    "/policies",
    response_model=List[PolicyRule],
    summary="List all enterprise dynamic policy rules",
)
async def list_policies() -> List[PolicyRule]:
    return governance_service.policy_engine.list_rules()


@router.put(
    "/policies/{rule_id}",
    response_model=PolicyRule,
    summary="Update or toggle an enterprise policy rule",
)
async def update_policy(rule_id: str, req: UpdatePolicyRequest) -> PolicyRule:
    rule = governance_service.policy_engine.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy rule not found")

    if req.is_active is not None:
        governance_service.policy_engine.toggle_rule(rule_id, req.is_active)
    if req.threshold_amount is not None:
        governance_service.policy_engine.update_rule_threshold(rule_id, req.threshold_amount)

    return governance_service.policy_engine.get_rule(rule_id)  # type: ignore


@router.post(
    "/guardrails/inspect",
    summary="Inspect text for PII, adversarial prompt injection, and harmful instructions",
)
async def inspect_text(req: InspectTextRequest) -> Dict[str, Any]:
    return governance_service.inspect_text(req.text, tenant_id=req.tenant_id)


@router.get(
    "/audit-log",
    response_model=List[AuditEvent],
    summary="Retrieve compliance audit trail events",
)
async def get_audit_log(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    verdict: Optional[str] = Query(None, description="Filter by verdict"),
    limit: int = Query(50, ge=1, le=200),
) -> List[AuditEvent]:
    return governance_service.audit_logger.list_events(tenant_id=tenant_id, verdict=verdict, limit=limit)


@router.get(
    "/tenants",
    summary="List all enterprise tenants with quota and workspace summaries",
)
async def list_tenants_summary() -> List[Dict[str, Any]]:
    tenants = tenant_manager.list_tenants()
    results = []
    for t in tenants:
        workspaces = tenant_manager.list_workspaces(t.tenant_id)
        quota = tenant_manager.quota_tracker.get_quota(t.tenant_id)
        keys = tenant_manager.list_api_keys(t.tenant_id)
        results.append({
            "tenant_id": t.tenant_id,
            "name": t.name,
            "slug": t.slug,
            "plan": t.plan.value,
            "is_active": t.is_active,
            "config": t.config.model_dump(),
            "workspaces_count": len(workspaces),
            "workspaces": [w.model_dump() for w in workspaces],
            "api_keys_count": len(keys),
            "api_keys": [
                {
                    "key_id": k.key_id,
                    "name": k.name,
                    "prefix": k.prefix,
                    "scopes": k.scopes,
                    "is_revoked": k.is_revoked,
                    "created_at": k.created_at.isoformat(),
                    "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                }
                for k in keys
            ],
            "quota_usage": {
                "current_tokens": quota.current_tokens,
                "current_spend_cents": quota.current_spend_cents,
                "total_requests": quota.total_requests,
                "token_budget": t.config.monthly_token_budget,
                "spend_cap_cents": t.config.monthly_spend_cap_cents,
                "rate_limit_rpm": t.config.rate_limit_rpm,
            },
        })
    return results


@router.post(
    "/api-keys",
    summary="Generate a new enterprise API key for a tenant",
)
async def generate_api_key(req: GenerateApiKeyRequest) -> Dict[str, Any]:
    try:
        api_key, raw_secret = tenant_manager.generate_api_key(
            tenant_id=req.tenant_id,
            name=req.name,
            workspace_id=req.workspace_id,
            scopes=req.scopes,
        )
        return {
            "key_id": api_key.key_id,
            "tenant_id": api_key.tenant_id,
            "name": api_key.name,
            "prefix": api_key.prefix,
            "scopes": api_key.scopes,
            "raw_secret": raw_secret,  # Note: ONLY shown on creation
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/api-keys/{key_id}",
    summary="Revoke an enterprise API key",
)
async def revoke_api_key(key_id: str) -> Dict[str, Any]:
    revoked = tenant_manager.revoke_api_key(key_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked successfully", "key_id": key_id}
