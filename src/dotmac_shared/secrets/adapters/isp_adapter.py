"""
ISP Framework Secrets Adapter

Provides integration between the ISP Framework and the shared secrets management system.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Import core secrets components
try:
    from ..core.enterprise_secrets_manager import (
        EnterpriseSecretsManager,
        SecretSource,
        SecretType,
    )
    from ..core.rbac import RBACManager
    from ..core.vault_client import OpenBaoClient, VaultConfig

    SECRETS_CORE_AVAILABLE = True
except ImportError:
    SECRETS_CORE_AVAILABLE = False
    EnterpriseSecretsManager = VaultConfig = OpenBaoClient = RBACManager = None


class ISPSecretsAdapter:
    """
    Adapter for ISP Framework secrets integration.

    Provides:
    - ISP-specific secret management
    - Tenant-based secret isolation
    - Customer data encryption
    - Network device credentials
    """

    def __init__(
        self,
        secrets_manager: Optional[EnterpriseSecretsManager] = None,
        vault_client: Optional[OpenBaoClient] = None,
        rbac_manager: Optional[RBACManager] = None,
    ):
        """
        Initialize the ISP secrets adapter.

        Args:
            secrets_manager: Enterprise secrets manager instance
            vault_client: Vault client instance
            rbac_manager: RBAC manager instance
        """
        if not SECRETS_CORE_AVAILABLE:
            logger.warning(
                "Secrets core components not available, adapter will have limited functionality"
            )

        self._secrets_manager = secrets_manager
        self._vault_client = vault_client
        self._rbac_manager = rbac_manager

        # Initialize ISP-specific secret types
        self._initialize_isp_secrets()

    def _initialize_isp_secrets(self) -> None:
        """Initialize ISP-specific secrets in the manager."""
        if not self._secrets_manager:
            return

        # Common ISP secrets
        isp_secrets = [
            {
                "secret_id": "RADIUS_SHARED_SECRET",
                "secret_type": SecretType.RADIUS_SECRET,
                "description": "RADIUS shared secret for network authentication",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 90,
            },
            {
                "secret_id": "DATABASE_PASSWORD",
                "secret_type": SecretType.DATABASE_PASSWORD,
                "description": "ISP framework database password",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 30,
            },
            {
                "secret_id": "JWT_SECRET_KEY",
                "secret_type": SecretType.JWT_SECRET,
                "description": "JWT signing key for ISP authentication",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 7,
            },
            {
                "secret_id": "CUSTOMER_ENCRYPTION_KEY",
                "secret_type": SecretType.ENCRYPTION_KEY,
                "description": "Master key for customer data encryption",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 60,
            },
        ]

        for secret_config in isp_secrets:
            try:
                self._secrets_manager.register_secret(**secret_config)
                logger.debug(f"Registered ISP secret: {secret_config['secret_id']}")
            except Exception as e:
                logger.error(
                    f"Failed to register ISP secret {secret_config['secret_id']}: {e}"
                )

    async def get_database_credentials(
        self, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Get database credentials for the ISP framework.

        Args:
            tenant_id: Optional tenant ID for tenant-specific credentials

        Returns:
            Dictionary with database credentials or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            # Get database password
            db_password = await self._secrets_manager.get_secret("DATABASE_PASSWORD")
            if not db_password:
                logger.error("Database password not found")
                return None

            # Get other database configuration from environment
            import os

            credentials = {
                "host": os.getenv("DATABASE_HOST", "localhost"),
                "port": os.getenv("DATABASE_PORT", "5432"),
                "database": os.getenv("DATABASE_NAME", "dotmac_isp"),
                "username": os.getenv("DATABASE_USER", "dotmac_user"),
                "password": db_password,
            }

            # Add tenant-specific database if provided
            if tenant_id:
                credentials["database"] = f"dotmac_isp_tenant_{tenant_id}"

            logger.info(
                f"Retrieved database credentials for tenant: {tenant_id or 'default'}"
            )
            return credentials

        except Exception as e:
            logger.error(f"Failed to get database credentials: {e}")
            return None

    async def get_radius_secret(
        self, nas_identifier: Optional[str] = None
    ) -> Optional[str]:
        """
        Get RADIUS shared secret for network authentication.

        Args:
            nas_identifier: Optional NAS identifier for device-specific secrets

        Returns:
            RADIUS shared secret or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            secret_id = (
                f"RADIUS_SECRET_{nas_identifier}"
                if nas_identifier
                else "RADIUS_SHARED_SECRET"
            )
            radius_secret = await self._secrets_manager.get_secret(secret_id)

            if radius_secret:
                logger.info(
                    f"Retrieved RADIUS secret for NAS: {nas_identifier or 'default'}"
                )
            else:
                logger.warning(
                    f"RADIUS secret not found for NAS: {nas_identifier or 'default'}"
                )

            return radius_secret

        except Exception as e:
            logger.error(f"Failed to get RADIUS secret: {e}")
            return None

    async def get_jwt_secret(self) -> Optional[str]:
        """
        Get JWT signing secret for ISP authentication.

        Returns:
            JWT secret or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            jwt_secret = await self._secrets_manager.get_secret("JWT_SECRET_KEY")

            if jwt_secret:
                logger.info("Retrieved JWT secret for authentication")
            else:
                logger.warning("JWT secret not found")

            return jwt_secret

        except Exception as e:
            logger.error(f"Failed to get JWT secret: {e}")
            return None

    async def get_customer_encryption_key(self, tenant_id: str) -> Optional[str]:
        """
        Get customer data encryption key for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Encryption key or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            # Check if tenant-specific key exists
            tenant_key_id = f"CUSTOMER_ENCRYPTION_KEY_{tenant_id}"
            encryption_key = await self._secrets_manager.get_secret(tenant_key_id)

            if not encryption_key:
                # Fall back to default key
                encryption_key = await self._secrets_manager.get_secret(
                    "CUSTOMER_ENCRYPTION_KEY"
                )

            if encryption_key:
                logger.info(
                    f"Retrieved customer encryption key for tenant: {tenant_id}"
                )
            else:
                logger.warning(
                    f"Customer encryption key not found for tenant: {tenant_id}"
                )

            return encryption_key

        except Exception as e:
            logger.error(f"Failed to get customer encryption key: {e}")
            return None

    async def store_device_credentials(
        self,
        device_id: str,
        credentials: Dict[str, str],
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        Store network device credentials securely.

        Args:
            device_id: Network device identifier
            credentials: Device credentials dictionary
            tenant_id: Optional tenant ID

        Returns:
            True if successful, False otherwise
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return False

        try:
            # Create vault path for device credentials
            vault_path = f"network/devices/{device_id}"
            if tenant_id:
                vault_path = f"tenants/{tenant_id}/network/devices/{device_id}"

            # Store credentials in vault
            success = await self._vault_client.put_secret(vault_path, credentials)

            if success:
                logger.info(f"Stored device credentials for: {device_id}")
            else:
                logger.error(f"Failed to store device credentials for: {device_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to store device credentials: {e}")
            return False

    async def get_device_credentials(
        self,
        device_id: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve network device credentials.

        Args:
            device_id: Network device identifier
            tenant_id: Optional tenant ID

        Returns:
            Device credentials or None if not found
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return None

        try:
            # Create vault path for device credentials
            vault_path = f"network/devices/{device_id}"
            if tenant_id:
                vault_path = f"tenants/{tenant_id}/network/devices/{device_id}"

            # Retrieve credentials from vault
            credentials = await self._vault_client.get_secret(vault_path)

            if credentials:
                logger.info(f"Retrieved device credentials for: {device_id}")
            else:
                logger.warning(f"Device credentials not found for: {device_id}")

            return credentials

        except Exception as e:
            logger.error(f"Failed to get device credentials: {e}")
            return None

    async def rotate_tenant_secrets(self, tenant_id: str) -> Dict[str, bool]:
        """
        Rotate all secrets for a specific tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dictionary mapping secret IDs to rotation success status
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return {}

        results = {}

        # List of tenant-specific secrets to rotate
        tenant_secrets = [
            f"DATABASE_PASSWORD_{tenant_id}",
            f"CUSTOMER_ENCRYPTION_KEY_{tenant_id}",
            f"API_KEY_{tenant_id}",
        ]

        for secret_id in tenant_secrets:
            try:
                success = await self._secrets_manager.rotate_secret(secret_id)
                results[secret_id] = success

                if success:
                    logger.info(f"Rotated secret: {secret_id}")
                else:
                    logger.warning(f"Failed to rotate secret: {secret_id}")

            except Exception as e:
                logger.error(f"Error rotating secret {secret_id}: {e}")
                results[secret_id] = False

        logger.info(f"Tenant secret rotation completed for: {tenant_id}")
        return results

    async def setup_tenant_rbac(self, tenant_id: str, admin_user_id: str) -> bool:
        """
        Setup RBAC for a new tenant.

        Args:
            tenant_id: Tenant identifier
            admin_user_id: Initial admin user ID

        Returns:
            True if successful, False otherwise
        """
        if not self._rbac_manager:
            logger.error("RBAC manager not available")
            return False

        try:
            # Create tenant-specific roles
            tenant_admin_role = f"tenant_{tenant_id}_admin"
            tenant_user_role = f"tenant_{tenant_id}_user"

            # Create tenant admin role
            self._rbac_manager.create_role(
                role_id=tenant_admin_role,
                name=f"Tenant {tenant_id} Administrator",
                description=f"Administrator role for tenant {tenant_id}",
                permissions={
                    "secret:read",
                    "secret:create",
                    "secret:update",
                    "secret:rotate",
                    "encryption_key:read",
                    "vault_path:read",
                    "audit_log:read",
                },
            )

            # Create tenant user role
            self._rbac_manager.create_role(
                role_id=tenant_user_role,
                name=f"Tenant {tenant_id} User",
                description=f"User role for tenant {tenant_id}",
                permissions={"secret:read", "audit_log:read"},
            )

            # Create admin subject and assign role
            admin_subject_id = f"{tenant_id}_{admin_user_id}"
            self._rbac_manager.create_subject(
                subject_id=admin_subject_id,
                subject_type="user",
                roles={tenant_admin_role},
                attributes={"tenant_id": tenant_id},
                session_duration=3600,  # 1 hour
            )

            logger.info(f"Setup RBAC for tenant: {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup tenant RBAC: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the ISP secrets adapter.

        Returns:
            Health status information
        """
        status = {
            "healthy": True,
            "secrets_core_available": SECRETS_CORE_AVAILABLE,
            "secrets_manager": self._secrets_manager is not None,
            "vault_client": self._vault_client is not None,
            "rbac_manager": self._rbac_manager is not None,
            "checks": [],
        }

        # Check secrets manager
        if self._secrets_manager:
            try:
                secrets_health = await self._secrets_manager.health_check()
                status["checks"].append(
                    {
                        "name": "secrets_manager",
                        "status": (
                            "healthy" if secrets_health["healthy"] else "unhealthy"
                        ),
                        "details": secrets_health,
                    }
                )
            except Exception as e:
                status["healthy"] = False
                status["checks"].append(
                    {
                        "name": "secrets_manager",
                        "status": "unhealthy",
                        "error": str(e),
                    }
                )

        # Check vault client
        if self._vault_client:
            try:
                vault_health = await self._vault_client.health_check()
                status["checks"].append(
                    {
                        "name": "vault_client",
                        "status": "healthy" if vault_health["healthy"] else "unhealthy",
                        "details": vault_health,
                    }
                )
            except Exception as e:
                status["healthy"] = False
                status["checks"].append(
                    {
                        "name": "vault_client",
                        "status": "unhealthy",
                        "error": str(e),
                    }
                )

        # Check RBAC manager
        if self._rbac_manager:
            try:
                rbac_health = await self._rbac_manager.health_check()
                status["checks"].append(
                    {
                        "name": "rbac_manager",
                        "status": "healthy" if rbac_health["healthy"] else "unhealthy",
                        "details": rbac_health,
                    }
                )
            except Exception as e:
                status["healthy"] = False
                status["checks"].append(
                    {
                        "name": "rbac_manager",
                        "status": "unhealthy",
                        "error": str(e),
                    }
                )

        return status
