"""
Production-ready API layer for user management with multi-app support.
Leverages RouterFactory for DRY patterns and includes tenant super admin capabilities.
"""

from .auth_router import (
    api_key_response,
    assignments,
    auth_router,
    auth_service,
    client_ip,
    create_auth_router,
    create_rbac_router,
    device_fingerprint,
    logger,
    permission_router,
    rbac_router,
    rbac_service,
    response_data,
    result,
    role_router,
    router,
    security,
    session,
    session_id,
    setup_response,
    success,
    summary,
    tokens,
    user_agent,
)
from .tenant_admin_router import (
    audit_entries,
    end_date,
    logger,
    period_end,
    period_start,
    role,
    router,
    setup_tenant_admin_router,
    start_date,
    templates,
    tenant_id,
    user,
)
from .user_router import admin_router, profile_router, user_router

__all__ = [
    # User management routers
    "user_router",
    "profile_router",
    "admin_router",
    # Authentication routers
    "auth_router",
    "session_router",
    "mfa_router",
    # Multi-app tenant administration
    "tenant_admin_router",
]
