"""
Hardened Secret Factory Integration

Provides secure secret retrieval for the DotMac application factory
with OpenBao/Vault integration and environment-specific enforcement.
"""

import os
from typing import Any, Optional
from uuid import UUID

import structlog

from ..application.config import DeploymentContext, DeploymentMode
from .secrets_policy import (
    Environment,
    HardenedSecretsManager,
    SecretsEnvironmentError,
    SecretType,
    create_secrets_manager,
)

logger = structlog.get_logger(__name__)


class HardenedSecretFactory:
    """
    Hardened secret factory with environment-specific security enforcement.

    Integrates with DotMac application factory to provide production-grade
    secret management with OpenBao/Vault requirement in production.
    """

    _instance: Optional["HardenedSecretFactory"] = None
    _secrets_manager: Optional[HardenedSecretsManager] = None

    def __new__(cls) -> "HardenedSecretFactory":
        """Singleton pattern to ensure consistent secret management."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize hardened secret factory."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._secrets_manager = None
            self._environment_validated = False

    async def initialize(self, deployment_context: Optional[DeploymentContext] = None) -> None:
        """
        Initialize the secrets manager based on deployment context.

        Args:
            deployment_context: Deployment context for environment detection
        """
        if self._secrets_manager and self._environment_validated:
            return  # Already initialized and validated

        # Determine environment from deployment context or environment variables
        environment = self._determine_environment(deployment_context)

        try:
            self._secrets_manager = create_secrets_manager(
                environment=environment.value,
                vault_url=os.getenv("VAULT_URL"),
                vault_token=os.getenv("VAULT_TOKEN"),
            )

            # Validate environment compliance
            compliance = await self._secrets_manager.validate_environment_compliance()

            if not compliance["compliant"]:
                logger.error(
                    "Environment compliance validation failed",
                    violations=compliance["violations"],
                    environment=environment.value,
                )

                # In production, compliance failures are critical
                if environment == Environment.PRODUCTION:
                    raise SecretsEnvironmentError(
                        f"Production environment compliance failed: {compliance['violations']}",
                        environment,
                        SecretType.JWT_SECRET,
                    )

            self._environment_validated = True

            logger.info(
                "Hardened secret factory initialized",
                environment=environment.value,
                compliant=compliance["compliant"],
                store_status=compliance["store_status"],
            )

        except Exception as e:
            logger.error(f"Failed to initialize hardened secret factory: {e}")

            # In production, initialization failure is critical
            if environment == Environment.PRODUCTION:
                raise SecretsEnvironmentError(
                    f"Critical: Cannot initialize secrets in production: {e}",
                    environment,
                    SecretType.JWT_SECRET,
                ) from e

            # In development, log warning but continue
            logger.warning("Using fallback secret management in development", error=str(e))

    def _determine_environment(self, deployment_context: Optional[DeploymentContext]) -> Environment:
        """Determine environment from deployment context or environment variables."""

        # Check deployment context first
        if deployment_context:
            if deployment_context.mode == DeploymentMode.DEVELOPMENT:
                return Environment.DEVELOPMENT
            elif deployment_context.mode in [
                DeploymentMode.TENANT_CONTAINER,
                DeploymentMode.MANAGEMENT_PLATFORM,
            ]:
                # Check if this is production deployment
                env_name = os.getenv("ENVIRONMENT", "").lower()
                if env_name in ["production", "prod"]:
                    return Environment.PRODUCTION
                elif env_name in ["staging", "stage"]:
                    return Environment.STAGING
                else:
                    return Environment.DEVELOPMENT

        # Fallback to environment variable
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        try:
            return Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment '{env_name}', defaulting to development")
            return Environment.DEVELOPMENT

    async def get_jwt_secret(self, tenant_id: Optional[UUID] = None) -> str:
        """
        Retrieve JWT secret with production enforcement.

        Args:
            tenant_id: Optional tenant identifier for multi-tenant secrets

        Returns:
            JWT secret value

        Raises:
            SecretsEnvironmentError: If production requirements not met
        """
        await self._ensure_initialized()

        secret_value = await self._secrets_manager.get_secret(
            SecretType.JWT_SECRET, "auth", "jwt_secret_key", tenant_id
        )

        if not secret_value:
            # Fallback for development environments
            if self._secrets_manager.environment != Environment.PRODUCTION:
                secret_value = os.getenv("JWT_SECRET_KEY")
                if secret_value:
                    logger.warning(
                        "Using environment fallback for JWT secret",
                        environment=self._secrets_manager.environment.value,
                    )

            if not secret_value:
                raise SecretsEnvironmentError(
                    "JWT secret not available and required for operation",
                    self._secrets_manager.environment,
                    SecretType.JWT_SECRET,
                )

        return secret_value

    async def get_database_credentials(
        self, database_name: str = "main", tenant_id: Optional[UUID] = None
    ) -> dict[str, str]:
        """
        Retrieve database credentials with production enforcement.

        Args:
            database_name: Database identifier
            tenant_id: Optional tenant identifier

        Returns:
            Dictionary with 'username', 'password', and optionally other credentials
        """
        await self._ensure_initialized()

        credentials = {}

        # Get database password
        password = await self._secrets_manager.get_secret(
            SecretType.DATABASE_CREDENTIAL,
            f"database/{database_name}",
            "password",
            tenant_id,
        )

        if not password:
            # Fallback for development
            if self._secrets_manager.environment != Environment.PRODUCTION:
                password = os.getenv(f"DB_PASSWORD_{database_name.upper()}")
                if password:
                    logger.warning(
                        "Using environment fallback for database password",
                        database=database_name,
                        environment=self._secrets_manager.environment.value,
                    )

        if not password:
            raise SecretsEnvironmentError(
                f"Database password for '{database_name}' not available",
                self._secrets_manager.environment,
                SecretType.DATABASE_CREDENTIAL,
            )

        credentials["password"] = password

        # Get username (often not secret, but may be stored in vault)
        username = await self._secrets_manager.get_secret(
            SecretType.DATABASE_CREDENTIAL,
            f"database/{database_name}",
            "username",
            tenant_id,
        )

        if not username:
            # Fallback to environment or default
            username = os.getenv(f"DB_USERNAME_{database_name.upper()}", "dotmac_user")

        credentials["username"] = username

        return credentials

    async def get_service_api_key(self, service_name: str, tenant_id: Optional[UUID] = None) -> str:
        """
        Retrieve service API key with production enforcement.

        Args:
            service_name: Service identifier
            tenant_id: Optional tenant identifier

        Returns:
            API key value
        """
        await self._ensure_initialized()

        api_key = await self._secrets_manager.get_secret(
            SecretType.API_KEY, f"services/{service_name}", "api_key", tenant_id
        )

        if not api_key:
            # Fallback for development
            if self._secrets_manager.environment != Environment.PRODUCTION:
                api_key = os.getenv(f"API_KEY_{service_name.upper()}")
                if api_key:
                    logger.warning(
                        "Using environment fallback for service API key",
                        service=service_name,
                        environment=self._secrets_manager.environment.value,
                    )

        if not api_key:
            raise SecretsEnvironmentError(
                f"API key for service '{service_name}' not available",
                self._secrets_manager.environment,
                SecretType.API_KEY,
            )

        return api_key

    async def get_encryption_key(self, purpose: str = "default", tenant_id: Optional[UUID] = None) -> str:
        """
        Retrieve encryption key with strict production enforcement.

        Note: Encryption keys never fallback to environment variables
        as they require secure generation and storage.

        Args:
            purpose: Encryption key purpose identifier
            tenant_id: Optional tenant identifier

        Returns:
            Encryption key value
        """
        await self._ensure_initialized()

        encryption_key = await self._secrets_manager.get_secret(
            SecretType.ENCRYPTION_KEY, f"encryption/{purpose}", "key", tenant_id
        )

        if not encryption_key:
            raise SecretsEnvironmentError(
                f"Encryption key for '{purpose}' not available - no fallback allowed",
                self._secrets_manager.environment,
                SecretType.ENCRYPTION_KEY,
            )

        return encryption_key

    async def rotate_secrets(
        self,
        secret_types: Optional[list[SecretType]] = None,
        tenant_id: Optional[UUID] = None,
    ) -> dict[str, bool]:
        """
        Rotate specified secrets or all rotatable secrets.

        Args:
            secret_types: List of secret types to rotate (None for all)
            tenant_id: Optional tenant identifier

        Returns:
            Dictionary mapping secret paths to rotation success
        """
        await self._ensure_initialized()

        if secret_types is None:
            # Rotate commonly rotated secret types
            secret_types = [
                SecretType.JWT_SECRET,
                SecretType.API_KEY,
                SecretType.DATABASE_CREDENTIAL,
            ]

        results = {}

        for secret_type in secret_types:
            try:
                if secret_type == SecretType.JWT_SECRET:
                    success = await self._secrets_manager.rotate_secret(
                        secret_type, "auth", "jwt_secret_key", tenant_id
                    )
                    results[f"{secret_type.value}/auth/jwt_secret_key"] = success

                elif secret_type == SecretType.DATABASE_CREDENTIAL:
                    success = await self._secrets_manager.rotate_secret(
                        secret_type, "database/main", "password", tenant_id
                    )
                    results[f"{secret_type.value}/database/main/password"] = success

                elif secret_type == SecretType.API_KEY:
                    # Would need to know which services to rotate
                    logger.info("API key rotation requires specific service names")
                    results[f"{secret_type.value}/services/*"] = False

            except Exception as e:
                logger.error(f"Failed to rotate {secret_type.value}: {e}")
                results[f"{secret_type.value}/*"] = False

        return results

    async def validate_security_compliance(self) -> dict[str, Any]:
        """
        Validate current security compliance for audit purposes.

        Returns:
            Detailed compliance report
        """
        await self._ensure_initialized()

        return await self._secrets_manager.validate_environment_compliance()

    async def _ensure_initialized(self) -> None:
        """Ensure the secrets manager is initialized."""
        if not self._secrets_manager:
            await self.initialize()


# Global singleton instance
hardened_secret_factory = HardenedSecretFactory()


# Convenience functions for integration with existing code
async def get_hardened_jwt_secret(tenant_id: Optional[UUID] = None) -> str:
    """Get JWT secret with hardened security enforcement."""
    return await hardened_secret_factory.get_jwt_secret(tenant_id)


async def get_hardened_db_credentials(database_name: str = "main", tenant_id: Optional[UUID] = None) -> dict[str, str]:
    """Get database credentials with hardened security enforcement."""
    return await hardened_secret_factory.get_database_credentials(database_name, tenant_id)


async def get_hardened_service_api_key(service_name: str, tenant_id: Optional[UUID] = None) -> str:
    """Get service API key with hardened security enforcement."""
    return await hardened_secret_factory.get_service_api_key(service_name, tenant_id)


async def initialize_hardened_secrets(
    deployment_context: Optional[DeploymentContext] = None,
) -> None:
    """Initialize hardened secret management for application startup."""
    await hardened_secret_factory.initialize(deployment_context)


async def validate_secrets_compliance() -> dict[str, Any]:
    """Validate security compliance for monitoring/auditing."""
    return await hardened_secret_factory.validate_security_compliance()
