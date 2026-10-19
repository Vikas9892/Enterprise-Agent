"""Data models and schemas for multi-tenant isolation, workspaces, and API keys."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TenantPlan(str, Enum):
    """Subscription tiers governing rate limits and quotas."""
    COMMUNITY = "community"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class TenantConfig(BaseModel):
    """Quota and concurrency configuration thresholds for a tenant."""
    max_workspaces: int = Field(default=10)
    monthly_token_budget: int = Field(default=5_000_000)
    monthly_spend_cap_cents: int = Field(default=50_000)  # $500.00
    rate_limit_rpm: int = Field(default=600)  # requests per minute
    allowed_models: List[str] = Field(default_factory=lambda: ["gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"])
    enforce_pii_masking: bool = Field(default=True)


class Tenant(BaseModel):
    """Top-level enterprise organizational boundary."""
    tenant_id: str = Field(default_factory=lambda: f"ten_{uuid.uuid4().hex[:10]}")
    name: str = Field(..., description="Organization or customer company name")
    slug: str = Field(..., description="URL and identifier safe slug")
    plan: TenantPlan = Field(default=TenantPlan.ENTERPRISE)
    is_active: bool = Field(default=True)
    config: TenantConfig = Field(default_factory=TenantConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Workspace(BaseModel):
    """Sub-division or project environment within a tenant organization."""
    workspace_id: str = Field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:10]}")
    tenant_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApiKey(BaseModel):
    """Hashed authentication credential with fine-grained authorization scopes."""
    key_id: str = Field(default_factory=lambda: f"key_{uuid.uuid4().hex[:10]}")
    tenant_id: str
    workspace_id: Optional[str] = None
    name: str
    prefix: str = Field(description="First 10 chars e.g. ea_live_ab12...")
    hashed_secret: str
    scopes: List[str] = Field(default_factory=lambda: ["agent:run", "knowledge:read"])
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class TenantQuota(BaseModel):
    """Current rolling usage metrics and consumption tallies for a tenant."""
    tenant_id: str
    current_tokens: int = 0
    current_spend_cents: int = 0
    current_rpm: int = 0
    active_workspaces: int = 0
    total_requests: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenantContext(BaseModel):
    """Resolved tenant runtime context for incoming HTTP request."""
    tenant: Tenant
    workspace: Optional[Workspace] = None
    api_key: Optional[ApiKey] = None
    authenticated: bool = True
