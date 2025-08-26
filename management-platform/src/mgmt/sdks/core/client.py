"""
Base SDK client with common functionality for all service SDKs.

Provides HTTP operations, retry logic, error handling, and authentication
for ISP framework SDKs with proper code quality standards.
"""

from typing import Dict, Any, Optional, Union, Type, TypeVar, Generic
from datetime import datetime
import httpx
import logging
from functools import wraps
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from .exceptions import (
    SDKError,
    SDKConnectionError,
    SDKAuthenticationError,
    SDKValidationError,
    SDKRateLimitError,
    SDKTimeoutError
, timezone)
from .utils import build_headers, parse_response

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseSDKClient(Generic[T]):
    """
    Base client for all DotMac ISP Framework service SDKs.
    
    Provides common HTTP operations, retry logic, error handling,
    and authentication for consistent SDK behavior across all services.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize base SDK client.
        
        Args:
            base_url: Base URL of the service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
            tenant_id: Tenant ID for multi-tenant isolation
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.tenant_id = tenant_id
        
        # Configure HTTP client
        headers = build_headers(api_key, tenant_id)
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers=headers,
            follow_redirects=True
        )
        
        # Sync client for backward compatibility
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers=headers,
            follow_redirects=True
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def __enter__(self):
        """Sync context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        self.close_sync()
    
    async def close(self):
        """Close async HTTP client."""
        await self.client.aclose()
    
    def close_sync(self):
        """Close sync HTTP client."""
        self.sync_client.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional httpx arguments
            
        Returns:
            Parsed response data
            
        Raises:
            SDKError: Base SDK error
            SDKConnectionError: Connection issues
            SDKAuthenticationError: Auth failures
            SDKValidationError: Validation errors
            SDKRateLimitError: Rate limiting
            SDKTimeoutError: Request timeout
        """
        try:
            # Prepare request
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            request_headers = dict(self.client.headers)
            if headers:
                request_headers.update(headers)
            
            # Make request
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                **kwargs
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise SDKAuthenticationError("Authentication failed")
            elif response.status_code == 403:
                raise SDKAuthenticationError("Access forbidden")
            elif response.status_code == 404:
                return {}  # Not found is often acceptable
            elif response.status_code == 422:
                error_detail = response.model_dump_json().get('detail', 'Validation error')
                raise SDKValidationError(f"Validation failed: {error_detail}")
            elif response.status_code == 429:
                raise SDKRateLimitError("Rate limit exceeded")
            elif response.status_code >= 400:
                error_msg = response.model_dump_json().get('detail', f'HTTP {response.status_code}')
                raise SDKError(f"Request failed: {error_msg}")
            
            # Parse successful response
            return parse_response(response)
            
        except httpx.TimeoutException as e:
            raise SDKTimeoutError(f"Request timeout: {e}")
        except httpx.ConnectError as e:
            raise SDKConnectionError(f"Connection error: {e}")
        except httpx.HTTPError as e:
            raise SDKConnectionError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in SDK request: {e}")
            raise SDKError(f"Unexpected error: {e}")
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", endpoint, params=params, **kwargs)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", endpoint, data=data, **kwargs)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", endpoint, data=data, **kwargs)
    
    async def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PATCH request."""
        return await self.request("PATCH", endpoint, data=data, **kwargs)
    
    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", endpoint, **kwargs)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service.
        
        Returns:
            Health status information
        """
        try:
            response = await self.get("/health")
            return response
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


# Convenience decorator for SDK methods
def sdk_method(f):
    """
    Decorator for SDK methods to provide consistent error handling.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function with error handling
    """
    @wraps(f)
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except SDKError:
            # Re-raise SDK errors as-is
            raise
        except Exception as e:
            # Convert unexpected errors to SDK errors
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            raise SDKError(f"Method {f.__name__} failed: {e}")
    
    return wrapper


# Retry decorator specifically for SDK operations
def sdk_retry(max_attempts: int = 3, backoff_factor: float = 1.0):
    """
    Retry decorator for SDK operations.
    
    Args:
        max_attempts: Maximum retry attempts
        backoff_factor: Exponential backoff multiplier
        
    Returns:
        Retry decorator
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff_factor, min=1, max=10),
        reraise=True
    )