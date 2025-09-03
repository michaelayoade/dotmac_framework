"""
Migration Shim for dotmac_shared.auth

DEPRECATED: This module is deprecated. Use dotmac.auth instead.

This shim provides backward compatibility for existing code that imports
from dotmac_shared.auth. All functionality has been moved to the standalone
dotmac.auth package.

Migration Guide:
    Old: from dotmac_shared.auth import JWTService
    New: from dotmac.auth import JWTService

    Old: from dotmac_shared.auth.current_user import get_current_user  
    New: from dotmac.auth import get_current_user

The shim will be removed in a future version.
"""

import warnings
from typing import Any

# Issue deprecation warning
warnings.warn(
    "dotmac_shared.auth is deprecated and will be removed in a future version. "
    "Use 'dotmac.auth' instead. "
    "See migration guide: https://docs.dotmac.com/auth/migration",
    DeprecationWarning,
    stacklevel=2
)

# Import and re-export everything from the new location
try:
    from dotmac.auth import *  # noqa: F401, F403
    
    # Explicit re-exports for better IDE support
    from dotmac.auth import (
        # Core JWT service
        JWTService,
        create_jwt_service_from_config,
        
        # Current user dependencies
        get_current_user,
        get_optional_user,
        get_current_service,
        UserClaims,
        ServiceClaims,
        
        # Authorization helpers
        require_scopes,
        require_roles,
        require_admin,
        require_tenant_access,
        require_service_operation,
        
        # Edge validation
        EdgeJWTValidator,
        EdgeAuthMiddleware,
        SensitivityLevel,
        create_edge_validator,
        get_common_sensitivity_patterns,
        
        # Service tokens
        ServiceTokenManager,
        ServiceIdentity,
        ServiceAuthMiddleware,
        create_service_token_manager,
        
        # Exceptions
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
        ConfigurationError,
        SecretsProviderError,
        OpenBaoError,
        
        # Secrets providers
        SecretsProvider,
        OpenBaoProvider,
        
        # API factory
        create_auth_api,
    )
    
except ImportError as e:
    # If the new package isn't available, provide helpful error message
    raise ImportError(
        f"Failed to import from dotmac.auth: {e}\n\n"
        "The dotmac.auth package is not installed. Install it with:\n"
        "  pip install dotmac-auth\n\n"
        "Or if you're in development mode:\n"
        "  pip install -e packages/dotmac-auth/"
    ) from e


def __getattr__(name: str) -> Any:
    """
    Dynamic attribute access for backward compatibility.
    
    This allows accessing any attribute that might have been available
    in the old dotmac_shared.auth module but isn't explicitly re-exported.
    """
    try:
        import dotmac.auth as new_module
        return getattr(new_module, name)
    except AttributeError:
        raise AttributeError(
            f"module 'dotmac_shared.auth' has no attribute '{name}'. "
            f"Check the migration guide: https://docs.dotmac.com/auth/migration"
        ) from None


# Legacy module aliases for common imports
class _DeprecatedModule:
    """Helper class for deprecated submodule access"""
    
    def __init__(self, new_path: str, old_path: str):
        self.new_path = new_path
        self.old_path = old_path
        self._cached_module = None
    
    def __getattr__(self, name: str) -> Any:
        if self._cached_module is None:
            warnings.warn(
                f"Importing from '{self.old_path}' is deprecated. "
                f"Use '{self.new_path}' instead.",
                DeprecationWarning,
                stacklevel=2
            )
            try:
                import importlib
                self._cached_module = importlib.import_module(self.new_path)
            except ImportError as e:
                raise ImportError(
                    f"Failed to import {self.new_path}: {e}"
                ) from e
        
        return getattr(self._cached_module, name)


# Deprecated submodule access
import sys
sys.modules[f"{__name__}.current_user"] = _DeprecatedModule(
    "dotmac.auth.current_user", "dotmac_shared.auth.current_user"
)
sys.modules[f"{__name__}.jwt_service"] = _DeprecatedModule(
    "dotmac.auth.jwt_service", "dotmac_shared.auth.jwt_service"
)
sys.modules[f"{__name__}.edge_validation"] = _DeprecatedModule(
    "dotmac.auth.edge_validation", "dotmac_shared.auth.edge_validation"
)
sys.modules[f"{__name__}.service_tokens"] = _DeprecatedModule(
    "dotmac.auth.service_tokens", "dotmac_shared.auth.service_tokens"
)
sys.modules[f"{__name__}.exceptions"] = _DeprecatedModule(
    "dotmac.auth.exceptions", "dotmac_shared.auth.exceptions"
)

# Legacy attributes for backward compatibility
__version__ = "2.0.0"  # Updated version to indicate migration
__author__ = "DotMac Framework Team"

# Legacy __all__ export list
__all__ = [
    # Core JWT service
    "JWTService",
    "create_jwt_service_from_config",
    
    # Current user dependencies  
    "get_current_user",
    "get_optional_user",
    "get_current_service",
    "UserClaims",
    "ServiceClaims",
    
    # Authorization helpers
    "require_scopes",
    "require_roles",
    "require_admin",
    "require_tenant_access",
    "require_service_operation",
    
    # Edge validation
    "EdgeJWTValidator",
    "EdgeAuthMiddleware", 
    "SensitivityLevel",
    "create_edge_validator",
    "get_common_sensitivity_patterns",
    
    # Service tokens
    "ServiceTokenManager",
    "ServiceIdentity",
    "ServiceAuthMiddleware",
    "create_service_token_manager",
    
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
    "ConfigurationError",
    "SecretsProviderError",
    "OpenBaoError",
    
    # Secrets providers
    "SecretsProvider",
    "OpenBaoProvider",
    
    # API factory
    "create_auth_api",
]
