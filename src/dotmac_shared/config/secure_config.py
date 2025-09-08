"""
Secure Configuration Manager with OpenBao Integration
====================================================
Integrates existing OpenBao secrets management with configuration management
to eliminate hardcoded secrets in the authentication system.
"""

import asyncio
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Import existing OpenBao client
try:
    from ..secrets.adapters.management_adapter import ManagementPlatformSecretsAdapter
    from ..secrets.core.vault_client import OpenBaoClient, VaultConfig

    OPENBAO_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenBao client not available: {e}")
    OPENBAO_AVAILABLE = False
    ManagementPlatformSecretsAdapter = None
    OpenBaoClient = VaultConfig = None


@dataclass
class SecureConfigValue:
    """Represents a securely retrieved configuration value"""

    value: str
    source: str
    cached: bool = False


class SecureConfigManager:
    """
    Secure configuration manager that integrates with existing OpenBao infrastructure.
    Provides fallback to environment variables for development and testing.
    """

    def __init__(self):
        self._cache: dict[str, SecureConfigValue] = {}
        self._openbao_client = None
        self._adapter = None

        # Initialize OpenBao if available
        if OPENBAO_AVAILABLE:
            try:
                self._adapter = ManagementPlatformSecretsAdapter()
                self._openbao_client = OpenBaoClient()
                logger.info("OpenBao secrets integration initialized")
            except Exception as e:
                logger.warning(f"OpenBao initialization failed, using fallback: {e}")
                self._openbao_client = None
                self._adapter = None

    async def get_secret(self, path: str, env_fallback: Optional[str] = None, required: bool = True) -> str:
        """
        Get a secret from OpenBao with environment variable fallback.

        Args:
            path: OpenBao secret path (e.g., 'auth/jwt_secret_key')
            env_fallback: Environment variable name for fallback
            required: Whether this secret is required

        Returns:
            Secret value as string

        Raises:
            ValueError: If required secret is not found
        """
        # Check cache first
        if path in self._cache:
            cached_value = self._cache[path]
            logger.debug(f"Retrieved cached secret from {cached_value.source}")
            return cached_value.value

        secret_value = None
        source = "unknown"

        # Try OpenBao first
        if self._adapter and OPENBAO_AVAILABLE:
            try:
                secret_result = await self._adapter.get_secret(path=path, secret_type="application_secret")  # noqa: S106 - label for secret backend
                if secret_result and hasattr(secret_result, "value"):
                    secret_value = secret_result.value
                    source = "openbao"
                    logger.info(f"Retrieved secret from OpenBao: {path}")
            except Exception as e:
                logger.warning(f"OpenBao retrieval failed for {path}: {e}")

        # Fallback to environment variable
        if not secret_value and env_fallback:
            secret_value = os.getenv(env_fallback)
            if secret_value:
                source = "environment"
                logger.info(f"Retrieved secret from environment: {env_fallback}")

        # Check if secret was found
        if not secret_value:
            error_msg = f"Required secret not found: {path}"
            if env_fallback:
                error_msg += f" (also checked {env_fallback})"

            if required:
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.warning(error_msg)
                return ""

        # Cache the result
        config_value = SecureConfigValue(value=secret_value, source=source, cached=True)
        self._cache[path] = config_value

        return secret_value

    def get_secret_sync(self, path: str, env_fallback: Optional[str] = None, required: bool = True) -> str:
        """
        Synchronous wrapper for get_secret for use in non-async contexts.
        """
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.get_secret(path, env_fallback, required))
        except RuntimeError:
            # No event loop running, create a new one
            return asyncio.run(self.get_secret(path, env_fallback, required))

    async def store_secret(self, path: str, value: str) -> bool:
        """
        Store a secret in OpenBao.

        Args:
            path: OpenBao secret path
            value: Secret value to store

        Returns:
            True if successful, False otherwise
        """
        if not self._adapter or not OPENBAO_AVAILABLE:
            logger.warning("OpenBao not available for secret storage")
            return False

        try:
            await self._adapter.store_secret(path=path, value=value, secret_type="application_secret")  # noqa: S106 - label for secret backend

            # Clear cache for this path
            if path in self._cache:
                del self._cache[path]

            logger.info(f"Stored secret in OpenBao: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {path}: {e}")
            return False

    def clear_cache(self, path: Optional[str] = None):
        """Clear cached secrets"""
        if path:
            self._cache.pop(path, None)
            logger.debug(f"Cleared cache for: {path}")
        else:
            self._cache.clear()
            logger.debug("Cleared all cached secrets")

    def get_cache_info(self) -> dict[str, Any]:
        """Get information about cached secrets"""
        return {
            "cached_secrets": len(self._cache),
            "sources": {path: config.source for path, config in self._cache.items()},
            "openbao_available": OPENBAO_AVAILABLE and self._openbao_client is not None,
        }


# Global instance for use across the application
_config_manager: Optional[SecureConfigManager] = None


@lru_cache
def get_config_manager() -> SecureConfigManager:
    """Get the global secure configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager


async def get_jwt_secret() -> str:
    """
    Get JWT secret with proper OpenBao integration.
    This replaces the hardcoded 'your-jwt-secret-key' values.
    """
    config_manager = get_config_manager()
    return await config_manager.get_secret(path="auth/jwt_secret_key", env_fallback="JWT_SECRET_KEY", required=True)


def get_jwt_secret_sync() -> str:
    """Synchronous version of get_jwt_secret for middleware initialization"""
    config_manager = get_config_manager()
    return config_manager.get_secret_sync(path="auth/jwt_secret_key", env_fallback="JWT_SECRET_KEY", required=True)


async def get_database_url() -> str:
    """Get database URL from OpenBao or environment"""
    config_manager = get_config_manager()
    return await config_manager.get_secret(path="database/primary_url", env_fallback="DATABASE_URL", required=True)


async def get_redis_url() -> str:
    """Get Redis URL from OpenBao or environment"""
    config_manager = get_config_manager()
    return (
        await config_manager.get_secret(path="cache/redis_url", env_fallback="REDIS_URL", required=False)
        or "redis://localhost:6379/0"
    )


# Development helper functions
async def initialize_development_secrets():
    """Initialize development secrets in OpenBao for testing"""
    config_manager = get_config_manager()

    # Generate secure JWT secret if not exists
    import secrets

    jwt_secret = secrets.token_hex(32)

    development_secrets = {
        "auth/jwt_secret_key": jwt_secret,
        "database/primary_url": "postgresql://dotmac:dotmac@localhost:5432/dotmac_dev",
        "cache/redis_url": "redis://localhost:6379/0",
    }

    for path, value in development_secrets.items():
        try:
            # Only store if not already exists
            existing = await config_manager.get_secret(path, required=False)
            if not existing:
                await config_manager.store_secret(path, value)
                logger.info(f"Initialized development secret: {path}")
        except Exception as e:
            logger.warning(f"Could not initialize {path}: {e}")
