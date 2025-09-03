"""
OpenBao/HashiCorp Vault provider for secrets management
Modern implementation with httpx and comprehensive error handling
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from ..interfaces import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderConnectionError,
    SecretNotFoundError,
    SecretsProviderError,
    WritableSecretsProvider,
)
from ..types import SecretData
from .base import BaseProvider, HTTPProviderMixin

logger = logging.getLogger(__name__)


class OpenBaoProvider(BaseProvider, HTTPProviderMixin):
    """
    OpenBao/HashiCorp Vault secrets provider
    Supports both KV v1 and KV v2 engines with automatic detection
    """
    
    def __init__(
        self,
        url: str,
        token: str,
        mount_path: str = "kv",
        api_version: str = "v2",
        verify_ssl: bool = True,
        ca_cert_path: Optional[str] = None,
        namespace: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        
        self.url = url.rstrip('/')
        self.token = token
        self.mount_path = mount_path
        self.api_version = api_version
        self.verify_ssl = verify_ssl
        self.ca_cert_path = ca_cert_path
        self.namespace = namespace
        
        # Cache for KV engine version detection
        self._kv_version_cache: Dict[str, str] = {}
        
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate provider configuration"""
        if not self.url:
            raise ValueError("OpenBao URL is required")
        
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("OpenBao URL must start with http:// or https://")
        
        if not self.token:
            raise ValueError("OpenBao token is required")
        
        if self.api_version not in {"v1", "v2"}:
            raise ValueError(f"Unsupported API version: {self.api_version}")
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get HTTP client with OpenBao-specific configuration"""
        if self._client is None or self._client.is_closed:
            verify: Union[bool, str] = self.verify_ssl
            if self.ca_cert_path:
                verify = self.ca_cert_path
            
            headers = self._get_headers(
                token=self.token,
                additional_headers={"X-Vault-Request": "true"}
            )
            
            if self.namespace:
                headers["X-Vault-Namespace"] = self.namespace
            
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                verify=verify,
                headers=headers,
                follow_redirects=True,
            )
        
        return self._client
    
    async def _detect_kv_version(self, mount_path: str) -> str:
        """
        Detect KV engine version (v1 or v2) for a mount
        
        Args:
            mount_path: Mount path to check
            
        Returns:
            KV version ("v1" or "v2")
        """
        if mount_path in self._kv_version_cache:
            return self._kv_version_cache[mount_path]
        
        try:
            client = await self._get_http_client()
            url = self._build_url(self.url, f"v1/sys/mounts/{mount_path}")
            
            async def _get_mount_info() -> httpx.Response:
                response = await client.get(url)
                return response
            
            response = await self._retry_with_backoff("detect_kv_version", _get_mount_info())
            
            if response.status_code == 200:
                mount_data = response.json()
                engine_type = mount_data.get("data", {}).get("type", "kv")
                version = mount_data.get("data", {}).get("options", {}).get("version", "1")
                
                if engine_type == "kv" and version == "2":
                    detected_version = "v2"
                else:
                    detected_version = "v1"
                
                self._kv_version_cache[mount_path] = detected_version
                logger.debug(f"Detected KV version {detected_version} for mount {mount_path}")
                return detected_version
            
            elif response.status_code == 403:
                # If we can't read mount info, assume configured version
                logger.warning(f"Cannot detect KV version for {mount_path}, using configured version")
                return self.api_version
            
            else:
                self._handle_http_error(response, f"sys/mounts/{mount_path}")
                
        except Exception as e:
            logger.warning(f"KV version detection failed for {mount_path}: {e}, using configured version")
            return self.api_version
        
        return self.api_version
    
    def _build_secret_path(self, path: str, kv_version: str) -> str:
        """
        Build the full API path for a secret
        
        Args:
            path: Secret path
            kv_version: KV engine version
            
        Returns:
            Full API path
        """
        normalized_path = self._normalize_path(path)
        
        if kv_version == "v2":
            return f"v1/{self.mount_path}/data/{normalized_path}"
        else:
            return f"v1/{self.mount_path}/{normalized_path}"
    
    async def get_secret(self, path: str) -> SecretData:
        """
        Retrieve a secret from OpenBao/Vault
        
        Args:
            path: Secret path
            
        Returns:
            Secret data dictionary
            
        Raises:
            SecretNotFoundError: If secret doesn't exist
            ProviderConnectionError: If connection fails
            ProviderAuthenticationError: If authentication fails
            ProviderAuthorizationError: If access is denied
        """
        kv_version = await self._detect_kv_version(self.mount_path)
        api_path = self._build_secret_path(path, kv_version)
        
        client = await self._get_http_client()
        url = self._build_url(self.url, api_path)
        
        async def _get_secret_data() -> httpx.Response:
            response = await client.get(url)
            return response
        
        try:
            response = await self._retry_with_backoff(f"get_secret:{path}", _get_secret_data())
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract secret data based on KV version
                if kv_version == "v2":
                    secret_data = response_data.get("data", {}).get("data", {})
                    if not secret_data:
                        raise SecretNotFoundError(f"Secret data empty for: {path}")
                else:
                    secret_data = response_data.get("data", {})
                    if not secret_data:
                        raise SecretNotFoundError(f"Secret data empty for: {path}")
                
                return self._validate_secret_data(secret_data, path)
            
            else:
                self._handle_http_error(response, path)
                
        except (SecretNotFoundError, ProviderAuthenticationError, ProviderAuthorizationError):
            raise
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Failed to connect to OpenBao: {e}")
        except httpx.TimeoutException as e:
            raise ProviderConnectionError(f"Request timeout for secret {path}: {e}")
        except json.JSONDecodeError as e:
            raise SecretsProviderError(f"Invalid JSON response for secret {path}: {e}")
        except Exception as e:
            raise SecretsProviderError(f"Unexpected error retrieving secret {path}: {e}")
    
    async def put_secret(self, path: str, data: SecretData) -> bool:
        """
        Store a secret in OpenBao/Vault (if provider implements WritableSecretsProvider)
        
        Args:
            path: Secret path
            data: Secret data to store
            
        Returns:
            True if successful
        """
        kv_version = await self._detect_kv_version(self.mount_path)
        api_path = self._build_secret_path(path, kv_version)
        
        client = await self._get_http_client()
        url = self._build_url(self.url, api_path)
        
        # Prepare payload based on KV version
        if kv_version == "v2":
            payload = {"data": data}
        else:
            payload = data
        
        async def _put_secret_data() -> httpx.Response:
            response = await client.post(url, json=payload)
            return response
        
        try:
            response = await self._retry_with_backoff(f"put_secret:{path}", _put_secret_data())
            
            if response.status_code in (200, 204):
                logger.info(f"Successfully stored secret: {path}")
                return True
            else:
                self._handle_http_error(response, path)
                return False
                
        except (ProviderAuthenticationError, ProviderAuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Failed to store secret {path}: {e}")
            raise SecretsProviderError(f"Failed to store secret {path}: {e}")
    
    async def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from OpenBao/Vault
        
        Args:
            path: Secret path
            
        Returns:
            True if successful or secret didn't exist
        """
        kv_version = await self._detect_kv_version(self.mount_path)
        
        if kv_version == "v2":
            # For KV v2, we do a soft delete by updating metadata
            api_path = f"v1/{self.mount_path}/metadata/{self._normalize_path(path)}"
        else:
            api_path = f"v1/{self.mount_path}/{self._normalize_path(path)}"
        
        client = await self._get_http_client()
        url = self._build_url(self.url, api_path)
        
        async def _delete_secret_data() -> httpx.Response:
            response = await client.delete(url)
            return response
        
        try:
            response = await self._retry_with_backoff(f"delete_secret:{path}", _delete_secret_data())
            
            if response.status_code in (200, 204, 404):
                logger.info(f"Successfully deleted secret: {path}")
                return True
            else:
                self._handle_http_error(response, path)
                return False
                
        except SecretNotFoundError:
            # Secret not found is considered successful deletion
            return True
        except (ProviderAuthenticationError, ProviderAuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete secret {path}: {e}")
            raise SecretsProviderError(f"Failed to delete secret {path}: {e}")
    
    async def list_secrets(self, path_prefix: str = "") -> List[str]:
        """
        List available secrets with optional path prefix
        
        Args:
            path_prefix: Optional path prefix to filter results
            
        Returns:
            List of secret paths
        """
        kv_version = await self._detect_kv_version(self.mount_path)
        
        # Build list path
        if kv_version == "v2":
            list_path = f"v1/{self.mount_path}/metadata"
        else:
            list_path = f"v1/{self.mount_path}"
        
        if path_prefix:
            list_path += f"/{self._normalize_path(path_prefix)}"
        
        client = await self._get_http_client()
        url = self._build_url(self.url, list_path, list="true")
        
        async def _list_secrets_data() -> httpx.Response:
            response = await client.get(url)
            return response
        
        try:
            response = await self._retry_with_backoff("list_secrets", _list_secrets_data())
            
            if response.status_code == 200:
                response_data = response.json()
                keys = response_data.get("data", {}).get("keys", [])
                
                # Filter and process keys
                secrets = []
                for key in keys:
                    if key.endswith('/'):
                        # Directory - recursively list if needed
                        continue
                    
                    full_path = f"{path_prefix}/{key}".strip('/')
                    secrets.append(full_path)
                
                return sorted(secrets)
            
            elif response.status_code == 404:
                # No secrets found
                return []
            
            else:
                self._handle_http_error(response, f"list:{path_prefix}")
                return []
                
        except (ProviderAuthenticationError, ProviderAuthorizationError):
            raise
        except Exception as e:
            logger.warning(f"Failed to list secrets with prefix '{path_prefix}': {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check if OpenBao/Vault is healthy and accessible
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._get_http_client()
            url = self._build_url(self.url, "v1/sys/health")
            
            # Remove auth header for health check
            health_headers = {k: v for k, v in client.headers.items() if k != "Authorization"}
            
            async def _health_check() -> httpx.Response:
                response = await client.get(url, headers=health_headers)
                return response
            
            response = await self._retry_with_backoff("health_check", _health_check())
            
            # OpenBao/Vault health check returns various status codes
            if response.status_code in (200, 429, 472, 473, 501, 503):
                self._healthy = True
                logger.debug("OpenBao health check passed")
                return True
            else:
                self._healthy = False
                logger.warning(f"OpenBao health check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self._healthy = False
            logger.warning(f"OpenBao health check failed: {e}")
            return False
    
    async def get_auth_info(self) -> Dict[str, Any]:
        """
        Get information about the current authentication token
        
        Returns:
            Token information dictionary
        """
        client = await self._get_http_client()
        url = self._build_url(self.url, "v1/auth/token/lookup-self")
        
        async def _get_auth_info() -> httpx.Response:
            response = await client.get(url)
            return response
        
        try:
            response = await self._retry_with_backoff("auth_info", _get_auth_info())
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                self._handle_http_error(response, "auth/token/lookup-self")
                return {}
                
        except Exception as e:
            logger.warning(f"Failed to get auth info: {e}")
            return {}
    
    def __repr__(self) -> str:
        """String representation of provider"""
        return f"OpenBaoProvider(url={self.url}, mount={self.mount_path}, version={self.api_version})"


# Make it compatible with WritableSecretsProvider interface
WritableSecretsProvider.register(OpenBaoProvider)