"""
DotMac Secrets - Standalone secrets management package
Provides unified interface for secrets management with multiple providers
"""

# Core classes and interfaces
from .manager import SecretsManager
from .interfaces import (
    SecretsProvider,
    WritableSecretsProvider,
    SecretValidator,
    SecretCache,
    KeyRotationPolicy,
    ObservabilityHook,
    # Exceptions
    SecretsProviderError,
    SecretNotFoundError,
    SecretValidationError,
    ProviderConnectionError,
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    SecretExpiredError,
    SecretsManagerError,
    ConfigurationError,
    ProviderNotAvailableError,
)

# Types and data structures
from .types import (
    SecretKind,
    Environment,
    JWTKeypair,
    DatabaseCredentials,
    SecretPolicy,
    SecretMetadata,
    SecretValue,
    SecretPaths,
    OpenBaoConfig,
    EnvConfig,
    FileConfig,
)

# Providers
from .providers import (
    OpenBaoProvider,
    EnvironmentProvider,
    FileProvider,
)

# Caching
from .cache import (
    InMemoryCache,
    RedisCache,
    NullCache,
    create_cache,
)

# Validators
from .validators import (
    SecretValidator as DefaultSecretValidator,
    JWTValidator,
    DatabaseCredentialsValidator,
    PolicyValidator,
    create_default_validator,
    create_development_validator,
)

# Rotation
from .rotation import (
    RotationScheduler,
    RotationRule,
    RotationResult,
    RotationStatus,
    DefaultRotationPolicy,
    schedule_rotation,
    rotate_jwt_keypair,
)

# Observability
from .observability import (
    LoggingObservabilityHook,
    OpenTelemetryObservabilityHook,
    CompositeObservabilityHook,
    NullObservabilityHook,
    create_observability_hook,
)

# Public API and factory functions
from .api import (
    from_env,
    create_secrets_manager,
    create_openbao_secrets_manager,
    create_development_secrets_manager,
    get_current_environment,
    is_production_environment,
    validate_production_config,
)

# Version info
__version__ = "1.0.0"
__author__ = "DotMac Framework"
__email__ = "dev@dotmac.framework"

# Public API
__all__ = [
    # Core classes
    "SecretsManager",
    
    # Main factory function
    "from_env",
    
    # Provider interfaces
    "SecretsProvider",
    "WritableSecretsProvider",
    
    # Concrete providers
    "OpenBaoProvider", 
    "EnvironmentProvider",
    "FileProvider",
    
    # Types
    "SecretKind",
    "Environment", 
    "JWTKeypair",
    "DatabaseCredentials",
    "SecretPolicy",
    "SecretMetadata",
    "SecretValue",
    "SecretPaths",
    
    # Configuration types
    "OpenBaoConfig",
    "EnvConfig", 
    "FileConfig",
    
    # Caching
    "SecretCache",
    "InMemoryCache",
    "RedisCache", 
    "NullCache",
    "create_cache",
    
    # Validation
    "SecretValidator",
    "DefaultSecretValidator",
    "JWTValidator",
    "DatabaseCredentialsValidator", 
    "PolicyValidator",
    "create_default_validator",
    "create_development_validator",
    
    # Rotation
    "KeyRotationPolicy",
    "RotationScheduler",
    "RotationRule",
    "RotationResult", 
    "RotationStatus",
    "DefaultRotationPolicy",
    "schedule_rotation",
    "rotate_jwt_keypair",
    
    # Observability
    "ObservabilityHook",
    "LoggingObservabilityHook",
    "OpenTelemetryObservabilityHook",
    "CompositeObservabilityHook",
    "NullObservabilityHook",
    "create_observability_hook",
    
    # Factory functions
    "create_secrets_manager",
    "create_openbao_secrets_manager", 
    "create_development_secrets_manager",
    
    # Utilities
    "get_current_environment",
    "is_production_environment",
    "validate_production_config",
    
    # Exceptions
    "SecretsProviderError",
    "SecretNotFoundError",
    "SecretValidationError", 
    "ProviderConnectionError",
    "ProviderAuthenticationError",
    "ProviderAuthorizationError",
    "SecretExpiredError",
    "SecretsManagerError",
    "ConfigurationError",
    "ProviderNotAvailableError",
]

# Module-level configuration
import logging

# Set up default logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Configuration validation on import for production environments
import warnings
import os

def _check_production_config() -> None:
    """Check configuration on module import for production"""
    try:
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production":
            config_warnings = validate_production_config()
            for warning in config_warnings:
                warnings.warn(warning, UserWarning, stacklevel=2)
    except Exception:
        # Don't fail on import if validation fails
        pass

# Only run production check if not in testing
if not os.getenv("PYTEST_CURRENT_TEST"):
    _check_production_config()


# Convenience function for backward compatibility
def create_client(*args, **kwargs):
    """
    Deprecated: Use from_env() or create_secrets_manager() instead
    """
    warnings.warn(
        "create_client() is deprecated, use from_env() instead",
        DeprecationWarning,
        stacklevel=2
    )
    return from_env(*args, **kwargs)