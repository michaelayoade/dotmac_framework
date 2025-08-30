"""
DotMac HTTP Client - Core HTTP client framework with observability and resilience.

Provides standardized HTTP communication for DotMac services with built-in:
- Async and sync client support
- Retry logic with configurable strategies
- Circuit breaker integration
- OpenTelemetry instrumentation
- Middleware pipeline
- Error handling and response parsing
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from httpx import Limits, Timeout

from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..auth.providers import AuthProvider
from ..exceptions import (
    AuthenticationError,
    ConnectionError,
    HTTPClientError,
    RateLimitError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from ..middleware.base import HTTPMiddleware
from ..resilience.circuit_breaker import CircuitBreaker
from ..resilience.retry_strategies import ExponentialBackoffStrategy, RetryStrategy
from ..utils.request_builder import RequestBuilder
from ..utils.response_parser import ResponseParser

logger = logging.getLogger(__name__)


@dataclass
class HTTPClientConfig:
    """Configuration for DotMac HTTP client."""

    # Connection settings
    base_url: str
    timeout: float = 30.0
    follow_redirects: bool = True
    verify_ssl: bool = True
    max_redirects: int = 10

    # Connection pool settings
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 5.0

    # Retry configuration
    retry_strategy: Optional[RetryStrategy] = field(
        default_factory=lambda: ExponentialBackoffStrategy()
    )
    max_retries: int = 3
    retry_on_status: List[int] = field(default_factory=lambda: [429, 502, 503, 504])

    # Circuit breaker settings
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: float = 60.0
    circuit_breaker_expected_exception: type = HTTPClientError

    # Authentication
    auth_provider: Optional[AuthProvider] = None

    # Headers and user agent
    default_headers: Dict[str, str] = field(default_factory=dict)
    user_agent: str = "DotMac-SDK-Core/1.0.0"

    # Middleware
    middleware: List[HTTPMiddleware] = field(default_factory=list)

    # Observability
    enable_telemetry: bool = True
    service_name: str = "dotmac-http-client"

    # Rate limiting
    enable_rate_limiting: bool = False
    rate_limit_requests_per_second: float = 10.0

    # Tenant context
    tenant_header_name: str = "X-Tenant-ID"
    user_header_name: str = "X-User-ID"


@dataclass
class HTTPResponse:
    """Standardized HTTP response wrapper."""

    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    json_data: Optional[Dict[str, Any]] = None
    url: str = ""
    request_time: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response indicates client error."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response indicates server error."""
        return 500 <= self.status_code < 600


class HTTPError(HTTPClientError):
    """HTTP-specific error with response details."""

    def __init__(self, message: str, response: Optional[HTTPResponse] = None):
        super().__init__(message)
        self.response = response


class DotMacHTTPClient:
    """
    DotMac HTTP client with observability and resilience features.

    Provides both async and sync interfaces with standardized error handling,
    retry logic, circuit breakers, and OpenTelemetry instrumentation.
    """

    def __init__(self, config: HTTPClientConfig):
        """
        Initialize HTTP client with configuration.

        Args:
            config: Client configuration
        """
        self.config = config
        self.response_parser = ResponseParser()
        self.request_builder = RequestBuilder(config)

        # Initialize circuit breaker if enabled
        self.circuit_breaker = None
        if config.enable_circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=config.circuit_breaker_failure_threshold,
                recovery_timeout=config.circuit_breaker_recovery_timeout,
                expected_exception=config.circuit_breaker_expected_exception,
            )

        # Configure HTTP clients
        self._setup_clients()

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0

    def _setup_clients(self):
        """Configure httpx clients."""
        # Timeout configuration
        timeout = Timeout(self.config.timeout, connect=10.0)

        # Connection limits
        limits = Limits(
            max_connections=self.config.max_connections,
            max_keepalive_connections=self.config.max_keepalive_connections,
            keepalive_expiry=self.config.keepalive_expiry,
        )

        # Default headers
        headers = {"User-Agent": self.config.user_agent, **self.config.default_headers}

        # Async client
        self._async_client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=timeout,
            limits=limits,
            headers=headers,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
            verify=self.config.verify_ssl,
        )

        # Sync client
        self._sync_client = httpx.Client(
            base_url=self.config.base_url,
            timeout=timeout,
            limits=limits,
            headers=headers,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
            verify=self.config.verify_ssl,
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
        if hasattr(self, "_async_client"):
            await self._async_client.aclose()

    def close_sync(self):
        """Close sync HTTP client."""
        if hasattr(self, "_sync_client"):
            self._sync_client.close()

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> HTTPResponse:
        """
        Make async HTTP request with full resilience and observability.

        Args:
            method: HTTP method
            url: Request URL (relative to base_url or absolute)
            params: Query parameters
            json: JSON request body
            data: Request body data
            files: File uploads
            headers: Additional headers
            timeout: Request timeout override
            tenant_id: Tenant context
            user_id: User context
            **kwargs: Additional httpx parameters

        Returns:
            HTTPResponse object

        Raises:
            HTTPClientError: On request failure
        """
        # Build request
        request_data = self.request_builder.build_request(
            method=method,
            url=url,
            params=params,
            json=json,
            data=data,
            files=files,
            headers=headers,
            timeout=timeout,
            tenant_id=tenant_id,
            user_id=user_id,
            **kwargs,
        )

        # Apply rate limiting
        if self.config.enable_rate_limiting:
            await self._apply_rate_limiting()

        # Execute with circuit breaker if enabled
        if self.circuit_breaker:
            return await self.circuit_breaker.call(
                self._execute_request_async, request_data
            )
        else:
            return await self._execute_request_async(request_data)

    def request_sync(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> HTTPResponse:
        """
        Make sync HTTP request.

        Same interface as async request() but synchronous.
        """
        # Build request
        request_data = self.request_builder.build_request(
            method=method,
            url=url,
            params=params,
            json=json,
            data=data,
            files=files,
            headers=headers,
            timeout=timeout,
            tenant_id=tenant_id,
            user_id=user_id,
            **kwargs,
        )

        # Apply rate limiting
        if self.config.enable_rate_limiting:
            self._apply_rate_limiting_sync()

        # Execute with circuit breaker if enabled
        if self.circuit_breaker:
            return self.circuit_breaker.call_sync(
                self._execute_request_sync, request_data
            )
        else:
            return self._execute_request_sync(request_data)

    async def _execute_request_async(
        self, request_data: Dict[str, Any]
    ) -> HTTPResponse:
        """Execute async HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()

                # Make the request
                response = await self._async_client.request(**request_data)

                request_time = time.time() - start_time

                # Parse response
                http_response = self.response_parser.parse_response(
                    response, request_time
                )

                # Check if we should retry based on status code
                if (
                    attempt < self.config.max_retries
                    and response.status_code in self.config.retry_on_status
                ):
                    delay = self.config.retry_strategy.get_delay(attempt)
                    logger.warning(
                        f"HTTP {response.status_code} on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {request_data.get('url', 'unknown')}"
                    )
                    await asyncio.sleep(delay)
                    continue

                # Handle error status codes
                if response.status_code >= 400:
                    error = self._create_http_error(http_response)
                    if response.status_code < 500:
                        # Client errors shouldn't be retried
                        raise error
                    else:
                        # Server errors can be retried
                        if attempt < self.config.max_retries:
                            last_exception = error
                            delay = self.config.retry_strategy.get_delay(attempt)
                            await asyncio.sleep(delay)
                            continue
                        raise error

                return http_response

            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request timeout: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

            except httpx.ConnectError as e:
                last_exception = ConnectionError(f"Connection failed: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

            except Exception as e:
                if isinstance(e, HTTPClientError):
                    raise
                last_exception = HTTPClientError(f"Request failed: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    continue

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise HTTPClientError("Request failed after all retries")

    def _execute_request_sync(self, request_data: Dict[str, Any]) -> HTTPResponse:
        """Execute sync HTTP request with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()

                # Make the request
                response = self._sync_client.request(**request_data)

                request_time = time.time() - start_time

                # Parse response
                http_response = self.response_parser.parse_response(
                    response, request_time
                )

                # Check if we should retry based on status code
                if (
                    attempt < self.config.max_retries
                    and response.status_code in self.config.retry_on_status
                ):
                    delay = self.config.retry_strategy.get_delay(attempt)
                    logger.warning(
                        f"HTTP {response.status_code} on attempt {attempt + 1}, "
                        f"retrying in {delay:.2f}s: {request_data.get('url', 'unknown')}"
                    )
                    time.sleep(delay)
                    continue

                # Handle error status codes
                if response.status_code >= 400:
                    error = self._create_http_error(http_response)
                    if response.status_code < 500:
                        # Client errors shouldn't be retried
                        raise error
                    else:
                        # Server errors can be retried
                        if attempt < self.config.max_retries:
                            last_exception = error
                            delay = self.config.retry_strategy.get_delay(attempt)
                            time.sleep(delay)
                            continue
                        raise error

                return http_response

            except httpx.TimeoutException as e:
                last_exception = TimeoutError(f"Request timeout: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    time.sleep(delay)
                    continue

            except httpx.ConnectError as e:
                last_exception = ConnectionError(f"Connection failed: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    time.sleep(delay)
                    continue

            except Exception as e:
                if isinstance(e, HTTPClientError):
                    raise
                last_exception = HTTPClientError(f"Request failed: {e}")
                if attempt < self.config.max_retries:
                    delay = self.config.retry_strategy.get_delay(attempt)
                    time.sleep(delay)
                    continue

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise HTTPClientError("Request failed after all retries")

    def _create_http_error(self, response: HTTPResponse) -> HTTPError:
        """Create appropriate HTTP error based on status code."""
        if response.status_code == 401:
            return AuthenticationError("Authentication failed", response)
        elif response.status_code == 429:
            return RateLimitError("Rate limit exceeded", response)
        elif 400 <= response.status_code < 500:
            return ValidationError(f"Client error {response.status_code}", response)
        elif response.status_code >= 500:
            return ServerError(f"Server error {response.status_code}", response)
        else:
            return HTTPError(f"HTTP {response.status_code}", response)

    async def _apply_rate_limiting(self):
        """Apply async rate limiting."""
        now = time.time()
        time_since_last = now - self._last_request_time
        min_interval = 1.0 / self.config.rate_limit_requests_per_second

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)

        self._last_request_time = time.time()

    def _apply_rate_limiting_sync(self):
        """Apply sync rate limiting."""
        now = time.time()
        time_since_last = now - self._last_request_time
        min_interval = 1.0 / self.config.rate_limit_requests_per_second

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    # Convenience methods
    async def get(self, url: str, **kwargs) -> HTTPResponse:
        """Make GET request."""
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> HTTPResponse:
        """Make POST request."""
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> HTTPResponse:
        """Make PUT request."""
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> HTTPResponse:
        """Make PATCH request."""
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> HTTPResponse:
        """Make DELETE request."""
        return await self.request("DELETE", url, **kwargs)

    def get_sync(self, url: str, **kwargs) -> HTTPResponse:
        """Make sync GET request."""
        return self.request_sync("GET", url, **kwargs)

    def post_sync(self, url: str, **kwargs) -> HTTPResponse:
        """Make sync POST request."""
        return self.request_sync("POST", url, **kwargs)

    def put_sync(self, url: str, **kwargs) -> HTTPResponse:
        """Make sync PUT request."""
        return self.request_sync("PUT", url, **kwargs)

    def patch_sync(self, url: str, **kwargs) -> HTTPResponse:
        """Make sync PATCH request."""
        return self.request_sync("PATCH", url, **kwargs)

    def delete_sync(self, url: str, **kwargs) -> HTTPResponse:
        """Make sync DELETE request."""
        return self.request_sync("DELETE", url, **kwargs)

    async def stream(
        self, method: str, url: str, **kwargs
    ) -> AsyncGenerator[bytes, None]:
        """Stream response data."""
        request_data = self.request_builder.build_request(method, url, **kwargs)

        async with self._async_client.stream(method, **request_data) as response:
            async for chunk in response.aiter_bytes():
                yield chunk

    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        if self.circuit_breaker:
            return self.circuit_breaker.get_stats()
        return {"circuit_breaker_enabled": False}
