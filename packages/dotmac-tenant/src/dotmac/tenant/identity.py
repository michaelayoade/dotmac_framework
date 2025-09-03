"""
Tenant identity resolution and context management.
"""

import re
from typing import Optional, Dict, Any, List
from contextvars import ContextVar
from urllib.parse import urlparse

from fastapi import Request, Depends, HTTPException
from pydantic import BaseModel
from loguru import logger

from .config import TenantConfig, TenantResolutionStrategy, TenantMetadata
from .exceptions import (
    TenantNotFoundError,
    TenantResolutionError,
    TenantContextError,
    TenantSecurityError,
)


# Context variable to store current tenant information
_tenant_context: ContextVar[Optional['TenantContext']] = ContextVar(
    'tenant_context', default=None
)


class TenantContext(BaseModel):
    """
    Container for tenant information and context data.
    
    This model represents the current tenant context including identification,
    metadata, and request-specific information.
    """
    
    tenant_id: str
    display_name: Optional[str] = None
    metadata: Optional[TenantMetadata] = None
    
    # Resolution information
    resolution_method: str
    resolved_from: str  # The actual value used to resolve tenant
    
    # Request context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    
    # Security context
    security_level: str = "standard"
    permissions: List[str] = []
    
    # Custom context data
    context_data: Dict[str, Any] = {}
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"


class TenantIdentityResolver:
    """
    Resolves tenant identity from HTTP requests using configurable strategies.
    
    Supports multiple resolution strategies including host-based, subdomain,
    header-based, and composite approaches.
    """
    
    def __init__(self, config: TenantConfig):
        self.config = config
        self._tenant_cache: Dict[str, TenantContext] = {}
    
    async def resolve_tenant(self, request: Request) -> TenantContext:
        """
        Resolve tenant identity from the incoming request.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            TenantContext with resolved tenant information
            
        Raises:
            TenantResolutionError: If resolution fails
            TenantNotFoundError: If tenant cannot be found
        """
        strategy = self.config.resolution_strategy
        
        try:
            if strategy == TenantResolutionStrategy.HOST_BASED:
                return await self._resolve_from_host(request)
            elif strategy == TenantResolutionStrategy.SUBDOMAIN:
                return await self._resolve_from_subdomain(request)
            elif strategy == TenantResolutionStrategy.HEADER_BASED:
                return await self._resolve_from_headers(request)
            elif strategy == TenantResolutionStrategy.PATH_BASED:
                return await self._resolve_from_path(request)
            elif strategy == TenantResolutionStrategy.COMPOSITE:
                return await self._resolve_composite(request)
            else:
                raise TenantResolutionError(
                    f"Unsupported resolution strategy: {strategy}",
                    str(strategy)
                )
                
        except TenantNotFoundError:
            # Try fallback tenant if configured
            if self.config.fallback_tenant_id:
                return self._create_fallback_context(request)
            raise
        
        except Exception as e:
            logger.error(f"Tenant resolution failed: {e}")
            raise TenantResolutionError(
                f"Resolution error: {str(e)}",
                str(strategy)
            )
    
    async def _resolve_from_host(self, request: Request) -> TenantContext:
        """Resolve tenant from Host header."""
        host = request.headers.get("host")
        if not host:
            raise TenantResolutionError("No host header found", "host")
        
        # Strip port if present
        host = host.split(':')[0].lower()
        
        # Check explicit host mapping first
        if host in self.config.host_tenant_mapping:
            tenant_id = self.config.host_tenant_mapping[host]
            return self._create_tenant_context(
                tenant_id=tenant_id,
                resolution_method="host_mapping",
                resolved_from=host,
                request=request
            )
        
        # Check default host pattern
        if self.config.default_host_pattern:
            tenant_id = self._extract_tenant_from_pattern(
                host, self.config.default_host_pattern
            )
            if tenant_id:
                return self._create_tenant_context(
                    tenant_id=tenant_id,
                    resolution_method="host_pattern", 
                    resolved_from=host,
                    request=request
                )
        
        raise TenantNotFoundError(host, "host")
    
    async def _resolve_from_subdomain(self, request: Request) -> TenantContext:
        """Resolve tenant from subdomain."""
        host = request.headers.get("host", "").split(':')[0].lower()
        
        if not host:
            raise TenantResolutionError("No host header found", "subdomain")
        
        # Split host into parts
        host_parts = host.split('.')
        
        if len(host_parts) < 2:
            raise TenantResolutionError(
                f"Invalid host format for subdomain resolution: {host}",
                "subdomain"
            )
        
        # Extract tenant from configured position
        position = self.config.subdomain_position
        if position >= len(host_parts):
            raise TenantResolutionError(
                f"Subdomain position {position} out of range for host: {host}",
                "subdomain"
            )
        
        tenant_id = host_parts[position]
        
        # Validate against base domain if configured
        if self.config.base_domain:
            expected_suffix = '.' + self.config.base_domain
            if not host.endswith(expected_suffix):
                raise TenantResolutionError(
                    f"Host {host} does not match base domain {self.config.base_domain}",
                    "subdomain"
                )
        
        return self._create_tenant_context(
            tenant_id=tenant_id,
            resolution_method="subdomain",
            resolved_from=host,
            request=request
        )
    
    async def _resolve_from_headers(self, request: Request) -> TenantContext:
        """Resolve tenant from HTTP headers."""
        # Try tenant ID header first
        tenant_id = request.headers.get(self.config.tenant_header_name)
        
        if tenant_id:
            return self._create_tenant_context(
                tenant_id=tenant_id,
                resolution_method="header_tenant_id",
                resolved_from=tenant_id,
                request=request
            )
        
        # Try tenant domain header
        tenant_domain = request.headers.get(self.config.tenant_domain_header)
        if tenant_domain and tenant_domain in self.config.host_tenant_mapping:
            tenant_id = self.config.host_tenant_mapping[tenant_domain]
            return self._create_tenant_context(
                tenant_id=tenant_id,
                resolution_method="header_tenant_domain",
                resolved_from=tenant_domain,
                request=request
            )
        
        # If headers are required, fail here
        if self.config.require_tenant_header:
            raise TenantResolutionError(
                f"Required tenant header '{self.config.tenant_header_name}' not found",
                "header"
            )
        
        raise TenantNotFoundError("no_header_found", "header")
    
    async def _resolve_from_path(self, request: Request) -> TenantContext:
        """Resolve tenant from URL path."""
        path = request.url.path
        path_segments = [seg for seg in path.split('/') if seg]
        
        # Check if path starts with tenant prefix
        if (len(path_segments) > 0 and 
            path_segments[0] == self.config.path_prefix.strip('/')):
            # Remove prefix and try again
            path_segments = path_segments[1:]
        
        # Extract tenant from configured position
        position = self.config.path_position
        if position >= len(path_segments):
            raise TenantResolutionError(
                f"Path position {position} out of range for path: {path}",
                "path"
            )
        
        tenant_id = path_segments[position]
        
        return self._create_tenant_context(
            tenant_id=tenant_id,
            resolution_method="path",
            resolved_from=path,
            request=request
        )
    
    async def _resolve_composite(self, request: Request) -> TenantContext:
        """
        Resolve tenant using composite strategy (try multiple methods).
        """
        strategies = [
            ("header", self._resolve_from_headers),
            ("host", self._resolve_from_host), 
            ("subdomain", self._resolve_from_subdomain),
            ("path", self._resolve_from_path),
        ]
        
        last_error = None
        
        for strategy_name, resolver in strategies:
            try:
                return await resolver(request)
            except (TenantNotFoundError, TenantResolutionError) as e:
                last_error = e
                logger.debug(f"Composite resolution: {strategy_name} failed: {e}")
                continue
        
        # If all strategies failed, raise the last error
        if last_error:
            raise last_error
        
        raise TenantResolutionError("All composite resolution strategies failed", "composite")
    
    def _extract_tenant_from_pattern(self, host: str, pattern: str) -> Optional[str]:
        """Extract tenant ID from host using pattern matching."""
        # Convert pattern to regex (replace {tenant} with capture group)
        regex_pattern = pattern.replace("{tenant}", r"([a-zA-Z0-9\-_]+)")
        regex_pattern = regex_pattern.replace(".", r"\.")
        
        match = re.match(f"^{regex_pattern}$", host)
        if match:
            return match.group(1)
        
        return None
    
    def _create_tenant_context(
        self,
        tenant_id: str,
        resolution_method: str,
        resolved_from: str,
        request: Request
    ) -> TenantContext:
        """Create tenant context with metadata."""
        # Generate request ID if not present
        request_id = getattr(request.state, 'request_id', None)
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
        
        # Create context
        context = TenantContext(
            tenant_id=tenant_id,
            resolution_method=resolution_method,
            resolved_from=resolved_from,
            request_id=request_id,
        )
        
        # Add to cache if enabled
        if self.config.enable_tenant_caching:
            cache_key = f"{resolution_method}:{resolved_from}"
            self._tenant_cache[cache_key] = context
        
        # Log tenant access if enabled
        if self.config.log_tenant_access:
            logger.info(
                f"Tenant resolved: {tenant_id} via {resolution_method} from {resolved_from}",
                extra={
                    "tenant_id": tenant_id,
                    "resolution_method": resolution_method,
                    "resolved_from": resolved_from,
                    "request_id": request_id,
                }
            )
        
        return context
    
    def _create_fallback_context(self, request: Request) -> TenantContext:
        """Create context using fallback tenant."""
        return self._create_tenant_context(
            tenant_id=self.config.fallback_tenant_id,
            resolution_method="fallback",
            resolved_from="config",
            request=request
        )


def get_current_tenant() -> Optional[TenantContext]:
    """
    Get the current tenant context.
    
    Returns:
        Current TenantContext or None if not set
    """
    return _tenant_context.get()


def set_tenant_context(context: TenantContext) -> None:
    """
    Set the current tenant context.
    
    Args:
        context: TenantContext to set as current
    """
    _tenant_context.set(context)


def clear_tenant_context() -> None:
    """Clear the current tenant context."""
    _tenant_context.set(None)


def require_tenant() -> TenantContext:
    """
    Dependency to require tenant context in FastAPI routes.
    
    Returns:
        Current TenantContext
        
    Raises:
        HTTPException: If no tenant context is available
    """
    context = get_current_tenant()
    if not context:
        raise HTTPException(
            status_code=400,
            detail="Tenant context required but not available"
        )
    return context


def tenant_required(func):
    """
    Decorator to require tenant context for function execution.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that checks for tenant context
    """
    def wrapper(*args, **kwargs):
        context = get_current_tenant()
        if not context:
            raise TenantContextError("Tenant context required but not available")
        return func(*args, **kwargs)
    
    return wrapper