"""
OpenBao/HashiCorp Vault Integration for Secrets Management

Provides secure secrets management using OpenBao/HashiCorp Vault for the DotMac Framework.
Replaces hardcoded secrets with dynamic secret retrieval.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

# Safe datetime handling
try:
    from datetime import timezone

    UTC = timezone.utc

    def utcnow():
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)

    def utc_now_iso():
        """Get current UTC datetime as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def expires_in_days(days: int):
        """Get datetime that expires in specified days."""
        return datetime.now(timezone.utc) + timedelta(days=days)

    def expires_in_hours(hours: int):
        """Get datetime that expires in specified hours."""
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    def is_expired(dt: datetime):
        """Check if datetime is expired."""
        return datetime.now(timezone.utc) > dt

except ImportError:
    # Python < 3.7 fallback
    import pytz

    UTC = pytz.UTC

    def utcnow():
        return datetime.now(pytz.UTC)

    def utc_now_iso():
        return datetime.now(pytz.UTC).isoformat()

    def expires_in_days(days: int):
        return datetime.now(pytz.UTC) + timedelta(days=days)

    def expires_in_hours(hours: int):
        return datetime.now(pytz.UTC) + timedelta(hours=hours)

    def is_expired(dt: datetime):
        return datetime.now(pytz.UTC) > dt


# Handle optional dependencies gracefully
try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ConfigDict, Field, SecretStr

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object
    PYDANTIC_AVAILABLE = False

    # Mock ConfigDict for when Pydantic is not available
    class ConfigDict:
        """ConfigDict implementation."""

        def __init__(self, **kwargs):
            pass


try:
    import hvac
    from hvac.exceptions import Forbidden, InvalidPath, InvalidRequest

    HVAC_AVAILABLE = True
except ImportError:
    HVAC_AVAILABLE = False
    hvac = None

    # Mock exceptions
    class Forbidden(Exception):
        """Forbidden implementation."""

        pass

    class InvalidPath(Exception):
        """InvalidPath implementation."""

        pass

    class InvalidRequest(Exception):
        """InvalidRequest implementation."""

        pass


try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None


if PYDANTIC_AVAILABLE:

    class VaultConfig(BaseModel):
        """Vault configuration settings"""

        url: str = Field(
            default="http://localhost:8200", description="Vault server URL"
        )
        token: Optional[SecretStr] = Field(default=None, description="Vault token")
        namespace: Optional[str] = Field(default=None, description="Vault namespace")
        mount_point: str = Field(default="secret", description="KV mount point")
        kv_version: int = Field(default=2, description="KV engine version")
        ssl_verify: bool = Field(default=True, description="Verify SSL certificates")
        timeout: int = Field(default=30, description="Request timeout in seconds")
        max_retries: int = Field(default=3, description="Maximum retry attempts")
        cache_ttl: int = Field(default=300, description="Cache TTL in seconds")

        # Authentication methods
        auth_method: str = Field(default="token", description="Authentication method")
        role_id: Optional[SecretStr] = Field(
            default=None, description="AppRole role ID"
        )
        secret_id: Optional[SecretStr] = Field(
            default=None, description="AppRole secret ID"
        )
        kubernetes_role: Optional[str] = Field(
            default=None, description="Kubernetes role"
        )
        aws_role: Optional[str] = Field(default=None, description="AWS IAM role")

        model_config = ConfigDict(validate_assignment=True)

else:
    # Fallback class when Pydantic is not available
    @dataclass
    class VaultConfig:
        """VaultConfig implementation."""

        url: str = "http://localhost:8200"
        token: Optional[str] = None
        namespace: Optional[str] = None
        mount_point: str = "secret"
        kv_version: int = 2
        ssl_verify: bool = True
        timeout: int = 30
        max_retries: int = 3
        cache_ttl: int = 300
        auth_method: str = "token"
        role_id: Optional[str] = None
        secret_id: Optional[str] = None
        kubernetes_role: Optional[str] = None
        aws_role: Optional[str] = None


@dataclass
class SecretMetadata:
    """Metadata for cached secrets"""

    path: str
    version: Optional[int]
    created_at: datetime
    expires_at: datetime
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if the cached secret has expired"""
        return utcnow() > self.expires_at


class OpenBaoClient:
    """
    OpenBao/HashiCorp Vault client for secure secrets management.

    Features:
    - Multiple authentication methods (Token, AppRole, Kubernetes, AWS)
    - Secret caching with TTL
    - Automatic token renewal
    - Dynamic secret generation
    - Encryption as a Service (Transit engine)
    - Secret rotation support
    """

    def __init__(self, config: VaultConfig):
        """
        Initialize the Vault client.

        Args:
            config: Vault configuration settings
        """
        self.config = config
        self._client = None
        self._authenticated = False
        self._token_expires_at: Optional[datetime] = None
        self._secret_cache: Dict[str, SecretMetadata] = {}
        self._lock = asyncio.Lock()

        # Initialize hvac client if available
        if HVAC_AVAILABLE:
            self._client = hvac.Client(
                url=config.url,
                token=(
                    config.token.get_secret_value()
                    if hasattr(config.token, "get_secret_value")
                    else config.token
                ),
                namespace=config.namespace,
                verify=config.ssl_verify,
                timeout=config.timeout,
            )
        else:
            logger.warning(
                "hvac library not available, Vault client will have limited functionality"
            )

    async def authenticate(self) -> bool:
        """
        Authenticate with Vault using configured method.

        Returns:
            True if authentication successful, False otherwise
        """
        if not HVAC_AVAILABLE:
            logger.error("Cannot authenticate: hvac library not available")
            return False

        try:
            async with self._lock:
                if self.config.auth_method == "token":
                    # Token authentication (default)
                    if not self.config.token:
                        logger.error("Token authentication requires a token")
                        return False

                    # Verify token is valid
                    token_value = (
                        self.config.token.get_secret_value()
                        if hasattr(self.config.token, "get_secret_value")
                        else self.config.token
                    )
                    self._client.token = token_value

                    if self._client.is_authenticated():
                        self._authenticated = True
                        # Get token info for expiration
                        try:
                            token_info = self._client.auth.token.lookup_self()
                            if token_info and "data" in token_info:
                                ttl = token_info["data"].get("ttl", 0)
                                if ttl > 0:
                                    self._token_expires_at = utcnow() + timedelta(
                                        seconds=ttl
                                    )
                        except Exception as e:
                            logger.warning(f"Could not get token TTL: {e}")

                        logger.info("Successfully authenticated with Vault using token")
                        return True

                elif self.config.auth_method == "approle":
                    # AppRole authentication
                    if not self.config.role_id or not self.config.secret_id:
                        logger.error(
                            "AppRole authentication requires role_id and secret_id"
                        )
                        return False

                    role_id = (
                        self.config.role_id.get_secret_value()
                        if hasattr(self.config.role_id, "get_secret_value")
                        else self.config.role_id
                    )
                    secret_id = (
                        self.config.secret_id.get_secret_value()
                        if hasattr(self.config.secret_id, "get_secret_value")
                        else self.config.secret_id
                    )

                    response = self._client.auth.approle.login(
                        role_id=role_id,
                        secret_id=secret_id,
                    )

                    if response and "auth" in response:
                        self._client.token = response["auth"]["client_token"]
                        self._authenticated = True

                        # Set token expiration
                        lease_duration = response["auth"].get("lease_duration", 0)
                        if lease_duration > 0:
                            self._token_expires_at = utcnow() + timedelta(
                                seconds=lease_duration
                            )

                        logger.info(
                            "Successfully authenticated with Vault using AppRole"
                        )
                        return True

                elif self.config.auth_method == "kubernetes":
                    # Kubernetes authentication
                    if not self.config.kubernetes_role:
                        logger.error(
                            "Kubernetes authentication requires kubernetes_role"
                        )
                        return False

                    # Read service account token
                    token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
                    try:
                        with open(token_path, "r") as f:
                            jwt_token = f.read().strip()
                    except FileNotFoundError:
                        logger.error(
                            f"Kubernetes service account token not found at {token_path}"
                        )
                        return False

                    response = self._client.auth.kubernetes.login(
                        role=self.config.kubernetes_role,
                        jwt=jwt_token,
                    )

                    if response and "auth" in response:
                        self._client.token = response["auth"]["client_token"]
                        self._authenticated = True

                        lease_duration = response["auth"].get("lease_duration", 0)
                        if lease_duration > 0:
                            self._token_expires_at = utcnow() + timedelta(
                                seconds=lease_duration
                            )

                        logger.info(
                            "Successfully authenticated with Vault using Kubernetes"
                        )
                        return True

                elif self.config.auth_method == "aws":
                    # AWS IAM authentication
                    if not self.config.aws_role:
                        logger.error("AWS authentication requires aws_role")
                        return False

                    response = self._client.auth.aws.iam_login(
                        access_key=os.getenv("AWS_ACCESS_KEY_ID"),
                        secret_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                        session_token=os.getenv("AWS_SESSION_TOKEN"),
                        role=self.config.aws_role,
                    )

                    if response and "auth" in response:
                        self._client.token = response["auth"]["client_token"]
                        self._authenticated = True

                        lease_duration = response["auth"].get("lease_duration", 0)
                        if lease_duration > 0:
                            self._token_expires_at = utcnow() + timedelta(
                                seconds=lease_duration
                            )

                        logger.info(
                            "Successfully authenticated with Vault using AWS IAM"
                        )
                        return True

                else:
                    logger.error(
                        f"Unsupported authentication method: {self.config.auth_method}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Vault authentication failed: {e}")
            self._authenticated = False
            return False

        logger.error("Vault authentication failed")
        return False

    async def is_authenticated(self) -> bool:
        """Check if client is authenticated and token is valid."""
        if not self._authenticated or not HVAC_AVAILABLE:
            return False

        # Check token expiration
        if self._token_expires_at and utcnow() >= self._token_expires_at:
            logger.info("Vault token expired, need to re-authenticate")
            self._authenticated = False
            return False

        # Verify with Vault
        try:
            return self._client.is_authenticated()
        except Exception as e:
            logger.error(f"Failed to verify Vault authentication: {e}")
            self._authenticated = False
            return False

    async def get_secret(
        self,
        path: str,
        version: Optional[int] = None,
        use_cache: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a secret from Vault.

        Args:
            path: Secret path
            version: Specific version (KV v2 only)
            use_cache: Whether to use cached value

        Returns:
            Secret data or None if not found
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot retrieve secret: not authenticated with Vault")
                return None

        # Check cache first
        cache_key = f"{path}:v{version}" if version else path
        if use_cache and cache_key in self._secret_cache:
            cached_secret = self._secret_cache[cache_key]
            if not cached_secret.is_expired():
                logger.debug(f"Retrieved secret from cache: {path}")
                return cached_secret.data

        if not HVAC_AVAILABLE:
            logger.error("Cannot retrieve secret: hvac library not available")
            return None

        try:
            # Retrieve from Vault
            if self.config.kv_version == 2:
                response = self._client.secrets.kv.v2.read_secret_version(
                    path=path,
                    version=version,
                    mount_point=self.config.mount_point,
                )
                secret_data = response["data"]["data"] if response else None
                secret_metadata = response["data"]["metadata"] if response else {}
            else:
                response = self._client.secrets.kv.v1.read_secret(
                    path=path,
                    mount_point=self.config.mount_point,
                )
                secret_data = response["data"] if response else None
                secret_metadata = {}

            if secret_data:
                # Cache the secret
                if use_cache:
                    self._secret_cache[cache_key] = SecretMetadata(
                        path=path,
                        version=version,
                        created_at=utcnow(),
                        expires_at=utcnow() + timedelta(seconds=self.config.cache_ttl),
                        data=secret_data,
                        metadata=secret_metadata,
                    )

                logger.debug(f"Successfully retrieved secret: {path}")
                return secret_data

        except (Forbidden, InvalidPath, InvalidRequest) as e:
            logger.error(f"Vault error retrieving secret {path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret {path}: {e}")

        return None

    async def put_secret(
        self,
        path: str,
        secret_data: Dict[str, Any],
        cas: Optional[int] = None,
    ) -> bool:
        """
        Store a secret in Vault.

        Args:
            path: Secret path
            secret_data: Secret data to store
            cas: Check-and-Set value for atomic updates (KV v2 only)

        Returns:
            True if successful, False otherwise
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot store secret: not authenticated with Vault")
                return False

        if not HVAC_AVAILABLE:
            logger.error("Cannot store secret: hvac library not available")
            return False

        try:
            if self.config.kv_version == 2:
                self._client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret=secret_data,
                    cas=cas,
                    mount_point=self.config.mount_point,
                )
            else:
                self._client.secrets.kv.v1.create_or_update_secret(
                    path=path,
                    secret=secret_data,
                    mount_point=self.config.mount_point,
                )

            # Invalidate cache for this path
            cache_keys_to_remove = [
                key for key in self._secret_cache.keys() if key.startswith(path)
            ]
            for key in cache_keys_to_remove:
                del self._secret_cache[key]

            logger.info(f"Successfully stored secret: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to store secret {path}: {e}")
            return False

    async def delete_secret(
        self, path: str, versions: Optional[List[int]] = None
    ) -> bool:
        """
        Delete a secret from Vault.

        Args:
            path: Secret path
            versions: Specific versions to delete (KV v2 only)

        Returns:
            True if successful, False otherwise
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot delete secret: not authenticated with Vault")
                return False

        if not HVAC_AVAILABLE:
            logger.error("Cannot delete secret: hvac library not available")
            return False

        try:
            if self.config.kv_version == 2:
                if versions:
                    self._client.secrets.kv.v2.delete_secret_versions(
                        path=path,
                        versions=versions,
                        mount_point=self.config.mount_point,
                    )
                else:
                    self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                        path=path,
                        mount_point=self.config.mount_point,
                    )
            else:
                self._client.secrets.kv.v1.delete_secret(
                    path=path,
                    mount_point=self.config.mount_point,
                )

            # Remove from cache
            cache_keys_to_remove = [
                key for key in self._secret_cache.keys() if key.startswith(path)
            ]
            for key in cache_keys_to_remove:
                del self._secret_cache[key]

            logger.info(f"Successfully deleted secret: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete secret {path}: {e}")
            return False

    async def list_secrets(self, path: str) -> Optional[List[str]]:
        """
        List secrets at a path.

        Args:
            path: Path to list

        Returns:
            List of secret names or None if error
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot list secrets: not authenticated with Vault")
                return None

        if not HVAC_AVAILABLE:
            logger.error("Cannot list secrets: hvac library not available")
            return None

        try:
            if self.config.kv_version == 2:
                response = self._client.secrets.kv.v2.list_secrets(
                    path=path,
                    mount_point=self.config.mount_point,
                )
            else:
                response = self._client.secrets.kv.v1.list_secrets(
                    path=path,
                    mount_point=self.config.mount_point,
                )

            if response and "data" in response and "keys" in response["data"]:
                return response["data"]["keys"]

        except Exception as e:
            logger.error(f"Failed to list secrets at {path}: {e}")

        return None

    async def encrypt_data(
        self,
        plaintext: str,
        key_name: str = "default",
        context: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Encrypt data using Vault's Transit engine.

        Args:
            plaintext: Data to encrypt
            key_name: Encryption key name
            context: Additional context for encryption

        Returns:
            Encrypted ciphertext or None if error
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot encrypt data: not authenticated with Vault")
                return None

        if not HVAC_AVAILABLE:
            logger.error("Cannot encrypt data: hvac library not available")
            return None

        try:
            # Encode plaintext as base64
            import base64

            plaintext_b64 = base64.b64encode(plaintext.encode()).decode()

            response = self._client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=plaintext_b64,
                context=context,
            )

            if response and "data" in response:
                return response["data"]["ciphertext"]

        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")

        return None

    async def decrypt_data(
        self,
        ciphertext: str,
        key_name: str = "default",
        context: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Decrypt data using Vault's Transit engine.

        Args:
            ciphertext: Data to decrypt
            key_name: Encryption key name
            context: Additional context for decryption

        Returns:
            Decrypted plaintext or None if error
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error("Cannot decrypt data: not authenticated with Vault")
                return None

        if not HVAC_AVAILABLE:
            logger.error("Cannot decrypt data: hvac library not available")
            return None

        try:
            response = self._client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext,
                context=context,
            )

            if response and "data" in response:
                # Decode from base64
                import base64

                plaintext_b64 = response["data"]["plaintext"]
                return base64.b64decode(plaintext_b64).decode()

        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")

        return None

    async def generate_dynamic_secret(
        self,
        backend: str,
        role: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a dynamic secret.

        Args:
            backend: Secret backend (e.g., 'database', 'aws')
            role: Role to use for generation
            **kwargs: Additional parameters

        Returns:
            Dynamic secret data or None if error
        """
        if not await self.is_authenticated():
            if not await self.authenticate():
                logger.error(
                    "Cannot generate dynamic secret: not authenticated with Vault"
                )
                return None

        if not HVAC_AVAILABLE:
            logger.error("Cannot generate dynamic secret: hvac library not available")
            return None

        try:
            # This would need to be customized based on the specific backend
            response = self._client.read(f"{backend}/creds/{role}")

            if response and "data" in response:
                return response["data"]

        except Exception as e:
            logger.error(f"Failed to generate dynamic secret: {e}")

        return None

    async def renew_token(self, increment: Optional[int] = None) -> bool:
        """
        Renew the current token.

        Args:
            increment: Requested TTL increment in seconds

        Returns:
            True if successful, False otherwise
        """
        if not HVAC_AVAILABLE:
            logger.error("Cannot renew token: hvac library not available")
            return False

        try:
            response = self._client.auth.token.renew_self(increment=increment)

            if response and "auth" in response:
                lease_duration = response["auth"].get("lease_duration", 0)
                if lease_duration > 0:
                    self._token_expires_at = utcnow() + timedelta(
                        seconds=lease_duration
                    )

                logger.info("Successfully renewed Vault token")
                return True

        except Exception as e:
            logger.error(f"Failed to renew token: {e}")

        return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Vault connection.

        Returns:
            Health status information
        """
        status = {
            "healthy": False,
            "authenticated": False,
            "hvac_available": HVAC_AVAILABLE,
            "config": {
                "url": self.config.url,
                "mount_point": self.config.mount_point,
                "kv_version": self.config.kv_version,
                "auth_method": self.config.auth_method,
            },
            "cache_size": len(self._secret_cache),
            "token_expires_at": (
                self._token_expires_at.isoformat() if self._token_expires_at else None
            ),
        }

        if HVAC_AVAILABLE and self._client:
            try:
                # Check authentication
                status["authenticated"] = await self.is_authenticated()

                # Check Vault health
                health_response = self._client.sys.read_health_status()
                if health_response:
                    status["healthy"] = True
                    status["vault_info"] = {
                        "version": health_response.get("version"),
                        "cluster_name": health_response.get("cluster_name"),
                        "cluster_id": health_response.get("cluster_id"),
                    }

            except Exception as e:
                status["error"] = str(e)

        return status

    @asynccontextmanager
    async def secret_context(self, path: str):
        """
        Context manager for temporary secret access.

        Args:
            path: Secret path

        Yields:
            Secret data
        """
        secret_data = await self.get_secret(path)
        try:
            yield secret_data
        finally:
            # Clear sensitive data from memory
            if secret_data:
                for key in secret_data:
                    if isinstance(secret_data[key], str):
                        # Overwrite string data (basic protection)
                        secret_data[key] = "0" * len(secret_data[key])

    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self._secret_cache.clear()
        logger.info("Vault secret cache cleared")
