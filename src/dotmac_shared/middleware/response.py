"""
Response Decorator for DotMac Framework.

Provides standardized response header management and formatting
to eliminate duplication across middleware components.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .state import RequestStateManager, get_request_id
from ..utils.datetime_utils import format_iso, utc_now

logger = logging.getLogger(__name__)


@dataclass
class ResponseHeaderConfig:
    """Configuration for response headers."""
    
    # Standard headers to always include
    STANDARD_HEADERS = {
        "X-Request-ID": "request_id",
        "X-Processing-Time-UTC": "timestamp", 
        "X-Powered-By": "DotMac Framework",
    }
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }
    
    # CORS headers (configurable)
    CORS_HEADERS = {
        "Access-Control-Allow-Origin": None,  # Set dynamically
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "X-Request-ID, X-Processing-Time, X-Rate-Limit-*",
    }
    
    # Cache control headers
    CACHE_HEADERS = {
        "no_cache": {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0"
        },
        "short_cache": {
            "Cache-Control": "public, max-age=300",  # 5 minutes
        },
        "long_cache": {
            "Cache-Control": "public, max-age=86400",  # 1 day
        }
    }


@dataclass
class ResponseContext:
    """Context for response decoration."""
    
    # Processing info
    processing_time_ms: Optional[float] = None
    middleware_chain: List[str] = field(default_factory=list)
    
    # Cache info  
    cache_status: Optional[str] = None  # hit, miss, bypass
    cache_ttl: Optional[int] = None
    
    # Rate limiting
    rate_limit_remaining: Optional[int] = None
    rate_limit_reset: Optional[str] = None
    rate_limit_limit: Optional[int] = None
    
    # Deprecation warnings
    deprecation_warnings: List[str] = field(default_factory=list)
    sunset_date: Optional[str] = None
    replacement_version: Optional[str] = None
    
    # Custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)


class ResponseDecorator:
    """Standardized response header management and decoration."""
    
    def __init__(self, config: Optional[ResponseHeaderConfig] = None):
        """Initialize response decorator.
        
        Args:
            config: Optional response header configuration
        """
        self.config = config or ResponseHeaderConfig()
        
    def decorate_response(self, 
                         response: Response, 
                         request: Request,
                         context: Optional[ResponseContext] = None) -> Response:
        """Add standard headers to response.
        
        Args:
            response: FastAPI response object
            request: FastAPI request object  
            context: Optional response context
            
        Returns:
            Decorated response
        """
        context = context or ResponseContext()
        
        # Add standard headers
        self._add_standard_headers(response, request, context)
        
        # Add state-based headers
        self._add_state_headers(response, request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        # Add deprecation warnings
        self._add_deprecation_headers(response, request, context)
        
        # Add rate limiting headers
        self._add_rate_limit_headers(response, context)
        
        # Add cache headers
        self._add_cache_headers(response, context)
        
        # Add custom headers
        self._add_custom_headers(response, context)
        
        logger.debug(f"Decorated response with {len(response.headers)} headers")
        
        return response
        
    def create_error_response(self,
                            status_code: int,
                            detail: str,
                            request: Request,
                            error_code: Optional[str] = None,
                            additional_info: Optional[Dict[str, Any]] = None) -> JSONResponse:
        """Create standardized error response.
        
        Args:
            status_code: HTTP status code
            detail: Error detail message
            request: FastAPI request object
            error_code: Optional error code
            additional_info: Optional additional error information
            
        Returns:
            Decorated JSON error response
        """
        error_data = {
            "detail": detail,
            "error_code": error_code,
            "timestamp": format_iso(),
            "request_id": get_request_id(request),
        }
        
        if additional_info:
            error_data.update(additional_info)
            
        response = JSONResponse(
            status_code=status_code,
            content=error_data
        )
        
        # Decorate with standard headers
        context = ResponseContext()
        return self.decorate_response(response, request, context)
        
    def create_success_response(self,
                              data: Any,
                              request: Request,
                              status_code: int = 200,
                              context: Optional[ResponseContext] = None) -> JSONResponse:
        """Create standardized success response.
        
        Args:
            data: Response data
            request: FastAPI request object
            status_code: HTTP status code
            context: Optional response context
            
        Returns:
            Decorated JSON success response
        """
        response_data = {
            "data": data,
            "timestamp": format_iso(),
            "request_id": get_request_id(request),
        }
        
        response = JSONResponse(
            status_code=status_code,
            content=response_data
        )
        
        return self.decorate_response(response, request, context)
        
    def _add_standard_headers(self, 
                             response: Response, 
                             request: Request, 
                             context: ResponseContext):
        """Add standard headers to response."""
        
        # Request ID
        response.headers["X-Request-ID"] = get_request_id(request)
        
        # Processing timestamp
        response.headers["X-Processing-Time-UTC"] = format_iso()
        
        # Framework signature
        response.headers["X-Powered-By"] = "DotMac Framework"
        
        # Processing time
        if context.processing_time_ms is not None:
            response.headers["X-Processing-Time"] = f"{context.processing_time_ms:.4f}ms"
            
        # Middleware chain
        if context.middleware_chain:
            response.headers["X-Middleware-Chain"] = ", ".join(context.middleware_chain)
            
    def _add_state_headers(self, response: Response, request: Request):
        """Add headers based on request state."""
        state = RequestStateManager.get_from_request(request)
        
        # Tenant context
        if state.tenant_context:
            response.headers["X-Tenant-Context"] = (
                f"{state.tenant_context.tenant_id}:{state.tenant_context.source}"
            )
            if state.tenant_context.gateway_validated:
                response.headers["X-Gateway-Validated"] = "true"
                
        # API version
        if state.api_version_context:
            response.headers["X-API-Version"] = state.api_version_context.version
            response.headers["X-Version-Status"] = state.api_version_context.status
            
        # Operation context  
        if state.operation_context:
            if state.operation_context.idempotency_key:
                response.headers["X-Idempotency-Key"] = state.operation_context.idempotency_key
            if state.operation_context.correlation_id:
                response.headers["X-Correlation-ID"] = state.operation_context.correlation_id
                
        # Processing stages
        if state.metadata.processing_stages:
            response.headers["X-Processing-Stages"] = ", ".join(state.metadata.processing_stages)
            
    def _add_security_headers(self, response: Response, request: Request):
        """Add security headers to response."""
        
        # Standard security headers
        for header, value in self.config.SECURITY_HEADERS.items():
            response.headers[header] = value
            
        # CORS headers (if configured)
        origin = request.headers.get("origin")
        if origin:
            # This would need proper CORS configuration in practice
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
    def _add_deprecation_headers(self, 
                               response: Response, 
                               request: Request, 
                               context: ResponseContext):
        """Add deprecation warning headers."""
        
        if context.deprecation_warnings:
            warning_text = "; ".join(context.deprecation_warnings)
            response.headers["Warning"] = f'299 - "{warning_text}"'
            response.headers["X-API-Deprecation-Warning"] = "true"
            
        if context.sunset_date:
            response.headers["X-Sunset-Date"] = context.sunset_date
            
        if context.replacement_version:
            response.headers["X-Replacement-Version"] = context.replacement_version
            
        # Add supported versions (would come from API versioning middleware)
        state = RequestStateManager.get_from_request(request)
        if state.api_version_context:
            # This would be populated by the API versioning middleware
            supported_versions = getattr(state.api_version_context, "supported_versions", None)
            if supported_versions:
                response.headers["X-Supported-Versions"] = ", ".join(supported_versions)
                
    def _add_rate_limit_headers(self, response: Response, context: ResponseContext):
        """Add rate limiting headers."""
        
        if context.rate_limit_remaining is not None:
            response.headers["X-Rate-Limit-Remaining"] = str(context.rate_limit_remaining)
            
        if context.rate_limit_limit is not None:
            response.headers["X-Rate-Limit-Limit"] = str(context.rate_limit_limit)
            
        if context.rate_limit_reset:
            response.headers["X-Rate-Limit-Reset"] = context.rate_limit_reset
            
    def _add_cache_headers(self, response: Response, context: ResponseContext):
        """Add cache-related headers."""
        
        if context.cache_status:
            response.headers["X-Cache"] = context.cache_status
            
        if context.cache_ttl is not None:
            response.headers["X-Cache-TTL"] = str(context.cache_ttl)
            
        # Add cache control based on cache status
        if context.cache_status == "hit":
            cache_headers = self.config.CACHE_HEADERS.get("short_cache", {})
        elif context.cache_status == "no-cache":
            cache_headers = self.config.CACHE_HEADERS.get("no_cache", {})
        else:
            cache_headers = {}
            
        for header, value in cache_headers.items():
            response.headers[header] = value
            
    def _add_custom_headers(self, response: Response, context: ResponseContext):
        """Add custom headers from context."""
        
        for header, value in context.custom_headers.items():
            # Ensure header name follows X- convention for custom headers
            if not header.startswith(("X-", "x-")):
                header = f"X-{header}"
            response.headers[header] = value


class StandardResponseDecorator(ResponseDecorator):
    """Standard response decorator with common DotMac patterns."""
    
    def __init__(self):
        """Initialize with DotMac standard configuration."""
        config = ResponseHeaderConfig()
        
        # Add DotMac specific headers
        config.STANDARD_HEADERS.update({
            "X-DotMac-Version": "1.0",
            "X-Service-Type": "ISP-Management",
        })
        
        super().__init__(config)
        
    def add_tenant_headers(self, 
                          response: Response, 
                          tenant_id: str, 
                          tenant_source: str = "unknown"):
        """Add tenant-specific headers.
        
        Args:
            response: Response object
            tenant_id: Tenant ID
            tenant_source: Source of tenant information
        """
        response.headers["X-Tenant-ID"] = tenant_id
        response.headers["X-Tenant-Source"] = tenant_source
        
    def add_performance_headers(self, 
                              response: Response,
                              processing_time: float,
                              db_queries: Optional[int] = None,
                              cache_hits: Optional[int] = None):
        """Add performance monitoring headers.
        
        Args:
            response: Response object
            processing_time: Processing time in seconds
            db_queries: Number of database queries
            cache_hits: Number of cache hits
        """
        response.headers["X-Processing-Time"] = f"{processing_time:.4f}s"
        
        if db_queries is not None:
            response.headers["X-DB-Queries"] = str(db_queries)
            
        if cache_hits is not None:
            response.headers["X-Cache-Hits"] = str(cache_hits)
            
    def add_pagination_headers(self, 
                             response: Response,
                             page: int,
                             per_page: int,
                             total: int,
                             total_pages: int):
        """Add pagination headers.
        
        Args:
            response: Response object
            page: Current page number
            per_page: Items per page
            total: Total items
            total_pages: Total pages
        """
        response.headers["X-Page"] = str(page)
        response.headers["X-Per-Page"] = str(per_page)
        response.headers["X-Total"] = str(total)
        response.headers["X-Total-Pages"] = str(total_pages)


# Convenience functions
def decorate_response(response: Response, request: Request, **kwargs) -> Response:
    """Convenience function to decorate response with standard headers."""
    decorator = StandardResponseDecorator()
    context = ResponseContext(**kwargs)
    return decorator.decorate_response(response, request, context)

def create_error_response(status_code: int, detail: str, request: Request, **kwargs) -> JSONResponse:
    """Convenience function to create standardized error response."""
    decorator = StandardResponseDecorator()
    return decorator.create_error_response(status_code, detail, request, **kwargs)

def create_success_response(data: Any, request: Request, **kwargs) -> JSONResponse:
    """Convenience function to create standardized success response.""" 
    decorator = StandardResponseDecorator()
    return decorator.create_success_response(data, request, **kwargs)