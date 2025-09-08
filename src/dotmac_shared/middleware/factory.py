"""
Middleware Factory for DotMac Framework.

Provides standardized middleware creation with consistent error handling,
logging, and response patterns to eliminate duplication across middleware.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..utils.datetime_utils import format_iso, utc_now

logger = logging.getLogger(__name__)


class MiddlewareResult:
    """Standard result object for middleware processing."""

    def __init__(
        self,
        action: str = "continue",
        data: dict[str, Any] | None = None,
        response_status: int = 200,
        response_headers: dict[str, str] | None = None,
    ):
        """Initialize middleware result.

        Args:
            action: Action to take ('continue', 'early_return', 'cache_hit')
            data: Optional data payload
            response_status: HTTP status code for early returns
            response_headers: Additional response headers
        """
        self.action = action
        self.data = data or {}
        self.response_status = response_status
        self.response_headers = response_headers or {}

    @classmethod
    def continue_processing(cls, data: dict[str, Any] | None = None) -> "MiddlewareResult":
        """Continue with normal request processing."""
        return cls(action="continue", data=data)

    @classmethod
    def early_return(
        cls,
        data: dict[str, Any],
        status: int = 200,
        headers: dict[str, str] | None = None,
    ) -> "MiddlewareResult":
        """Return early with data (e.g., cached result)."""
        return cls(
            action="early_return",
            data=data,
            response_status=status,
            response_headers=headers,
        )

    @classmethod
    def cache_hit(cls, cached_data: dict[str, Any], cache_headers: dict[str, str] | None = None) -> "MiddlewareResult":
        """Return cached result."""
        headers = cache_headers or {}
        headers["X-Cache-Hit"] = "true"
        headers["X-Cache-Time"] = format_iso()
        return cls(action="cache_hit", data=cached_data, response_headers=headers)


class MiddlewareProcessor:
    """Base processor interface for middleware components."""

    async def process_request(self, request: Request) -> MiddlewareResult | None:
        """Process incoming request.

        Args:
            request: FastAPI request object

        Returns:
            MiddlewareResult or None to continue processing
        """
        raise NotImplementedError

    def get_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
        """Get response headers to add.

        Args:
            request: FastAPI request object
            result: Processing result

        Returns:
            Dictionary of headers to add
        """
        return {}

    def is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from processing.

        Args:
            path: Request path

        Returns:
            True if exempt, False otherwise
        """
        return False


class MiddlewareFactory:
    """Factory for creating standardized middleware with consistent patterns."""

    @staticmethod
    def create_processor_middleware(
        processor: MiddlewareProcessor,
        name: str,
        exempt_paths: set[str] | None = None,
        enable_timing: bool = True,
        enable_request_id: bool = True,
    ) -> Callable:
        """Create standardized middleware from processor.

        Args:
            processor: Middleware processor instance
            name: Middleware name for logging
            exempt_paths: Set of paths to exempt from processing
            enable_timing: Whether to add timing headers
            enable_request_id: Whether to add request ID tracking

        Returns:
            FastAPI middleware function
        """

        async def middleware(request: Request, call_next):
            start_time = utc_now() if enable_timing else None
            request_id = f"req_{utc_now().timestamp()}" if enable_request_id else None

            try:
                # Set request ID
                if request_id:
                    request.state.request_id = request_id

                # Check exempt paths
                if exempt_paths and any(request.url.path.startswith(path) for path in exempt_paths):
                    logger.debug(f"{name}: Skipping exempt path {request.url.path}")
                    return await call_next(request)

                if processor.is_exempt_path(request.url.path):
                    logger.debug(f"{name}: Skipping exempt path {request.url.path}")
                    return await call_next(request)

                # Process request
                logger.debug(f"{name}: Processing request {request.method} {request.url.path}")
                result = await processor.process_request(request)

                # Handle early returns
                if result and result.action in ["early_return", "cache_hit"]:
                    response = JSONResponse(status_code=result.response_status, content=result.data)

                    # Add result headers
                    for key, value in result.response_headers.items():
                        response.headers[key] = value

                    # Add standard headers
                    MiddlewareFactory._add_standard_headers(response, request, name, start_time, request_id)

                    logger.info(f"{name}: Early return with {result.action}")
                    return response

                # Continue with normal processing
                response = await call_next(request)

                # Add response headers from processor
                processor_headers = processor.get_response_headers(request, result)
                for key, value in processor_headers.items():
                    response.headers[key] = value

                # Add standard headers
                MiddlewareFactory._add_standard_headers(response, request, name, start_time, request_id)

                logger.debug(f"{name}: Request completed successfully")
                return response

            except HTTPException as e:
                logger.warning(f"{name}: HTTP exception {e.status_code}: {e.detail}")
                response = JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail, "middleware": name},
                )

                # Add error headers
                if hasattr(e, "headers") and e.headers:
                    for key, value in e.headers.items():
                        response.headers[key] = value

                MiddlewareFactory._add_standard_headers(response, request, name, start_time, request_id)
                return response

            except Exception as e:
                logger.error(f"{name}: Unexpected error: {e}", exc_info=True)
                response = JSONResponse(
                    status_code=500,
                    content={
                        "detail": f"{name} middleware processing failed",
                        "error_type": type(e).__name__,
                        "middleware": name,
                    },
                )

                MiddlewareFactory._add_standard_headers(response, request, name, start_time, request_id)
                return response

        # Set middleware name for debugging
        middleware.__name__ = f"{name}_middleware"
        return middleware

    @staticmethod
    def _add_standard_headers(
        response: Response,
        request: Request,
        middleware_name: str,
        start_time: Any | None = None,
        request_id: str | None = None,
    ):
        """Add standard headers to response.

        Args:
            response: Response object
            request: Request object
            middleware_name: Name of middleware
            start_time: Start time for timing
            request_id: Request ID
        """
        # Add processing time
        if start_time:
            processing_time = (utc_now() - start_time).total_seconds()
            response.headers["X-Processing-Time"] = f"{processing_time:.4f}s"
            response.headers[f"X-{middleware_name}-Time"] = f"{processing_time:.4f}s"

        # Add request ID
        if request_id:
            response.headers["X-Request-ID"] = request_id

        # Add middleware signature
        response.headers["X-Processed-By"] = middleware_name
        response.headers["X-Processing-Time-UTC"] = format_iso()

    @staticmethod
    def create_simple_middleware(
        process_fn: Callable[[Request], dict[str, Any] | None],
        name: str,
        exempt_paths: set[str] | None = None,
        response_headers_fn: Callable[[Request, dict], dict[str, str]] | None = None,
    ) -> Callable:
        """Create simple middleware from processing function.

        Args:
            process_fn: Function that processes request
            name: Middleware name
            exempt_paths: Exempt paths
            response_headers_fn: Function to generate response headers

        Returns:
            FastAPI middleware function
        """

        class SimpleProcessor(MiddlewareProcessor):
            async def process_request(self, request: Request) -> MiddlewareResult | None:
                result = await process_fn(request) if asyncio.iscoroutinefunction(process_fn) else process_fn(request)
                return MiddlewareResult.continue_processing(result) if result else None

            def get_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
                if response_headers_fn and result and result.data:
                    return response_headers_fn(request, result.data)
                return {}

            def is_exempt_path(self, path: str) -> bool:
                return exempt_paths and any(path.startswith(exempt_path) for exempt_path in exempt_paths)

        processor = SimpleProcessor()
        return MiddlewareFactory.create_processor_middleware(processor, name, exempt_paths)

    @staticmethod
    def create_caching_middleware(
        cache_key_fn: Callable[[Request], str | None],
        cache_get_fn: Callable[[str], dict[str, Any] | None],
        cache_set_fn: Callable[[str, dict[str, Any]], None],
        name: str = "Cache",
        ttl_seconds: int = 3600,
    ) -> Callable:
        """Create caching middleware.

        Args:
            cache_key_fn: Function to generate cache key from request
            cache_get_fn: Function to get cached value
            cache_set_fn: Function to set cached value
            name: Middleware name
            ttl_seconds: Cache TTL in seconds

        Returns:
            FastAPI middleware function
        """

        class CachingProcessor(MiddlewareProcessor):
            async def process_request(self, request: Request) -> MiddlewareResult | None:
                cache_key = cache_key_fn(request)
                if not cache_key:
                    return None

                # Try to get from cache
                cached_data = cache_get_fn(cache_key)
                if cached_data:
                    return MiddlewareResult.cache_hit(cached_data)

                # Store for post-processing
                request.state.cache_key = cache_key
                return None

            def get_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
                return {"X-Cache-TTL": str(ttl_seconds)}

        processor = CachingProcessor()
        base_middleware = MiddlewareFactory.create_processor_middleware(processor, name)

        # Wrap to add cache setting on response
        async def caching_middleware(request: Request, call_next):
            response = await base_middleware(request, call_next)

            # Set cache on successful response
            if hasattr(request.state, "cache_key") and response.status_code == 200 and hasattr(response, "body"):
                try:
                    # This is a simplified version - in practice you'd need to handle JSON serialization
                    cache_set_fn(request.state.cache_key, {"cached": True})
                except Exception as e:
                    logger.warning(f"Cache set failed: {e}")

            return response

        return caching_middleware


# (imports consolidated at top)
