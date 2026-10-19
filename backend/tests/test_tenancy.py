"""Unit and integration tests for multi-tenancy, workspaces, API keys, and quotas."""

import pytest
from app.tenancy.models import TenantPlan, TenantConfig
from app.tenancy.manager import TenantManager
from app.tenancy.quota import QuotaTracker, RateLimitExceededError, QuotaExceededError


def test_tenant_creation_and_workspaces():
    mgr = TenantManager()

    # Seeded tenants exist
    default_tenant = mgr.get_tenant("tenant-default")
    assert default_tenant is not None
    assert default_tenant.name == "Enterprise Core Platform"

    # Create new tenant
    tenant = mgr.create_tenant(
        name="Acme Corp",
        slug="acme-corp",
        plan=TenantPlan.ENTERPRISE,
        config=TenantConfig(max_workspaces=2),
    )
    assert tenant.tenant_id.startswith("ten_")
    assert tenant.slug == "acme-corp"

    # Default workspace created
    workspaces = mgr.list_workspaces(tenant.tenant_id)
    assert len(workspaces) == 1

    # Create 2nd workspace
    ws2 = mgr.create_workspace(tenant.tenant_id, "Staging Environment")
    assert ws2.name == "Staging Environment"

    # 3rd workspace should exceed limit of 2
    with pytest.raises(ValueError, match="Workspace limit"):
        mgr.create_workspace(tenant.tenant_id, "Dev Environment")


def test_api_key_generation_and_verification():
    mgr = TenantManager()
    tenant = mgr.get_tenant("tenant-apex")
    assert tenant is not None

    # Generate API key
    key_record, raw_key = mgr.generate_api_key(
        tenant_id=tenant.tenant_id,
        name="Production CI Key",
        scopes=["agent:run", "knowledge:read"],
    )

    assert raw_key.startswith("ea_live_")
    assert key_record.prefix.startswith("ea_live_")
    assert key_record.hashed_secret != raw_key

    # Verification success
    verified = mgr.verify_api_key(raw_key)
    assert verified is not None
    v_tenant, v_ws, v_key = verified
    assert v_tenant.tenant_id == tenant.tenant_id
    assert v_key.key_id == key_record.key_id

    # Verification failure on tampered key
    tampered_key = raw_key + "_invalid"
    assert mgr.verify_api_key(tampered_key) is None

    # Revocation
    assert mgr.revoke_api_key(key_record.key_id) is True
    assert mgr.verify_api_key(raw_key) is None


def test_quota_tracker_rate_limiting_and_token_budget():
    tracker = QuotaTracker()
    tenant = TenantManager().get_tenant("tenant-default")
    assert tenant is not None

    # Artificially set small limits for testing
    tenant.config.rate_limit_rpm = 3
    tenant.config.monthly_token_budget = 1000

    # 1. Test RPM rate limit
    tracker.check_and_record_request(tenant)
    tracker.check_and_record_request(tenant)
    tracker.check_and_record_request(tenant)

    # 4th request exceeds RPM limit of 3
    with pytest.raises(RateLimitExceededError):
        tracker.check_and_record_request(tenant)

    # 2. Test Token Budget
    tracker.record_usage(tenant, tokens=400)
    tracker.record_usage(tenant, tokens=500)

    # Next 200 tokens exceed 1000 budget (900 + 200 = 1100)
    with pytest.raises(QuotaExceededError, match="token budget"):
        tracker.record_usage(tenant, tokens=200)
