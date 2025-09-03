"""
DotMac Authentication Package

Standalone authentication package offering:
- JWT management (access/refresh tokens; RS256/HS256)
- Edge JWT validation with request sensitivity patterns
- Service-to-service tokens with signed internal tokens
- Current user dependency and common auth exceptions
- Optional secrets provider integration (OpenBao/Vault via extras)

Quick Start:
    from dotmac.auth import JWTService, EdgeJWTValidator, get_current_user
    
    # JWT Service
    jwt_service = JWTService(algorithm="RS256", private_key=private_key)
    token = jwt_service.issue_access_token("user123", scopes=["read", "write"])
    
    # Edge Validation
    validator = EdgeJWTValidator(jwt_service)
    validator.configure_sensitivity_patterns({
        (r"/api/public/.*", r".*"): "public",
        (r"/api/admin/.*", r".*"): "admin",
    })
    
    # FastAPI Integration
    @app.get("/protected")
    async def protected_route(user: UserClaims = Depends(get_current_user)):
        return {"user_id": user.user_id, "scopes": user.scopes}
"""

from .api import *

# Package metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"
__description__ = "Standalone authentication package for DotMac platform"

# For type checking
__all__ = [
    # Core JWT functionality
    "JWTService",
    "create_jwt_service_from_config",
    
    # Edge validation and middleware
    "EdgeJWTValidator",
    "EdgeAuthMiddleware", 
    "SensitivityLevel",
    "create_edge_validator",
    "COMMON_SENSITIVITY_PATTERNS",
    "DEVELOPMENT_PATTERNS",
    "PRODUCTION_PATTERNS",
    
    # Service-to-service authentication
    "ServiceIdentity",
    "ServiceTokenManager",
    "ServiceAuthMiddleware",
    "create_service_token_manager",
    
    # FastAPI dependencies
    "UserClaims",
    "ServiceClaims", 
    "get_current_user",
    "get_current_service",
    "get_optional_user",
    "require_scopes",
    "require_roles",
    "require_admin",
    "require_tenant_access",
    "require_service_operation",
    
    # Convenience dependencies
    "RequireAuthenticated",
    "RequireAdmin", 
    "RequireReadAccess",
    "RequireWriteAccess",
    "RequireAdminAccess",
    "RequireUserRole",
    "RequireModeratorRole",
    "RequireAdminRole",
    
    # Exception classes
    "AuthError",
    "TokenError",
    "TokenExpired",
    "TokenNotFound",
    "InvalidToken", 
    "InvalidSignature",
    "InvalidAlgorithm",
    "InvalidAudience",
    "InvalidIssuer",
    "InsufficientScope",
    "InsufficientRole",
    "TenantMismatch",
    "ServiceTokenError",
    "UnauthorizedService",
    "InvalidServiceToken",
    "SecretsProviderError",
    "ConfigurationError",
    "get_http_status",
    
    # Secrets providers
    "SecretsProvider",
    "MockSecretsProvider",
]

# Add OpenBao exports if available (from secrets extra)
try:
    from .providers import OpenBaoProvider, create_openbao_provider
    __all__.extend(["OpenBaoProvider", "create_openbao_provider"])
except ImportError:
    pass