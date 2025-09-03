"""
Tenant configuration models and settings.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class TenantResolutionStrategy(str, Enum):
    """Available tenant resolution strategies."""
    
    HOST_BASED = "host"
    SUBDOMAIN = "subdomain"  
    HEADER_BASED = "header"
    PATH_BASED = "path"
    COMPOSITE = "composite"


class TenantDatabaseStrategy(str, Enum):
    """Database isolation strategies."""
    
    SHARED = "shared"
    RLS = "rls"  # Row-Level Security
    SCHEMA_PER_TENANT = "schema"
    DATABASE_PER_TENANT = "database"


class TenantConfig(BaseModel):
    """Configuration for tenant resolution and management."""
    
    # Resolution strategy
    resolution_strategy: TenantResolutionStrategy = TenantResolutionStrategy.HOST_BASED
    fallback_tenant_id: Optional[str] = None
    
    # Header-based resolution settings
    tenant_header_name: str = "X-Tenant-ID"
    tenant_domain_header: str = "X-Tenant-Domain"
    
    # Host-based resolution settings
    host_tenant_mapping: Dict[str, str] = Field(default_factory=dict)
    default_host_pattern: Optional[str] = None  # e.g., "{tenant}.example.com"
    
    # Subdomain resolution settings
    subdomain_position: int = 0  # Position of tenant in subdomain (0 = first)
    base_domain: Optional[str] = None
    
    # Path-based resolution settings
    path_prefix: str = "/tenant"
    path_position: int = 1  # Position in path segments
    
    # Security settings
    enforce_tenant_isolation: bool = True
    allow_cross_tenant_access: bool = False
    require_tenant_header: bool = False
    trusted_proxies: List[str] = Field(default_factory=list)
    
    # Database settings
    database_strategy: TenantDatabaseStrategy = TenantDatabaseStrategy.SHARED
    enable_rls: bool = False
    tenant_schema_prefix: str = "tenant_"
    
    # Caching and performance
    enable_tenant_caching: bool = True
    cache_ttl_seconds: int = 300
    
    # Logging and monitoring
    log_tenant_access: bool = True
    log_tenant_switches: bool = True
    enable_tenant_metrics: bool = True
    
    # Advanced settings
    custom_resolver_class: Optional[str] = None
    tenant_metadata_fields: List[str] = Field(default_factory=list)
    
    @validator('host_tenant_mapping')
    def validate_host_mapping(cls, v):
        """Validate host-to-tenant mapping."""
        if not isinstance(v, dict):
            raise ValueError("host_tenant_mapping must be a dictionary")
        return v
    
    @validator('trusted_proxies')
    def validate_trusted_proxies(cls, v):
        """Validate trusted proxy configuration."""
        if not isinstance(v, list):
            raise ValueError("trusted_proxies must be a list")
        return v
    
    @validator('fallback_tenant_id')
    def validate_fallback_tenant(cls, v, values):
        """Validate fallback tenant configuration."""
        if v and not isinstance(v, str):
            raise ValueError("fallback_tenant_id must be a string")
        return v
    
    class Config:
        """Pydantic model configuration."""
        use_enum_values = True
        extra = "forbid"
        validate_assignment = True


class TenantMetadata(BaseModel):
    """Metadata associated with a tenant."""
    
    tenant_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Custom fields
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    # Database configuration
    database_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Feature flags
    features: Dict[str, bool] = Field(default_factory=dict)
    
    class Config:
        """Pydantic model configuration."""
        extra = "allow"