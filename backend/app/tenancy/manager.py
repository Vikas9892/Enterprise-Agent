"""Tenant management service handling tenant lifecycles, workspaces, and cryptographically hashed API keys."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from app.tenancy.models import (
    ApiKey,
    Tenant,
    TenantConfig,
    TenantPlan,
    Workspace,
)
from app.tenancy.quota import QuotaTracker


def hash_api_key(raw_key: str) -> str:
    """Compute SHA-256 digest of API key secret."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


class TenantManager:
    """Enterprise multi-tenant organizational manager."""

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._workspaces: Dict[str, Workspace] = {}
        # hashed_key -> ApiKey
        self._api_keys: Dict[str, ApiKey] = {}
        self.quota_tracker = QuotaTracker()
        self._seed_default_tenants()

    def _seed_default_tenants(self) -> None:
        """Seed canonical enterprise organizations."""
        default_tenants = [
            Tenant(
                tenant_id="tenant-default",
                name="Enterprise Core Platform",
                slug="enterprise-core",
                plan=TenantPlan.ENTERPRISE,
                config=TenantConfig(
                    max_workspaces=20,
                    monthly_token_budget=10_000_000,
                    monthly_spend_cap_cents=100_000,
                    rate_limit_rpm=1000,
                ),
            ),
            Tenant(
                tenant_id="tenant-apex",
                name="Apex Global Logistics",
                slug="apex-logistics",
                plan=TenantPlan.ENTERPRISE,
                config=TenantConfig(
                    max_workspaces=10,
                    monthly_token_budget=5_000_000,
                    monthly_spend_cap_cents=50_000,
                    rate_limit_rpm=600,
                ),
            ),
            Tenant(
                tenant_id="tenant-novatech",
                name="NovaTech Dynamics",
                slug="novatech-dynamics",
                plan=TenantPlan.ENTERPRISE,
                config=TenantConfig(
                    max_workspaces=15,
                    monthly_token_budget=20_000_000,
                    monthly_spend_cap_cents=200_000,
                    rate_limit_rpm=2000,
                ),
            ),
        ]

        for t in default_tenants:
            self._tenants[t.tenant_id] = t
            # Default workspace
            ws = Workspace(
                workspace_id=f"ws-{t.slug}-prod",
                tenant_id=t.tenant_id,
                name="Production Environment",
                description="Primary live agent workspace",
            )
            self._workspaces[ws.workspace_id] = ws

    def create_tenant(
        self,
        name: str,
        slug: str,
        plan: TenantPlan = TenantPlan.ENTERPRISE,
        config: Optional[TenantConfig] = None,
    ) -> Tenant:
        """Register a new enterprise tenant."""
        tenant = Tenant(
            name=name,
            slug=slug,
            plan=plan,
            config=config or TenantConfig(),
        )
        self._tenants[tenant.tenant_id] = tenant

        # Auto-create default workspace
        ws = Workspace(
            workspace_id=f"ws-{tenant.slug}-default",
            tenant_id=tenant.tenant_id,
            name="Default Workspace",
        )
        self._workspaces[ws.workspace_id] = ws
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Fetch tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Fetch tenant by slug."""
        for t in self._tenants.values():
            if t.slug == slug:
                return t
        return None

    def list_tenants(self) -> List[Tenant]:
        """Return all registered tenants."""
        return list(self._tenants.values())

    def create_workspace(self, tenant_id: str, name: str, description: Optional[str] = None) -> Workspace:
        """Create a workspace within an existing tenant, enforcing limit."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' does not exist")

        existing_count = sum(1 for w in self._workspaces.values() if w.tenant_id == tenant_id)
        if existing_count >= tenant.config.max_workspaces:
            raise ValueError(f"Workspace limit ({tenant.config.max_workspaces}) reached for tenant '{tenant_id}'")

        ws = Workspace(tenant_id=tenant_id, name=name, description=description)
        self._workspaces[ws.workspace_id] = ws
        return ws

    def list_workspaces(self, tenant_id: str) -> List[Workspace]:
        """List all workspaces for a specific tenant."""
        return [w for w in self._workspaces.values() if w.tenant_id == tenant_id]

    def generate_api_key(
        self,
        tenant_id: str,
        name: str,
        workspace_id: Optional[str] = None,
        scopes: Optional[List[str]] = None,
    ) -> Tuple[ApiKey, str]:
        """Generate a cryptographically secure API key and store its hash.

        Returns:
            Tuple of (ApiKey record, raw_secret_key). The raw key is ONLY returned once.
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' not found")

        random_entropy = secrets.token_hex(20)
        raw_key = f"ea_live_{random_entropy}"
        prefix = raw_key[:12] + "..."
        hashed = hash_api_key(raw_key)

        api_key = ApiKey(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=name,
            prefix=prefix,
            hashed_secret=hashed,
            scopes=scopes or ["agent:run", "knowledge:read"],
        )

        self._api_keys[hashed] = api_key
        return api_key, raw_key

    def verify_api_key(self, raw_key: str) -> Optional[Tuple[Tenant, Optional[Workspace], ApiKey]]:
        """Verify raw API key secret against registered SHA-256 hashes.

        Returns:
            Tuple of (Tenant, Workspace, ApiKey) if valid, else None.
        """
        if not raw_key.startswith("ea_live_"):
            return None

        hashed = hash_api_key(raw_key)
        key_record = self._api_keys.get(hashed)
        if not key_record or key_record.is_revoked:
            return None

        # Check expiry
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            return None

        tenant = self.get_tenant(key_record.tenant_id)
        if not tenant or not tenant.is_active:
            return None

        workspace = self._workspaces.get(key_record.workspace_id) if key_record.workspace_id else None

        # Record last used
        key_record.last_used_at = datetime.now(timezone.utc)
        return tenant, workspace, key_record

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key by ID."""
        for key in self._api_keys.values():
            if key.key_id == key_id:
                key.is_revoked = True
                return True
        return False

    def list_api_keys(self, tenant_id: str) -> List[ApiKey]:
        """List active and revoked API keys for a tenant."""
        return [k for k in self._api_keys.values() if k.tenant_id == tenant_id]


# Global singleton instance
tenant_manager = TenantManager()
