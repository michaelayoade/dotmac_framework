"""
Tenant-specific exceptions and error handling.
"""

from typing import Optional, Any, Dict


class TenantError(Exception):
    """Base exception for all tenant-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class TenantNotFoundError(TenantError):
    """Raised when tenant cannot be identified or found."""
    
    def __init__(self, identifier: str, resolution_method: str):
        super().__init__(
            f"Tenant not found: {identifier} (method: {resolution_method})",
            {"identifier": identifier, "resolution_method": resolution_method}
        )


class TenantResolutionError(TenantError):
    """Raised when tenant resolution fails due to configuration or logic errors."""
    
    def __init__(self, message: str, resolution_strategy: str):
        super().__init__(
            f"Tenant resolution failed: {message} (strategy: {resolution_strategy})",
            {"resolution_strategy": resolution_strategy}
        )


class TenantSecurityError(TenantError):
    """Raised when tenant security boundaries are violated."""
    
    def __init__(self, message: str, tenant_id: str, violation_type: str):
        super().__init__(
            f"Tenant security violation: {message} (tenant: {tenant_id}, type: {violation_type})",
            {"tenant_id": tenant_id, "violation_type": violation_type}
        )


class TenantContextError(TenantError):
    """Raised when tenant context is missing or invalid."""
    
    def __init__(self, message: str = "No tenant context available"):
        super().__init__(message)


class TenantConfigurationError(TenantError):
    """Raised when tenant configuration is invalid or missing."""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(
            f"Tenant configuration error: {message}",
            {"config_key": config_key} if config_key else {}
        )