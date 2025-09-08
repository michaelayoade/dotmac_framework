"""
Tenant security placeholder for platform auth core.

Provides a minimal manager to satisfy imports while full implementation is developed.
"""

from __future__ import annotations


class TenantSecurityManager:
    """Placeholder tenant security manager.

    Add policy checks and enforcement as needed.
    """

    def verify_access(self, tenant_id: str, user_id: str) -> bool:  # pragma: no cover
        # Allow-all placeholder; implement real checks later
        return True

