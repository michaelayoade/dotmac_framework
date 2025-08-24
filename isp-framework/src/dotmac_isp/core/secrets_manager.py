"""
Centralized secrets management with OpenBao/Vault integration.
Provides secure storage, retrieval, and rotation of sensitive configuration.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import hvac
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets managed by the system."""

    JWT_SECRET = "jwt_secret"
    DATABASE_PASSWORD = "database_password"
    API_KEY = "api_key"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_SECRET = "oauth_secret"
    WEBHOOK_SECRET = "webhook_secret"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"


class SecretMetadata(BaseModel):
    """Metadata for managed secrets."""

    secret_id: str
    secret_type: SecretType
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    rotation_interval_days: Optional[int] = None
    last_rotated: Optional[datetime] = None
    environment: str
    service: str
    tags: List[str] = Field(default_factory=list)
    encrypted: bool = True


class SecretValue(BaseModel):
    """Secure secret value container."""

    value: str
    metadata: SecretMetadata
    checksum: str


class SecretsManager:
    """
    Centralized secrets management with multiple backend support.
    Supports OpenBao/Vault, local encrypted storage, and environment variables.
    """

    def __init__(
        """  Init   operation."""
        self,
        backend: str = "openbao",
        openbao_url: Optional[str] = None,
        openbao_token: Optional[str] = None,
        encryption_key: Optional[str] = None,
        local_storage_path: str = "/etc/dotmac/secrets",
    ):
        self.backend = backend
        self.openbao_url = openbao_url or os.getenv(
            "OPENBAO_URL", "http://localhost:8200"
        )
        self.openbao_token = openbao_token or os.getenv("OPENBAO_TOKEN")
        self.local_storage_path = local_storage_path

        # Initialize encryption for local storage
        self.encryption_key = encryption_key or os.getenv("SECRETS_ENCRYPTION_KEY")
        if self.encryption_key:
            self._cipher = self._create_cipher(self.encryption_key)
        else:
            self._cipher = None

        # Initialize backend
        self._vault_client = None
        self._initialize_backend()

    def _create_cipher(self, password: str) -> Fernet:
        """Create encryption cipher from password."""
        password_bytes = password.encode()
        salt = b"dotmac_salt_2024"  # In production, use random salt per secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return Fernet(key)

    def _initialize_backend(self):
        """Initialize the secrets backend."""
        if self.backend == "openbao" and self.openbao_token:
            try:
                self._vault_client = hvac.Client(
                    url=self.openbao_url, token=self.openbao_token
                )
                if self._vault_client.is_authenticated():
                    logger.info("OpenBao client initialized successfully")
                else:
                    logger.warning(
                        "OpenBao authentication failed, falling back to local storage"
                    )
                    self.backend = "local"
            except Exception as e:
                logger.error(f"Failed to initialize OpenBao client: {e}")
                self.backend = "local"

        if self.backend == "local":
            os.makedirs(self.local_storage_path, mode=0o700, exist_ok=True)
            logger.info(
                f"Local secrets storage initialized at {self.local_storage_path}"
            )

    async def store_secret(
        self,
        secret_id: str,
        value: str,
        secret_type: SecretType,
        environment: str,
        service: str,
        expires_at: Optional[datetime] = None,
        rotation_interval_days: Optional[int] = None,
        tags: Optional[List[str]] = None,
        overwrite: bool = False,
    ) -> SecretMetadata:
        """
        Store a secret securely.

        Args:
            secret_id: Unique identifier for the secret
            value: The secret value to store
            secret_type: Type of secret
            environment: Environment (development/staging/production)
            service: Service name
            expires_at: Optional expiration datetime
            rotation_interval_days: Automatic rotation interval
            tags: Optional tags for organization
            overwrite: Whether to overwrite existing secret

        Returns:
            SecretMetadata for the stored secret
        """
        # Check if secret already exists
        existing = await self.get_secret_metadata(secret_id)
        if existing and not overwrite:
            raise ValueError(
                f"Secret {secret_id} already exists. Use overwrite=True to replace."
            )

        # Create metadata
        now = datetime.utcnow()
        metadata = SecretMetadata(
            secret_id=secret_id,
            secret_type=secret_type,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days,
            last_rotated=now if rotation_interval_days else None,
            environment=environment,
            service=service,
            tags=tags or [],
            encrypted=True,
        )

        # Calculate checksum
        checksum = self._calculate_checksum(value)

        # Store based on backend
        if self.backend == "openbao" and self._vault_client:
            await self._store_secret_vault(secret_id, value, metadata, checksum)
        else:
            await self._store_secret_local(secret_id, value, metadata, checksum)

        # Log the operation (without secret value)
        logger.info(
            f"Secret stored: {secret_id} (type: {secret_type}, env: {environment}, service: {service})"
        )

        return metadata

    async def get_secret(self, secret_id: str) -> Optional[SecretValue]:
        """
        Retrieve a secret value.

        Args:
            secret_id: Secret identifier

        Returns:
            SecretValue if found, None otherwise
        """
        if self.backend == "openbao" and self._vault_client:
            return await self._get_secret_vault(secret_id)
        else:
            return await self._get_secret_local(secret_id)

    async def get_secret_metadata(self, secret_id: str) -> Optional[SecretMetadata]:
        """Get secret metadata without the actual value."""
        secret = await self.get_secret(secret_id)
        return secret.metadata if secret else None

    async def list_secrets(
        self,
        environment: Optional[str] = None,
        service: Optional[str] = None,
        secret_type: Optional[SecretType] = None,
        include_expired: bool = False,
    ) -> List[SecretMetadata]:
        """
        List secrets with optional filtering.

        Args:
            environment: Filter by environment
            service: Filter by service
            secret_type: Filter by secret type
            include_expired: Include expired secrets

        Returns:
            List of SecretMetadata
        """
        if self.backend == "openbao" and self._vault_client:
            return await self._list_secrets_vault(
                environment, service, secret_type, include_expired
            )
        else:
            return await self._list_secrets_local(
                environment, service, secret_type, include_expired
            )

    async def rotate_secret(
        self, secret_id: str, new_value: Optional[str] = None
    ) -> SecretMetadata:
        """
        Rotate a secret value.

        Args:
            secret_id: Secret to rotate
            new_value: New value (if None, auto-generate based on type)

        Returns:
            Updated SecretMetadata
        """
        # Get existing secret
        secret = await self.get_secret(secret_id)
        if not secret:
            raise ValueError(f"Secret {secret_id} not found")

        # Generate new value if not provided
        if new_value is None:
            new_value = self._generate_secret_value(secret.metadata.secret_type)

        # Update secret
        metadata = secret.metadata
        metadata.updated_at = datetime.utcnow()
        metadata.last_rotated = datetime.utcnow()

        # Store updated secret
        await self.store_secret(
            secret_id=secret_id,
            value=new_value,
            secret_type=metadata.secret_type,
            environment=metadata.environment,
            service=metadata.service,
            expires_at=metadata.expires_at,
            rotation_interval_days=metadata.rotation_interval_days,
            tags=metadata.tags,
            overwrite=True,
        )

        logger.info(f"Secret rotated: {secret_id}")
        return metadata

    async def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret.

        Args:
            secret_id: Secret to delete

        Returns:
            True if deleted, False if not found
        """
        if self.backend == "openbao" and self._vault_client:
            result = await self._delete_secret_vault(secret_id)
        else:
            result = await self._delete_secret_local(secret_id)

        if result:
            logger.info(f"Secret deleted: {secret_id}")

        return result

    async def check_secret_health(self) -> Dict[str, Any]:
        """
        Check health of secrets management system.

        Returns:
            Health status and metrics
        """
        health = {
            "backend": self.backend,
            "status": "healthy",
            "secrets_count": 0,
            "expired_secrets": 0,
            "rotation_due": 0,
            "backend_accessible": False,
            "encryption_available": self._cipher is not None,
        }

        try:
            # Check backend accessibility
            if self.backend == "openbao" and self._vault_client:
                health["backend_accessible"] = self._vault_client.is_authenticated()
            else:
                health["backend_accessible"] = os.path.exists(self.local_storage_path)

            # Get secrets statistics
            all_secrets = await self.list_secrets(include_expired=True)
            health["secrets_count"] = len(all_secrets)

            now = datetime.utcnow()
            for secret in all_secrets:
                # Check expiration
                if secret.expires_at and secret.expires_at < now:
                    health["expired_secrets"] += 1

                # Check rotation due
                if (
                    secret.rotation_interval_days
                    and secret.last_rotated
                    and secret.last_rotated
                    + timedelta(days=secret.rotation_interval_days)
                    < now
                ):
                    health["rotation_due"] += 1

            # Set status based on issues
            if health["expired_secrets"] > 0 or health["rotation_due"] > 0:
                health["status"] = "warning"
            if not health["backend_accessible"]:
                health["status"] = "critical"

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
            logger.error(f"Secret health check failed: {e}")

        return health

    # Backend-specific implementations

    async def _store_secret_vault(
        self, secret_id: str, value: str, metadata: SecretMetadata, checksum: str
    ):
        """Store secret in OpenBao/Vault."""
        secret_path = (
            f"secret/dotmac/{metadata.environment}/{metadata.service}/{secret_id}"
        )
        secret_data = {
            "value": value,
            "metadata": metadata.dict(),
            "checksum": checksum,
        }

        self._vault_client.secrets.kv.v2.create_or_update_secret(
            path=secret_path, secret=secret_data
        )

    async def _get_secret_vault(self, secret_id: str) -> Optional[SecretValue]:
        """Retrieve secret from OpenBao/Vault."""
        try:
            # Try to find secret in all environments/services
            for env in ["development", "staging", "production"]:
                for service in [
                    "api",
                    "auth",
                    "billing",
                    "core",
                ]:  # Add more services as needed
                    secret_path = f"secret/dotmac/{env}/{service}/{secret_id}"
                    try:
                        response = self._vault_client.secrets.kv.v2.read_secret_version(
                            path=secret_path
                        )
                        secret_data = response["data"]["data"]

                        return SecretValue(
                            value=secret_data["value"],
                            metadata=SecretMetadata(**secret_data["metadata"]),
                            checksum=secret_data["checksum"],
                        )
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(f"Invalid secret data format in response: {e}")
                        continue
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve secret from Vault: {e}")
            return None

    async def _store_secret_local(
        self, secret_id: str, value: str, metadata: SecretMetadata, checksum: str
    ):
        """Store secret in local encrypted storage."""
        secret_file = os.path.join(self.local_storage_path, f"{secret_id}.json")

        secret_data = {
            "value": self._encrypt_value(value) if self._cipher else value,
            "metadata": metadata.dict(),
            "checksum": checksum,
        }

        with open(secret_file, "w", mode=0o600) as f:
            json.dump(secret_data, f, default=str)

    async def _get_secret_local(self, secret_id: str) -> Optional[SecretValue]:
        """Retrieve secret from local storage."""
        secret_file = os.path.join(self.local_storage_path, f"{secret_id}.json")

        if not os.path.exists(secret_file):
            return None

        try:
            with open(secret_file, "r") as f:
                secret_data = json.load(f)

            value = secret_data["value"]
            if self._cipher and secret_data["metadata"].get("encrypted", True):
                value = self._decrypt_value(value)

            return SecretValue(
                value=value,
                metadata=SecretMetadata(**secret_data["metadata"]),
                checksum=secret_data["checksum"],
            )
        except Exception as e:
            logger.error(f"Failed to read local secret {secret_id}: {e}")
            return None

    async def _list_secrets_local(
        self,
        environment: Optional[str] = None,
        service: Optional[str] = None,
        secret_type: Optional[SecretType] = None,
        include_expired: bool = False,
    ) -> List[SecretMetadata]:
        """List secrets from local storage."""
        secrets = []

        if not os.path.exists(self.local_storage_path):
            return secrets

        for filename in os.listdir(self.local_storage_path):
            if not filename.endswith(".json"):
                continue

            try:
                secret_file = os.path.join(self.local_storage_path, filename)
                with open(secret_file, "r") as f:
                    secret_data = json.load(f)

                metadata = SecretMetadata(**secret_data["metadata"])

                # Apply filters
                if environment and metadata.environment != environment:
                    continue
                if service and metadata.service != service:
                    continue
                if secret_type and metadata.secret_type != secret_type:
                    continue
                if (
                    not include_expired
                    and metadata.expires_at
                    and metadata.expires_at < datetime.utcnow()
                ):
                    continue

                secrets.append(metadata)

            except Exception as e:
                logger.warning(f"Failed to read secret metadata from {filename}: {e}")

        return secrets

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a secret value."""
        if not self._cipher:
            return value
        return self._cipher.encrypt(value.encode()).decode()

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a secret value."""
        if not self._cipher:
            return encrypted_value
        return self._cipher.decrypt(encrypted_value.encode()).decode()

    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for secret value."""
        import hashlib

        return hashlib.sha256(value.encode()).hexdigest()

    def _generate_secret_value(self, secret_type: SecretType) -> str:
        """Generate a new secret value based on type."""
        import secrets

        if secret_type == SecretType.JWT_SECRET:
            return secrets.token_urlsafe(64)
        elif secret_type == SecretType.DATABASE_PASSWORD:
            return secrets.token_urlsafe(32)
        elif secret_type == SecretType.API_KEY:
            return f"sk_{secrets.token_urlsafe(32)}"
        elif secret_type == SecretType.ENCRYPTION_KEY:
            return secrets.token_urlsafe(32)
        else:
            return secrets.token_urlsafe(32)


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


async def init_secrets_manager(
    backend: str = "openbao",
    openbao_url: Optional[str] = None,
    openbao_token: Optional[str] = None,
    encryption_key: Optional[str] = None,
) -> SecretsManager:
    """Initialize the global secrets manager."""
    global _secrets_manager
    _secrets_manager = SecretsManager(
        backend=backend,
        openbao_url=openbao_url,
        openbao_token=openbao_token,
        encryption_key=encryption_key,
    )
    return _secrets_manager
