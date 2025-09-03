"""
Public API and factory functions for dotmac.secrets
Provides convenient ways to create SecretsManager instances
"""
from __future__ import annotations

import os
import warnings
from typing import Any, Dict, Optional, Union

from .cache import create_cache
from .interfaces import ObservabilityHook, SecretCache, SecretValidator
from .manager import SecretsManager
from .observability import create_observability_hook
from .providers import (
    BaseProvider,
    EnvironmentProvider,
    FileProvider,
    OpenBaoProvider,
)
from .types import EnvConfig, Environment, FileConfig, OpenBaoConfig
from .validators import create_default_validator, create_development_validator


def from_env(
    environment: Optional[str] = None,
    service_name: Optional[str] = None,
    cache_type: str = "memory",
    cache_config: Optional[Dict[str, Any]] = None,
    validator: Optional[SecretValidator] = None,
    observability_hook: Optional[ObservabilityHook] = None,
    **kwargs: Any
) -> SecretsManager:
    """
    Create SecretsManager from environment variables
    
    Environment variables used:
    - SECRETS_PROVIDER: Provider type ("openbao", "env", "file")
    - OPENBAO_URL: OpenBao/Vault URL
    - OPENBAO_TOKEN: OpenBao/Vault token
    - OPENBAO_MOUNT: OpenBao/Vault mount path (default: "kv")
    - OPENBAO_NAMESPACE: OpenBao/Vault namespace (optional)
    - OPENBAO_VERIFY_SSL: Verify SSL certificates (default: "true")
    - SECRETS_FILE_PATH: File provider base path
    - SECRETS_FILE_FORMAT: File provider format ("json", "yaml", "toml")
    - SECRETS_CACHE_TYPE: Cache type ("memory", "redis", "null")
    - SECRETS_CACHE_TTL: Default cache TTL in seconds
    - SECRETS_REDIS_URL: Redis URL for Redis cache
    - ENVIRONMENT: Environment name ("development", "staging", "production")
    - EXPLICIT_ALLOW_ENV_SECRETS: Allow env provider in production
    
    Args:
        environment: Override environment detection
        service_name: Service name for context
        cache_type: Cache type to use
        cache_config: Cache configuration override
        validator: Custom validator (uses environment-appropriate default if None)
        observability_hook: Custom observability hook
        **kwargs: Additional configuration
        
    Returns:
        Configured SecretsManager instance
        
    Raises:
        ValueError: If required configuration is missing
        ImportError: If required dependencies are missing
    """
    # Determine environment
    env_name = environment or os.getenv("ENVIRONMENT", "development")
    try:
        env = Environment(env_name.lower())
    except ValueError:
        warnings.warn(f"Unknown environment '{env_name}', using development")
        env = Environment.DEVELOPMENT
    
    # Create provider based on configuration
    provider = _create_provider_from_env(env)
    
    # Create cache
    cache = _create_cache_from_env(cache_type, cache_config or {})
    
    # Create validator if not provided
    if validator is None:
        if env == Environment.PRODUCTION:
            validator = create_default_validator()
        else:
            validator = create_development_validator()
    
    # Create observability hook if not provided
    if observability_hook is None:
        hook_type = os.getenv("SECRETS_OBSERVABILITY", "logging")
        try:
            observability_hook = create_observability_hook(hook_type)
        except Exception as e:
            warnings.warn(f"Failed to create observability hook: {e}")
            observability_hook = None
    
    # Get additional configuration
    default_ttl = int(os.getenv("SECRETS_CACHE_TTL", "300"))
    negative_cache_ttl = int(os.getenv("SECRETS_NEGATIVE_CACHE_TTL", "30"))
    validate_secrets = os.getenv("SECRETS_VALIDATE", "true").lower() == "true"
    
    return SecretsManager(
        provider=provider,
        cache=cache,
        validator=validator,
        observability_hook=observability_hook,
        default_ttl=default_ttl,
        negative_cache_ttl=negative_cache_ttl,
        validate_secrets=validate_secrets,
        **kwargs
    )


def _create_provider_from_env(env: Environment) -> BaseProvider:
    """Create secrets provider from environment variables"""
    provider_type = os.getenv("SECRETS_PROVIDER", "").lower()
    
    # Auto-detect provider if not specified
    if not provider_type:
        if os.getenv("OPENBAO_URL") or os.getenv("VAULT_ADDR"):
            provider_type = "openbao"
        elif os.getenv("SECRETS_FILE_PATH"):
            provider_type = "file"
        else:
            provider_type = "env"
            if env == Environment.PRODUCTION:
                warnings.warn(
                    "No secrets provider configured, falling back to environment variables. "
                    "This is not recommended for production. Set SECRETS_PROVIDER=openbao "
                    "and configure OpenBao/Vault.",
                    UserWarning
                )
    
    # Create provider based on type
    if provider_type == "openbao" or provider_type == "vault":
        return _create_openbao_provider(env)
    elif provider_type == "env" or provider_type == "environment":
        return _create_env_provider(env)
    elif provider_type == "file":
        return _create_file_provider(env)
    else:
        raise ValueError(f"Unknown secrets provider type: {provider_type}")


def _create_openbao_provider(env: Environment) -> OpenBaoProvider:
    """Create OpenBao/Vault provider from environment"""
    url = os.getenv("OPENBAO_URL") or os.getenv("VAULT_ADDR")
    token = os.getenv("OPENBAO_TOKEN") or os.getenv("VAULT_TOKEN")
    
    if not url:
        raise ValueError(
            "OPENBAO_URL (or VAULT_ADDR) is required for OpenBao provider"
        )
    
    if not token:
        raise ValueError(
            "OPENBAO_TOKEN (or VAULT_TOKEN) is required for OpenBao provider"
        )
    
    mount_path = os.getenv("OPENBAO_MOUNT", "kv")
    api_version = os.getenv("OPENBAO_API_VERSION", "v2")
    verify_ssl = os.getenv("OPENBAO_VERIFY_SSL", "true").lower() == "true"
    ca_cert_path = os.getenv("OPENBAO_CA_CERT")
    namespace = os.getenv("OPENBAO_NAMESPACE") or os.getenv("VAULT_NAMESPACE")
    
    timeout = int(os.getenv("OPENBAO_TIMEOUT", "30"))
    retry_attempts = int(os.getenv("OPENBAO_RETRY_ATTEMPTS", "3"))
    
    return OpenBaoProvider(
        url=url,
        token=token,
        mount_path=mount_path,
        api_version=api_version,
        verify_ssl=verify_ssl,
        ca_cert_path=ca_cert_path,
        namespace=namespace,
        timeout=timeout,
        retry_attempts=retry_attempts,
    )


def _create_env_provider(env: Environment) -> EnvironmentProvider:
    """Create environment provider from environment"""
    prefix = os.getenv("SECRETS_ENV_PREFIX", "")
    allow_production = os.getenv("EXPLICIT_ALLOW_ENV_SECRETS", "false").lower() == "true"
    
    timeout = int(os.getenv("SECRETS_TIMEOUT", "30"))
    
    return EnvironmentProvider(
        prefix=prefix,
        allow_production=allow_production,
        environment=env,
        timeout=timeout,
    )


def _create_file_provider(env: Environment) -> FileProvider:
    """Create file provider from environment"""
    base_path = os.getenv("SECRETS_FILE_PATH")
    if not base_path:
        raise ValueError("SECRETS_FILE_PATH is required for file provider")
    
    file_format = os.getenv("SECRETS_FILE_FORMAT", "json")
    timeout = int(os.getenv("SECRETS_TIMEOUT", "30"))
    
    return FileProvider(
        base_path=base_path,
        file_format=file_format,
        timeout=timeout,
    )


def _create_cache_from_env(
    cache_type: str,
    cache_config: Dict[str, Any]
) -> Optional[SecretCache]:
    """Create cache from environment variables"""
    # Override cache type from environment if not specified
    env_cache_type = os.getenv("SECRETS_CACHE_TYPE")
    if env_cache_type:
        cache_type = env_cache_type.lower()
    
    if cache_type == "null" or cache_type == "none":
        return None
    
    # Build cache configuration
    config = cache_config.copy()
    
    if cache_type == "memory":
        config.setdefault("default_ttl", int(os.getenv("SECRETS_CACHE_TTL", "300")))
        config.setdefault("max_size", int(os.getenv("SECRETS_CACHE_MAX_SIZE", "1000")))
    
    elif cache_type == "redis":
        config.setdefault("redis_url", os.getenv("SECRETS_REDIS_URL", "redis://localhost:6379"))
        config.setdefault("key_prefix", os.getenv("SECRETS_REDIS_PREFIX", "secrets:"))
        config.setdefault("default_ttl", int(os.getenv("SECRETS_CACHE_TTL", "300")))
    
    try:
        return create_cache(cache_type, **config)
    except Exception as e:
        warnings.warn(f"Failed to create {cache_type} cache: {e}, falling back to memory cache")
        return create_cache("memory", default_ttl=300)


# Convenience factory functions
def create_secrets_manager(
    provider: BaseProvider,
    cache: Optional[SecretCache] = None,
    validator: Optional[SecretValidator] = None,
    observability_hook: Optional[ObservabilityHook] = None,
    **kwargs: Any
) -> SecretsManager:
    """
    Create SecretsManager with explicit configuration
    
    Args:
        provider: Secrets provider implementation
        cache: Optional cache implementation
        validator: Optional secret validator
        observability_hook: Optional observability hook
        **kwargs: Additional SecretsManager configuration
        
    Returns:
        Configured SecretsManager instance
    """
    return SecretsManager(
        provider=provider,
        cache=cache,
        validator=validator,
        observability_hook=observability_hook,
        **kwargs
    )


def create_openbao_secrets_manager(
    url: str,
    token: str,
    mount_path: str = "kv",
    **kwargs: Any
) -> SecretsManager:
    """
    Create SecretsManager with OpenBao/Vault provider
    
    Args:
        url: OpenBao/Vault URL
        token: Authentication token
        mount_path: KV mount path
        **kwargs: Additional configuration
        
    Returns:
        SecretsManager with OpenBao provider
    """
    provider = OpenBaoProvider(url=url, token=token, mount_path=mount_path)
    cache = create_cache("memory")
    validator = create_default_validator()
    
    return SecretsManager(
        provider=provider,
        cache=cache,
        validator=validator,
        **kwargs
    )


def create_development_secrets_manager(
    provider_type: str = "env",
    **kwargs: Any
) -> SecretsManager:
    """
    Create SecretsManager for development environment
    
    Args:
        provider_type: Provider type ("env", "file")
        **kwargs: Additional configuration
        
    Returns:
        SecretsManager configured for development
    """
    if provider_type == "env":
        provider = EnvironmentProvider(
            environment=Environment.DEVELOPMENT,
            allow_production=True
        )
    elif provider_type == "file":
        base_path = kwargs.get("base_path", "./secrets")
        provider = FileProvider(base_path=base_path)
    else:
        raise ValueError(f"Unsupported development provider: {provider_type}")
    
    cache = create_cache("memory", default_ttl=60)  # Shorter TTL for development
    validator = create_development_validator()
    observability_hook = create_observability_hook("logging")
    
    return SecretsManager(
        provider=provider,
        cache=cache,
        validator=validator,
        observability_hook=observability_hook,
        validate_secrets=False,  # Relaxed validation for development
        **kwargs
    )


# Environment detection utilities
def get_current_environment() -> Environment:
    """
    Detect current environment from environment variables
    
    Returns:
        Current environment
    """
    env_name = os.getenv("ENVIRONMENT", "development").lower()
    
    # Common environment variable names
    if not env_name or env_name == "development":
        for var in ["NODE_ENV", "FLASK_ENV", "DJANGO_SETTINGS_MODULE"]:
            value = os.getenv(var, "").lower()
            if "prod" in value:
                env_name = "production"
                break
            elif "staging" in value or "stage" in value:
                env_name = "staging"
                break
            elif "test" in value:
                env_name = "testing"
                break
    
    try:
        return Environment(env_name)
    except ValueError:
        return Environment.DEVELOPMENT


def is_production_environment() -> bool:
    """
    Check if running in production environment
    
    Returns:
        True if production environment detected
    """
    return get_current_environment() == Environment.PRODUCTION


def validate_production_config() -> List[str]:
    """
    Validate configuration for production deployment
    
    Returns:
        List of validation warnings/errors
    """
    warnings = []
    env = get_current_environment()
    
    if env != Environment.PRODUCTION:
        return warnings
    
    # Check secrets provider
    provider_type = os.getenv("SECRETS_PROVIDER", "").lower()
    if not provider_type or provider_type == "env":
        allow_env = os.getenv("EXPLICIT_ALLOW_ENV_SECRETS", "false").lower()
        if allow_env != "true":
            warnings.append(
                "Environment variable provider not recommended for production. "
                "Configure OpenBao/Vault with SECRETS_PROVIDER=openbao"
            )
    
    # Check OpenBao configuration if using OpenBao
    if provider_type in ("openbao", "vault"):
        if not os.getenv("OPENBAO_URL") and not os.getenv("VAULT_ADDR"):
            warnings.append("OPENBAO_URL is required for OpenBao provider")
        
        if not os.getenv("OPENBAO_TOKEN") and not os.getenv("VAULT_TOKEN"):
            warnings.append("OPENBAO_TOKEN is required for OpenBao provider")
        
        verify_ssl = os.getenv("OPENBAO_VERIFY_SSL", "true").lower()
        if verify_ssl != "true":
            warnings.append("SSL verification should be enabled in production")
    
    # Check cache configuration
    cache_type = os.getenv("SECRETS_CACHE_TYPE", "memory").lower()
    if cache_type == "memory":
        warnings.append(
            "Memory cache may not be suitable for production deployments. "
            "Consider using Redis cache with SECRETS_CACHE_TYPE=redis"
        )
    
    return warnings