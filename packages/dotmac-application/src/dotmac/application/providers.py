"""
Provider protocols and configuration for dependency injection.
Enables integration with platform services while maintaining independence.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class DatabaseProvider(Protocol):
    """Protocol for database session providers."""

    async def get_session(self) -> Any:
        """Get an async database session."""
        ...

    async def close_session(self, session: Any) -> None:
        """Close a database session."""
        ...


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol for authentication providers."""

    async def get_current_user(self, token: str) -> dict[str, Any]:
        """Get current user from token."""
        ...

    async def validate_token(self, token: str) -> bool:
        """Validate authentication token."""
        ...


@runtime_checkable
class TenantProvider(Protocol):
    """Protocol for tenant resolution providers."""

    async def get_current_tenant(self, user_id: Any) -> str | None:
        """Get current tenant for user."""
        ...

    async def validate_tenant_access(self, user_id: Any, tenant_id: str) -> bool:
        """Validate user access to tenant."""
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """Protocol for caching providers."""

    async def get(self, key: str) -> Any:
        """Get value from cache."""
        ...

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache."""
        ...

    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        ...


@runtime_checkable
class IntegrationProvider(Protocol):
    """Protocol for external integration providers."""

    async def call_external_service(
        self, service_name: str, method: str, **kwargs
    ) -> dict[str, Any]:
        """Call external service."""
        ...


@runtime_checkable
class ObservabilityProvider(Protocol):
    """Protocol for observability providers."""

    def log_metric(self, name: str, value: float, tags: dict[str, str] = None) -> None:
        """Log a metric."""
        ...

    def start_trace(self, name: str) -> Any:
        """Start a trace span."""
        ...


@dataclass
class Providers:
    """Container for all application providers."""

    # Core providers
    database: DatabaseProvider | None = None
    auth: AuthProvider | None = None
    tenant: TenantProvider | None = None

    # Optional providers
    cache: CacheProvider | None = None
    integrations: IntegrationProvider | None = None
    observability: ObservabilityProvider | None = None

    # Configuration
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, platform: bool = True) -> "Providers":
        """Create providers from environment configuration."""
        providers = cls()

        if platform:
            providers._load_platform_providers()
        else:
            providers._load_default_providers()

        return providers

    def _load_platform_providers(self) -> None:
        """Load platform service providers."""
        logger.info("Loading platform service providers...")

        # Try to load platform database provider
        try:
            from dotmac.platform.database import DatabaseProvider as PlatformDBProvider
            self.database = PlatformDBProvider()
            logger.info("✅ Platform database provider loaded")
        except ImportError:
            logger.warning("⚠️ Platform database provider not available")

        # Try to load platform auth provider
        try:
            from dotmac.platform.auth import AuthProvider as PlatformAuthProvider
            self.auth = PlatformAuthProvider()
            logger.info("✅ Platform auth provider loaded")
        except ImportError:
            logger.warning("⚠️ Platform auth provider not available")

        # Try to load platform tenant provider
        try:
            from dotmac.platform.tenant import TenantProvider as PlatformTenantProvider
            self.tenant = PlatformTenantProvider()
            logger.info("✅ Platform tenant provider loaded")
        except ImportError:
            logger.warning("⚠️ Platform tenant provider not available")

        # Try to load platform cache provider
        try:
            from dotmac.platform.cache import CacheProvider as PlatformCacheProvider
            self.cache = PlatformCacheProvider()
            logger.info("✅ Platform cache provider loaded")
        except ImportError:
            logger.debug("Platform cache provider not available (optional)")

        # Try to load platform observability provider
        try:
            from dotmac.platform.observability import (
                ObservabilityProvider as PlatformObsProvider,
            )
            self.observability = PlatformObsProvider()
            logger.info("✅ Platform observability provider loaded")
        except ImportError:
            logger.debug("Platform observability provider not available (optional)")

    def _load_default_providers(self) -> None:
        """Load default/mock providers for development."""
        logger.info("Loading default providers for development...")

        # Use simple mock implementations
        self.database = MockDatabaseProvider()
        self.auth = MockAuthProvider()
        self.tenant = MockTenantProvider()

        logger.info("✅ Default providers loaded")

    def validate_required_providers(self) -> None:
        """Validate that required providers are available."""
        errors = []

        if not self.database:
            errors.append("Database provider is required")

        if not self.auth:
            errors.append("Auth provider is required")

        if errors:
            raise RuntimeError(f"Missing required providers: {', '.join(errors)}")

        logger.info("✅ All required providers validated")


# Mock implementations for development/testing

class MockDatabaseProvider:
    """Mock database provider for development."""

    async def get_session(self) -> Any:
        """Mock database session."""
        return MockSession()

    async def close_session(self, session: Any) -> None:
        """Mock session close."""
        pass


class MockSession:
    """Mock database session."""

    async def execute(self, query: str) -> Any:
        """Mock query execution."""
        return {"result": "mock"}

    async def commit(self) -> None:
        """Mock commit."""
        pass

    async def rollback(self) -> None:
        """Mock rollback."""
        pass


class MockAuthProvider:
    """Mock auth provider for development."""

    async def get_current_user(self, token: str) -> dict[str, Any]:
        """Mock current user."""
        return {
            "user_id": 1,
            "email": "test@example.com",
            "is_active": True,
            "is_admin": False,
        }

    async def validate_token(self, token: str) -> bool:
        """Mock token validation."""
        return token == "valid_token"


class MockTenantProvider:
    """Mock tenant provider for development."""

    async def get_current_tenant(self, user_id: Any) -> str | None:
        """Mock current tenant."""
        return "tenant_123"

    async def validate_tenant_access(self, user_id: Any, tenant_id: str) -> bool:
        """Mock tenant access validation."""
        return True


# Export main classes
__all__ = [
    "Providers",
    "DatabaseProvider",
    "AuthProvider",
    "TenantProvider",
    "CacheProvider",
    "IntegrationProvider",
    "ObservabilityProvider",
]

