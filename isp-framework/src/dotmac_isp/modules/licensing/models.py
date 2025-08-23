"""Licensing models for software licenses, compliance, and asset management."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class LicenseType(str, Enum):
    """Software license types."""

    PERPETUAL = "perpetual"
    SUBSCRIPTION = "subscription"
    VOLUME = "volume"
    SITE = "site"
    USER = "user"
    DEVICE = "device"
    CONCURRENT = "concurrent"
    TRIAL = "trial"
    EDUCATIONAL = "educational"
    OEM = "oem"


class LicenseStatus(str, Enum):
    """License status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    VIOLATED = "violated"
    CANCELLED = "cancelled"
    PENDING = "pending"


class ComplianceStatus(str, Enum):
    """License compliance status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    AT_RISK = "at_risk"
    UNKNOWN = "unknown"


class AllocationStatus(str, Enum):
    """License allocation status."""

    ALLOCATED = "allocated"
    UNALLOCATED = "unallocated"
    RESERVED = "reserved"
    IN_USE = "in_use"
    RETIRED = "retired"


class AuditStatus(str, Enum):
    """License audit status."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class AlertType(str, Enum):
    """License alert types."""

    EXPIRY = "expiry"
    COMPLIANCE = "compliance"
    OVER_USAGE = "over_usage"
    RENEWAL = "renewal"
    AUDIT = "audit"
    MAINTENANCE = "maintenance"


class Software(TenantModel, StatusMixin, AuditMixin):
    """Software products and applications."""

    __tablename__ = "licensing_software"

    # Software identification
    software_code = Column(String(100), nullable=False, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Vendor information
    vendor_name = Column(String(200), nullable=False, index=True)
    manufacturer = Column(String(200), nullable=True)
    publisher = Column(String(200), nullable=True)

    # Product details
    version = Column(String(100), nullable=True)
    edition = Column(String(100), nullable=True)
    platform = Column(String(100), nullable=True)  # Windows, Linux, macOS, etc.
    architecture = Column(String(50), nullable=True)  # x86, x64, ARM

    # Classification
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True)
    business_criticality = Column(
        String(50), nullable=True
    )  # critical, high, medium, low

    # Release information
    release_date = Column(Date, nullable=True)
    end_of_life_date = Column(Date, nullable=True)
    end_of_support_date = Column(Date, nullable=True)

    # Technical specifications
    system_requirements = Column(JSON, nullable=True)
    installation_notes = Column(Text, nullable=True)
    compatibility_info = Column(JSON, nullable=True)

    # Documentation and resources
    documentation_url = Column(String(500), nullable=True)
    support_url = Column(String(500), nullable=True)
    download_url = Column(String(500), nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    licenses = relationship(
        "License", back_populates="software", cascade="all, delete-orphan"
    )
    installations = relationship("Installation", back_populates="software")

    __table_args__ = (
        Index("ix_software_tenant_code", "tenant_id", "software_code", unique=True),
        Index("ix_software_vendor_category", "vendor_name", "category"),
    )

    @hybrid_property
    def is_end_of_life(self) -> bool:
        """Check if software is end-of-life."""
        return self.end_of_life_date and date.today() >= self.end_of_life_date

    @hybrid_property
    def total_licenses(self) -> int:
        """Get total number of licenses."""
        return len(self.licenses)

    def __repr__(self):
        return f"<Software(code='{self.software_code}', name='{self.name}', vendor='{self.vendor_name}')>"


class License(TenantModel, StatusMixin, AuditMixin):
    """Software licenses and entitlements."""

    __tablename__ = "licensing_licenses"

    # License identification
    license_key = Column(String(500), nullable=True, index=True)
    license_number = Column(String(200), nullable=False, index=True)
    certificate_number = Column(String(200), nullable=True)

    # Software reference
    software_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_software.id"),
        nullable=False,
        index=True,
    )
    software_version = Column(String(100), nullable=True)

    # License details
    license_type = Column(SQLEnum(LicenseType), nullable=False, index=True)
    license_status = Column(
        SQLEnum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False, index=True
    )

    # Entitlements
    licensed_quantity = Column(Integer, nullable=False, default=1)
    allocated_quantity = Column(Integer, default=0, nullable=False)
    used_quantity = Column(Integer, default=0, nullable=False)

    # Dates
    purchase_date = Column(Date, nullable=True)
    activation_date = Column(Date, nullable=True)
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)

    # Vendor and purchase information
    vendor_name = Column(String(200), nullable=False)
    vendor_contact = Column(String(200), nullable=True)
    purchase_order_number = Column(String(100), nullable=True)
    invoice_number = Column(String(100), nullable=True)

    # Financial details
    purchase_cost = Column(Numeric(12, 2), nullable=True)
    annual_cost = Column(Numeric(12, 2), nullable=True)
    maintenance_cost = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)

    # Subscription details (for subscription licenses)
    billing_cycle = Column(String(50), nullable=True)  # monthly, quarterly, annually
    auto_renewal = Column(Boolean, default=False, nullable=False)
    renewal_date = Column(Date, nullable=True)

    # Compliance and usage
    compliance_status = Column(
        SQLEnum(ComplianceStatus),
        default=ComplianceStatus.COMPLIANT,
        nullable=False,
        index=True,
    )
    usage_tracking_enabled = Column(Boolean, default=True, nullable=False)

    # Maintenance and support
    maintenance_included = Column(Boolean, default=False, nullable=False)
    maintenance_expiry = Column(Date, nullable=True)
    support_level = Column(String(100), nullable=True)

    # Terms and conditions
    license_terms = Column(Text, nullable=True)
    usage_restrictions = Column(JSON, nullable=True)
    transfer_rights = Column(Text, nullable=True)

    # Additional metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    software = relationship("Software", back_populates="licenses")
    allocations = relationship(
        "LicenseAllocation", back_populates="license", cascade="all, delete-orphan"
    )
    audits = relationship("LicenseAudit", back_populates="license")

    __table_args__ = (
        Index("ix_licenses_software_status", "software_id", "license_status"),
        Index("ix_licenses_expiry_date", "expiry_date"),
        Index("ix_licenses_compliance", "compliance_status"),
    )

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if license is expired."""
        return self.expiry_date and date.today() > self.expiry_date

    @hybrid_property
    def days_to_expiry(self) -> Optional[int]:
        """Calculate days until license expires."""
        if self.expiry_date:
            return (self.expiry_date - date.today()).days
        return None

    @hybrid_property
    def utilization_percentage(self) -> float:
        """Calculate license utilization percentage."""
        if self.licensed_quantity == 0:
            return 0.0
        return round((self.used_quantity / self.licensed_quantity) * 100, 2)

    @hybrid_property
    def available_quantity(self) -> int:
        """Calculate available license quantity."""
        return self.licensed_quantity - self.used_quantity

    def __repr__(self):
        return f"<License(number='{self.license_number}', type='{self.license_type}', status='{self.license_status}')>"


class LicenseAllocation(TenantModel, AuditMixin):
    """License allocations to users, devices, or systems."""

    __tablename__ = "licensing_allocations"

    # References
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_licenses.id"),
        nullable=False,
        index=True,
    )

    # Allocation target
    allocation_type = Column(String(50), nullable=False)  # user, device, system, group
    allocated_to_id = Column(
        String(100), nullable=True, index=True
    )  # User/device/system ID
    allocated_to_name = Column(String(200), nullable=False)
    allocated_to_email = Column(String(255), nullable=True)

    # Allocation details
    allocation_status = Column(
        SQLEnum(AllocationStatus),
        default=AllocationStatus.ALLOCATED,
        nullable=False,
        index=True,
    )
    allocation_date = Column(Date, nullable=False, default=date.today)
    activation_date = Column(Date, nullable=True)
    deactivation_date = Column(Date, nullable=True)

    # Usage tracking
    first_use_date = Column(Date, nullable=True)
    last_use_date = Column(Date, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Installation details
    installation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_installations.id"),
        nullable=True,
        index=True,
    )
    device_info = Column(JSON, nullable=True)

    # Approval
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Additional information
    business_justification = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    license = relationship("License", back_populates="allocations")
    installation = relationship("Installation", back_populates="allocations")

    __table_args__ = (
        Index("ix_allocations_license_status", "license_id", "allocation_status"),
        Index("ix_allocations_allocated_to", "allocated_to_id"),
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if allocation is active."""
        return self.allocation_status == AllocationStatus.ALLOCATED

    @hybrid_property
    def days_since_last_use(self) -> Optional[int]:
        """Calculate days since last use."""
        if self.last_use_date:
            return (date.today() - self.last_use_date).days
        return None

    def __repr__(self):
        return f"<LicenseAllocation(license_id='{self.license_id}', allocated_to='{self.allocated_to_name}')>"


class Installation(TenantModel, AuditMixin):
    """Software installations on devices and systems."""

    __tablename__ = "licensing_installations"

    # Installation identification
    installation_id = Column(String(100), nullable=False, unique=True, index=True)

    # Software reference
    software_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_software.id"),
        nullable=False,
        index=True,
    )
    installed_version = Column(String(100), nullable=True)

    # Device/system information
    device_id = Column(String(100), nullable=True, index=True)
    device_name = Column(String(200), nullable=False)
    device_type = Column(String(50), nullable=True)  # desktop, server, laptop, mobile
    hostname = Column(String(200), nullable=True)
    ip_address = Column(String(45), nullable=True)
    mac_address = Column(String(17), nullable=True)

    # Operating system
    os_name = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    os_architecture = Column(String(50), nullable=True)

    # Installation details
    installation_date = Column(Date, nullable=False)
    installation_path = Column(String(500), nullable=True)
    installation_method = Column(
        String(100), nullable=True
    )  # manual, automated, msi, etc.
    installer_version = Column(String(100), nullable=True)

    # Status
    installation_status = Column(
        String(50), default="active", nullable=False, index=True
    )
    last_seen_date = Column(Date, nullable=True)

    # Usage tracking
    first_use_date = Column(Date, nullable=True)
    last_use_date = Column(Date, nullable=True)
    usage_hours = Column(Float, default=0, nullable=False)
    launch_count = Column(Integer, default=0, nullable=False)

    # Discovery information
    discovered_by = Column(String(100), nullable=True)  # agent, scan, manual
    discovery_date = Column(Date, nullable=True)
    discovery_source = Column(String(200), nullable=True)

    # Compliance
    license_compliant = Column(Boolean, nullable=True)
    compliance_notes = Column(Text, nullable=True)

    # Additional information
    user_name = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    location = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    software = relationship("Software", back_populates="installations")
    allocations = relationship("LicenseAllocation", back_populates="installation")

    __table_args__ = (
        Index("ix_installations_software_device", "software_id", "device_id"),
        Index("ix_installations_status", "installation_status"),
        Index("ix_installations_last_seen", "last_seen_date"),
    )

    @hybrid_property
    def is_active(self) -> bool:
        """Check if installation is active."""
        return self.installation_status == "active"

    @hybrid_property
    def days_since_last_seen(self) -> Optional[int]:
        """Calculate days since last seen."""
        if self.last_seen_date:
            return (date.today() - self.last_seen_date).days
        return None

    def __repr__(self):
        return f"<Installation(id='{self.installation_id}', software_id='{self.software_id}', device='{self.device_name}')>"


class LicenseAudit(TenantModel, AuditMixin):
    """License audits and compliance reviews."""

    __tablename__ = "licensing_audits"

    # Audit identification
    audit_id = Column(String(100), nullable=False, unique=True, index=True)
    audit_name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Audit scope
    audit_type = Column(String(50), nullable=False)  # full, software-specific, vendor
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_licenses.id"),
        nullable=True,
        index=True,
    )
    software_filter = Column(JSON, nullable=True)
    vendor_filter = Column(String(200), nullable=True)

    # Timeline
    planned_start_date = Column(Date, nullable=False)
    planned_end_date = Column(Date, nullable=False)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Status
    audit_status = Column(
        SQLEnum(AuditStatus), default=AuditStatus.SCHEDULED, nullable=False, index=True
    )

    # Personnel
    auditor_name = Column(String(200), nullable=False)
    audit_team = Column(JSON, nullable=True)
    external_auditor = Column(String(200), nullable=True)

    # Results
    total_licenses_reviewed = Column(Integer, default=0, nullable=False)
    compliant_licenses = Column(Integer, default=0, nullable=False)
    non_compliant_licenses = Column(Integer, default=0, nullable=False)

    # Findings summary
    findings_summary = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)  # low, medium, high, critical

    # Cost impact
    potential_penalty = Column(Numeric(12, 2), nullable=True)
    remediation_cost = Column(Numeric(12, 2), nullable=True)

    # Documentation
    audit_report_url = Column(String(500), nullable=True)
    evidence_links = Column(JSON, nullable=True)

    # Follow-up
    remediation_required = Column(Boolean, default=False, nullable=False)
    remediation_due_date = Column(Date, nullable=True)
    next_audit_date = Column(Date, nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    license = relationship("License", back_populates="audits")
    findings = relationship(
        "AuditFinding", back_populates="audit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_audits_status_dates", "audit_status", "planned_start_date"),
        Index("ix_audits_vendor", "vendor_filter"),
    )

    @hybrid_property
    def compliance_rate(self) -> float:
        """Calculate compliance rate percentage."""
        if self.total_licenses_reviewed == 0:
            return 0.0
        return round((self.compliant_licenses / self.total_licenses_reviewed) * 100, 2)

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if audit is overdue."""
        return (
            self.audit_status != AuditStatus.COMPLETED
            and date.today() > self.planned_end_date
        )

    def __repr__(self):
        return f"<LicenseAudit(id='{self.audit_id}', name='{self.audit_name}', status='{self.audit_status}')>"


class AuditFinding(TenantModel, AuditMixin):
    """Individual findings from license audits."""

    __tablename__ = "licensing_audit_findings"

    # Finding identification
    finding_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # References
    audit_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_audits.id"),
        nullable=False,
        index=True,
    )
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_licenses.id"),
        nullable=True,
        index=True,
    )
    software_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_software.id"),
        nullable=True,
        index=True,
    )

    # Finding classification
    finding_type = Column(
        String(100), nullable=False, index=True
    )  # over-deployment, under-licensing, etc.
    severity = Column(
        String(20), nullable=False, index=True
    )  # low, medium, high, critical
    category = Column(String(100), nullable=True)

    # Impact assessment
    compliance_impact = Column(Text, nullable=True)
    financial_impact = Column(Numeric(12, 2), nullable=True)
    risk_level = Column(String(20), nullable=True)

    # Evidence
    evidence = Column(JSON, nullable=True)
    screenshots = Column(JSON, nullable=True)
    supporting_data = Column(JSON, nullable=True)

    # Remediation
    recommended_action = Column(Text, nullable=False)
    remediation_plan = Column(Text, nullable=True)
    remediation_due_date = Column(Date, nullable=True)

    # Status
    finding_status = Column(String(50), default="open", nullable=False, index=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_date = Column(Date, nullable=True)
    verified_date = Column(Date, nullable=True)

    # Assignment
    assigned_to = Column(String(200), nullable=True)
    responsible_team = Column(String(100), nullable=True)

    # Additional information
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    audit = relationship("LicenseAudit", back_populates="findings")
    license = relationship("License")
    software = relationship("Software")

    __table_args__ = (
        Index("ix_findings_audit_severity", "audit_id", "severity"),
        Index("ix_findings_status", "finding_status"),
        Index("ix_findings_due_date", "remediation_due_date"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if finding remediation is overdue."""
        return (
            self.finding_status not in ["resolved", "closed"]
            and self.remediation_due_date
            and date.today() > self.remediation_due_date
        )

    def __repr__(self):
        return f"<AuditFinding(id='{self.finding_id}', type='{self.finding_type}', severity='{self.severity}')>"


class LicenseAlert(TenantModel, AuditMixin):
    """License alerts and notifications."""

    __tablename__ = "licensing_alerts"

    # Alert identification
    alert_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # References
    license_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_licenses.id"),
        nullable=True,
        index=True,
    )
    software_id = Column(
        UUID(as_uuid=True),
        ForeignKey("licensing_software.id"),
        nullable=True,
        index=True,
    )

    # Alert classification
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(
        String(20), nullable=False, index=True
    )  # low, medium, high, critical

    # Trigger conditions
    trigger_date = Column(Date, nullable=False, default=date.today)
    trigger_conditions = Column(JSON, nullable=False)

    # Status
    alert_status = Column(String(50), default="active", nullable=False, index=True)
    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_by = Column(String(200), nullable=True)
    acknowledged_date = Column(DateTime, nullable=True)

    # Resolution
    resolved = Column(Boolean, default=False, nullable=False)
    resolution_notes = Column(Text, nullable=True)
    resolved_date = Column(DateTime, nullable=True)

    # Notification
    notification_sent = Column(Boolean, default=False, nullable=False)
    recipients = Column(JSON, nullable=True)

    # Additional information
    action_required = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    license = relationship("License")
    software = relationship("Software")

    __table_args__ = (
        Index("ix_alerts_type_severity", "alert_type", "severity"),
        Index("ix_alerts_status_date", "alert_status", "trigger_date"),
        Index("ix_alerts_due_date", "due_date"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if alert action is overdue."""
        return not self.resolved and self.due_date and date.today() > self.due_date

    @hybrid_property
    def days_active(self) -> int:
        """Calculate days since alert was triggered."""
        return (date.today() - self.trigger_date).days

    def __repr__(self):
        return f"<LicenseAlert(id='{self.alert_id}', type='{self.alert_type}', severity='{self.severity}')>"
