"""
HTTP Client for REST API communication.

Provides robust async HTTP client with:
- Automatic retries with exponential backoff
- Error handling and response validation
- Authentication support
- Request/response logging
- Timeout management
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

import httpx
import structlog

logger = structlog.get_logger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class HTTPTimeoutError(HTTPClientError):
    """Exception raised when HTTP request times out."""
    pass


class HTTPRetryError(HTTPClientError):
    """Exception raised when all retry attempts fail."""
    pass


class HTTPClient:
    """
    Robust async HTTP client with retries and error handling.

    Provides:
    - Automatic retries with exponential backoff
    - Request/response logging
    - Authentication support
    - Timeout management
    - Error handling
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        retry_statuses: Optional[List[int]] = None,
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for all requests
            headers: Default headers to include in requests
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Backoff multiplier for retries
            retry_statuses: HTTP status codes to retry on
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self.retry_statuses = retry_statuses or [429, 500, 502, 503, 504]

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self):
        """Ensure client is initialized."""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
            )

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retries.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Raises:
            HTTPRetryError: If all retry attempts fail
            HTTPTimeoutError: If request times out
        """
        await self._ensure_client()

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(
                    "Making HTTP request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_attempts=self.max_retries + 1,
                )

                response = await self._client.request(method, url, **kwargs)

                # Check if we should retry based on status code
                if response.status_code in self.retry_statuses and attempt < self.max_retries:
                    logger.warning(
                        "HTTP request failed, will retry",
                        method=method,
                        url=url,
                        status_code=response.status_code,
                        attempt=attempt + 1,
                    )

                    # Wait before retry with exponential backoff
                    wait_time = self.retry_backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue

                # Log response
                logger.debug(
                    "HTTP request completed",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                    response_size=len(response.content),
                )

                return response

            except httpx.TimeoutException as e:
                last_exception = HTTPTimeoutError(f"Request timed out: {e}")
                logger.warning(
                    "HTTP request timed out",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    timeout=self.timeout,
                )

                if attempt < self.max_retries:
                    wait_time = self.retry_backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue

            except Exception as e:
                last_exception = HTTPClientError(f"Request failed: {e}")
                logger.error(
                    "HTTP request failed",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt < self.max_retries:
                    wait_time = self.retry_backoff_factor ** attempt
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted
        raise HTTPRetryError(f"All retry attempts failed. Last error: {last_exception}")

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make GET request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data
        """
        response = await self._make_request(
            "GET",
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return {"content": response.text}

    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make POST request.

        Args:
            url: Request URL
            json: JSON data to send
            data: Raw data to send
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data
        """
        response = await self._make_request(
            "POST",
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return {"content": response.text}

    async def put(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make PUT request.

        Args:
            url: Request URL
            json: JSON data to send
            data: Raw data to send
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data
        """
        response = await self._make_request(
            "PUT",
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return {"content": response.text}

    async def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make DELETE request.

        Args:
            url: Request URL
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data if any
        """
        response = await self._make_request(
            "DELETE",
            url,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        if response.content and response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return None

    async def patch(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make PATCH request.

        Args:
            url: Request URL
            json: JSON data to send
            data: Raw data to send
            params: Query parameters
            headers: Additional headers

        Returns:
            Response JSON data
        """
        response = await self._make_request(
            "PATCH",
            url,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

        response.raise_for_status()

        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        else:
            return {"content": response.text}

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
