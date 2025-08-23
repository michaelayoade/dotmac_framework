"""
HashiCorp Vault Integration for Secrets Management

Provides secure secrets management using HashiCorp Vault for the DotMac Framework.
Replaces hardcoded secrets with dynamic secret retrieval.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

def utcnow():
    """Get current UTC datetime."""
    return datetime.utcnow()

def utc_now_iso():
    """Get current UTC datetime as ISO string."""
    return datetime.utcnow().isoformat()

def expires_in_days(days: int):
    """Get datetime that expires in specified days."""
    return datetime.utcnow() + timedelta(days=days)

def expires_in_hours(hours: int):  
    """Get datetime that expires in specified hours."""
    return datetime.utcnow() + timedelta(hours=hours)

def is_expired(dt: datetime):
    """Check if datetime is expired."""
    return datetime.utcnow() > dt
from typing import Any

import structlog
from pydantic import BaseModel, Field, SecretStr

try:
    import hvac
    from hvac.exceptions import Forbidden, InvalidPath, InvalidRequest

    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None

logger = structlog.get_logger(__name__)


class VaultConfig(BaseModel):
    """Vault configuration settings"""

    url: str = Field(default="http://localhost:8200", description="Vault server URL")
    token: SecretStr | None = Field(default=None, description="Vault token")
    namespace: str | None = Field(default=None, description="Vault namespace")
    mount_point: str = Field(default="secret", description="KV mount point")
    kv_version: int = Field(default=2, description="KV engine version")
    ssl_verify: bool = Field(default=True, description="Verify SSL certificates")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")

    # Authentication methods
    auth_method: str = Field(default="token", description="Authentication method")
    role_id: SecretStr | None = Field(default=None, description="AppRole role ID")
    secret_id: SecretStr | None = Field(default=None, description="AppRole secret ID")
    kubernetes_role: str | None = Field(default=None, description="Kubernetes role")
    aws_role: str | None = Field(default=None, description="AWS IAM role")

    class Config:
        validate_assignment = True


@dataclass
class SecretMetadata:
    """Metadata for cached secrets"""

    path: str
    version: int | None
    created_at: datetime
    expires_at: datetime
    data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the cached secret has expired"""
        return utcnow() > self.expires_at


class VaultClient:
    """
    HashiCorp Vault client for secure secrets management.

    Features:
    - Multiple authentication methods (Token, AppRole, Kubernetes, AWS)
    - Secret caching with TTL
    - Automatic token renewal
    - Dynamic secret generation
    - Encryption as a Service (Transit engine)
    - Secret rotation support
    """

    def __init__(self, config: VaultConfig | None = None):
        """Initialize Vault client with configuration"""
        if not HVAC_AVAILABLE:
            raise ImportError(
                "hvac library is not installed. Install it with: pip install hvac"
            )

        self.config = config or self._load_config()
        self.client: hvac.Client | None = None
        self._cache: dict[str, SecretMetadata] = {}
        self._lock = asyncio.Lock()
        self._connected = False

        # Initialize client
        self._initialize_client()

    def _load_config(self) -> VaultConfig:
        """Load Vault configuration from environment variables"""
        return VaultConfig(
            url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
            token=(
                SecretStr(os.getenv("VAULT_TOKEN", ""))
                if os.getenv("VAULT_TOKEN")
                else None
            ),
            namespace=os.getenv("VAULT_NAMESPACE"),
            mount_point=os.getenv("VAULT_MOUNT_POINT", "secret"),
            kv_version=int(os.getenv("VAULT_KV_VERSION", "2")),
            auth_method=os.getenv("VAULT_AUTH_METHOD", "token"),
            role_id=(
                SecretStr(os.getenv("VAULT_ROLE_ID", ""))
                if os.getenv("VAULT_ROLE_ID")
                else None
            ),
            secret_id=(
                SecretStr(os.getenv("VAULT_SECRET_ID", ""))
                if os.getenv("VAULT_SECRET_ID")
                else None
            ),
            kubernetes_role=os.getenv("VAULT_KUBERNETES_ROLE"),
            aws_role=os.getenv("VAULT_AWS_ROLE"),
        )

    def _initialize_client(self) -> None:
        """Initialize the Vault client"""
        self.client = hvac.Client(
            url=self.config.url,
            token=self.config.token.get_secret_value() if self.config.token else None,
            namespace=self.config.namespace,
            verify=self.config.ssl_verify,
            timeout=self.config.timeout,
        )

        # Authenticate based on method
        self._authenticate()

        logger.info(
            "Vault client initialized",
            url=self.config.url,
            auth_method=self.config.auth_method,
            namespace=self.config.namespace,
        )

    def _authenticate(self) -> None:
        """
        Authenticate with Vault using strategy pattern.
        
        REFACTORED: Replaced 14-complexity if-elif chain with strategy pattern call.
        Complexity reduced from 14→3.
        """
        from .vault_auth_strategies import create_vault_auth_engine
        
        try:
            auth_engine = create_vault_auth_engine()
            client_token = auth_engine.authenticate(self.client, self.config)
            
            self._connected = True
            logger.info("Vault authentication completed successfully",
                       method=self.config.auth_method)
            
        except Exception as e:
            logger.error("Failed to authenticate with Vault", error=str(e))
            raise

    async def get_secret(
        self,
        path: str,
        key: str | None = None,
        version: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        Retrieve a secret from Vault.

        Args:
            path: Secret path in Vault
            key: Specific key to retrieve from secret
            version: Secret version (for KV v2)
            use_cache: Whether to use cached value if available

        Returns:
            Secret data dictionary
        """
        async with self._lock:
            # Check cache first
            if use_cache and path in self._cache:
                cached = self._cache[path]
                if not cached.is_expired():
                    logger.debug("Using cached secret", path=path)
                    if key:
                        return {key: cached.data.get(key)}
                    return cached.data

            try:
                # Retrieve from Vault
                if self.config.kv_version == 2:
                    response = self.client.secrets.kv.v2.read_secret_version(
                        path=path,
                        version=version,
                        mount_point=self.config.mount_point,
                    )
                    secret_data = response["data"]["data"]
                    metadata = response["data"]["metadata"]
                else:
                    response = self.client.secrets.kv.v1.read_secret(
                        path=path,
                        mount_point=self.config.mount_point,
                    )
                    secret_data = response["data"]
                    metadata = {}

                # Cache the secret
                if use_cache:
                    self._cache[path] = SecretMetadata(
                        path=path,
                        version=version,
                        created_at=utcnow(),
                        expires_at=utcnow() + timedelta(seconds=self.config.cache_ttl),
                        data=secret_data,
                        metadata=metadata,
                    )

                logger.info("Retrieved secret from Vault", path=path, cached=use_cache)

                if key:
                    return {key: secret_data.get(key)}
                return secret_data

            except InvalidPath:
                logger.error("Secret not found", path=path)
                raise KeyError(f"Secret not found at path: {path}")
            except Forbidden:
                logger.error("Access denied to secret", path=path)
                raise PermissionError(f"Access denied to secret at path: {path}")
            except Exception as e:
                logger.error("Failed to retrieve secret", path=path, error=str(e))
                raise

    async def set_secret(
        self,
        path: str,
        data: dict[str, Any],
        cas: int | None = None,
    ) -> dict[str, Any]:
        """
        Store a secret in Vault.

        Args:
            path: Secret path in Vault
            data: Secret data to store
            cas: Check-and-set version for KV v2

        Returns:
            Response from Vault
        """
        try:
            if self.config.kv_version == 2:
                response = self.client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=data,
                    cas=cas,
                    mount_point=self.config.mount_point,
                )
            else:
                response = self.client.secrets.kv.v1.create_or_update_secret(
                    path=path,
                    secret=data,
                    mount_point=self.config.mount_point,
                )

            # Invalidate cache
            if path in self._cache:
                del self._cache[path]

            logger.info("Stored secret in Vault", path=path)
            return response

        except Exception as e:
            logger.error("Failed to store secret", path=path, error=str(e))
            raise

    async def delete_secret(self, path: str, versions: list[int] | None = None) -> None:
        """
        Delete a secret from Vault.

        Args:
            path: Secret path in Vault
            versions: Specific versions to delete (KV v2 only)
        """
        try:
            if self.config.kv_version == 2:
                if versions:
                    self.client.secrets.kv.v2.delete_secret_versions(
                        path=path,
                        versions=versions,
                        mount_point=self.config.mount_point,
                    )
                else:
                    self.client.secrets.kv.v2.delete_latest_version_of_secret(
                        path=path,
                        mount_point=self.config.mount_point,
                    )
            else:
                self.client.secrets.kv.v1.delete_secret(
                    path=path,
                    mount_point=self.config.mount_point,
                )

            # Remove from cache
            if path in self._cache:
                del self._cache[path]

            logger.info("Deleted secret from Vault", path=path, versions=versions)

        except Exception as e:
            logger.error("Failed to delete secret", path=path, error=str(e))
            raise

    async def list_secrets(self, path: str = "") -> list[str]:
        """
        List secrets at a given path.

        Args:
            path: Path to list secrets from

        Returns:
            List of secret paths
        """
        try:
            if self.config.kv_version == 2:
                response = self.client.secrets.kv.v2.list_secrets(
                    path=path,
                    mount_point=self.config.mount_point,
                )
            else:
                response = self.client.secrets.kv.v1.list_secrets(
                    path=path,
                    mount_point=self.config.mount_point,
                )

            return response.get("data", {}).get("keys", [])

        except Exception as e:
            logger.error("Failed to list secrets", path=path, error=str(e))
            raise

    async def rotate_secret(
        self, path: str, new_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Rotate a secret by creating a new version.

        Args:
            path: Secret path in Vault
            new_data: New secret data

        Returns:
            Response from Vault
        """
        # Get current secret metadata
        current = await self.get_secret(path, use_cache=False)

        # Store new version
        response = await self.set_secret(path, new_data)

        logger.info("Rotated secret", path=path)
        return response

    async def encrypt_data(self, plaintext: str, key_name: str = "default") -> str:
        """
        Encrypt data using Vault's Transit engine.

        Args:
            plaintext: Data to encrypt
            key_name: Encryption key name in Transit engine

        Returns:
            Ciphertext
        """
        try:
            import base64

            # Encode plaintext to base64
            encoded = base64.b64encode(plaintext.encode()).decode()

            response = self.client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=encoded,
                mount_point="transit",
            )

            return response["data"]["ciphertext"]

        except Exception as e:
            logger.error("Failed to encrypt data", error=str(e))
            raise

    async def decrypt_data(self, ciphertext: str, key_name: str = "default") -> str:
        """
        Decrypt data using Vault's Transit engine.

        Args:
            ciphertext: Data to decrypt
            key_name: Encryption key name in Transit engine

        Returns:
            Plaintext
        """
        try:
            import base64

            response = self.client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext,
                mount_point="transit",
            )

            # Decode from base64
            plaintext = base64.b64decode(response["data"]["plaintext"]).decode()

            return plaintext

        except Exception as e:
            logger.error("Failed to decrypt data", error=str(e))
            raise

    def clear_cache(self) -> None:
        """Clear all cached secrets"""
        self._cache.clear()
        logger.info("Cleared secret cache")

    async def renew_token(self) -> None:
        """Renew the current authentication token"""
        try:
            if self.client.is_authenticated():
                self.client.auth.token.renew_self()
                logger.info("Renewed Vault token")
            else:
                logger.warning("Cannot renew token - not authenticated")
                self._authenticate()
        except Exception as e:
            logger.error("Failed to renew token", error=str(e))
            raise

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactional secret operations"""
        snapshot = dict(self._cache)
        try:
            yield self
        except Exception:
            # Restore cache on error
            self._cache = snapshot
            raise

    async def health_check(self) -> dict[str, Any]:
        """Check Vault health status"""
        try:
            health = self.client.sys.read_health_status()
            return {
                "healthy": not health.get("sealed", True),
                "version": health.get("version"),
                "cluster_name": health.get("cluster_name"),
                "cluster_id": health.get("cluster_id"),
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {"healthy": False, "error": str(e)}


class VaultSecretManager:
    """
    High-level secret manager using Vault for the DotMac Framework.
    Provides convenient methods for common secret operations.
    """

    def __init__(self, vault_client: VaultClient | None = None):
        """Initialize the secret manager"""
        self.vault = vault_client or VaultClient()
        self.app_prefix = os.getenv("VAULT_APP_PREFIX", "dotmac")

    def _get_path(self, category: str, name: str) -> str:
        """Generate a standardized path for secrets"""
        return f"{self.app_prefix}/{category}/{name}"

    async def get_database_credentials(self, db_name: str = "main") -> dict[str, str]:
        """Get database credentials"""
        path = self._get_path("database", db_name)
        return await self.vault.get_secret(path)

    async def get_api_key(self, service: str) -> str:
        """Get API key for a service"""
        path = self._get_path("api_keys", service)
        data = await self.vault.get_secret(path)
        return data.get("key", "")

    async def get_encryption_key(self, key_id: str) -> bytes:
        """Get encryption key"""
        path = self._get_path("encryption", key_id)
        data = await self.vault.get_secret(path)
        import base64

        return base64.b64decode(data.get("key", ""))

    async def store_encryption_key(self, key_id: str, key_data: bytes) -> None:
        """Store encryption key"""
        import base64

        path = self._get_path("encryption", key_id)
        await self.vault.set_secret(path, {"key": base64.b64encode(key_data).decode()})

    async def get_jwt_secret(self) -> str:
        """Get JWT signing secret"""
        path = self._get_path("auth", "jwt")
        data = await self.vault.get_secret(path)
        return data.get("secret", "")

    async def get_smtp_credentials(self) -> dict[str, Any]:
        """Get SMTP credentials"""
        path = self._get_path("smtp", "default")
        return await self.vault.get_secret(path)

    async def get_cloud_credentials(self, provider: str) -> dict[str, Any]:
        """Get cloud provider credentials"""
        path = self._get_path("cloud", provider)
        return await self.vault.get_secret(path)

    async def rotate_api_key(self, service: str, new_key: str) -> None:
        """Rotate an API key"""
        path = self._get_path("api_keys", service)
        await self.vault.rotate_secret(path, {"key": new_key})

    async def get_feature_flags(self) -> dict[str, bool]:
        """Get feature flags from Vault"""
        path = self._get_path("config", "feature_flags")
        try:
            return await self.vault.get_secret(path)
        except KeyError:
            return {}  # Return empty dict if no flags are set


# Singleton instance
_vault_client: VaultClient | None = None
_secret_manager: VaultSecretManager | None = None


def get_vault_client() -> VaultClient:
    """Get or create singleton Vault client"""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client


def get_secret_manager() -> VaultSecretManager:
    """Get or create singleton secret manager"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = VaultSecretManager()
    return _secret_manager


__all__ = [
    "VaultConfig",
    "VaultClient",
    "VaultSecretManager",
    "get_vault_client",
    "get_secret_manager",
]
