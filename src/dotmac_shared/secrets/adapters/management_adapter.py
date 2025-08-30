"""
Management Platform Secrets Adapter

Provides integration between the Management Platform and the shared secrets management system.
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


class ManagementPlatformSecretsAdapter:
    """
    Adapter for Management Platform secrets integration.

    Provides:
    - Multi-tenant secret management
    - Organization-based access control
    - API key management
    - Webhook secret handling
    """

    def __init__(
        self,
        secrets_manager: Optional[EnterpriseSecretsManager] = None,
        vault_client: Optional[OpenBaoClient] = None,
        rbac_manager: Optional[RBACManager] = None,
    ):
        """
        Initialize the Management Platform secrets adapter.

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

        # Initialize Management Platform specific secret types
        self._initialize_management_secrets()

    def _initialize_management_secrets(self) -> None:
        """Initialize Management Platform specific secrets in the manager."""
        if not self._secrets_manager:
            return

        # Common Management Platform secrets
        management_secrets = [
            {
                "secret_id": "PLATFORM_API_KEY",
                "secret_type": SecretType.API_KEY,
                "description": "Management platform API master key",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 30,
            },
            {
                "secret_id": "DATABASE_ENCRYPTION_KEY",
                "secret_type": SecretType.ENCRYPTION_KEY,
                "description": "Database field encryption master key",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 90,
            },
            {
                "secret_id": "WEBHOOK_SIGNING_SECRET",
                "secret_type": SecretType.WEBHOOK_SECRET,
                "description": "Webhook payload signing secret",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 60,
            },
            {
                "secret_id": "JWT_ACCESS_TOKEN_SECRET",
                "secret_type": SecretType.JWT_SECRET,
                "description": "JWT access token signing secret",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 7,
            },
            {
                "secret_id": "OAUTH_CLIENT_SECRET",
                "secret_type": SecretType.OAUTH_CLIENT_SECRET,
                "description": "OAuth client secret for external integrations",
                "source": SecretSource.VAULT,
                "is_critical": True,
                "auto_rotate": True,
                "rotation_interval_days": 90,
            },
        ]

        for secret_config in management_secrets:
            try:
                self._secrets_manager.register_secret(**secret_config)
                logger.debug(
                    f"Registered Management Platform secret: {secret_config['secret_id']}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to register Management Platform secret {secret_config['secret_id']}: {e}"
                )

    async def get_platform_api_key(
        self, organization_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Get API key for the Management Platform.

        Args:
            organization_id: Optional organization ID for org-specific API key

        Returns:
            API key or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            # Try organization-specific key first
            secret_id = (
                f"API_KEY_{organization_id}" if organization_id else "PLATFORM_API_KEY"
            )
            api_key = await self._secrets_manager.get_secret(secret_id)

            # Fall back to platform key if org-specific not found
            if not api_key and organization_id:
                api_key = await self._secrets_manager.get_secret("PLATFORM_API_KEY")

            if api_key:
                logger.info(
                    f"Retrieved API key for organization: {organization_id or 'platform'}"
                )
            else:
                logger.warning(
                    f"API key not found for organization: {organization_id or 'platform'}"
                )

            return api_key

        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            return None

    async def get_database_encryption_key(
        self, table_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Get database field encryption key.

        Args:
            table_name: Optional table name for table-specific encryption

        Returns:
            Encryption key or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            # Try table-specific key first
            secret_id = (
                f"DB_ENCRYPTION_{table_name}"
                if table_name
                else "DATABASE_ENCRYPTION_KEY"
            )
            encryption_key = await self._secrets_manager.get_secret(secret_id)

            # Fall back to master key if table-specific not found
            if not encryption_key and table_name:
                encryption_key = await self._secrets_manager.get_secret(
                    "DATABASE_ENCRYPTION_KEY"
                )

            if encryption_key:
                logger.info(
                    f"Retrieved database encryption key for table: {table_name or 'default'}"
                )
            else:
                logger.warning(
                    f"Database encryption key not found for table: {table_name or 'default'}"
                )

            return encryption_key

        except Exception as e:
            logger.error(f"Failed to get database encryption key: {e}")
            return None

    async def get_webhook_signing_secret(
        self, webhook_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Get webhook signing secret.

        Args:
            webhook_id: Optional webhook ID for webhook-specific secret

        Returns:
            Webhook signing secret or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            secret_id = (
                f"WEBHOOK_SECRET_{webhook_id}"
                if webhook_id
                else "WEBHOOK_SIGNING_SECRET"
            )
            webhook_secret = await self._secrets_manager.get_secret(secret_id)

            # Fall back to default webhook secret
            if not webhook_secret and webhook_id:
                webhook_secret = await self._secrets_manager.get_secret(
                    "WEBHOOK_SIGNING_SECRET"
                )

            if webhook_secret:
                logger.info(
                    f"Retrieved webhook signing secret for: {webhook_id or 'default'}"
                )
            else:
                logger.warning(
                    f"Webhook signing secret not found for: {webhook_id or 'default'}"
                )

            return webhook_secret

        except Exception as e:
            logger.error(f"Failed to get webhook signing secret: {e}")
            return None

    async def get_jwt_secret(self, token_type: str = "access") -> Optional[str]:
        """
        Get JWT signing secret.

        Args:
            token_type: Type of token (access, refresh, etc.)

        Returns:
            JWT secret or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            secret_id = f"JWT_{token_type.upper()}_TOKEN_SECRET"
            jwt_secret = await self._secrets_manager.get_secret(secret_id)

            if jwt_secret:
                logger.info(f"Retrieved JWT secret for token type: {token_type}")
            else:
                logger.warning(f"JWT secret not found for token type: {token_type}")

            return jwt_secret

        except Exception as e:
            logger.error(f"Failed to get JWT secret: {e}")
            return None

    async def get_oauth_credentials(self, provider: str) -> Optional[Dict[str, str]]:
        """
        Get OAuth credentials for external integrations.

        Args:
            provider: OAuth provider name (google, microsoft, etc.)

        Returns:
            OAuth credentials or None if not found
        """
        if not self._secrets_manager:
            logger.error("Secrets manager not available")
            return None

        try:
            # Get client ID and secret
            client_id_secret = f"OAUTH_{provider.upper()}_CLIENT_ID"
            client_secret_secret = f"OAUTH_{provider.upper()}_CLIENT_SECRET"

            client_id = await self._secrets_manager.get_secret(client_id_secret)
            client_secret = await self._secrets_manager.get_secret(client_secret_secret)

            if client_id and client_secret:
                credentials = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
                logger.info(f"Retrieved OAuth credentials for provider: {provider}")
                return credentials
            else:
                logger.warning(f"OAuth credentials not found for provider: {provider}")
                return None

        except Exception as e:
            logger.error(f"Failed to get OAuth credentials: {e}")
            return None

    async def store_organization_secrets(
        self,
        organization_id: str,
        secrets: Dict[str, str],
    ) -> bool:
        """
        Store organization-specific secrets.

        Args:
            organization_id: Organization identifier
            secrets: Dictionary of secret key-value pairs

        Returns:
            True if successful, False otherwise
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return False

        try:
            # Store in organization-specific vault path
            vault_path = f"organizations/{organization_id}/secrets"

            success = await self._vault_client.put_secret(vault_path, secrets)

            if success:
                logger.info(f"Stored organization secrets for: {organization_id}")
            else:
                logger.error(
                    f"Failed to store organization secrets for: {organization_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to store organization secrets: {e}")
            return False

    async def get_organization_secrets(
        self, organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve organization-specific secrets.

        Args:
            organization_id: Organization identifier

        Returns:
            Organization secrets or None if not found
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return None

        try:
            vault_path = f"organizations/{organization_id}/secrets"
            secrets = await self._vault_client.get_secret(vault_path)

            if secrets:
                logger.info(f"Retrieved organization secrets for: {organization_id}")
            else:
                logger.warning(f"Organization secrets not found for: {organization_id}")

            return secrets

        except Exception as e:
            logger.error(f"Failed to get organization secrets: {e}")
            return None

    async def generate_api_key(
        self,
        organization_id: str,
        key_name: str,
        permissions: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Generate a new API key for an organization.

        Args:
            organization_id: Organization identifier
            key_name: Name for the API key
            permissions: Optional list of permissions

        Returns:
            Generated API key or None if failed
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return None

        try:
            import secrets
            import string

            # Generate a secure API key
            alphabet = string.ascii_letters + string.digits
            api_key = "".join(secrets.choice(alphabet) for _ in range(64))

            # Store API key metadata
            api_key_data = {
                "key": api_key,
                "organization_id": organization_id,
                "name": key_name,
                "permissions": permissions or [],
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True,
            }

            vault_path = f"organizations/{organization_id}/api_keys/{key_name}"
            success = await self._vault_client.put_secret(vault_path, api_key_data)

            if success:
                logger.info(
                    f"Generated API key '{key_name}' for organization: {organization_id}"
                )
                return api_key
            else:
                logger.error(
                    f"Failed to store API key '{key_name}' for organization: {organization_id}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to generate API key: {e}")
            return None

    async def revoke_api_key(self, organization_id: str, key_name: str) -> bool:
        """
        Revoke an API key for an organization.

        Args:
            organization_id: Organization identifier
            key_name: Name of the API key to revoke

        Returns:
            True if successful, False otherwise
        """
        if not self._vault_client:
            logger.error("Vault client not available")
            return False

        try:
            vault_path = f"organizations/{organization_id}/api_keys/{key_name}"

            # Get existing API key data
            api_key_data = await self._vault_client.get_secret(vault_path)
            if not api_key_data:
                logger.warning(
                    f"API key '{key_name}' not found for organization: {organization_id}"
                )
                return False

            # Mark as inactive instead of deleting (for audit purposes)
            api_key_data["is_active"] = False
            api_key_data["revoked_at"] = datetime.utcnow().isoformat()

            success = await self._vault_client.put_secret(vault_path, api_key_data)

            if success:
                logger.info(
                    f"Revoked API key '{key_name}' for organization: {organization_id}"
                )
            else:
                logger.error(
                    f"Failed to revoke API key '{key_name}' for organization: {organization_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Failed to revoke API key: {e}")
            return False

    async def setup_organization_rbac(
        self, organization_id: str, admin_user_id: str
    ) -> bool:
        """
        Setup RBAC for a new organization.

        Args:
            organization_id: Organization identifier
            admin_user_id: Initial admin user ID

        Returns:
            True if successful, False otherwise
        """
        if not self._rbac_manager:
            logger.error("RBAC manager not available")
            return False

        try:
            # Create organization-specific roles
            org_admin_role = f"org_{organization_id}_admin"
            org_manager_role = f"org_{organization_id}_manager"
            org_user_role = f"org_{organization_id}_user"

            # Create organization admin role
            self._rbac_manager.create_role(
                role_id=org_admin_role,
                name=f"Organization {organization_id} Administrator",
                description=f"Administrator role for organization {organization_id}",
                permissions={
                    "secret:read",
                    "secret:create",
                    "secret:update",
                    "secret:delete",
                    "secret:rotate",
                    "encryption_key:read",
                    "encryption_key:manage",
                    "vault_path:read",
                    "vault_path:write",
                    "audit_log:read",
                    "role:manage",
                },
            )

            # Create organization manager role
            self._rbac_manager.create_role(
                role_id=org_manager_role,
                name=f"Organization {organization_id} Manager",
                description=f"Manager role for organization {organization_id}",
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

            # Create organization user role
            self._rbac_manager.create_role(
                role_id=org_user_role,
                name=f"Organization {organization_id} User",
                description=f"User role for organization {organization_id}",
                permissions={"secret:read", "audit_log:read"},
            )

            # Create admin subject and assign role
            admin_subject_id = f"{organization_id}_{admin_user_id}"
            self._rbac_manager.create_subject(
                subject_id=admin_subject_id,
                subject_type="user",
                roles={org_admin_role},
                attributes={"organization_id": organization_id},
                session_duration=7200,  # 2 hours
            )

            logger.info(f"Setup RBAC for organization: {organization_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to setup organization RBAC: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the Management Platform secrets adapter.

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
