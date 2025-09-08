"""
Unified Middleware Base Classes for DotMac Framework.

Provides base classes that consolidate all DRY components into
easy-to-use middleware building blocks.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

from fastapi import FastAPI, Request

from ..utils.datetime_utils import utc_now
from .factory import MiddlewareFactory, MiddlewareProcessor, MiddlewareResult
from .headers import ExtractedHeaders, HeaderExtractor
from .response import StandardResponseDecorator
from .state import RequestStateManager

logger = logging.getLogger(__name__)


@dataclass
class MiddlewareConfig:
    """Configuration for unified middleware."""

    name: str
    exempt_paths: set[str] = None
    enable_timing: bool = True
    enable_request_id: bool = True
    enable_header_extraction: bool = True
    enable_response_decoration: bool = True
    enable_state_management: bool = True

    def __post_init__(self):
        if self.exempt_paths is None:
            self.exempt_paths = {
                "/docs",
                "/redoc",
                "/openapi.json",
                "/health",
                "/metrics",
            }


class UnifiedMiddlewareProcessor(MiddlewareProcessor, ABC):
    """Base processor that combines all DRY components.

    This class provides a foundation for building middleware that automatically
    handles header extraction, state management, and response decoration.
    """

    def __init__(self, config: MiddlewareConfig):
        """Initialize unified middleware processor.

        Args:
            config: Middleware configuration
        """
        self.config = config
        self.header_extractor = HeaderExtractor()
        self.response_decorator = StandardResponseDecorator()
        self.start_time = None

    async def process_request(self, request: Request) -> MiddlewareResult | None:
        """Process request with unified components.

        This method orchestrates the entire request processing pipeline:
        1. Extract headers
        2. Update request state
        3. Call custom processing logic
        4. Handle results

        Args:
            request: FastAPI request object

        Returns:
            MiddlewareResult or None
        """
        self.start_time = utc_now()

        try:
            # Step 1: Extract headers if enabled
            extracted_headers = None
            if self.config.enable_header_extraction:
                extracted_headers = self.header_extractor.extract_all(request)

            # Step 2: Update request state if enabled
            if self.config.enable_state_management:
                self._update_request_state(request, extracted_headers)

            # Step 3: Call custom processing logic
            result = await self.process_middleware(request, extracted_headers)

            # Step 4: Handle processing stages
            if self.config.enable_state_management:
                RequestStateManager.add_processing_stage(request, self.config.name)

            return result

        except Exception as e:
            logger.error(f"{self.config.name} processing error: {e}")
            raise

    @abstractmethod
    async def process_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Custom middleware processing logic.

        Subclasses implement their specific logic here while getting
        all the benefits of unified header extraction and state management.

        Args:
            request: FastAPI request object
            headers: Extracted headers (if enabled)

        Returns:
            MiddlewareResult or None to continue processing
        """
        pass

    def get_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
        """Generate response headers with processing context.

        Args:
            request: FastAPI request object
            result: Processing result

        Returns:
            Dictionary of response headers
        """
        headers = {}

        # Add processing time
        if self.start_time:
            processing_time = (utc_now() - self.start_time).total_seconds() * 1000
            headers[f"X-{self.config.name}-Time"] = f"{processing_time:.2f}ms"

        # Add custom headers
        custom_headers = self.get_custom_response_headers(request, result)
        headers.update(custom_headers)

        return headers

    def get_custom_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
        """Get custom response headers - override in subclasses.

        Args:
            request: FastAPI request object
            result: Processing result

        Returns:
            Dictionary of custom response headers
        """
        return {}

    def is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from processing."""
        return any(path.startswith(exempt_path) for exempt_path in self.config.exempt_paths)

    def _update_request_state(self, request: Request, headers: ExtractedHeaders | None):
        """Update request state based on extracted headers."""
        if not headers:
            return

        # Update tenant context
        if headers.tenant_id:
            RequestStateManager.update_tenant_context(
                request,
                headers.tenant_id,
                source=headers.sources.get("tenant_id", "header"),
            )

        # Update user context
        if headers.user_id:
            RequestStateManager.update_user_context(request, headers.user_id)

        # Update API version context
        if headers.api_version:
            RequestStateManager.update_api_version_context(request, headers.api_version)

        # Update operation context
        operation_updates = {}
        if headers.idempotency_key:
            operation_updates["idempotency_key"] = headers.idempotency_key
        if headers.correlation_id:
            operation_updates["correlation_id"] = headers.correlation_id

        if operation_updates:
            RequestStateManager.update_operation_context(request, **operation_updates)


class SimpleUnifiedMiddleware(UnifiedMiddlewareProcessor):
    """Simple unified middleware for basic processing.

    This class makes it easy to create middleware with just a processing function
    while still getting all the DRY benefits.
    """

    def __init__(
        self,
        name: str,
        process_fn: Callable[[Request, ExtractedHeaders | None], MiddlewareResult | None],
        exempt_paths: set[str] | None = None,
        **config_kwargs,
    ):
        """Initialize simple unified middleware.

        Args:
            name: Middleware name
            process_fn: Processing function
            exempt_paths: Exempt paths
            **config_kwargs: Additional configuration
        """
        config = MiddlewareConfig(name=name, exempt_paths=exempt_paths, **config_kwargs)
        super().__init__(config)
        self.process_fn = process_fn

    async def process_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Call the provided processing function."""
        if asyncio.iscoroutinefunction(self.process_fn):
            return await self.process_fn(request, headers)
        else:
            return self.process_fn(request, headers)


class TenantAwareMiddleware(UnifiedMiddlewareProcessor):
    """Base class for tenant-aware middleware.

    Automatically validates tenant context and provides tenant-scoped processing.
    """

    def __init__(self, config: MiddlewareConfig, require_tenant: bool = True):
        """Initialize tenant-aware middleware.

        Args:
            config: Middleware configuration
            require_tenant: Whether tenant is required
        """
        super().__init__(config)
        self.require_tenant = require_tenant

    async def process_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Process with tenant validation."""

        # Validate tenant context
        if self.require_tenant and (not headers or not headers.tenant_id):
            return MiddlewareResult.early_return({"detail": "Tenant context required"}, status=400)

        # Call tenant-specific processing
        return await self.process_tenant_middleware(request, headers)

    @abstractmethod
    async def process_tenant_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Process request with validated tenant context."""
        pass


class CachingMiddleware(UnifiedMiddlewareProcessor):
    """Base class for caching middleware with unified components."""

    def __init__(
        self,
        config: MiddlewareConfig,
        cache_get_fn: Callable[[str], dict[str, Any] | None],
        cache_set_fn: Callable[[str, dict[str, Any]], None],
        cache_key_fn: Callable[[Request], str] | None = None,
    ):
        """Initialize caching middleware.

        Args:
            config: Middleware configuration
            cache_get_fn: Function to get cached value
            cache_set_fn: Function to set cached value
            cache_key_fn: Function to generate cache key
        """
        super().__init__(config)
        self.cache_get = cache_get_fn
        self.cache_set = cache_set_fn
        self.cache_key_fn = cache_key_fn or self._default_cache_key

    async def process_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Process with caching logic."""

        # Generate cache key
        cache_key = self.cache_key_fn(request)
        if not cache_key:
            return None

        # Try cache
        cached_data = self.cache_get(cache_key)
        if cached_data:
            return MiddlewareResult.cache_hit(cached_data)

        # Store for post-processing
        request.state.cache_key = cache_key
        return None

    def _default_cache_key(self, request: Request) -> str:
        """Default cache key generation."""
        state = RequestStateManager.get_from_request(request)
        key_parts = [
            request.method,
            request.url.path,
            state.tenant_id or "no-tenant",
            state.api_version or "v1",
        ]
        return ":".join(key_parts)


class UnifiedMiddlewareManager:
    """Manager for creating and applying unified middleware."""

    @staticmethod
    def create_middleware(processor: UnifiedMiddlewareProcessor) -> Callable:
        """Create FastAPI middleware from unified processor.

        Args:
            processor: Unified middleware processor

        Returns:
            FastAPI middleware function
        """
        return MiddlewareFactory.create_processor_middleware(
            processor=processor,
            name=processor.config.name,
            exempt_paths=processor.config.exempt_paths,
            enable_timing=processor.config.enable_timing,
            enable_request_id=processor.config.enable_request_id,
        )

    @staticmethod
    def create_simple_middleware(
        name: str,
        process_fn: Callable[[Request, ExtractedHeaders | None], MiddlewareResult | None],
        **kwargs,
    ) -> Callable:
        """Create simple middleware from function.

        Args:
            name: Middleware name
            process_fn: Processing function
            **kwargs: Additional configuration

        Returns:
            FastAPI middleware function
        """
        processor = SimpleUnifiedMiddleware(name, process_fn, **kwargs)
        return UnifiedMiddlewareManager.create_middleware(processor)

    @staticmethod
    def apply_to_app(app: FastAPI, processors: list[UnifiedMiddlewareProcessor]):
        """Apply multiple unified middleware to FastAPI app.

        Args:
            app: FastAPI application
            processors: List of middleware processors
        """
        for processor in processors:
            middleware_fn = UnifiedMiddlewareManager.create_middleware(processor)
            app.middleware("http")(middleware_fn)
            logger.info(f"Applied unified middleware: {processor.config.name}")


# (imports consolidated at top)

# Example implementations showing how to use the unified base classes


class ExampleTenantSecurityMiddleware(TenantAwareMiddleware):
    """Example tenant security middleware using unified base."""

    def __init__(self):
        config = MiddlewareConfig(name="TenantSecurity", exempt_paths={"/docs", "/health", "/api/auth/login"})
        super().__init__(config, require_tenant=True)

    async def process_tenant_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Validate tenant security."""

        if not headers or not headers.tenant_id:
            return None

        # Validate tenant exists and is active (placeholder)
        if len(headers.tenant_id) < 3:
            return MiddlewareResult.early_return({"detail": "Invalid tenant ID format"}, status=403)

        # Continue processing
        return None


class ExampleAPIVersioningMiddleware(UnifiedMiddlewareProcessor):
    """Example API versioning middleware using unified base."""

    def __init__(self, supported_versions: Optional[set[str]] = None):
        config = MiddlewareConfig(name="APIVersioning", exempt_paths={"/docs", "/health"})
        super().__init__(config)
        self.supported_versions = supported_versions or {"v1", "v2"}

    async def process_middleware(
        self, request: Request, headers: ExtractedHeaders | None = None
    ) -> MiddlewareResult | None:
        """Validate API version."""

        if not headers or not headers.api_version:
            # Default to v1
            RequestStateManager.update_api_version_context(request, "v1")
            return None

        if headers.api_version not in self.supported_versions:
            return MiddlewareResult.early_return(
                {
                    "detail": f"API version '{headers.api_version}' not supported",
                    "supported_versions": list(self.supported_versions),
                },
                status=400,
            )

        return None

    def get_custom_response_headers(self, request: Request, result: MiddlewareResult | None = None) -> dict[str, str]:
        """Add API versioning headers."""
        return {"X-Supported-Versions": ", ".join(sorted(self.supported_versions))}
