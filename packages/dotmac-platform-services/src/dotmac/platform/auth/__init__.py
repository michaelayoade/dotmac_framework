"""
DotMac Platform Auth Services

Comprehensive authentication and authorization services including:
- JWT token management (access/refresh tokens, RS256/HS256)
- Role-Based Access Control (RBAC) engine
- Multi-factor authentication (TOTP, SMS, Email)
- Session management with Redis backend
- Edge JWT validation with sensitivity patterns
- Service-to-service authentication
- API key management
- OAuth2/OIDC provider integration

Design Principles:
- Production-ready with battle-tested components
- Extensible with plugin architecture
- Multi-tenant aware
- Security-first approach
- DRY leveraging dotmac-core utilities
"""

import contextlib
import warnings
from typing import Any

try:
    from .jwt_service import JWTService, create_jwt_service_from_config

    _jwt_available = True
except ImportError as e:
    warnings.warn(f"JWT service not available: {e}")
    JWTService = None
    create_jwt_service_from_config = None
    _jwt_available = False

try:
    from .rbac_engine import Permission, RBACEngine, Role, create_rbac_engine

    _rbac_available = True
except ImportError as e:
    warnings.warn(f"RBAC engine not available: {e}")
    RBACEngine = Role = Permission = create_rbac_engine = None
    _rbac_available = False

try:
    from .session_manager import (
        MemorySessionBackend,
        RedisSessionBackend,
        SessionBackend,
        SessionManager,
    )

    _sessions_available = True
except ImportError as e:
    warnings.warn(f"Session management not available: {e}")
    SessionManager = SessionBackend = RedisSessionBackend = MemorySessionBackend = None
    _sessions_available = False

try:
    from .mfa_service import (
        EmailProvider,
        MFAEnrollmentRequest,
        MFAMethod,
        MFAService,
        MFAServiceConfig,
        MFAStatus,
        MFAVerificationRequest,
        SMSProvider,
        TOTPSetupResponse,
        extract_mfa_claims,
        is_mfa_required_for_scope,
        is_mfa_token_valid,
    )

    _mfa_available = True
except ImportError as e:
    warnings.warn(f"MFA service not available: {e}")
    MFAService = MFAServiceConfig = MFAEnrollmentRequest = MFAVerificationRequest = None
    MFAMethod = MFAStatus = TOTPSetupResponse = SMSProvider = EmailProvider = None
    extract_mfa_claims = is_mfa_required_for_scope = is_mfa_token_valid = None
    _mfa_available = False

try:
    from .edge_validation import (
        COMMON_SENSITIVITY_PATTERNS,
        DEVELOPMENT_PATTERNS,
        PRODUCTION_PATTERNS,
        EdgeAuthMiddleware,
        EdgeJWTValidator,
        SensitivityLevel,
        create_edge_validator,
    )

    _edge_validation_available = True
except ImportError as e:
    warnings.warn(f"Edge validation not available: {e}")
    EdgeJWTValidator = EdgeAuthMiddleware = SensitivityLevel = None
    create_edge_validator = COMMON_SENSITIVITY_PATTERNS = None
    DEVELOPMENT_PATTERNS = PRODUCTION_PATTERNS = None
    _edge_validation_available = False

try:
    from .service_auth import (
        ServiceAuthMiddleware,
        ServiceIdentity,
        ServiceTokenManager,
        create_service_token_manager,
    )

    _service_auth_available = True
except ImportError as e:
    warnings.warn(f"Service auth not available: {e}")
    ServiceIdentity = ServiceTokenManager = ServiceAuthMiddleware = None
    create_service_token_manager = None
    _service_auth_available = False

# Compatibility aliases for service_tokens
with contextlib.suppress(ImportError):
    from .service_auth import (
        ServiceAuthMiddleware,
    )

try:
    from .current_user import (
        RequireAdmin,
        RequireAdminAccess,
        RequireAdminRole,
        RequireAuthenticated,
        RequireModeratorRole,
        RequireReadAccess,
        RequireUserRole,
        RequireWriteAccess,
        ServiceClaims,
        UserClaims,
        get_current_service,
        get_current_tenant,
        get_current_user,
        get_optional_user,
        require_admin,
        require_roles,
        require_scopes,
        require_service_operation,
        require_tenant_access,
    )

    _current_user_available = True
except ImportError as e:
    warnings.warn(f"Current user dependencies not available: {e}")
    UserClaims = ServiceClaims = get_current_user = get_current_tenant = None
    get_current_service = get_optional_user = require_scopes = require_roles = None
    require_admin = require_tenant_access = require_service_operation = None
    RequireAuthenticated = RequireAdmin = RequireReadAccess = RequireWriteAccess = None
    RequireAdminAccess = RequireUserRole = RequireModeratorRole = RequireAdminRole = None
    _current_user_available = False

try:
    from .api_keys import (
        APIKeyCreateRequest,
        APIKeyCreateResponse,
        APIKeyResponse,
        APIKeyScope,
        APIKeyService,
        APIKeyServiceConfig,
        APIKeyStatus,
        APIKeyUpdateRequest,
        RateLimitWindow,
        api_key_required,
        check_api_rate_limit,
    )

    _api_keys_available = True
except ImportError as e:
    warnings.warn(f"API keys not available: {e}")
    APIKeyService = APIKeyServiceConfig = APIKeyCreateRequest = APIKeyUpdateRequest = None
    APIKeyResponse = APIKeyCreateResponse = APIKeyScope = APIKeyStatus = RateLimitWindow = None
    api_key_required = check_api_rate_limit = None
    _api_keys_available = False

try:
    from .oauth_providers import (
        PROVIDER_CONFIGS,
        OAuthAuthorizationRequest,
        OAuthCallbackRequest,
        OAuthProvider,
        OAuthService,
        OAuthServiceConfig,
        OAuthTokenResponse,
        OAuthUserInfo,
        generate_oauth_state,
        generate_pkce_pair,
        setup_oauth_provider,
    )

    _oauth_available = True
except ImportError as e:
    warnings.warn(f"OAuth providers not available: {e}")
    OAuthService = OAuthServiceConfig = OAuthAuthorizationRequest = OAuthCallbackRequest = None
    OAuthProvider = OAuthTokenResponse = OAuthUserInfo = PROVIDER_CONFIGS = None
    setup_oauth_provider = generate_oauth_state = generate_pkce_pair = None
    _oauth_available = False

# Exception handling
try:
    from .exceptions import (
        AuthError,
        ConfigurationError,
        InsufficientRole,
        InsufficientScope,
        InvalidAlgorithm,
        InvalidAudience,
        InvalidIssuer,
        InvalidServiceToken,
        InvalidSignature,
        InvalidToken,
        ServiceTokenError,
        TenantMismatch,
        TokenError,
        TokenExpired,
        TokenNotFound,
        UnauthorizedService,
        get_http_status,
    )

    _exceptions_available = True
except ImportError as e:
    warnings.warn(f"Auth exceptions not available: {e}")
    AuthError = TokenError = TokenExpired = TokenNotFound = InvalidToken = None
    InvalidSignature = InvalidAlgorithm = InvalidAudience = InvalidIssuer = None
    InsufficientScope = InsufficientRole = TenantMismatch = ServiceTokenError = None
    UnauthorizedService = InvalidServiceToken = ConfigurationError = None
    get_http_status = None
    _exceptions_available = False

# Service initialization and management
_auth_service_registry: dict[str, Any] = {}


def initialize_auth_service(config: dict[str, Any]) -> None:
    """Initialize authentication services with configuration."""
    if _jwt_available and "jwt_secret_key" in config:
        jwt_service = create_jwt_service_from_config(config)
        _auth_service_registry["jwt"] = jwt_service

    if _rbac_available:
        rbac_engine = create_rbac_engine()
        _auth_service_registry["rbac"] = rbac_engine

    if _sessions_available:
        session_config = config.get("session", {})
        backend_type = session_config.get("backend", "memory")

        if backend_type == "redis" and "redis_url" in session_config:
            backend = RedisSessionBackend(session_config["redis_url"])
        else:
            backend = MemorySessionBackend()

        session_manager = SessionManager(backend)
        _auth_service_registry["sessions"] = session_manager

    if _mfa_available:
        mfa_service = MFAService()
        _auth_service_registry["mfa"] = mfa_service

    if _api_keys_available:
        try:
            from .api_keys import create_api_key_manager

            api_key_manager = create_api_key_manager(config)
            _auth_service_registry["api_keys"] = api_key_manager
        except ImportError:
            # API key manager not available
            pass


def get_auth_service(name: str) -> Any | None:
    """Get an initialized auth service."""
    return _auth_service_registry.get(name)


def is_auth_service_available(name: str) -> bool:
    """Check if auth service is available."""
    return name in _auth_service_registry


# FastAPI integration helpers
def add_auth_middleware(app, config: dict[str, Any] | None = None) -> None:
    """Add authentication middleware to FastAPI app."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("app must be a FastAPI instance")

    config = config or {}

    # Add edge auth middleware if available
    if _edge_validation_available and "edge_patterns" in config:
        edge_validator = create_edge_validator(
            jwt_service=get_auth_service("jwt"), sensitivity_patterns=config["edge_patterns"]
        )
        app.add_middleware(EdgeAuthMiddleware, validator=edge_validator)

    # Add service auth middleware if available
    if _service_auth_available and "service_tokens" in config:
        service_manager = get_auth_service("service_tokens")
        if service_manager:
            app.add_middleware(ServiceAuthMiddleware, token_manager=service_manager)


# Utility functions for creating services
def create_complete_auth_system(config: dict[str, Any]):
    """Create a complete authentication system with all components."""
    components = {}

    if _jwt_available:
        components["jwt"] = create_jwt_service_from_config(config.get("jwt", {}))

    if _rbac_available:
        components["rbac"] = create_rbac_engine()

    if _sessions_available:
        session_config = config.get("sessions", {})
        backend_type = session_config.get("backend", "memory")

        if backend_type == "redis":
            backend = RedisSessionBackend(session_config.get("redis_url", "redis://localhost:6379"))
        else:
            backend = MemorySessionBackend()

        components["sessions"] = SessionManager(backend)

    if _mfa_available:
        components["mfa"] = MFAService()

    if _api_keys_available:
        try:
            from .api_keys import create_api_key_manager

            components["api_keys"] = create_api_key_manager(config.get("api_keys", {}))
        except ImportError:
            # API key manager not available
            pass

    return components


# Version and metadata
__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "dev@dotmac.com"

# Export everything that's available
__all__ = [
    # Version
    "__version__",
    # Service management
    "initialize_auth_service",
    "get_auth_service",
    "is_auth_service_available",
    "add_auth_middleware",
    "create_complete_auth_system",
]

# Add available components to exports
if _jwt_available:
    __all__.extend(
        [
            "JWTService",
            "create_jwt_service_from_config",
        ]
    )

if _rbac_available:
    __all__.extend(
        [
            "RBACEngine",
            "Role",
            "Permission",
            "create_rbac_engine",
        ]
    )

if _sessions_available:
    __all__.extend(
        [
            "SessionManager",
            "SessionBackend",
            "RedisSessionBackend",
            "MemorySessionBackend",
        ]
    )

if _mfa_available:
    __all__.extend(
        [
            "MFAService",
            "MFAServiceConfig",
            "MFAEnrollmentRequest",
            "MFAVerificationRequest",
            "MFAMethod",
            "MFAStatus",
            "TOTPSetupResponse",
            "SMSProvider",
            "EmailProvider",
            "extract_mfa_claims",
            "is_mfa_required_for_scope",
            "is_mfa_token_valid",
        ]
    )

if _edge_validation_available:
    __all__.extend(
        [
            "EdgeJWTValidator",
            "EdgeAuthMiddleware",
            "SensitivityLevel",
            "create_edge_validator",
            "COMMON_SENSITIVITY_PATTERNS",
            "DEVELOPMENT_PATTERNS",
            "PRODUCTION_PATTERNS",
        ]
    )

if _service_auth_available:
    __all__.extend(
        [
            "ServiceIdentity",
            "ServiceTokenManager",
            "ServiceAuthMiddleware",
            "create_service_token_manager",
        ]
    )

if _current_user_available:
    __all__.extend(
        [
            "UserClaims",
            "ServiceClaims",
            "get_current_user",
            "get_current_tenant",
            "get_current_service",
            "get_optional_user",
            "require_scopes",
            "require_roles",
            "require_admin",
            "require_tenant_access",
            "require_service_operation",
            "RequireAuthenticated",
            "RequireAdmin",
            "RequireReadAccess",
            "RequireWriteAccess",
            "RequireAdminAccess",
            "RequireUserRole",
            "RequireModeratorRole",
            "RequireAdminRole",
        ]
    )

if _api_keys_available:
    __all__.extend(
        [
            "APIKeyService",
            "APIKeyServiceConfig",
            "APIKeyCreateRequest",
            "APIKeyUpdateRequest",
            "APIKeyResponse",
            "APIKeyCreateResponse",
            "APIKeyScope",
            "APIKeyStatus",
            "RateLimitWindow",
            "api_key_required",
            "check_api_rate_limit",
        ]
    )

if _oauth_available:
    __all__.extend(
        [
            "OAuthService",
            "OAuthServiceConfig",
            "OAuthAuthorizationRequest",
            "OAuthCallbackRequest",
            "OAuthProvider",
            "OAuthTokenResponse",
            "OAuthUserInfo",
            "PROVIDER_CONFIGS",
            "setup_oauth_provider",
            "generate_oauth_state",
            "generate_pkce_pair",
        ]
    )

if _exceptions_available:
    __all__.extend(
        [
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
            "ConfigurationError",
            "get_http_status",
        ]
    )

# Compatibility aliases for migration
get_current_user_with_tenant = get_current_user  # Legacy alias
