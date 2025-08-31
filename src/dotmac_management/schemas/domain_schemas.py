"""Domain Management Schemas for the Management Platform."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..models.domain_management import (
    DNSRecordType,
    DomainProvider,
    DomainStatus,
    SSLStatus,
    VerificationStatus,
)


# Base Schemas

class BaseSchema(BaseModel):
    """Base schema with common fields."""
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[BaseModel]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    pages: int


# Domain Schemas

class DomainBase(BaseModel):
    """Base domain schema."""
    domain_name: str = Field(..., min_length=1, max_length=255)
    subdomain: Optional[str] = Field(None, max_length=100)
    is_primary: bool = False
    auto_renew: bool = True
    notes: Optional[str] = Field(None, max_length=1000)
    tags: List[str] = Field(default_factory=list, max_length=10)
    
    @field_validator('domain_name')
    @classmethod
    def validate_domain_name(cls, v):
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(pattern, v):
            raise ValueError('Invalid domain name format')
        return v.lower()
    
    @field_validator('subdomain')
    @classmethod
    def validate_subdomain(cls, v):
        if v:
            import re
            pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
            if not re.match(pattern, v):
                raise ValueError('Invalid subdomain format')
            return v.lower()
        return v


class DomainCreate(DomainBase):
    """Schema for creating domains."""
    dns_provider: DomainProvider = DomainProvider.COREDNS
    auto_ssl: bool = True


class DomainUpdate(BaseModel):
    """Schema for updating domains."""
    domain_name: Optional[str] = Field(None, min_length=1, max_length=255)
    auto_renew: Optional[bool] = None
    notes: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(None, max_length=10)


class DomainResponse(DomainBase, BaseSchema):
    """Response schema for domains."""
    domain_id: str
    tenant_id: str
    full_domain: str
    domain_status: DomainStatus
    registrar: Optional[DomainProvider]
    registration_date: Optional[datetime]
    expiration_date: Optional[datetime]
    dns_provider: DomainProvider
    nameservers: List[str] = Field(default_factory=list)
    dns_zone_id: Optional[str]
    verification_status: VerificationStatus
    verified_at: Optional[datetime]
    ssl_status: SSLStatus
    ssl_certificate_id: Optional[str]
    ssl_expires_at: Optional[datetime]
    last_dns_check: Optional[datetime]
    dns_check_status: str = "unknown"
    uptime_percentage: int = Field(ge=0, le=100)
    owner_user_id: str
    managed_by_system: bool = True
    
    # Computed properties
    is_expired: Optional[bool] = None
    days_until_expiration: Optional[int] = None
    ssl_is_expired: Optional[bool] = None
    days_until_ssl_expiration: Optional[int] = None
    is_verified: Optional[bool] = None


class DomainListResponse(PaginatedResponse):
    """Paginated domain list response."""
    items: List[DomainResponse]


# DNS Record Schemas

class DNSRecordBase(BaseModel):
    """Base DNS record schema."""
    name: str = Field(..., min_length=1, max_length=255)
    record_type: DNSRecordType
    value: str = Field(..., min_length=1, max_length=2000)
    ttl: int = Field(default=3600, ge=60, le=86400)  # 1 minute to 24 hours
    priority: Optional[int] = Field(None, ge=0, le=65535)
    port: Optional[int] = Field(None, ge=1, le=65535)
    weight: Optional[int] = Field(None, ge=0, le=65535)
    notes: Optional[str] = Field(None, max_length=500)
    tags: List[str] = Field(default_factory=list, max_length=5)


class DNSRecordCreate(DNSRecordBase):
    """Schema for creating DNS records."""
    domain_id: str = Field(..., min_length=1)


class DNSRecordUpdate(BaseModel):
    """Schema for updating DNS records."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=2000)
    ttl: Optional[int] = Field(None, ge=60, le=86400)
    priority: Optional[int] = Field(None, ge=0, le=65535)
    notes: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None, max_length=5)


class DNSRecordResponse(DNSRecordBase, BaseSchema):
    """Response schema for DNS records."""
    record_id: str
    domain_id: str
    tenant_id: str
    is_system_managed: bool = True
    is_editable: bool = True
    provider_record_id: Optional[str]
    sync_status: str = "pending"
    last_sync_attempt: Optional[datetime]
    sync_error_message: Optional[str]
    is_valid: bool = True
    validation_errors: Optional[Dict] = None
    last_validated: Optional[datetime]
    
    # Computed properties
    full_record_name: Optional[str] = None
    needs_sync: Optional[bool] = None


# SSL Certificate Schemas

class SSLCertificateBase(BaseModel):
    """Base SSL certificate schema."""
    certificate_name: str = Field(..., min_length=1, max_length=200)
    common_name: str = Field(..., min_length=1, max_length=255)
    subject_alternative_names: List[str] = Field(default_factory=list, max_length=100)
    certificate_authority: str = Field(default="letsencrypt", max_length=100)
    auto_renew: bool = True
    renewal_threshold_days: int = Field(default=30, ge=1, le=90)


class SSLCertificateCreate(SSLCertificateBase):
    """Schema for creating SSL certificates."""
    domain_id: str = Field(..., min_length=1)


class SSLCertificateResponse(SSLCertificateBase, BaseSchema):
    """Response schema for SSL certificates."""
    certificate_id: str
    domain_id: str
    tenant_id: str
    issuer: str
    issued_at: datetime
    expires_at: datetime
    ssl_status: SSLStatus
    validation_method: Optional[str]
    deployment_status: str = "pending"
    provider_certificate_id: Optional[str]
    key_size: int = 2048
    signature_algorithm: Optional[str]
    fingerprint_sha256: Optional[str]
    
    # Computed properties
    is_expired: Optional[bool] = None
    days_until_expiration: Optional[int] = None
    needs_renewal: Optional[bool] = None
    is_valid: Optional[bool] = None


# Domain Verification Schemas

class DomainVerificationBase(BaseModel):
    """Base domain verification schema."""
    verification_method: str = Field(default="DNS", pattern="^(DNS|HTTP|email)$")


class DomainVerificationCreate(DomainVerificationBase):
    """Schema for creating domain verifications."""
    domain_id: str = Field(..., min_length=1)


class DomainVerificationResponse(DomainVerificationBase, BaseSchema):
    """Response schema for domain verifications."""
    verification_id: str
    domain_id: str
    tenant_id: str
    verification_token: str
    verification_value: Optional[str]
    status: VerificationStatus
    attempts: int = Field(ge=0)
    max_attempts: int = 5
    initiated_at: datetime
    verified_at: Optional[datetime]
    expires_at: Optional[datetime]
    last_check: Optional[datetime]
    next_check: Optional[datetime]
    verification_response: Optional[Dict] = None
    error_details: Optional[Dict] = None
    
    # Computed properties
    is_expired: Optional[bool] = None
    is_due_for_check: Optional[bool] = None
    has_failed: Optional[bool] = None


class DomainVerificationInstructions(BaseModel):
    """Domain verification instructions."""
    method: str
    instructions: str
    record_name: Optional[str] = None
    record_type: Optional[str] = None
    record_value: Optional[str] = None
    file_path: Optional[str] = None
    file_content: Optional[str] = None


# Domain Log Schemas

class DomainLogResponse(BaseModel):
    """Response schema for domain logs."""
    id: UUID
    domain_id: str
    tenant_id: str
    log_timestamp: datetime
    action: str
    user_id: str
    description: str
    before_state: Optional[Dict] = None
    after_state: Optional[Dict] = None
    success: bool
    error_code: Optional[str]
    error_message: Optional[str]
    duration_ms: Optional[int]
    operation_id: Optional[str]
    
    # Computed properties
    operation_duration_seconds: Optional[float] = None


# Statistics Schemas

class DomainStatsResponse(BaseModel):
    """Domain statistics response."""
    tenant_id: str
    total_domains: int = Field(ge=0)
    domains_by_status: Dict[str, int] = Field(default_factory=dict)
    ssl_by_status: Dict[str, int] = Field(default_factory=dict)
    providers_usage: Dict[str, int] = Field(default_factory=dict)
    expiring_domains: List[DomainResponse] = Field(default_factory=list)
    expiring_ssl_certificates: List[SSLCertificateResponse] = Field(default_factory=list)


# Search and Filter Schemas

class DomainSearchFilters(BaseModel):
    """Domain search filters."""
    status: Optional[DomainStatus] = None
    dns_provider: Optional[DomainProvider] = None
    verification_status: Optional[VerificationStatus] = None
    ssl_status: Optional[SSLStatus] = None
    is_primary: Optional[bool] = None
    expires_within_days: Optional[int] = Field(None, ge=1, le=365)
    owner_user_id: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_length=10)


class DomainSearchRequest(BaseModel):
    """Domain search request."""
    query: Optional[str] = Field(None, max_length=200)  # Search in domain name
    filters: Optional[DomainSearchFilters] = None
    sort_by: str = Field(default="created_at", pattern="^(created_at|domain_name|expiration_date|status)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=50, ge=1, le=100)


# Domain Operations Schemas

class BulkDomainOperationRequest(BaseModel):
    """Bulk domain operations request."""
    domain_ids: List[str] = Field(..., min_length=1, max_length=50)
    operation: str = Field(..., pattern="^(delete|suspend|activate|renew|update_dns)$")
    parameters: Optional[Dict] = Field(default_factory=dict)


class BulkDomainOperationResponse(BaseModel):
    """Bulk domain operations response."""
    total_requested: int = Field(ge=0)
    successful: int = Field(ge=0)
    failed: int = Field(ge=0)
    results: List[Dict] = Field(default_factory=list)


# DNS Zone Schemas

class DNSZoneBase(BaseModel):
    """Base DNS zone schema."""
    zone_name: str = Field(..., min_length=1, max_length=255)
    primary_nameserver: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(..., min_length=1, max_length=255)
    refresh_interval: int = Field(default=3600, ge=300, le=86400)
    retry_interval: int = Field(default=1800, ge=300, le=7200)
    expire_interval: int = Field(default=604800, ge=86400, le=2419200)
    minimum_ttl: int = Field(default=3600, ge=60, le=86400)


class DNSZoneCreate(DNSZoneBase):
    """Schema for creating DNS zones."""
    provider: DomainProvider = DomainProvider.COREDNS


class DNSZoneResponse(DNSZoneBase, BaseSchema):
    """Response schema for DNS zones."""
    zone_id: str
    tenant_id: str
    serial_number: int = Field(ge=1)
    provider: DomainProvider
    provider_zone_id: Optional[str]
    is_active: bool = True
    last_sync: Optional[datetime]
    sync_status: str = "pending"
    sync_error_message: Optional[str]
    zone_file_path: Optional[str]
    zone_file_hash: Optional[str]
    
    # Computed properties
    needs_sync: Optional[bool] = None


# Export all schemas
__all__ = [
    # Base
    "BaseSchema",
    "PaginatedResponse",
    
    # Domains
    "DomainBase",
    "DomainCreate",
    "DomainUpdate",
    "DomainResponse",
    "DomainListResponse",
    
    # DNS Records
    "DNSRecordBase",
    "DNSRecordCreate",
    "DNSRecordUpdate",
    "DNSRecordResponse",
    
    # SSL Certificates
    "SSLCertificateBase",
    "SSLCertificateCreate",
    "SSLCertificateResponse",
    
    # Domain Verification
    "DomainVerificationBase",
    "DomainVerificationCreate",
    "DomainVerificationResponse",
    "DomainVerificationInstructions",
    
    # Domain Logs
    "DomainLogResponse",
    
    # Statistics
    "DomainStatsResponse",
    
    # Search
    "DomainSearchFilters",
    "DomainSearchRequest",
    
    # Operations
    "BulkDomainOperationRequest",
    "BulkDomainOperationResponse",
    
    # DNS Zones
    "DNSZoneBase",
    "DNSZoneCreate",
    "DNSZoneResponse",
]