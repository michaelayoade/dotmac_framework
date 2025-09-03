"""
Tenant middleware for FastAPI applications.

Provides automatic tenant resolution and context management for incoming requests.
"""

import time
from typing import Optional, Callable, Any
from contextvars import copy_context

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger

from .config import TenantConfig
from .identity import TenantIdentityResolver, set_tenant_context, clear_tenant_context
from .exceptions import (
    TenantNotFoundError,
    TenantResolutionError,
    TenantSecurityError,
    TenantContextError,
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic tenant resolution and context management.
    
    This middleware:
    1. Resolves tenant identity from incoming requests
    2. Sets tenant context for the request lifecycle
    3. Handles tenant-related errors gracefully
    4. Provides logging and monitoring capabilities
    5. Enforces tenant security boundaries
    """
    
    def __init__(
        self,
        app: ASGIApp,
        config: Optional[TenantConfig] = None,
        resolver: Optional[TenantIdentityResolver] = None,
        error_handler: Optional[Callable[[Request, Exception], Response]] = None
    ):
        """
        Initialize tenant middleware.
        
        Args:
            app: FastAPI application
            config: Tenant configuration (uses defaults if None)
            resolver: Custom tenant resolver (creates default if None)
            error_handler: Custom error handler for tenant errors
        """
        super().__init__(app)
        self.config = config or TenantConfig()
        self.resolver = resolver or TenantIdentityResolver(self.config)
        self.error_handler = error_handler or self._default_error_handler
        
        # Metrics tracking
        self._request_count = 0
        self._error_count = 0
        self._resolution_times = []
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with tenant resolution and context management.
        
        Args:
            request: Incoming FastAPI request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from downstream handlers
        """
        start_time = time.time()
        self._request_count += 1
        
        # Skip tenant resolution for certain paths
        if self._should_skip_resolution(request):
            return await call_next(request)
        
        try:
            # Resolve tenant context
            resolution_start = time.time()
            tenant_context = await self.resolver.resolve_tenant(request)
            resolution_time = time.time() - resolution_start
            
            if self.config.enable_tenant_metrics:
                self._resolution_times.append(resolution_time)
                # Keep only last 100 measurements
                if len(self._resolution_times) > 100:
                    self._resolution_times = self._resolution_times[-100:]
            
            # Set tenant context for the request
            set_tenant_context(tenant_context)
            
            # Add tenant info to request state for easy access
            request.state.tenant = tenant_context
            
            # Process request with tenant context
            ctx = copy_context()
            response = await ctx.run(call_next, request)
            
            # Add tenant headers to response if configured
            if self.config.log_tenant_access:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
                response.headers["X-Tenant-Resolution"] = tenant_context.resolution_method
            
            # Log successful request
            total_time = time.time() - start_time
            if self.config.log_tenant_access:
                logger.info(
                    f"Tenant request completed: {tenant_context.tenant_id}",
                    extra={
                        "tenant_id": tenant_context.tenant_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "duration_ms": round(total_time * 1000, 2),
                        "resolution_duration_ms": round(resolution_time * 1000, 2),
                    }
                )
            
            return response
            
        except (TenantNotFoundError, TenantResolutionError, TenantSecurityError) as e:
            self._error_count += 1
            logger.warning(f"Tenant middleware error: {e}")
            return self.error_handler(request, e)
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Unexpected tenant middleware error: {e}")
            return self.error_handler(request, e)
            
        finally:
            # Always clear tenant context after request
            clear_tenant_context()
    
    def _should_skip_resolution(self, request: Request) -> bool:
        """
        Determine if tenant resolution should be skipped for this request.
        
        Args:
            request: Incoming request
            
        Returns:
            True if resolution should be skipped
        """
        path = request.url.path
        
        # Skip for health checks and monitoring endpoints
        skip_paths = [
            "/health",
            "/healthz", 
            "/ready",
            "/metrics",
            "/favicon.ico",
            "/robots.txt",
            "/.well-known",
        ]
        
        for skip_path in skip_paths:
            if path.startswith(skip_path):
                return True
        
        # Skip for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return True
        
        return False
    
    def _default_error_handler(self, request: Request, error: Exception) -> Response:
        """
        Default error handler for tenant-related errors.
        
        Args:
            request: The request that caused the error
            error: The exception that occurred
            
        Returns:
            JSON error response
        """
        if isinstance(error, TenantNotFoundError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "tenant_not_found",
                    "message": "Could not identify tenant for this request",
                    "details": error.details,
                }
            )
        
        elif isinstance(error, TenantResolutionError):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "tenant_resolution_failed",
                    "message": "Failed to resolve tenant identity",
                    "details": error.details,
                }
            )
        
        elif isinstance(error, TenantSecurityError):
            return JSONResponse(
                status_code=403,
                content={
                    "error": "tenant_security_violation",
                    "message": "Tenant security boundary violation",
                    "details": error.details,
                }
            )
        
        else:
            # Generic error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "tenant_middleware_error",
                    "message": "An error occurred processing tenant information",
                }
            )
    
    def get_metrics(self) -> dict:
        """
        Get middleware performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        avg_resolution_time = 0
        if self._resolution_times:
            avg_resolution_time = sum(self._resolution_times) / len(self._resolution_times)
        
        return {
            "total_requests": self._request_count,
            "total_errors": self._error_count,
            "error_rate": self._error_count / self._request_count if self._request_count > 0 else 0,
            "avg_resolution_time_ms": round(avg_resolution_time * 1000, 2),
            "recent_resolution_times": self._resolution_times[-10:],  # Last 10 measurements
        }


class TenantSecurityMiddleware(BaseHTTPMiddleware):
    """
    Additional middleware for tenant security enforcement.
    
    This middleware provides additional security checks and can be used
    in combination with TenantMiddleware for enhanced security.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        config: Optional[TenantConfig] = None,
        security_enforcer: Optional[Any] = None  # Will import TenantSecurityEnforcer later
    ):
        super().__init__(app)
        self.config = config or TenantConfig()
        self.security_enforcer = security_enforcer
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Enforce tenant security boundaries.
        
        Args:
            request: Incoming request
            call_next: Next handler in chain
            
        Returns:
            Response with security validation
        """
        # Skip security checks if tenant context is not required
        if self._should_skip_security(request):
            return await call_next(request)
        
        # Get tenant context (should be set by TenantMiddleware)
        tenant_context = getattr(request.state, 'tenant', None)
        
        if not tenant_context and self.config.enforce_tenant_isolation:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "tenant_context_missing",
                    "message": "Tenant context required for this request"
                }
            )
        
        # Additional security validations can be added here
        if self.security_enforcer and tenant_context:
            try:
                await self.security_enforcer.validate_tenant_access(
                    tenant_context, request
                )
            except TenantSecurityError as e:
                logger.warning(f"Tenant security violation: {e}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "tenant_access_denied",
                        "message": "Access denied for tenant",
                        "details": e.details,
                    }
                )
        
        return await call_next(request)
    
    def _should_skip_security(self, request: Request) -> bool:
        """Check if security validation should be skipped."""
        # Same skip logic as tenant resolution
        return TenantMiddleware._should_skip_resolution(self, request)