"""Tenant quota tracking, sliding window rate limiting, and consumption monitoring."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Dict, List, Optional
from app.tenancy.models import Tenant, TenantQuota


class RateLimitExceededError(Exception):
    """Raised when tenant exceeds maximum requests per minute."""
    def __init__(self, tenant_id: str, limit: int, current: int):
        super().__init__(f"Tenant '{tenant_id}' rate limit exceeded ({current}/{limit} req/min)")
        self.tenant_id = tenant_id
        self.limit = limit
        self.current = current


class QuotaExceededError(Exception):
    """Raised when tenant exceeds monthly token or spend budget."""
    def __init__(self, tenant_id: str, quota_type: str, limit: int, current: int):
        super().__init__(f"Tenant '{tenant_id}' exceeded {quota_type} budget ({current}/{limit})")
        self.tenant_id = tenant_id
        self.quota_type = quota_type
        self.limit = limit
        self.current = current


class QuotaTracker:
    """Tracks per-tenant requests, tokens, and financial budgets."""

    def __init__(self):
        # tenant_id -> list of unix timestamps (within last 60 seconds)
        self._request_windows: Dict[str, List[float]] = defaultdict(list)
        # tenant_id -> TenantQuota
        self._quotas: Dict[str, TenantQuota] = defaultdict(lambda: TenantQuota(tenant_id=""))

    def check_and_record_request(self, tenant: Tenant) -> int:
        """Check rate limit window and record new request. Returns current RPM."""
        tid = tenant.tenant_id
        now = time.time()
        window = self._request_windows[tid]

        # Evict timestamps older than 60 seconds
        cutoff = now - 60.0
        self._request_windows[tid] = [ts for ts in window if ts > cutoff]
        current_rpm = len(self._request_windows[tid])

        max_rpm = tenant.config.rate_limit_rpm
        if current_rpm >= max_rpm:
            raise RateLimitExceededError(tid, max_rpm, current_rpm + 1)

        # Record this request
        self._request_windows[tid].append(now)

        # Update quota tallies
        quota = self.get_quota(tid)
        quota.current_rpm = len(self._request_windows[tid])
        quota.total_requests += 1

        return quota.current_rpm

    def record_usage(self, tenant: Tenant, tokens: int, cost_cents: int = 0) -> TenantQuota:
        """Record token consumption and check against monthly budget."""
        tid = tenant.tenant_id
        quota = self.get_quota(tid)

        if quota.current_tokens + tokens > tenant.config.monthly_token_budget:
            raise QuotaExceededError(
                tid,
                "token",
                tenant.config.monthly_token_budget,
                quota.current_tokens + tokens,
            )

        if quota.current_spend_cents + cost_cents > tenant.config.monthly_spend_cap_cents:
            raise QuotaExceededError(
                tid,
                "financial spend",
                tenant.config.monthly_spend_cap_cents,
                quota.current_spend_cents + cost_cents,
            )

        quota.current_tokens += tokens
        quota.current_spend_cents += cost_cents
        return quota

    def get_quota(self, tenant_id: str) -> TenantQuota:
        """Retrieve quota record for a tenant."""
        if tenant_id not in self._quotas:
            self._quotas[tenant_id] = TenantQuota(tenant_id=tenant_id)
        return self._quotas[tenant_id]

    def reset(self, tenant_id: Optional[str] = None) -> None:
        """Reset usage metrics for testing or new billing cycle."""
        if tenant_id:
            self._request_windows.pop(tenant_id, None)
            self._quotas.pop(tenant_id, None)
        else:
            self._request_windows.clear()
            self._quotas.clear()
