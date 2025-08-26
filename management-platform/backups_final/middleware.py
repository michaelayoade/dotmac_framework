"""
Custom middleware for the application.
"""

import json
import logging
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import unquote

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings
from core.exceptions import SecurityValidationError
from core.logging import get_logger, log_security_event, request_logging_context
from core.monitoring import request_metrics
from core.sanitization import InputSanitizer

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging."""
        # Generate request ID
        request_id = str(uuid.uuid4()
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info()
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": str(request.url),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
            },
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            logger.error()
                "Request failed with exception",
                extra={
                    "request_id": request_id,
                    "exception": str(e),
                    "exception_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)
        
        # Record request metrics
        request_metrics.record_request(request.method, response.status_code, duration_ms)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log response
        logger.info()
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        
        return response


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant context and isolation."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tenant context."""
        # Extract tenant ID from various sources
        tenant_id = None
        
        # Try to get tenant ID from header
        tenant_id = request.headers.get("X-Tenant-ID")
        
        # Try to get tenant ID from path parameters
        if not tenant_id and hasattr(request, "path_params"):
            tenant_id = request.path_params.get("tenant_id")
        
        # Try to get tenant ID from query parameters
        if not tenant_id:
            tenant_id = request.query_params.get("tenant_id")
        
        # Store tenant ID in request state
        request.state.tenant_id = tenant_id
        
        # Log tenant context
        if tenant_id:
            logger.debug(f"Request tenant context: {tenant_id}")
        
        # Process request
        response = await call_next(request)
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(self, app, calls_per_minute: int = 100):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.client_calls = {}  # Simple in-memory store - use Redis in production
        self.window_size = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        
        # Simple rate limiting logic (use proper rate limiter in production)
        current_time = time.time()
        window_start = current_time - self.window_size
        
        # Clean old entries
        if client_ip in self.client_calls:
            self.client_calls[client_ip] = [
                call_time for call_time in self.client_calls[client_ip]
                if call_time > window_start
            ]
        
        # Check rate limit
        if client_ip not in self.client_calls:
            self.client_calls[client_ip] = []
        
        if len(self.client_calls[client_ip]) >= self.calls_per_minute:
            logger.warning(f"Rate limit exceeded for client {client_ip}")
            return Response()
                content='{"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests"}}',
                status_code=429,
                headers={"Content-Type": "application/json"}
            )
        
        # Add current request
        self.client_calls[client_ip].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining_calls = self.calls_per_minute - len(self.client_calls[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining_calls)
        response.headers["X-RateLimit-Reset"] = str(int(window_start + self.window_size)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Comprehensive request validation and security middleware."""
    
    # Suspicious patterns in URLs/headers
    SUSPICIOUS_PATTERNS = [
        r"\.\./",           # Path traversal  # nosec B105
        r"<script",         # XSS attempts
        r"javascript:",     # JavaScript in URLs
        r"union\s+select",  # SQL injection
        r"drop\s+table",    # SQL injection
        r"exec\s*\(",       # Command execution
        r"\${jndi:",        # Log4j/LDAP injection
        r"<%.*%>",          # Server-side template injection  # nosec B105
        r"{{.*}}",          # Template injection  # nosec B105
    ]
    
    # Maximum request sizes (bytes)
    MAX_CONTENT_LENGTH = {
        "default": 10 * 1024 * 1024,  # 10MB
        "POST": 50 * 1024 * 1024,     # 50MB for uploads
        "PUT": 50 * 1024 * 1024,      # 50MB for uploads
        "PATCH": 10 * 1024 * 1024,    # 10MB
    }
    
    # Rate limiting per endpoint
    ENDPOINT_RATE_LIMITS = {
        '/api/v1/auth/login': 5,      # 5 attempts per minute
        '/api/v1/auth/register': 3,   # 3 attempts per minute  
        '/api/v1/tenants': 10,        # 10 tenant operations per minute
        'default': 100                # 100 requests per minute default
    }
    
    def __init__(self, app):
        super().__init__(app)
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS]
        self.request_counts = {}  # In-memory store - use Redis in production
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate and secure incoming requests."""
        request_id = getattr(request.state, 'request_id', str(uuid.uuid4()
        
        try:
            # 1. Validate request size
            await self._validate_request_size(request)
            
            # 2. Validate URL and headers for suspicious patterns
            await self._validate_request_security(request)
            
            # 3. Validate content type and encoding
            await self._validate_content_type(request)
            
            # 4. Apply endpoint-specific rate limiting
            await self._apply_endpoint_rate_limiting(request)
            
            # 5. Sanitize and validate request body if present
            if request.method in ['POST', 'PUT', 'PATCH']:
                await self._validate_request_body(request)
            
            # 6. Validate and sanitize query parameters
            await self._validate_query_parameters(request)
            
            # Process the request
            response = await call_next(request)
            
            # 7. Validate and secure response
            await self._secure_response(response)
            
            return response
            
        except SecurityValidationError as e:
            log_security_event()
                event_type="request_validation_failure",
                details={
                    "error": str(e),
                    "path": str(request.url),
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown",
                    "user_agent": request.headers.get("User-Agent", "unknown")
                }
            )
            return Response()
                content=json.dumps({)
                    "error": {
                        "code": "SECURITY_VALIDATION_ERROR",
                        "message": "Request validation failed"
                    }
                }),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        except HTTPException as e:
            return Response()
                content=json.dumps({)
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": e.detail
                    }
                }),
                status_code=e.status_code,
                headers={"Content-Type": "application/json"}
            )
        
        except Exception as e:
            logger.error("Request validation middleware error", )
                        request_id=request_id, 
                        error=str(e), 
                        exc_info=True)
            return Response()
                content=json.dumps({)
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Request processing failed"
                    }
                }),
                status_code=500,
                headers={"Content-Type": "application/json"}
            )
    
    async def _validate_request_size(self, request: Request):
        """Validate request content length."""
        content_length = request.headers.get("content-length")
        
        if content_length:
            try:
                size = int(content_length)
                max_size = self.MAX_CONTENT_LENGTH.get()
                    request.method, 
                    self.MAX_CONTENT_LENGTH['default']
                )
                
                if size > max_size:
                    raise HTTPException()
                        status_code=413,
                        detail=f"Request too large: {size} bytes > {max_size} bytes"
                    )
                    
            except ValueError:
                raise HTTPException()
                    status_code=400,
                    detail="Invalid Content-Length header"
                )
    
    async def _validate_request_security(self, request: Request):
        """Check for suspicious patterns in URL and headers."""
        # Check URL path
        url_path = unquote(str(request.url)
        
        for pattern in self.compiled_patterns:
            if pattern.search(url_path):
                raise SecurityValidationError()
                    field="url",
                    reason=f"Suspicious pattern detected in URL: {pattern.pattern}"
                )
        
        # Check critical headers
        suspicious_headers = ['User-Agent', 'Referer', 'X-Forwarded-For']
        
        for header_name in suspicious_headers:
            header_value = request.headers.get(header_name, "")
            if header_value:
                for pattern in self.compiled_patterns:
                    if pattern.search(header_value):
                        raise SecurityValidationError()
                            field=header_name,
                            reason=f"Suspicious pattern detected in header: {pattern.pattern}"
                        )
    
    async def _validate_content_type(self, request: Request):
        """Validate request content type."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get("content-type", "")
            
            # Allow common content types
            allowed_types = [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
                'text/plain'
            ]
            
            if not any(allowed in content_type.lower() for allowed in allowed_types):
                log_security_event()
                    event_type="suspicious_content_type",
                    details={
                        "content_type": content_type,
                        "path": str(request.url),
                        "method": request.method
                    }
                )
    
    async def _apply_endpoint_rate_limiting(self, request: Request):
        """Apply endpoint-specific rate limiting."""
        client_ip = request.client.host if request.client else "unknown"
        endpoint = str(request.url.path)
        
        # Get rate limit for this endpoint
        rate_limit = self.ENDPOINT_RATE_LIMITS.get(endpoint, self.ENDPOINT_RATE_LIMITS['default'])
        
        # Simple rate limiting (use Redis in production)
        key = f"{client_ip}:{endpoint}"
        current_time = time.time()
        window_start = current_time - 60  # 1-minute window
        
        if key not in self.request_counts:
            self.request_counts[key] = []
        
        # Clean old entries
        self.request_counts[key] = [
            req_time for req_time in self.request_counts[key]
            if req_time > window_start
        ]
        
        if len(self.request_counts[key]) >= rate_limit:
            log_security_event()
                event_type="rate_limit_exceeded",
                details={
                    "endpoint": endpoint,
                    "client_ip": client_ip,
                    "rate_limit": rate_limit,
                    "current_count": len(self.request_counts[key])
                }
            )
            raise HTTPException()
                status_code=429,
                detail=f"Rate limit exceeded for endpoint {endpoint}"
            )
        
        # Add current request
        self.request_counts[key].append(current_time)
    
    async def _validate_request_body(self, request: Request):
        """Validate and sanitize request body."""
        if not hasattr(request, '_body'):
            # Read body once and cache it
            body = await request.body()
            request._body = body
        else:
            body = request._body
        
        if body:
            try:
                # Try to parse as JSON
                if request.headers.get("content-type", "").startswith("application/json"):
                    try:
                        data = json.loads(body)
                        # Sanitize JSON data recursively
                        sanitized_data = InputSanitizer.sanitize_json_input(data)
                        # Store sanitized data back (if needed)
                        request._sanitized_json = sanitized_data
                    except json.JSONDecodeError:
                        raise HTTPException()
                            status_code=400,
                            detail="Invalid JSON in request body"
                        )
                
                # Check for suspicious patterns in raw body
                body_str = body.decode('utf-8', errors='ignore')
                for pattern in self.compiled_patterns:
                    if pattern.search(body_str):
                        raise SecurityValidationError()
                            field="request_body",
                            reason=f"Suspicious pattern detected in body: {pattern.pattern}"
                        )
                        
            except UnicodeDecodeError:
                # Body is binary data, skip text-based validation
                pass
    
    async def _validate_query_parameters(self, request: Request):
        """Validate and sanitize query parameters."""
        for key, value in request.query_params.items():
            try:
                # Sanitize parameter name and value
                safe_key = InputSanitizer.validate_safe_input(key, f"query_param_{key}")
                safe_value = InputSanitizer.validate_safe_input(value, f"query_param_value_{key}")
                
                # Store sanitized params if needed
                if not hasattr(request.state, 'sanitized_params'):
                    request.state.sanitized_params = {}
                request.state.sanitized_params[safe_key] = safe_value
                
            except SecurityValidationError as e:
                log_security_event()
                    event_type="malicious_query_param",
                    details={
                        "parameter": key,
                        "value": value[:100] + "..." if len(value) > 100 else value,
                        "reason": str(e)
                    }
                )
                raise HTTPException()
                    status_code=400,
                    detail=f"Invalid query parameter: {key}"
                )
    
    async def _secure_response(self, response: Response):
        """Add security measures to response."""
        # Remove sensitive headers that might leak information
        sensitive_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
        for header in sensitive_headers:
            if header in response.headers:
                del response.headers[header]
        
        # Ensure no sensitive data in error responses
        if response.status_code >= 400:
            # Don't expose internal error details in production
            if settings.is_production and response.status_code == 500:
                response.headers['content-length'] = str(len(b'{"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}')
        
        return response