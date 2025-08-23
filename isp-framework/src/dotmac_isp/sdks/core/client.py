"""
Base SDK client with common functionality for all service SDKs.
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
    SDKTimeoutError,
)
from .utils import build_headers, parse_response

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseSDKClient(Generic[T]):
    """
    Base client for all DotMac service SDKs.
    Provides common HTTP operations, retry logic, and error handling.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True,
        include_deprecated: bool = False,
    ):
        """
        Initialize base SDK client.

        Args:
            base_url: Base URL of the service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
            include_deprecated: Whether to include deprecated entities in responses
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        self.include_deprecated = include_deprecated

        # Configure HTTP client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers=build_headers(api_key),
            follow_redirects=True,
        )

        # Sync client for backward compatibility
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
            headers=build_headers(api_key),
            follow_redirects=True,
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
        reraise=True,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers

        Returns:
            HTTP response

        Raises:
            SDKError: On request failure
        """
        url = f"{endpoint}" if endpoint.startswith("http") else endpoint

        # Add deprecation filter to params if needed
        if params is None:
            params = {}
        if not self.include_deprecated:
            params["exclude_deprecated"] = "true"

        try:
            response = await self.client.request(
                method=method, url=url, params=params, json=json_data, headers=headers
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise SDKRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )

            # Handle authentication errors
            if response.status_code in (401, 403):
                raise SDKAuthenticationError(f"Authentication failed: {response.text}")

            # Handle client errors
            if 400 <= response.status_code < 500:
                raise SDKValidationError(
                    f"Client error: {response.status_code} - {response.text}"
                )

            # Handle server errors
            if response.status_code >= 500:
                raise SDKConnectionError(
                    f"Server error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            raise SDKTimeoutError(f"Request timeout: {e}")
        except httpx.ConnectError as e:
            raise SDKConnectionError(f"Connection failed: {e}")
        except Exception as e:
            if isinstance(e, SDKError):
                raise
            raise SDKError(f"Request failed: {e}")

    def _make_request_sync(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        Synchronous version of _make_request.
        """
        url = f"{endpoint}" if endpoint.startswith("http") else endpoint

        # Add deprecation filter to params if needed
        if params is None:
            params = {}
        if not self.include_deprecated:
            params["exclude_deprecated"] = "true"

        try:
            response = self.sync_client.request(
                method=method, url=url, params=params, json=json_data, headers=headers
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise SDKRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )

            # Handle authentication errors
            if response.status_code in (401, 403):
                raise SDKAuthenticationError(f"Authentication failed: {response.text}")

            # Handle client errors
            if 400 <= response.status_code < 500:
                raise SDKValidationError(
                    f"Client error: {response.status_code} - {response.text}"
                )

            # Handle server errors
            if response.status_code >= 500:
                raise SDKConnectionError(
                    f"Server error: {response.status_code} - {response.text}"
                )

            response.raise_for_status()
            return response

        except httpx.TimeoutException as e:
            raise SDKTimeoutError(f"Request timeout: {e}")
        except httpx.ConnectError as e:
            raise SDKConnectionError(f"Connection failed: {e}")
        except Exception as e:
            if isinstance(e, SDKError):
                raise
            raise SDKError(f"Request failed: {e}")

    async def get(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        response = await self._make_request("GET", endpoint, params=params, **kwargs)
        return parse_response(response)

    async def post(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        response = await self._make_request("POST", endpoint, json_data=data, **kwargs)
        return parse_response(response)

    async def put(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        response = await self._make_request("PUT", endpoint, json_data=data, **kwargs)
        return parse_response(response)

    async def patch(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Make PATCH request."""
        response = await self._make_request("PATCH", endpoint, json_data=data, **kwargs)
        return parse_response(response)

    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request."""
        response = await self._make_request("DELETE", endpoint, **kwargs)
        return parse_response(response)

    def get_sync(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Synchronous GET request."""
        response = self._make_request_sync("GET", endpoint, params=params, **kwargs)
        return parse_response(response)

    def post_sync(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Synchronous POST request."""
        response = self._make_request_sync("POST", endpoint, json_data=data, **kwargs)
        return parse_response(response)

    def put_sync(
        self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Synchronous PUT request."""
        response = self._make_request_sync("PUT", endpoint, json_data=data, **kwargs)
        return parse_response(response)

    def delete_sync(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Synchronous DELETE request."""
        response = self._make_request_sync("DELETE", endpoint, **kwargs)
        return parse_response(response)

    def paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ):
        """
        Generator for paginated results.

        Args:
            endpoint: API endpoint
            params: Query parameters
            page_size: Number of items per page

        Yields:
            Items from each page
        """
        if params is None:
            params = {}

        params["limit"] = page_size
        params["offset"] = 0

        while True:
            response = self.get_sync(endpoint, params=params)

            items = response.get("items", response.get("data", []))
            if not items:
                break

            for item in items:
                yield item

            # Check if there are more pages
            if len(items) < page_size:
                break

            params["offset"] += page_size

    async def paginate_async(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ):
        """
        Async generator for paginated results.

        Args:
            endpoint: API endpoint
            params: Query parameters
            page_size: Number of items per page

        Yields:
            Items from each page
        """
        if params is None:
            params = {}

        params["limit"] = page_size
        params["offset"] = 0

        while True:
            response = await self.get(endpoint, params=params)

            items = response.get("items", response.get("data", []))
            if not items:
                break

            for item in items:
                yield item

            # Check if there are more pages
            if len(items) < page_size:
                break

            params["offset"] += page_size
