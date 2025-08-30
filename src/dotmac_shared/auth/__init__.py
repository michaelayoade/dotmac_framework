"""
DotMac Shared Authentication Service

A comprehensive, secure authentication and authorization package for the DotMac framework.
Provides JWT token management, RBAC, session management, MFA, and multi-platform integration.
"""

from .adapters.isp_adapter import ISPAuthAdapter
from .adapters.management_adapter import ManagementAuthAdapter

# New core authentication modules
from .core.jwt_service import JWTConfig, JWTService, TokenPair, TokenPayload
from .core.multi_factor import MFAManager
from .core.permissions import Permission, PermissionManager, Role, UserPermissions
from .core.portal_auth import (
    AuthenticationContext,
    AuthenticationMethod,
    PortalAuthService,
    PortalConfig,
    PortalType,
)
from .core.rbac_engine import (
    AccessDecision,
    AccessRequest,
    AccessResult,
    PolicyRule,
    RBACEngine,
    TenantPolicy,
)
from .core.sessions import SessionManager
from .core.tenant_security import (
    IsolationLevel,
    ResourceQuota,
    SecurityLevel,
    TenantInfo,
    TenantSecurityService,
)
from .core.tokens import JWTTokenManager
from .middleware.fastapi_middleware import AuthenticationMiddleware

__version__ = "1.0.0"
__author__ = "DotMac Framework Team"

# Main exports for easy importing
__all__ = [
    # Legacy core components
    "JWTTokenManager",
    "PermissionManager",
    "Permission",
    "Role",
    "UserPermissions",
    "SessionManager",
    "MFAManager",
    # New core authentication modules
    "JWTService",
    "RBACEngine",
    "PortalAuthService",
    "TenantSecurityService",
    # Configuration classes
    "JWTConfig",
    "PortalConfig",
    "TenantInfo",
    "ResourceQuota",
    # Data classes
    "TokenPair",
    "TokenPayload",
    "AccessRequest",
    "AccessResult",
    "AuthenticationContext",
    "PolicyRule",
    "TenantPolicy",
    # Enums
    "PortalType",
    "AuthenticationMethod",
    "SecurityLevel",
    "IsolationLevel",
    "AccessDecision",
    # Middleware
    "AuthenticationMiddleware",
    # Platform adapters
    "ISPAuthAdapter",
    "ManagementAuthAdapter",
]

# Package info
AUTH_SERVICE_INFO = {
    "name": "dotmac-auth-service",
    "version": __version__,
    "description": "Secure authentication service for DotMac framework",
    "features": [
        "JWT token management with RS256",
        "Role-based access control (RBAC)",
        "Multi-factor authentication (MFA)",
        "Session management with Redis",
        "Rate limiting and brute force protection",
        "Multi-platform integration",
        "Comprehensive audit logging",
        "FastAPI middleware integration",
    ],
    "security_standards": {
        "jwt_algorithm": "RS256",
        "password_hashing": "bcrypt (work factor 12)",
        "session_storage": "Redis with encryption",
        "token_expiry": {"access_token": "15 minutes", "refresh_token": "30 days"},
    },
}
