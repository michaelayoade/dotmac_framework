"""Secret management service for secure configuration injection."""

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..schemas.config_schemas import ISPConfiguration

logger = logging.getLogger(__name__)


class SecretEncryption:
    """Handles encryption and decryption of secrets."""

    def __init__(self, master_key: Optional[str] = None):
        """Initialize encryption with master key."""
        if master_key:
            self.master_key = master_key.encode()
        else:
            # Generate or get from environment
            self.master_key = os.getenv("SECRET_ENCRYPTION_KEY", "").encode()
            if not self.master_key:
                # Generate a new key (for development only)
                self.master_key = Fernet.generate_key()
                logger.warning(
                    "Generated new encryption key - should be configured in production"
                )

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"dotmac_config_salt",  # In production, use random salt per secret
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext and return base64 encoded ciphertext."""
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64 encoded ciphertext and return plaintext."""
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = self.fernet.decrypt(encrypted)
        return decrypted.decode()

    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted."""
        try:
            base64.urlsafe_b64decode(value.encode())
            # Additional validation could be added here
            return len(value) > 20 and "=" in value
        except Exception:
            return False


from abc import ABC, abstractmethod

class SecretStore(ABC):
    """Abstract secret storage interface."""

    @abstractmethod
    async def store_secret(
        self,
        tenant_id: UUID,
        key: str,
        encrypted_value: str,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Store an encrypted secret."""
        pass

    @abstractmethod
    async def get_secret(self, tenant_id: UUID, key: str) -> Optional[str]:
        """Retrieve an encrypted secret."""
        pass

    @abstractmethod
    async def delete_secret(self, tenant_id: UUID, key: str) -> bool:
        """Delete a secret."""
        pass

    @abstractmethod
    async def list_secrets(self, tenant_id: UUID) -> List[str]:
        """List secret keys for a tenant."""
        pass

    @abstractmethod
    async def rotate_secret(
        self, tenant_id: UUID, key: str, new_encrypted_value: str
    ) -> bool:
        """Rotate a secret."""
        pass


class InMemorySecretStore(SecretStore):
    """In-memory secret store for development/testing."""

    def __init__(self):
        self._secrets: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, tenant_id: UUID, key: str) -> str:
        """Create internal key for storage."""
        return f"{tenant_id}:{key}"

    async def store_secret(
        self,
        tenant_id: UUID,
        key: str,
        encrypted_value: str,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Store an encrypted secret."""
        internal_key = self._make_key(tenant_id, key)
        self._secrets[internal_key] = {
            "value": encrypted_value,
            "metadata": metadata or {},
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return True

    async def get_secret(self, tenant_id: UUID, key: str) -> Optional[str]:
        """Retrieve an encrypted secret."""
        internal_key = self._make_key(tenant_id, key)
        secret_data = self._secrets.get(internal_key)
        return secret_data["value"] if secret_data else None

    async def delete_secret(self, tenant_id: UUID, key: str) -> bool:
        """Delete a secret."""
        internal_key = self._make_key(tenant_id, key)
        if internal_key in self._secrets:
            del self._secrets[internal_key]
            return True
        return False

    async def list_secrets(self, tenant_id: UUID) -> List[str]:
        """List secret keys for a tenant."""
        tenant_prefix = f"{tenant_id}:"
        return [
            key.replace(tenant_prefix, "")
            for key in self._secrets.keys()
            if key.startswith(tenant_prefix)
        ]

    async def rotate_secret(
        self, tenant_id: UUID, key: str, new_encrypted_value: str
    ) -> bool:
        """Rotate a secret."""
        internal_key = self._make_key(tenant_id, key)
        if internal_key in self._secrets:
            self._secrets[internal_key]["value"] = new_encrypted_value
            self._secrets[internal_key]["updated_at"] = datetime.now()
            return True
        return False


class DatabaseSecretStore(SecretStore):
    """Database-backed secret store (placeholder implementation)."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        # In real implementation, would initialize database connection

    async def store_secret(
        self,
        tenant_id: UUID,
        key: str,
        encrypted_value: str,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Store an encrypted secret in database."""
        # Placeholder - would implement actual database storage
        logger.info(f"Would store secret {key} for tenant {tenant_id} in database")
        return True

    async def get_secret(self, tenant_id: UUID, key: str) -> Optional[str]:
        """Retrieve an encrypted secret from database."""
        # Placeholder - would implement actual database retrieval
        logger.info(f"Would retrieve secret {key} for tenant {tenant_id} from database")
        return None

    async def delete_secret(self, tenant_id: UUID, key: str) -> bool:
        """Delete a secret from database."""
        # Placeholder - would implement actual database deletion
        logger.info(f"Would delete secret {key} for tenant {tenant_id} from database")
        return True

    async def list_secrets(self, tenant_id: UUID) -> List[str]:
        """List secret keys for a tenant from database."""
        # Placeholder - would implement actual database query
        logger.info(f"Would list secrets for tenant {tenant_id} from database")
        return []

    async def rotate_secret(
        self, tenant_id: UUID, key: str, new_encrypted_value: str
    ) -> bool:
        """Rotate a secret in database."""
        # Placeholder - would implement actual database update
        logger.info(f"Would rotate secret {key} for tenant {tenant_id} in database")
        return True


class SecretManager:
    """
    Secure secret management for configuration injection.

    Handles encryption, storage, rotation, and injection of secrets
    into configuration templates and objects.
    """

    SECRET_PLACEHOLDER_PATTERN = re.compile(r"\$\{SECRET:([^}]+)\}")

    def __init__(
        self,
        secret_store: Optional[SecretStore] = None,
        encryption: Optional[SecretEncryption] = None,
        rotation_interval_days: int = 90,
        enable_auto_rotation: bool = False,
    ):
        """Initialize the secret manager."""
        self.secret_store = secret_store or InMemorySecretStore()
        self.encryption = encryption or SecretEncryption()
        self.rotation_interval_days = rotation_interval_days
        self.enable_auto_rotation = enable_auto_rotation

        # Predefined secret generators for auto-generation
        self.secret_generators = {
            "jwt_secret_key": self._generate_jwt_secret,
            "encryption_key": self._generate_encryption_key,
            "api_key": self._generate_api_key,
            "database_password": self._generate_database_password,
            "redis_password": self._generate_redis_password,
        }

    async def store_secret(
        self,
        tenant_id: UUID,
        key: str,
        value: str,
        rotation_interval_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store an encrypted secret.

        Args:
            tenant_id: Tenant identifier
            key: Secret key/name
            value: Secret value (plaintext)
            rotation_interval_days: Custom rotation interval
            metadata: Additional metadata

        Returns:
            True if stored successfully
        """
        try:
            # Encrypt the secret value
            encrypted_value = self.encryption.encrypt(value)

            # Prepare metadata
            secret_metadata = {
                "rotation_interval_days": rotation_interval_days
                or self.rotation_interval_days,
                "created_at": datetime.now().isoformat(),
                "auto_generated": False,
                **(metadata or {}),
            }

            # Store in secret store
            success = await self.secret_store.store_secret(
                tenant_id, key, encrypted_value, secret_metadata
            )

            if success:
                logger.info(f"Stored secret {key} for tenant {tenant_id}")
            else:
                logger.error(f"Failed to store secret {key} for tenant {tenant_id}")

            return success

        except Exception as e:
            logger.error(f"Error storing secret {key} for tenant {tenant_id}: {e}")
            return False

    async def get_secret(self, tenant_id: UUID, key: str) -> Optional[str]:
        """
        Retrieve and decrypt a secret.

        Args:
            tenant_id: Tenant identifier
            key: Secret key/name

        Returns:
            Decrypted secret value or None if not found
        """
        try:
            encrypted_value = await self.secret_store.get_secret(tenant_id, key)
            if not encrypted_value:
                return None

            # Decrypt the secret
            decrypted_value = self.encryption.decrypt(encrypted_value)
            logger.debug(f"Retrieved secret {key} for tenant {tenant_id}")

            return decrypted_value

        except Exception as e:
            logger.error(f"Error retrieving secret {key} for tenant {tenant_id}: {e}")
            return None

    async def inject_secrets(self, config: ISPConfiguration) -> ISPConfiguration:
        """
        Inject secrets into configuration object.

        Searches for secret placeholders in the format ${SECRET:key_name}
        and replaces them with actual secret values.

        Args:
            config: Configuration object with secret placeholders

        Returns:
            Configuration object with secrets injected
        """
        logger.info(f"Injecting secrets for tenant {config.tenant_id}")

        try:
            # Convert config to dictionary for processing
            config_dict = config.model_dump()

            # Find and replace secret placeholders
            await self._inject_secrets_recursive(config_dict, config.tenant_id)

            # Create new configuration object with secrets
            return ISPConfiguration.model_validate(config_dict)

        except Exception as e:
            logger.error(f"Failed to inject secrets for tenant {config.tenant_id}: {e}")
            raise

    async def _inject_secrets_recursive(
        self, obj: Any, tenant_id: UUID, path: str = ""
    ) -> None:
        """Recursively inject secrets into nested objects."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, str):
                    obj[key] = await self._replace_secret_placeholders(
                        value, tenant_id, current_path
                    )
                elif isinstance(value, (dict, list)):
                    await self._inject_secrets_recursive(value, tenant_id, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                if isinstance(item, str):
                    obj[i] = await self._replace_secret_placeholders(
                        item, tenant_id, current_path
                    )
                elif isinstance(item, (dict, list)):
                    await self._inject_secrets_recursive(item, tenant_id, current_path)

    async def _replace_secret_placeholders(
        self, value: str, tenant_id: UUID, path: str
    ) -> str:
        """Replace secret placeholders in a string value."""
        if not isinstance(value, str):
            return value

        matches = self.SECRET_PLACEHOLDER_PATTERN.findall(value)
        if not matches:
            return value

        result = value
        for secret_key in matches:
            secret_value = await self.get_secret(tenant_id, secret_key)

            if secret_value is None:
                # Try to auto-generate the secret if we have a generator
                if secret_key in self.secret_generators:
                    logger.info(
                        f"Auto-generating secret {secret_key} for tenant {tenant_id}"
                    )
                    secret_value = await self._auto_generate_secret(
                        tenant_id, secret_key
                    )
                else:
                    logger.warning(
                        f"Secret {secret_key} not found for tenant {tenant_id} at {path}"
                    )
                    continue

            placeholder = f"${{SECRET:{secret_key}}}"
            result = result.replace(placeholder, secret_value)

        return result

    async def _auto_generate_secret(
        self, tenant_id: UUID, secret_key: str
    ) -> Optional[str]:
        """Auto-generate a secret using the appropriate generator."""
        generator = self.secret_generators.get(secret_key)
        if not generator:
            return None

        # Generate the secret
        secret_value = generator()

        # Store the generated secret
        success = await self.store_secret(
            tenant_id=tenant_id,
            key=secret_key,
            value=secret_value,
            metadata={"auto_generated": True},
        )

        return secret_value if success else None

    def _generate_jwt_secret(self) -> str:
        """Generate a JWT secret key."""
        import secrets

        return secrets.token_urlsafe(64)

    def _generate_encryption_key(self) -> str:
        """Generate an encryption key."""
        return Fernet.generate_key().decode()

    def _generate_api_key(self) -> str:
        """Generate an API key."""
        import secrets

        return f"dtmac_{''.join(secrets.choice('0123456789abcdef') for _ in range(32))}"

    def _generate_database_password(self) -> str:
        """Generate a database password."""
        import secrets
        import string

        # Generate a strong password
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = "".join(secrets.choice(alphabet) for _ in range(32))

        # Ensure at least one of each character type
        password = password[:28] + "A1!" + password[31:]
        return password

    def _generate_redis_password(self) -> str:
        """Generate a Redis password."""
        import secrets

        return secrets.token_urlsafe(32)

    async def rotate_secret(self, tenant_id: UUID, key: str) -> bool:
        """
        Rotate a secret to a new value.

        Args:
            tenant_id: Tenant identifier
            key: Secret key to rotate

        Returns:
            True if rotated successfully
        """
        try:
            # Generate new secret value
            if key in self.secret_generators:
                new_value = self.secret_generators[key]()
            else:
                # Default rotation - generate random value
                import secrets

                new_value = secrets.token_urlsafe(32)

            # Store the new secret
            success = await self.store_secret(
                tenant_id=tenant_id,
                key=key,
                value=new_value,
                metadata={"rotated_at": datetime.now().isoformat()},
            )

            if success:
                logger.info(f"Rotated secret {key} for tenant {tenant_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to rotate secret {key} for tenant {tenant_id}: {e}")
            return False

    async def rotate_expired_secrets(self) -> List[Tuple[UUID, str, bool]]:
        """
        Rotate all expired secrets across all tenants.

        Returns:
            List of (tenant_id, secret_key, success) tuples
        """
        if not self.enable_auto_rotation:
            return []

        results = []

        # This is a placeholder implementation
        # In a real implementation, you would query the secret store
        # for all secrets that are past their rotation interval

        logger.info("Auto-rotation is enabled but not implemented in placeholder")
        return results

    async def validate_secret_access(
        self, tenant_id: UUID, secret_key: str, user_id: Optional[str] = None
    ) -> bool:
        """
        Validate that access to a secret is authorized.

        Args:
            tenant_id: Tenant identifier
            secret_key: Secret key being accessed
            user_id: Optional user identifier for access control

        Returns:
            True if access is authorized
        """
        # Basic validation - in production would implement RBAC
        try:
            # Check if secret exists
            secret_exists = (
                await self.secret_store.get_secret(tenant_id, secret_key) is not None
            )

            # For now, allow access if secret exists
            # In production, would check user permissions, API keys, etc.
            return secret_exists

        except Exception as e:
            logger.error(f"Error validating secret access: {e}")
            return False

    async def list_tenant_secrets(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        List all secrets for a tenant (without values).

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of secret metadata
        """
        try:
            secret_keys = await self.secret_store.list_secrets(tenant_id)

            secrets_info = []
            for key in secret_keys:
                secrets_info.append(
                    {
                        "key": key,
                        "tenant_id": str(tenant_id),
                        "exists": True,
                        "auto_generated": key in self.secret_generators,
                    }
                )

            return secrets_info

        except Exception as e:
            logger.error(f"Failed to list secrets for tenant {tenant_id}: {e}")
            return []

    async def backup_secrets(self, tenant_id: UUID) -> Dict[str, str]:
        """
        Create an encrypted backup of tenant secrets.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Encrypted backup data
        """
        try:
            secret_keys = await self.secret_store.list_secrets(tenant_id)

            backup_data = {}
            for key in secret_keys:
                # Get encrypted value (don't decrypt for backup)
                encrypted_value = await self.secret_store.get_secret(tenant_id, key)
                if encrypted_value:
                    backup_data[key] = encrypted_value

            # Create backup metadata
            backup = {
                "tenant_id": str(tenant_id),
                "created_at": datetime.now().isoformat(),
                "secrets": backup_data,
                "version": "1.0",
            }

            # Encrypt the entire backup
            backup_json = json.dumps(backup)
            encrypted_backup = self.encryption.encrypt(backup_json)

            logger.info(
                f"Created backup with {len(backup_data)} secrets for tenant {tenant_id}"
            )

            return {"backup": encrypted_backup}

        except Exception as e:
            logger.error(f"Failed to backup secrets for tenant {tenant_id}: {e}")
            return {}

    def create_secret_placeholder(self, secret_key: str) -> str:
        """Create a secret placeholder string."""
        return f"${{SECRET:{secret_key}}}"

    def extract_secret_keys(self, text: str) -> List[str]:
        """Extract all secret keys from a text containing placeholders."""
        return self.SECRET_PLACEHOLDER_PATTERN.findall(text)
