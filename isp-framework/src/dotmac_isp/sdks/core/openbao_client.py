"""
OpenBao SDK Client for DotMac Services

Provides a service-oriented interface for OpenBao secrets management.
This is the primary client for all DotMac services to retrieve secrets.
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dotmac_isp.core.secrets.openbao_native_client import (
    OpenBaoClient as CoreOpenBaoClient,
    OpenBaoConfig,
    OpenBaoSecretManager,
    OpenBaoAPIException
)

logger = logging.getLogger(__name__)


@dataclass
class Secret:
    """Represents a secret from OpenBao."""
    
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    lease_duration: int
    renewable: bool
    created_at: datetime

    def is_expired(self) -> bool:
        """Check if secret lease has expired."""
        if self.lease_duration == 0:
            return False  # No expiration
        expiry = self.created_at + timedelta(seconds=self.lease_duration)
        return datetime.now(timezone.utc) > expiry

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from secret data."""
        return self.data.get(key, default)


class OpenBaoClient:
    """
    Service-oriented OpenBao client for DotMac services.
    
    This client provides a simplified interface for services to retrieve
    secrets specific to their needs.
    """

    def __init__(
        self,
        service_name: str,
        bao_addr: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        namespace: Optional[str] = None,
        auto_renew: bool = True,
        cache_ttl: int = 300,
    ):
        """
        Initialize OpenBao client.

        Args:
            service_name: Name of the service
            bao_addr: OpenBao server address
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            namespace: OpenBao namespace (for multi-tenant)
            auto_renew: Enable automatic token renewal
            cache_ttl: Cache TTL in seconds
        """
        self.service_name = service_name
        self.bao_addr = bao_addr or os.getenv("OPENBAO_ADDR", os.getenv("BAO_ADDR", "http://localhost:8200"))
        self.namespace = namespace or os.getenv("OPENBAO_NAMESPACE", os.getenv("BAO_NAMESPACE"))
        self.auto_renew = auto_renew
        self.cache_ttl = cache_ttl

        # Authentication credentials
        self.role_id = role_id or self._get_role_id()
        self.secret_id = secret_id or self._get_secret_id()

        # Create OpenBao configuration
        config = OpenBaoConfig(
            url=self.bao_addr,
            namespace=self.namespace,
            cache_ttl=cache_ttl,
            auth_method="approle" if self.role_id and self.secret_id else "token",
            role_id=self.role_id,
            secret_id=self.secret_id,
            token=os.getenv("OPENBAO_TOKEN", os.getenv("BAO_TOKEN", ""))
        )

        # Initialize core client and secret manager
        self.core_client = CoreOpenBaoClient(config)
        self.secret_manager = OpenBaoSecretManager(self.core_client)
        
        logger.info(f"OpenBao SDK client initialized for service: {service_name}")

    def _get_role_id(self) -> str:
        """Get role ID from file or environment."""
        # Try service-specific environment variable first
        role_id = os.getenv(f"{self.service_name.upper()}_ROLE_ID")
        if role_id:
            return role_id

        # Try file
        role_file = f"/var/run/secrets/openbao/{self.service_name}-role-id"
        if os.path.exists(role_file):
            with open(role_file, "r") as f:
                return f.read().strip()

        # Fallback to generic env
        return os.getenv("OPENBAO_ROLE_ID", os.getenv("BAO_ROLE_ID", ""))

    def _get_secret_id(self) -> str:
        """Get secret ID from file or environment."""
        # Try service-specific environment variable first
        secret_id = os.getenv(f"{self.service_name.upper()}_SECRET_ID")
        if secret_id:
            return secret_id

        # Try file
        secret_file = f"/var/run/secrets/openbao/{self.service_name}-secret-id"
        if os.path.exists(secret_file):
            with open(secret_file, "r") as f:
                return f.read().strip()

        # Fallback to generic env
        return os.getenv("OPENBAO_SECRET_ID", os.getenv("BAO_SECRET_ID", ""))

    async def authenticate(self) -> bool:
        """Authenticate with OpenBao."""
        try:
            success = await self.core_client.authenticate()
            if success:
                logger.info(f"Authentication successful for service: {self.service_name}")
            return success
        except OpenBaoAPIException as e:
            logger.error(f"Authentication failed for service {self.service_name}: {e}")
            return False

    async def get_secret(self, path: str, use_cache: bool = True) -> Secret:
        """
        Get secret from OpenBao.
        
        Args:
            path: Secret path (relative to service namespace)
            use_cache: Whether to use cached secrets
            
        Returns:
            Secret object with data and metadata
        """
        # Prepend service namespace to path
        full_path = f"{self.service_name}/{path.lstrip('/')}"
        
        try:
            secret_data = await self.core_client.get_secret(full_path, use_cache=use_cache)
            
            return Secret(
                data=secret_data,
                metadata={},
                lease_duration=self.cache_ttl,
                renewable=True,
                created_at=datetime.now(timezone.utc)
            )
        except KeyError:
            raise OpenBaoAPIException(f"Secret not found: {full_path}")
        except Exception as e:
            raise OpenBaoAPIException(f"Failed to retrieve secret {full_path}: {e}")

    async def get_database_config(self, database_name: str = "default") -> Dict[str, str]:
        """
        Get database configuration for the service.
        
        Args:
            database_name: Name of the database configuration
            
        Returns:
            Database configuration dictionary
        """
        try:
            return await self.secret_manager.get_database_credentials(f"{self.service_name}-{database_name}")
        except OpenBaoAPIException:
            # Fallback to service-specific path
            secret = await self.get_secret(f"database/{database_name}")
            return {
                "host": secret.get("host", ""),
                "port": secret.get("port", ""),
                "database": secret.get("database", ""),
                "username": secret.get("username", ""),
                "password": secret.get("password", ""),
                "connection_string": secret.get("connection_string", "")
            }

    async def get_api_credentials(self, service: str) -> Dict[str, str]:
        """
        Get API credentials for external services.
        
        Args:
            service: External service name
            
        Returns:
            API credentials dictionary
        """
        secret = await self.get_secret(f"api/{service}")
        return {
            "api_key": secret.get("api_key", ""),
            "api_secret": secret.get("api_secret", ""),
            "client_id": secret.get("client_id", ""),
            "client_secret": secret.get("client_secret", ""),
            "access_token": secret.get("access_token", ""),
            "refresh_token": secret.get("refresh_token", "")
        }

    async def get_encryption_key(self, key_name: str = "default") -> str:
        """
        Get encryption key for the service.
        
        Args:
            key_name: Name of the encryption key
            
        Returns:
            Encryption key string
        """
        try:
            return await self.secret_manager.get_encryption_key(f"{self.service_name}-{key_name}")
        except OpenBaoAPIException:
            # Fallback to service-specific path
            secret = await self.get_secret(f"encryption/{key_name}")
            key = secret.get("key", "")
            if not key:
                raise OpenBaoAPIException(f"Encryption key not found: {key_name}")
            return key

    async def get_jwt_secret(self) -> str:
        """
        Get JWT signing secret for the service.
        
        Returns:
            JWT secret string
        """
        secret = await self.get_secret("auth/jwt")
        jwt_secret = secret.get("secret", "")
        if not jwt_secret:
            raise OpenBaoAPIException("JWT secret not found")
        return jwt_secret

    async def get_redis_config(self, instance: str = "default") -> Dict[str, str]:
        """
        Get Redis configuration.
        
        Args:
            instance: Redis instance name
            
        Returns:
            Redis configuration dictionary
        """
        secret = await self.get_secret(f"redis/{instance}")
        return {
            "host": secret.get("host", "localhost"),
            "port": secret.get("port", "6379"),
            "password": secret.get("password", ""),
            "database": secret.get("database", "0"),
            "ssl": secret.get("ssl", "false"),
            "connection_string": secret.get("connection_string", "")
        }

    async def get_smtp_config(self) -> Dict[str, str]:
        """
        Get SMTP configuration for email sending.
        
        Returns:
            SMTP configuration dictionary
        """
        secret = await self.get_secret("email/smtp")
        return {
            "host": secret.get("host", ""),
            "port": secret.get("port", "587"),
            "username": secret.get("username", ""),
            "password": secret.get("password", ""),
            "use_tls": secret.get("use_tls", "true"),
            "use_ssl": secret.get("use_ssl", "false")
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Check OpenBao connection health.
        
        Returns:
            Health status dictionary
        """
        try:
            health = await self.core_client.health_check()
            health["service"] = self.service_name
            health["sdk_version"] = "native"
            return health
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "service": self.service_name,
                "sdk_version": "native"
            }

    async def close(self):
        """Close the client connections."""
        await self.core_client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Factory functions
def create_service_client(service_name: str, **kwargs) -> OpenBaoClient:
    """
    Create OpenBao client for a specific service.
    
    Args:
        service_name: Name of the service
        **kwargs: Additional configuration options
        
    Returns:
        OpenBao client instance
    """
    return OpenBaoClient(service_name=service_name, **kwargs)

# Service-specific factory functions
def create_isp_client(**kwargs) -> OpenBaoClient:
    """Create OpenBao client for ISP framework."""
    return create_service_client("isp-framework", **kwargs)

def create_mgmt_client(**kwargs) -> OpenBaoClient:
    """Create OpenBao client for Management Platform."""
    return create_service_client("management-platform", **kwargs)

def create_billing_client(**kwargs) -> OpenBaoClient:
    """Create OpenBao client for Billing service."""
    return create_service_client("billing", **kwargs)

def create_identity_client(**kwargs) -> OpenBaoClient:
    """Create OpenBao client for Identity service."""
    return create_service_client("identity", **kwargs)