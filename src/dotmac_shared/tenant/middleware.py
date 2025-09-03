"""
Tenant Identity Middleware
Enforces tenant identity resolution and rejects client-supplied tenant IDs
"""

import time
from typing import Optional, Dict, Any, Callable
from contextvars import ContextVar
from functools import wraps

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.logging import get_logger
from ..api.response import APIResponse
from .identity import TenantContext, tenant_resolver, tenant_registry

logger = get_logger(__name__)

# Context variable for storing current tenant in request context
current_tenant_context: ContextVar[Optional[TenantContext]] = ContextVar(
    'current_tenant_context', 
    default=None
)


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces tenant identity resolution and security.
    
    Security Features:
    1. Rejects any client-supplied tenant headers
    2. Derives tenant identity from host headers only
    3. Validates tenant existence in registry
    4. Sets trusted internal headers for downstream services
    5. Provides tenant context to request handlers
    """
    
    def __init__(
        self,
        app,
        require_tenant: bool = True,
        skip_paths: list = None,
        enable_tenant_validation: bool = True,
        custom_resolver: Optional[TenantContext] = None
    ):
        super().__init__(app)
        self.require_tenant = require_tenant
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.enable_tenant_validation = enable_tenant_validation
        self.custom_resolver = custom_resolver
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Main middleware processing logic"""
        
        start_time = time.time()
        tenant_context = None
        
        try:
            # Skip tenant resolution for certain paths
            if self._should_skip_path(request.url.path):
                return await call_next(request)
            
            # Step 1: Validate client hasn't supplied protected headers
            violations = tenant_resolver.validate_client_headers(dict(request.headers))
            if violations:
                logger.warning("Client supplied protected tenant headers", extra={
                    "violations": violations,
                    "client_ip": request.client.host if request.client else None,
                    "user_agent": request.headers.get("user-agent", "")
                })
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Forbidden",
                        "message": "Client-supplied tenant headers not allowed",
                        "violations": violations
                    }
                )
            
            # Step 2: Check for existing trusted headers (from edge/gateway)
            tenant_context = tenant_resolver.extract_from_trusted_headers(dict(request.headers))
            
            # Step 3: If no trusted headers, resolve from host
            if not tenant_context:
                host = request.headers.get("host")
                if host:
                    tenant_context = await tenant_resolver.resolve_from_host(host)
                    
                    # Verify tenant exists if resolution was successful
                    if tenant_context and self.enable_tenant_validation:
                        tenant_info = await tenant_registry.get_tenant_info(tenant_context.tenant_id)
                        if tenant_info:
                            tenant_context.is_verified = True
                            tenant_context.metadata.update(tenant_info)
                        else:
                            logger.warning(f"Tenant {tenant_context.tenant_id} not found in registry")
                            tenant_context = None
            
            # Step 4: Handle missing tenant based on requirements
            if not tenant_context and self.require_tenant:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "Bad Request", 
                        "message": "Unable to resolve tenant identity",
                        "details": "Valid tenant subdomain or host required"
                    }
                )
            
            # Step 5: Set tenant context for request
            if tenant_context:
                current_tenant_context.set(tenant_context)
                
                # Add tenant info to request state
                request.state.tenant = tenant_context
                
                # Log tenant resolution
                logger.info("Tenant resolved", extra={
                    "tenant_id": tenant_context.tenant_id,
                    "host": tenant_context.host,
                    "strategy": tenant_context.resolution_strategy.value if tenant_context.resolution_strategy else None,
                    "is_management": tenant_context.is_management,
                    "is_verified": tenant_context.is_verified
                })
            
            # Step 6: Process request
            response = await call_next(request)
            
            # Step 7: Add trusted headers to response for downstream services
            if tenant_context and tenant_context.is_verified:
                trusted_headers = tenant_resolver.create_trusted_headers(tenant_context)
                for header_name, header_value in trusted_headers.items():
                    response.headers[header_name] = header_value
            
            # Add processing time header
            processing_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Tenant middleware error: {e}", extra={
                "path": request.url.path,
                "method": request.method,
                "host": request.headers.get("host", "")
            })
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": "Failed to process tenant identity"
                }
            )
        finally:
            # Clear tenant context
            current_tenant_context.set(None)
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if path should skip tenant resolution"""
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)


def get_current_tenant() -> Optional[TenantContext]:
    """Get the current tenant context from request context"""
    return current_tenant_context.get()


def require_tenant() -> TenantContext:
    """
    Get the current tenant context, raising an exception if not available.
    Use this in FastAPI dependencies.
    """
    tenant = get_current_tenant()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required but not available"
        )
    return tenant


def tenant_required(func: Callable) -> Callable:
    """
    Decorator that ensures tenant context is available for the function.
    Raises HTTPException if tenant is not resolved.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant = get_current_tenant()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required"
            )
        return await func(*args, **kwargs)
    
    return wrapper


class TenantScopedDependency:
    """
    FastAPI dependency for tenant-scoped operations.
    Provides both tenant context and validation.
    """
    
    def __init__(self, require_verified: bool = True, require_active: bool = True):
        self.require_verified = require_verified
        self.require_active = require_active
    
    async def __call__(self, request: Request) -> TenantContext:
        """FastAPI dependency callable"""
        tenant = getattr(request.state, 'tenant', None)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context not available"
            )
        
        if self.require_verified and not tenant.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant not verified"
            )
        
        if self.require_active:
            tenant_status = tenant.metadata.get("status", "unknown")
            if tenant_status not in ["active", "trial"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant status '{tenant_status}' not allowed"
                )
        
        return tenant


# Pre-configured dependency instances
verified_tenant = TenantScopedDependency(require_verified=True, require_active=True)
any_tenant = TenantScopedDependency(require_verified=False, require_active=False)