"""
Secrets Provider Interface

Abstract interface for secrets providers with OpenBao/Vault integration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import warnings

# Try to import new dotmac.secrets package
try:
    from dotmac.secrets import from_env as secrets_from_env
    _NEW_SECRETS_AVAILABLE = True
except ImportError:
    _NEW_SECRETS_AVAILABLE = False


class SecretsProvider(ABC):
    """
    Abstract interface for secrets providers.
    
    Implementations should handle authentication, connection management,
    and error handling for their respective secrets backends.
    """
    
    @abstractmethod
    async def get_jwt_private_key(self, path: Optional[str] = None) -> str:
        """
        Get JWT private key for RS256 signing.
        
        Args:
            path: Optional custom path for the key
            
        Returns:
            Private key in PEM format
        """
        pass
    
    @abstractmethod
    async def get_jwt_public_key(self, path: Optional[str] = None) -> str:
        """
        Get JWT public key for RS256 verification.
        
        Args:
            path: Optional custom path for the key
            
        Returns:
            Public key in PEM format
        """
        pass
    
    @abstractmethod
    async def get_symmetric_secret(self, path: Optional[str] = None) -> str:
        """
        Get symmetric secret for HS256.
        
        Args:
            path: Optional custom path for the secret
            
        Returns:
            Symmetric secret string
        """
        pass
    
    @abstractmethod
    async def get_service_signing_secret(self, path: Optional[str] = None) -> str:
        """
        Get signing secret for service-to-service tokens.
        
        Args:
            path: Optional custom path for the secret
            
        Returns:
            Service signing secret
        """
        pass
    
    @abstractmethod
    async def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """
        Get arbitrary secret from the provider.
        
        Args:
            path: Secret path
            key: Optional specific key within the secret
            
        Returns:
            Secret value
        """
        pass
    
    @abstractmethod
    async def set_secret(
        self, 
        path: str, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Set secret in the provider.
        
        Args:
            path: Secret path
            data: Secret data dictionary
            metadata: Optional metadata
        """
        pass
    
    @abstractmethod
    async def delete_secret(self, path: str) -> None:
        """
        Delete secret from the provider.
        
        Args:
            path: Secret path
        """
        pass
    
    @abstractmethod
    async def list_secrets(self, path: str) -> list[str]:
        """
        List secrets at the given path.
        
        Args:
            path: Path to list
            
        Returns:
            List of secret names/paths
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the secrets provider is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close connections and cleanup resources.
        """
        pass


class MockSecretsProvider(SecretsProvider):
    """
    Mock secrets provider for testing and development.
    """
    
    def __init__(self, secrets: Optional[Dict[str, Any]] = None):
        self.secrets = secrets or {}
        self.default_keys = {
            "jwt/private_key": """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKB
Uw8aMNqj8SyKI4xQvw6sYr3g3VCNl8k+gK5prgxh8LI2Vv8dU7g2xJ5K8ZNaQKnW
...
-----END PRIVATE KEY-----""",
            "jwt/public_key": """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1L7VLPHCgVMPGjDa
o/EsiiOMUL8OrGK94N1QjZfJPoCuaa4MYfCyNlb/HVO4NsSeSvGTWkCp1g==
-----END PUBLIC KEY-----""",
            "jwt/symmetric_secret": "your-256-bit-secret-key-goes-here-make-it-random",
            "service/signing_secret": "service-signing-secret-key-goes-here"
        }
    
    async def get_jwt_private_key(self, path: Optional[str] = None) -> str:
        path = path or "jwt/private_key"
        return self.secrets.get(path, self.default_keys.get("jwt/private_key", ""))
    
    async def get_jwt_public_key(self, path: Optional[str] = None) -> str:
        path = path or "jwt/public_key"
        return self.secrets.get(path, self.default_keys.get("jwt/public_key", ""))
    
    async def get_symmetric_secret(self, path: Optional[str] = None) -> str:
        path = path or "jwt/symmetric_secret"
        return self.secrets.get(path, self.default_keys.get("jwt/symmetric_secret", ""))
    
    async def get_service_signing_secret(self, path: Optional[str] = None) -> str:
        path = path or "service/signing_secret"
        return self.secrets.get(path, self.default_keys.get("service/signing_secret", ""))
    
    async def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        secret = self.secrets.get(path)
        if key and isinstance(secret, dict):
            return secret.get(key)
        return secret
    
    async def set_secret(
        self, 
        path: str, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.secrets[path] = data
    
    async def delete_secret(self, path: str) -> None:
        self.secrets.pop(path, None)
    
    async def list_secrets(self, path: str) -> list[str]:
        prefix = path.rstrip("/") + "/"
        return [k for k in self.secrets.keys() if k.startswith(prefix)]
    
    async def health_check(self) -> bool:
        return True
    
    async def close(self) -> None:
        pass


class DotMacSecretsAdapter(SecretsProvider):
    """
    Adapter that uses the new dotmac.secrets package.
    
    This provides backward compatibility while using the new unified secrets interface.
    """
    
    def __init__(self, app_name: str = "auth"):
        """
        Initialize with new secrets manager.
        
        Args:
            app_name: Application name for JWT keypair lookup
        """
        if not _NEW_SECRETS_AVAILABLE:
            raise ImportError("dotmac.secrets package not available. Install with: pip install dotmac-secrets")
        
        warnings.warn(
            "DotMacSecretsAdapter is using the new dotmac.secrets package. "
            "Consider migrating to use dotmac.secrets directly.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self._secrets_manager = secrets_from_env()
        self._app_name = app_name
    
    async def get_jwt_private_key(self, path: Optional[str] = None) -> str:
        """Get JWT private key from secrets manager."""
        if path:
            # Custom path - use as custom secret
            secret_data = await self._secrets_manager.get_custom_secret(path)
            if isinstance(secret_data, dict) and "private_pem" in secret_data:
                return secret_data["private_pem"]
            elif isinstance(secret_data, str):
                return secret_data
            raise ValueError(f"Invalid JWT private key data at path: {path}")
        
        # Use standard JWT keypair
        keypair = await self._secrets_manager.get_jwt_keypair(self._app_name)
        return keypair.private_pem
    
    async def get_jwt_public_key(self, path: Optional[str] = None) -> str:
        """Get JWT public key from secrets manager."""
        if path:
            # Custom path - use as custom secret
            secret_data = await self._secrets_manager.get_custom_secret(path)
            if isinstance(secret_data, dict) and "public_pem" in secret_data:
                return secret_data["public_pem"]
            elif isinstance(secret_data, str):
                return secret_data
            raise ValueError(f"Invalid JWT public key data at path: {path}")
        
        # Use standard JWT keypair
        keypair = await self._secrets_manager.get_jwt_keypair(self._app_name)
        return keypair.public_pem
    
    async def get_symmetric_secret(self, path: Optional[str] = None) -> str:
        """Get symmetric secret from secrets manager."""
        if path:
            # Custom path
            return await self._secrets_manager.get_symmetric_secret(path)
        
        # For backward compatibility, try to get JWT as symmetric if available
        try:
            keypair = await self._secrets_manager.get_jwt_keypair(self._app_name)
            if keypair.algorithm.startswith("HS"):
                return keypair.private_pem  # For symmetric, this contains the secret
        except:
            pass
        
        # Fallback to default symmetric secret
        return await self._secrets_manager.get_symmetric_secret("default")
    
    async def get_service_signing_secret(self, path: Optional[str] = None) -> str:
        """Get service signing secret from secrets manager."""
        service_name = path or self._app_name
        return await self._secrets_manager.get_service_signing_secret(service_name)
    
    async def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """Get arbitrary secret from secrets manager."""
        secret_data = await self._secrets_manager.get_custom_secret(path)
        
        if key and isinstance(secret_data, dict):
            return secret_data.get(key)
        
        return secret_data
    
    async def set_secret(
        self, 
        path: str, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set secret - not supported in dotmac.secrets (read-only interface)."""
        raise NotImplementedError("Setting secrets not supported through dotmac.secrets interface")
    
    async def delete_secret(self, path: str) -> None:
        """Delete secret - not supported in dotmac.secrets (read-only interface)."""
        raise NotImplementedError("Deleting secrets not supported through dotmac.secrets interface")
    
    async def list_secrets(self, path: str) -> list[str]:
        """List secrets at path."""
        try:
            return await self._secrets_manager.list_secrets(path)
        except AttributeError:
            # Fallback if list_secrets not available
            return []
    
    async def health_check(self) -> bool:
        """Check secrets manager health."""
        try:
            health = await self._secrets_manager.health_check()
            return health.get("manager") == "healthy"
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close secrets manager."""
        await self._secrets_manager.close()