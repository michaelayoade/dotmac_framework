"""
Tenant Identity System
Derives tenant identity from host headers at the edge and propagates through trusted headers
"""

import re
import hashlib
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from urllib.parse import urlparse
from enum import Enum

from ..core.logging import get_logger
from ..api.exception_handlers import standard_exception_handler

logger = get_logger(__name__)


class TenantResolutionStrategy(str, Enum):
    """Strategies for resolving tenant identity"""
    SUBDOMAIN = "subdomain"
    HOST_HEADER = "host_header"
    PATH_PREFIX = "path_prefix"
    CUSTOM_HEADER = "custom_header"


@dataclass
class TenantContext:
    """Complete tenant context information"""
    tenant_id: str
    subdomain: Optional[str] = None
    host: Optional[str] = None
    resolution_strategy: Optional[TenantResolutionStrategy] = None
    is_management: bool = False
    is_verified: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TenantIdentityResolver:
    """
    Resolves tenant identity from various sources with security validation.
    
    This system:
    1. Derives tenant ID from host headers at the edge
    2. Validates against known tenant registry
    3. Propagates via trusted internal headers
    4. Rejects any client-supplied tenant IDs
    """
    
    def __init__(self, base_domains: List[str] = None, management_domains: List[str] = None):
        self.base_domains = base_domains or ["dotmac.com", "dotmac.local"]
        self.management_domains = management_domains or ["manage.dotmac.com", "admin.dotmac.local"]
        self.trusted_header = "X-DotMac-Tenant-ID"
        self.verification_header = "X-DotMac-Tenant-Verified"
        
        # Compile regex patterns for efficiency
        self.subdomain_patterns = [
            re.compile(rf"^([a-zA-Z0-9]([a-zA-Z0-9-]{{0,61}}[a-zA-Z0-9])?)\.{re.escape(domain)}$")
            for domain in self.base_domains
        ]
        
        self.management_patterns = [
            re.compile(rf"^{re.escape(domain)}$")
            for domain in self.management_domains
        ]
    
    @standard_exception_handler
    async def resolve_from_host(
        self, 
        host: str, 
        strategy: TenantResolutionStrategy = TenantResolutionStrategy.SUBDOMAIN
    ) -> Optional[TenantContext]:
        """
        Resolve tenant identity from host header using specified strategy.
        This is the primary entry point at the edge.
        """
        try:
            if not host or not isinstance(host, str):
                logger.warning("Invalid or missing host header")
                return None
            
            # Clean the host header (remove port, whitespace)
            clean_host = host.split(':')[0].strip().lower()
            
            if strategy == TenantResolutionStrategy.SUBDOMAIN:
                return await self._resolve_from_subdomain(clean_host)
            elif strategy == TenantResolutionStrategy.HOST_HEADER:
                return await self._resolve_from_host_mapping(clean_host)
            else:
                logger.warning(f"Unsupported resolution strategy: {strategy}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to resolve tenant from host {host}: {e}")
            return None
    
    async def _resolve_from_subdomain(self, host: str) -> Optional[TenantContext]:
        """Resolve tenant from subdomain pattern"""
        
        # Check if this is a management domain
        for pattern in self.management_patterns:
            if pattern.match(host):
                return TenantContext(
                    tenant_id="management",
                    host=host,
                    resolution_strategy=TenantResolutionStrategy.SUBDOMAIN,
                    is_management=True,
                    is_verified=True,
                    metadata={"domain_type": "management"}
                )
        
        # Check subdomain patterns
        for pattern in self.subdomain_patterns:
            match = pattern.match(host)
            if match:
                subdomain = match.group(1)
                tenant_id = await self._derive_tenant_id(subdomain)
                
                return TenantContext(
                    tenant_id=tenant_id,
                    subdomain=subdomain,
                    host=host,
                    resolution_strategy=TenantResolutionStrategy.SUBDOMAIN,
                    is_management=False,
                    is_verified=False,  # Needs database verification
                    metadata={"extracted_subdomain": subdomain}
                )
        
        logger.warning(f"Host {host} does not match any known patterns")
        return None
    
    async def _resolve_from_host_mapping(self, host: str) -> Optional[TenantContext]:
        """Resolve tenant from explicit host mapping (for custom domains)"""
        # This would query a database/cache of custom domain mappings
        # For now, return None as this requires integration with tenant registry
        return None
    
    async def _derive_tenant_id(self, subdomain: str) -> str:
        """
        Derive a consistent tenant ID from subdomain.
        Uses the subdomain as-is but could implement hashing/normalization.
        """
        return subdomain.lower()
    
    @standard_exception_handler
    async def verify_tenant_exists(self, tenant_context: TenantContext) -> bool:
        """
        Verify that the tenant actually exists in the system.
        This should be implemented by each application with their tenant registry.
        """
        # Default implementation - override in specific applications
        return True
    
    def create_trusted_headers(self, tenant_context: TenantContext) -> Dict[str, str]:
        """
        Create trusted headers for propagating tenant identity to downstream services.
        These headers should only be set by the edge/gateway.
        """
        headers = {
            self.trusted_header: tenant_context.tenant_id
        }
        
        if tenant_context.is_verified:
            headers[self.verification_header] = "true"
            headers["X-DotMac-Tenant-Subdomain"] = tenant_context.subdomain or ""
            headers["X-DotMac-Tenant-Host"] = tenant_context.host or ""
            headers["X-DotMac-Tenant-Management"] = "true" if tenant_context.is_management else "false"
        
        return headers
    
    def extract_from_trusted_headers(self, headers: Dict[str, str]) -> Optional[TenantContext]:
        """
        Extract tenant context from trusted headers set by the edge.
        This is used by downstream services.
        """
        try:
            tenant_id = headers.get(self.trusted_header)
            if not tenant_id:
                return None
            
            is_verified = headers.get(self.verification_header, "").lower() == "true"
            subdomain = headers.get("X-DotMac-Tenant-Subdomain") or None
            host = headers.get("X-DotMac-Tenant-Host") or None
            is_management = headers.get("X-DotMac-Tenant-Management", "").lower() == "true"
            
            return TenantContext(
                tenant_id=tenant_id,
                subdomain=subdomain,
                host=host,
                resolution_strategy=TenantResolutionStrategy.CUSTOM_HEADER,
                is_management=is_management,
                is_verified=is_verified,
                metadata={"source": "trusted_headers"}
            )
            
        except Exception as e:
            logger.error(f"Failed to extract tenant from trusted headers: {e}")
            return None
    
    def validate_client_headers(self, headers: Dict[str, str]) -> List[str]:
        """
        Validate that client hasn't supplied any protected tenant headers.
        Returns list of violation messages.
        """
        violations = []
        protected_headers = {
            self.trusted_header,
            self.verification_header,
            "X-DotMac-Tenant-Subdomain",
            "X-DotMac-Tenant-Host", 
            "X-DotMac-Tenant-Management"
        }
        
        for header_name in protected_headers:
            if header_name in headers:
                violations.append(f"Client-supplied header {header_name} not allowed")
        
        return violations


class TenantRegistry:
    """
    Registry for validating tenant existence and retrieving tenant metadata.
    Should be implemented per application with appropriate data sources.
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    @standard_exception_handler
    async def get_tenant_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive tenant information"""
        # This should be implemented by each application
        # with their specific tenant data source
        return {
            "tenant_id": tenant_id,
            "status": "active",
            "plan": "professional",
            "features": ["billing", "monitoring"],
            "region": "us-east-1"
        }
    
    @standard_exception_handler
    async def validate_tenant_access(
        self, 
        tenant_id: str, 
        resource: str, 
        action: str
    ) -> bool:
        """Validate if tenant has access to specific resource/action"""
        # Implement tenant-specific authorization logic
        return True


# Global instances
tenant_resolver = TenantIdentityResolver()
tenant_registry = TenantRegistry()


async def resolve_tenant_from_host(host: str) -> Optional[TenantContext]:
    """Convenience function for resolving tenant from host"""
    return await tenant_resolver.resolve_from_host(host)