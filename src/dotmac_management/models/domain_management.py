"""Domain Management Models for the Management Platform."""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from dotmac.database.base import AuditableMixin, TenantModel


class DomainStatus(str, Enum):
    """Domain status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    FAILED = "failed"
    TRANSFERRING = "transferring"
    LOCKED = "locked"


class DNSRecordType(str, Enum):
    """DNS record types."""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    NS = "NS"
    PTR = "PTR"
    SOA = "SOA"
    SRV = "SRV"
    CAA = "CAA"


class DomainProvider(str, Enum):
    """Domain registrar providers."""

    CLOUDFLARE = "cloudflare"
    ROUTE53 = "route53"
    NAMECHEAP = "namecheap"
    GODADDY = "godaddy"
    GOOGLE_DOMAINS = "google_domains"
    CUSTOM = "custom"
    COREDNS = "coredns"


class VerificationStatus(str, Enum):
    """Domain verification status."""

    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class SSLStatus(str, Enum):
    """SSL certificate status."""

    NONE = "none"
    PENDING = "pending"
    ISSUED = "issued"
    EXPIRED = "expired"
    FAILED = "failed"
    REVOKED = "revoked"


class Domain(TenantModel, AuditableMixin):
    """Domain management and tracking."""

    __tablename__ = "domains"

    # Domain identification
    domain_id = Column(String(100), nullable=False, unique=True, index=True)
    domain_name = Column(String(255), nullable=False, index=True)
    subdomain = Column(String(100), nullable=True, index=True)
    full_domain = Column(String(255), nullable=False, unique=True, index=True)

    # Domain properties
    domain_status = Column(
        SQLEnum(DomainStatus), default=DomainStatus.PENDING, nullable=False, index=True
    )
    is_primary = Column(Boolean, default=False, nullable=False, index=True)
    is_wildcard = Column(Boolean, default=False, nullable=False)

    # Registration details
    registrar = Column(SQLEnum(DomainProvider), nullable=True, index=True)
    registration_date = Column(DateTime, nullable=True, index=True)
    expiration_date = Column(DateTime, nullable=True, index=True)
    auto_renew = Column(Boolean, default=True, nullable=False)

    # DNS Management
    dns_provider = Column(SQLEnum(DomainProvider), nullable=False, index=True)
    nameservers = Column(JSON, nullable=True)  # List of nameserver URLs
    dns_zone_id = Column(String(100), nullable=True, index=True)

    # Verification
    verification_status = Column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    verification_token = Column(String(255), nullable=True)
    verification_method = Column(String(50), nullable=True)  # DNS, HTTP, email
    verified_at = Column(DateTime, nullable=True, index=True)

    # SSL/TLS
    ssl_status = Column(
        SQLEnum(SSLStatus), default=SSLStatus.NONE, nullable=False, index=True
    )
    ssl_certificate_id = Column(String(100), nullable=True, index=True)
    ssl_issued_at = Column(DateTime, nullable=True)
    ssl_expires_at = Column(DateTime, nullable=True, index=True)
    ssl_auto_renew = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    last_dns_check = Column(DateTime, nullable=True)
    dns_check_status = Column(String(20), default="unknown", nullable=False)
    uptime_percentage = Column(Integer, default=100, nullable=False)  # 0-100

    # Configuration
    redirect_to = Column(String(255), nullable=True)  # Redirect target
    aliases = Column(JSON, nullable=True)  # Alternative domain names

    # Ownership and management
    owner_user_id = Column(String(100), nullable=False, index=True)
    managed_by_system = Column(Boolean, default=True, nullable=False)
    external_dns_config = Column(JSON, nullable=True)  # External DNS configuration

    # Custom fields
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    dns_records = relationship(
        "DNSRecord", back_populates="domain", cascade="all, delete-orphan"
    )
    ssl_certificates = relationship(
        "SSLCertificate", back_populates="domain", cascade="all, delete-orphan"
    )
    domain_logs = relationship(
        "DomainLog", back_populates="domain", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_domains_tenant_status", "tenant_id", "domain_status"),
        Index("ix_domains_owner", "owner_user_id"),
        Index("ix_domains_primary", "is_primary", "tenant_id"),
        Index("ix_domains_expiration", "expiration_date"),
        Index("ix_domains_ssl_expiration", "ssl_expires_at"),
        Index("ix_domains_verification", "verification_status", "verified_at"),
        Index("ix_domains_provider", "dns_provider", "registrar"),
    )

    @hybrid_property
    def is_expired(self):
        """Check if domain has expired."""
        return (
            self.expiration_date and datetime.now(timezone.utc) > self.expiration_date
        )

    @hybrid_property
    def days_until_expiration(self):
        """Calculate days until domain expiration."""
        if not self.expiration_date:
            return None
        delta = self.expiration_date - datetime.now(timezone.utc)
        return max(0, delta.days)

    @hybrid_property
    def ssl_is_expired(self):
        """Check if SSL certificate has expired."""
        return self.ssl_expires_at and datetime.now(timezone.utc) > self.ssl_expires_at

    @hybrid_property
    def days_until_ssl_expiration(self):
        """Calculate days until SSL expiration."""
        if not self.ssl_expires_at:
            return None
        delta = self.ssl_expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    @hybrid_property
    def is_verified(self):
        """Check if domain is verified."""
        return self.verification_status == VerificationStatus.VERIFIED

    def __repr__(self):
        return f"<Domain(id='{self.domain_id}', name='{self.full_domain}', status='{self.domain_status}')>"


class DNSRecord(TenantModel, AuditableMixin):
    """DNS record management."""

    __tablename__ = "dns_records"

    # Record identification
    record_id = Column(String(100), nullable=False, unique=True, index=True)
    domain_id = Column(
        String(100), ForeignKey("domains.domain_id"), nullable=False, index=True
    )

    # DNS record details
    name = Column(
        String(255), nullable=False, index=True
    )  # Record name (subdomain or @)
    record_type = Column(SQLEnum(DNSRecordType), nullable=False, index=True)
    value = Column(String(2000), nullable=False)  # Record value/target
    ttl = Column(Integer, default=3600, nullable=False)  # Time to live in seconds

    # Record properties
    priority = Column(Integer, nullable=True)  # For MX and SRV records
    port = Column(Integer, nullable=True)  # For SRV records
    weight = Column(Integer, nullable=True)  # For SRV records

    # Management
    is_system_managed = Column(Boolean, default=True, nullable=False)
    is_editable = Column(Boolean, default=True, nullable=False)
    provider_record_id = Column(
        String(100), nullable=True, index=True
    )  # Provider's internal ID

    # Status tracking
    sync_status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, synced, failed
    last_sync_attempt = Column(DateTime, nullable=True)
    sync_error_message = Column(Text, nullable=True)

    # Validation
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_errors = Column(JSON, nullable=True)
    last_validated = Column(DateTime, nullable=True)

    # Custom fields
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="dns_records")

    __table_args__ = (
        Index("ix_dns_records_domain_type", "domain_id", "record_type"),
        Index("ix_dns_records_name_type", "name", "record_type"),
        Index("ix_dns_records_sync_status", "sync_status", "last_sync_attempt"),
        Index("ix_dns_records_system_managed", "is_system_managed"),
        Index("ix_dns_records_provider", "provider_record_id"),
    )

    @hybrid_property
    def full_record_name(self):
        """Get full record name including domain."""
        if self.name == "@":
            return self.domain.full_domain
        return f"{self.name}.{self.domain.full_domain}"

    @hybrid_property
    def needs_sync(self):
        """Check if record needs synchronization."""
        return self.sync_status in ["pending", "failed"]

    def __repr__(self):
        return f"<DNSRecord(id='{self.record_id}', name='{self.name}', type='{self.record_type}')>"


class SSLCertificate(TenantModel, AuditableMixin):
    """SSL certificate management."""

    __tablename__ = "ssl_certificates"

    # Certificate identification
    certificate_id = Column(String(100), nullable=False, unique=True, index=True)
    domain_id = Column(
        String(100), ForeignKey("domains.domain_id"), nullable=False, index=True
    )

    # Certificate details
    certificate_name = Column(String(200), nullable=False)
    common_name = Column(String(255), nullable=False, index=True)
    subject_alternative_names = Column(JSON, nullable=True)  # List of SANs

    # Certificate authority
    issuer = Column(String(255), nullable=False)
    certificate_authority = Column(
        String(100), nullable=True, index=True
    )  # letsencrypt, comodo, etc.

    # Certificate lifecycle
    issued_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    auto_renew = Column(Boolean, default=True, nullable=False)
    renewal_threshold_days = Column(Integer, default=30, nullable=False)

    # Certificate content
    certificate_pem = Column(Text, nullable=True)
    private_key_pem = Column(Text, nullable=True)  # Encrypted storage recommended
    certificate_chain = Column(Text, nullable=True)

    # Status and validation
    ssl_status = Column(
        SQLEnum(SSLStatus), default=SSLStatus.PENDING, nullable=False, index=True
    )
    validation_method = Column(String(50), nullable=True)  # HTTP, DNS, email
    validation_token = Column(String(255), nullable=True)

    # Usage tracking
    last_validation_check = Column(DateTime, nullable=True)
    validation_errors = Column(JSON, nullable=True)
    deployment_status = Column(String(20), default="pending", nullable=False)

    # Provider integration
    provider_certificate_id = Column(String(100), nullable=True, index=True)
    provider_order_id = Column(String(100), nullable=True)

    # Security
    key_size = Column(Integer, default=2048, nullable=False)
    signature_algorithm = Column(String(50), nullable=True)
    fingerprint_sha1 = Column(String(40), nullable=True, index=True)
    fingerprint_sha256 = Column(String(64), nullable=True, index=True)

    # Custom fields
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="ssl_certificates")

    __table_args__ = (
        Index("ix_ssl_certificates_domain", "domain_id"),
        Index("ix_ssl_certificates_expires", "expires_at"),
        Index("ix_ssl_certificates_status", "ssl_status"),
        Index("ix_ssl_certificates_common_name", "common_name"),
        Index("ix_ssl_certificates_issuer", "issuer"),
        Index("ix_ssl_certificates_fingerprint", "fingerprint_sha256"),
    )

    @hybrid_property
    def is_expired(self):
        """Check if certificate has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @hybrid_property
    def days_until_expiration(self):
        """Calculate days until certificate expiration."""
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    @hybrid_property
    def needs_renewal(self):
        """Check if certificate needs renewal."""
        return self.days_until_expiration <= self.renewal_threshold_days

    @hybrid_property
    def is_valid(self):
        """Check if certificate is valid and not expired."""
        return (
            self.ssl_status == SSLStatus.ISSUED
            and not self.is_expired
            and not self.validation_errors
        )

    def __repr__(self):
        return f"<SSLCertificate(id='{self.certificate_id}', domain='{self.common_name}', status='{self.ssl_status}')>"


class DomainLog(TenantModel):
    """Domain operation and change logging."""

    __tablename__ = "domain_logs"

    # Log identification
    domain_id = Column(
        String(100), ForeignKey("domains.domain_id"), nullable=False, index=True
    )
    log_timestamp = Column(
        DateTime(timezone=True), nullable=False, default=func.now(), index=True
    )

    # Log details
    action = Column(
        String(50), nullable=False, index=True
    )  # created, updated, verified, ssl_issued, etc.
    user_id = Column(String(100), nullable=False, index=True)

    # Action details
    description = Column(Text, nullable=False)
    before_state = Column(JSON, nullable=True)  # State before action
    after_state = Column(JSON, nullable=True)  # State after action

    # Operation metadata
    operation_id = Column(String(100), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(String(500), nullable=True)

    # Result tracking
    success = Column(Boolean, nullable=False, index=True)
    error_code = Column(String(50), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Provider details
    provider_response = Column(JSON, nullable=True)
    provider_request_id = Column(String(100), nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="domain_logs")

    __table_args__ = (
        Index("ix_domain_logs_action", "action", "log_timestamp"),
        Index("ix_domain_logs_user", "user_id", "log_timestamp"),
        Index("ix_domain_logs_success", "success", "log_timestamp"),
        Index("ix_domain_logs_operation", "operation_id"),
        Index("ix_domain_logs_domain_action", "domain_id", "action"),
    )

    @hybrid_property
    def operation_duration_seconds(self):
        """Get operation duration in seconds."""
        return self.duration_ms / 1000 if self.duration_ms else None

    def __repr__(self):
        return f"<DomainLog(domain='{self.domain_id}', action='{self.action}', success={self.success})>"


class DNSZone(TenantModel, AuditableMixin):
    """DNS zone management."""

    __tablename__ = "dns_zones"

    # Zone identification
    zone_id = Column(String(100), nullable=False, unique=True, index=True)
    zone_name = Column(String(255), nullable=False, index=True)

    # Zone properties
    primary_nameserver = Column(String(255), nullable=False)
    admin_email = Column(String(255), nullable=False)
    serial_number = Column(Integer, nullable=False, default=1)
    refresh_interval = Column(Integer, default=3600, nullable=False)  # SOA refresh
    retry_interval = Column(Integer, default=1800, nullable=False)  # SOA retry
    expire_interval = Column(Integer, default=604800, nullable=False)  # SOA expire
    minimum_ttl = Column(Integer, default=3600, nullable=False)  # SOA minimum

    # Zone management
    provider = Column(SQLEnum(DomainProvider), nullable=False, index=True)
    provider_zone_id = Column(String(100), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Synchronization
    last_sync = Column(DateTime, nullable=True, index=True)
    sync_status = Column(String(20), default="pending", nullable=False, index=True)
    sync_error_message = Column(Text, nullable=True)

    # Zone file management
    zone_file_path = Column(String(500), nullable=True)
    zone_file_hash = Column(String(64), nullable=True)  # SHA256 hash

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_dns_zones_provider", "provider", "provider_zone_id"),
        Index("ix_dns_zones_sync", "sync_status", "last_sync"),
        Index("ix_dns_zones_active", "is_active"),
    )

    @hybrid_property
    def needs_sync(self):
        """Check if zone needs synchronization."""
        return self.sync_status in ["pending", "failed"]

    def increment_serial(self):
        """Increment SOA serial number."""
        self.serial_number += 1
        return self.serial_number

    def __repr__(self):
        return f"<DNSZone(id='{self.zone_id}', name='{self.zone_name}', provider='{self.provider}')>"


class DomainVerification(TenantModel, AuditableMixin):
    """Domain ownership verification tracking."""

    __tablename__ = "domain_verifications"

    # Verification identification
    verification_id = Column(String(100), nullable=False, unique=True, index=True)
    domain_id = Column(
        String(100), ForeignKey("domains.domain_id"), nullable=False, index=True
    )

    # Verification details
    verification_method = Column(
        String(50), nullable=False, index=True
    )  # DNS, HTTP, email
    verification_token = Column(String(255), nullable=False)
    verification_value = Column(String(1000), nullable=True)

    # Verification status
    status = Column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)

    # Timing
    initiated_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    verified_at = Column(DateTime, nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_check = Column(DateTime, nullable=True)

    # Check details
    check_interval_minutes = Column(Integer, default=5, nullable=False)
    next_check = Column(DateTime, nullable=True, index=True)

    # Results
    verification_response = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_domain_verifications_domain", "domain_id"),
        Index("ix_domain_verifications_status", "status", "next_check"),
        Index("ix_domain_verifications_method", "verification_method"),
        Index("ix_domain_verifications_expires", "expires_at"),
    )

    @hybrid_property
    def is_expired(self):
        """Check if verification has expired."""
        return self.expires_at and datetime.now(timezone.utc) > self.expires_at

    @hybrid_property
    def is_due_for_check(self):
        """Check if verification is due for check."""
        return self.next_check and datetime.now(timezone.utc) >= self.next_check

    @hybrid_property
    def has_failed(self):
        """Check if verification has failed."""
        return (
            self.status == VerificationStatus.FAILED
            or self.attempts >= self.max_attempts
        )

    def __repr__(self):
        return f"<DomainVerification(id='{self.verification_id}', method='{self.verification_method}', status='{self.status}')>"


# Export all models and enums
__all__ = [
    # Enums
    "DomainStatus",
    "DNSRecordType",
    "DomainProvider",
    "VerificationStatus",
    "SSLStatus",
    # Models
    "Domain",
    "DNSRecord",
    "SSLCertificate",
    "DomainLog",
    "DNSZone",
    "DomainVerification",
]
