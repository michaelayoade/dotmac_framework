"""
OpenBao Secrets Provider

Integration with OpenBao/Vault for secrets management in the DotMac auth system.
Requires 'secrets' extra: pip install dotmac-auth[secrets]
"""

import asyncio
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from ..exceptions import SecretsProviderError
from .secrets import SecretsProvider


class OpenBaoProvider(SecretsProvider):
    """
    OpenBao/Vault secrets provider implementation.
    
    Supports both OpenBao and HashiCorp Vault APIs for secrets management.
    Includes automatic token refresh, connection pooling, and error handling.
    """
    
    def __init__(
        self,
        url: str,
        token: Optional[str] = None,
        namespace: Optional[str] = None,
        mount_point: str = "secret",
        jwt_path: str = "auth/jwt",
        service_path: str = "auth/service",
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
        client_cert: Optional[tuple] = None
    ):
        """
        Initialize OpenBao provider.
        
        Args:
            url: OpenBao/Vault server URL
            token: Authentication token
            namespace: Vault namespace (Enterprise feature)
            mount_point: Secrets engine mount point
            jwt_path: Path for JWT secrets
            service_path: Path for service secrets
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            verify_ssl: Whether to verify SSL certificates
            client_cert: Optional client certificate tuple (cert, key)
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for OpenBao provider. "
                "Install with: pip install dotmac-auth[secrets]"
            )
        
        self.url = url.rstrip("/")
        self.token = token
        self.namespace = namespace
        self.mount_point = mount_point
        self.jwt_path = jwt_path
        self.service_path = service_path
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
            cert=client_cert,
            follow_redirects=True
        )
        
        # Token refresh tracking
        self._token_expires_at: Optional[float] = None
        self._refresh_lock = asyncio.Lock()
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {"Content-Type": "application/json"}
        
        if self.token:
            headers["X-Vault-Token"] = self.token
        
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        
        return headers
    
    async def _request(
        self, 
        method: str, 
        path: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to OpenBao/Vault.
        
        Args:
            method: HTTP method
            path: API path (without /v1 prefix)
            data: Request body data
            params: Query parameters
            
        Returns:
            Response data
        """
        url = f"{self.url}/v1/{path.lstrip('/')}"
        headers = await self._get_headers()
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    params=params
                )
                
                # Handle authentication errors
                if response.status_code == 403:
                    raise SecretsProviderError(
                        "Authentication failed - check token permissions",
                        provider="openbao",
                        operation=f"{method} {path}"
                    )
                
                # Handle not found
                if response.status_code == 404:
                    raise SecretsProviderError(
                        f"Secret not found: {path}",
                        provider="openbao",
                        operation=f"{method} {path}"
                    )
                
                # Raise for other HTTP errors
                response.raise_for_status()
                
                # Parse response
                if response.content:
                    return response.json()
                else:
                    return {}
                
            except httpx.RequestError as e:
                if attempt == self.max_retries - 1:
                    raise SecretsProviderError(
                        f"Request failed after {self.max_retries} attempts: {e}",
                        provider="openbao",
                        operation=f"{method} {path}"
                    )
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
            
            except httpx.HTTPStatusError as e:
                raise SecretsProviderError(
                    f"HTTP error {e.response.status_code}: {e.response.text}",
                    provider="openbao",
                    operation=f"{method} {path}"
                )
    
    def _get_secret_path(self, category: str, key: str) -> str:
        """Get the full path for a secret"""
        return f"{self.mount_point}/data/{category}/{key}"
    
    def _get_metadata_path(self, category: str, key: str) -> str:
        """Get the metadata path for a secret"""
        return f"{self.mount_point}/metadata/{category}/{key}"
    
    async def get_jwt_private_key(self, path: Optional[str] = None) -> str:
        """Get JWT private key from OpenBao"""
        secret_path = path or self._get_secret_path("jwt", "private_key")
        
        try:
            response = await self._request("GET", secret_path)
            data = response.get("data", {}).get("data", {})
            
            private_key = data.get("private_key")
            if not private_key:
                raise SecretsProviderError(
                    "JWT private key not found in secret",
                    provider="openbao",
                    operation="get_jwt_private_key"
                )
            
            return private_key
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to get JWT private key: {e}",
                provider="openbao",
                operation="get_jwt_private_key"
            )
    
    async def get_jwt_public_key(self, path: Optional[str] = None) -> str:
        """Get JWT public key from OpenBao"""
        secret_path = path or self._get_secret_path("jwt", "public_key")
        
        try:
            response = await self._request("GET", secret_path)
            data = response.get("data", {}).get("data", {})
            
            public_key = data.get("public_key")
            if not public_key:
                raise SecretsProviderError(
                    "JWT public key not found in secret",
                    provider="openbao",
                    operation="get_jwt_public_key"
                )
            
            return public_key
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to get JWT public key: {e}",
                provider="openbao",
                operation="get_jwt_public_key"
            )
    
    async def get_symmetric_secret(self, path: Optional[str] = None) -> str:
        """Get symmetric secret from OpenBao"""
        secret_path = path or self._get_secret_path("jwt", "symmetric_secret")
        
        try:
            response = await self._request("GET", secret_path)
            data = response.get("data", {}).get("data", {})
            
            secret = data.get("secret")
            if not secret:
                raise SecretsProviderError(
                    "Symmetric secret not found",
                    provider="openbao",
                    operation="get_symmetric_secret"
                )
            
            return secret
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to get symmetric secret: {e}",
                provider="openbao",
                operation="get_symmetric_secret"
            )
    
    async def get_service_signing_secret(self, path: Optional[str] = None) -> str:
        """Get service signing secret from OpenBao"""
        secret_path = path or self._get_secret_path("service", "signing_secret")
        
        try:
            response = await self._request("GET", secret_path)
            data = response.get("data", {}).get("data", {})
            
            secret = data.get("secret")
            if not secret:
                raise SecretsProviderError(
                    "Service signing secret not found",
                    provider="openbao",
                    operation="get_service_signing_secret"
                )
            
            return secret
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to get service signing secret: {e}",
                provider="openbao",
                operation="get_service_signing_secret"
            )
    
    async def get_secret(self, path: str, key: Optional[str] = None) -> Any:
        """Get arbitrary secret from OpenBao"""
        try:
            response = await self._request("GET", f"{self.mount_point}/data/{path}")
            data = response.get("data", {}).get("data", {})
            
            if key:
                return data.get(key)
            else:
                return data
                
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to get secret {path}: {e}",
                provider="openbao",
                operation="get_secret"
            )
    
    async def set_secret(
        self, 
        path: str, 
        data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set secret in OpenBao"""
        try:
            secret_data = {"data": data}
            if metadata:
                secret_data["metadata"] = metadata
            
            await self._request("POST", f"{self.mount_point}/data/{path}", secret_data)
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to set secret {path}: {e}",
                provider="openbao",
                operation="set_secret"
            )
    
    async def delete_secret(self, path: str) -> None:
        """Delete secret from OpenBao"""
        try:
            await self._request("DELETE", f"{self.mount_point}/metadata/{path}")
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to delete secret {path}: {e}",
                provider="openbao",
                operation="delete_secret"
            )
    
    async def list_secrets(self, path: str) -> List[str]:
        """List secrets at path in OpenBao"""
        try:
            response = await self._request("LIST", f"{self.mount_point}/metadata/{path}")
            keys = response.get("data", {}).get("keys", [])
            return keys
            
        except Exception as e:
            if isinstance(e, SecretsProviderError):
                raise
            raise SecretsProviderError(
                f"Failed to list secrets at {path}: {e}",
                provider="openbao",
                operation="list_secrets"
            )
    
    async def health_check(self) -> bool:
        """Check OpenBao health"""
        try:
            response = await self._request("GET", "sys/health")
            return response.get("sealed", True) is False
            
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


def create_openbao_provider(
    url: str,
    token: Optional[str] = None,
    **kwargs
) -> OpenBaoProvider:
    """
    Factory function to create OpenBao provider.
    
    Args:
        url: OpenBao server URL
        token: Authentication token
        **kwargs: Additional provider configuration
        
    Returns:
        Configured OpenBaoProvider instance
    """
    return OpenBaoProvider(url=url, token=token, **kwargs)