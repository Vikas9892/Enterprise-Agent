"""FastAPI dependencies and middleware for multi-tenant context resolution and quota enforcement."""

from __future__ import annotations

from typing import Optional
from fastapi import Header, HTTPException, Request, status
from app.tenancy.models import Tenant, TenantContext, Workspace
from app.tenancy.manager import tenant_manager
from app.tenancy.quota import RateLimitExceededError, QuotaExceededError


async def get_tenant_context(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    authorization: Optional[str] = Header(None),
) -> TenantContext:
    """Resolve tenant context from Bearer API key or X-Tenant-ID header."""
    # 1. Check Bearer API key first
    if authorization and authorization.startswith("Bearer ea_live_"):
        raw_key = authorization.split("Bearer ", 1)[1].strip()
        auth_tuple = tenant_manager.verify_api_key(raw_key)
        if not auth_tuple:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or revoked API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        tenant, workspace, api_key = auth_tuple

        # Check rate limits
        try:
            tenant_manager.quota_tracker.check_and_record_request(tenant)
        except RateLimitExceededError as rle:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(rle),
            )

        ctx = TenantContext(tenant=tenant, workspace=workspace, api_key=api_key, authenticated=True)
        request.state.tenant_context = ctx
        return ctx

    # 2. Check X-Tenant-ID header
    if x_tenant_id:
        tenant = tenant_manager.get_tenant(x_tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{x_tenant_id}' not found",
            )
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant '{x_tenant_id}' is deactivated",
            )

        try:
            tenant_manager.quota_tracker.check_and_record_request(tenant)
        except RateLimitExceededError as rle:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(rle),
            )

        ctx = TenantContext(tenant=tenant, authenticated=True)
        request.state.tenant_context = ctx
        return ctx

    # 3. Default fallback to core tenant for backward compatibility
    default_tenant = tenant_manager.get_tenant("tenant-default")
    if not default_tenant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Default enterprise tenant is uninitialized",
        )

    ctx = TenantContext(tenant=default_tenant, authenticated=True)
    request.state.tenant_context = ctx
    return ctx
