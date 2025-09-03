"""
Internal API Module

Internal implementation details that are re-exported through the main __init__.py
"""

# Re-export all public components
from .current_user import (
    UserClaims,
    ServiceClaims,
    get_current_user,
    get_current_service,
    get_optional_user,
    require_scopes,
    require_roles,
    require_admin,
    require_tenant_access,
    require_service_operation,
    # Convenience dependencies
    RequireAuthenticated,
    RequireAdmin,
    RequireReadAccess,
    RequireWriteAccess,
    RequireAdminAccess,
    RequireUserRole,
    RequireModeratorRole,
    RequireAdminRole,
)

from .edge_validation import (
    EdgeJWTValidator,
    EdgeAuthMiddleware,
    SensitivityLevel,
    create_edge_validator,
    COMMON_SENSITIVITY_PATTERNS,
    DEVELOPMENT_PATTERNS,
    PRODUCTION_PATTERNS,
)

from .exceptions import (
    AuthError,
    TokenError,
    TokenExpired,
    TokenNotFound,
    InvalidToken,
    InvalidSignature,
    InvalidAlgorithm,
    InvalidAudience,
    InvalidIssuer,
    InsufficientScope,
    InsufficientRole,
    TenantMismatch,
    ServiceTokenError,
    UnauthorizedService,
    InvalidServiceToken,
    SecretsProviderError,
    ConfigurationError,
    get_http_status,
)

from .jwt_service import (
    JWTService,
    create_jwt_service_from_config,
)

from .providers import (
    SecretsProvider,
    MockSecretsProvider,
)

# Optional OpenBao provider
try:
    from .providers import OpenBaoProvider, create_openbao_provider
    _openbao_available = True
except ImportError:
    _openbao_available = False

from .service_tokens import (
    ServiceIdentity,
    ServiceTokenManager,
    ServiceAuthMiddleware,
    create_service_token_manager,
)

# Export lists for controlled public API
__all__ = [
    # JWT Service
    "JWTService",
    "create_jwt_service_from_config",
    
    # Edge Validation
    "EdgeJWTValidator", 
    "EdgeAuthMiddleware",
    "SensitivityLevel",
    "create_edge_validator",
    "COMMON_SENSITIVITY_PATTERNS",
    "DEVELOPMENT_PATTERNS", 
    "PRODUCTION_PATTERNS",
    
    # Service Tokens
    "ServiceIdentity",
    "ServiceTokenManager",
    "ServiceAuthMiddleware", 
    "create_service_token_manager",
    
    # Current User
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
    
    # Exceptions
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
    
    # Providers
    "SecretsProvider",
    "MockSecretsProvider",
]

# Add OpenBao exports if available
if _openbao_available:
    __all__.extend([
        "OpenBaoProvider",
        "create_openbao_provider"
    ])