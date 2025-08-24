"""Compliance models for regulatory compliance, audits, and reporting."""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
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


class ComplianceFramework(str, Enum):
    """Compliance framework types."""

    SOX = "sox"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    FCC = "fcc"
    CALEA = "calea"
    CPNI = "cpni"
    STATE_TELECOM = "state_telecom"
    CUSTOM = "custom"


class ComplianceStatus(str, Enum):
    """Compliance status levels."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    UNDER_REVIEW = "under_review"
    EXEMPT = "exempt"
    NOT_APPLICABLE = "not_applicable"


class AuditType(str, Enum):
    """Audit types."""

    INTERNAL = "internal"
    EXTERNAL = "external"
    REGULATORY = "regulatory"
    THIRD_PARTY = "third_party"


class AuditStatus(str, Enum):
    """Audit status."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    """Audit finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    """Audit finding status."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class ComplianceRequirement(TenantModel, StatusMixin, AuditMixin):
    """Compliance requirements and standards."""

    __tablename__ = "compliance_requirements"

    # Requirement identification
    requirement_code = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)

    # Framework association
    framework = Column(SQLEnum(ComplianceFramework), nullable=False, index=True)
    section = Column(String(100), nullable=True)
    subsection = Column(String(100), nullable=True)

    # Requirement details
    mandatory = Column(Boolean, default=True, nullable=False)
    frequency = Column(String(50), nullable=True)  # annual, quarterly, monthly, etc.
    due_date = Column(Date, nullable=True)

    # Implementation
    implementation_notes = Column(Text, nullable=True)
    evidence_required = Column(JSON, nullable=True)
    control_activities = Column(JSON, nullable=True)

    # Status tracking
    compliance_status = Column(
        SQLEnum(ComplianceStatus), default=ComplianceStatus.UNDER_REVIEW, nullable=False
    )
    last_assessment_date = Column(Date, nullable=True)
    next_assessment_date = Column(Date, nullable=True)

    # Risk assessment
    risk_level = Column(String(20), nullable=True)  # high, medium, low
    business_impact = Column(Text, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    assessments = relationship(
        "ComplianceAssessment",
        back_populates="requirement",
        cascade="all, delete-orphan",
    )
    findings = relationship("ComplianceFinding", back_populates="requirement")

    __table_args__ = (
        Index("ix_requirements_framework_status", "framework", "compliance_status"),
        Index(
            "ix_requirements_tenant_code", "tenant_id", "requirement_code", unique=True
        ),
    )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ComplianceRequirement(code='{self.requirement_code}', framework='{self.framework}')>"


class ComplianceAssessment(TenantModel, AuditMixin):
    """Compliance assessments and evaluations."""

    __tablename__ = "compliance_assessments"

    # Assessment identification
    assessment_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Requirement reference
    requirement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_requirements.id"),
        nullable=False,
        index=True,
    )

    # Assessment details
    assessment_date = Column(Date, nullable=False)
    assessor_name = Column(String(200), nullable=False)
    assessor_role = Column(String(100), nullable=True)

    # Results
    result_status = Column(SQLEnum(ComplianceStatus), nullable=False)
    score = Column(Float, nullable=True)  # 0-100 compliance score

    # Evidence and documentation
    evidence_collected = Column(JSON, nullable=True)
    documentation_links = Column(JSON, nullable=True)

    # Assessment methodology
    methodology = Column(Text, nullable=True)
    tools_used = Column(JSON, nullable=True)
    sampling_method = Column(Text, nullable=True)

    # Findings summary
    findings_summary = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Follow-up
    next_assessment_date = Column(Date, nullable=True)
    remediation_required = Column(Boolean, default=False, nullable=False)

    # Additional data
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    requirement = relationship("ComplianceRequirement", back_populates="assessments")
    findings = relationship(
        "ComplianceFinding", back_populates="assessment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assessments_requirement_date", "requirement_id", "assessment_date"),
        Index("ix_assessments_status", "result_status"),
    )

    @hybrid_property
    def is_passing(self) -> bool:
        """Check if assessment is passing."""
        return self.result_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.EXEMPT,
        ]

    def __repr__(self):
        """  Repr   operation."""
        return f"<ComplianceAssessment(id='{self.assessment_id}', status='{self.result_status}')>"


class ComplianceFinding(TenantModel, AuditMixin):
    """Compliance findings and issues."""

    __tablename__ = "compliance_findings"

    # Finding identification
    finding_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # References
    requirement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_requirements.id"),
        nullable=False,
        index=True,
    )
    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("compliance_assessments.id"),
        nullable=True,
        index=True,
    )

    # Finding classification
    severity = Column(SQLEnum(FindingSeverity), nullable=False, index=True)
    category = Column(String(100), nullable=True)  # policy, process, technical, etc.

    # Impact assessment
    business_impact = Column(Text, nullable=True)
    risk_rating = Column(String(20), nullable=True)
    affected_systems = Column(JSON, nullable=True)

    # Status and resolution
    status = Column(
        SQLEnum(FindingStatus), default=FindingStatus.OPEN, nullable=False, index=True
    )
    resolution_plan = Column(Text, nullable=True)
    remediation_steps = Column(JSON, nullable=True)

    # Dates and deadlines
    discovered_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    resolved_date = Column(Date, nullable=True)

    # Assignment
    assigned_to = Column(String(200), nullable=True)
    responsible_team = Column(String(100), nullable=True)

    # Evidence and documentation
    evidence = Column(JSON, nullable=True)
    supporting_documents = Column(JSON, nullable=True)

    # Resolution tracking
    resolution_notes = Column(Text, nullable=True)
    verification_evidence = Column(JSON, nullable=True)
    verified_by = Column(String(200), nullable=True)
    verified_date = Column(Date, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    requirement = relationship("ComplianceRequirement", back_populates="findings")
    assessment = relationship("ComplianceAssessment", back_populates="findings")

    __table_args__ = (
        Index("ix_findings_severity_status", "severity", "status"),
        Index("ix_findings_due_date", "due_date"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if finding is overdue."""
        if not self.due_date:
            return False
        return (
            self.status not in [FindingStatus.RESOLVED, FindingStatus.CLOSED]
            and date.today() > self.due_date
        )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ComplianceFinding(id='{self.finding_id}', severity='{self.severity}', status='{self.status}')>"


class ComplianceAudit(TenantModel, AuditMixin):
    """Compliance audits and reviews."""

    __tablename__ = "compliance_audits"

    # Audit identification
    audit_id = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Audit classification
    audit_type = Column(SQLEnum(AuditType), nullable=False, index=True)
    framework = Column(SQLEnum(ComplianceFramework), nullable=False, index=True)
    scope = Column(Text, nullable=False)

    # Timeline
    planned_start_date = Column(Date, nullable=False)
    planned_end_date = Column(Date, nullable=False)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Status and progress
    status = Column(
        SQLEnum(AuditStatus), default=AuditStatus.PLANNED, nullable=False, index=True
    )
    progress_percentage = Column(Integer, default=0, nullable=False)

    # Audit team
    lead_auditor = Column(String(200), nullable=False)
    audit_team = Column(JSON, nullable=True)
    external_auditor = Column(String(200), nullable=True)

    # Methodology
    audit_methodology = Column(Text, nullable=True)
    testing_procedures = Column(JSON, nullable=True)
    sampling_approach = Column(Text, nullable=True)

    # Results summary
    overall_rating = Column(String(50), nullable=True)
    compliance_score = Column(Float, nullable=True)  # 0-100

    # Findings summary
    critical_findings = Column(Integer, default=0, nullable=False)
    high_findings = Column(Integer, default=0, nullable=False)
    medium_findings = Column(Integer, default=0, nullable=False)
    low_findings = Column(Integer, default=0, nullable=False)

    # Documentation
    audit_report_url = Column(String(500), nullable=True)
    management_response = Column(Text, nullable=True)

    # Follow-up
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(Date, nullable=True)
    next_audit_date = Column(Date, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_audits_type_framework", "audit_type", "framework"),
        Index("ix_audits_status_dates", "status", "planned_start_date"),
    )

    @hybrid_property
    def total_findings(self) -> int:
        """Get total number of findings."""
        return (
            self.critical_findings
            + self.high_findings
            + self.medium_findings
            + self.low_findings
        )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if audit is overdue."""
        if self.status in [AuditStatus.COMPLETED, AuditStatus.CANCELLED]:
            return False
        return date.today() > self.planned_end_date

    def __repr__(self):
        """  Repr   operation."""
        return f"<ComplianceAudit(id='{self.audit_id}', type='{self.audit_type}', status='{self.status}')>"


class CompliancePolicy(TenantModel, StatusMixin, AuditMixin):
    """Compliance policies and procedures."""

    __tablename__ = "compliance_policies"

    # Policy identification
    policy_number = Column(String(100), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=False)

    # Policy classification
    policy_type = Column(String(100), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    framework = Column(SQLEnum(ComplianceFramework), nullable=True, index=True)

    # Content
    policy_content = Column(Text, nullable=False)
    procedures = Column(Text, nullable=True)
    guidelines = Column(Text, nullable=True)

    # Approval and versioning
    version = Column(String(20), nullable=False, default="1.0")
    approved_by = Column(String(200), nullable=False)
    approval_date = Column(Date, nullable=False)

    # Effective dates
    effective_date = Column(Date, nullable=False)
    review_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=True)

    # Applicability
    scope = Column(Text, nullable=False)
    applicable_roles = Column(JSON, nullable=True)
    applicable_departments = Column(JSON, nullable=True)

    # Distribution and training
    distribution_list = Column(JSON, nullable=True)
    training_required = Column(Boolean, default=False, nullable=False)
    training_frequency = Column(String(50), nullable=True)

    # Related documents
    related_policies = Column(JSON, nullable=True)
    supporting_documents = Column(JSON, nullable=True)

    # Compliance tracking
    compliance_monitoring = Column(Boolean, default=True, nullable=False)
    violation_consequences = Column(Text, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_policies_tenant_number", "tenant_id", "policy_number", unique=True),
        Index("ix_policies_review_date", "review_date"),
    )

    @hybrid_property
    def is_due_for_review(self) -> bool:
        """Check if policy is due for review."""
        return date.today() >= self.review_date

    @hybrid_property
    def is_expired(self) -> bool:
        """Check if policy is expired."""
        return self.expiry_date and date.today() > self.expiry_date

    def __repr__(self):
        """  Repr   operation."""
        return (
            f"<CompliancePolicy(number='{self.policy_number}', title='{self.title}')>"
        )


class ComplianceReport(TenantModel, AuditMixin):
    """Compliance reports and documentation."""

    __tablename__ = "compliance_reports"

    # Report identification
    report_id = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # Report classification
    report_type = Column(String(100), nullable=False, index=True)
    framework = Column(SQLEnum(ComplianceFramework), nullable=True, index=True)
    reporting_period = Column(String(100), nullable=False)

    # Timeline
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    generated_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)

    # Content and data
    executive_summary = Column(Text, nullable=True)
    report_data = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=True)

    # Status and approval
    status = Column(String(50), default="draft", nullable=False, index=True)
    reviewed_by = Column(String(200), nullable=True)
    approved_by = Column(String(200), nullable=True)
    approval_date = Column(Date, nullable=True)

    # Distribution
    recipients = Column(JSON, nullable=True)
    submitted_to = Column(String(200), nullable=True)  # Regulatory body
    submission_date = Column(Date, nullable=True)

    # Files and links
    report_file_url = Column(String(500), nullable=True)
    supporting_files = Column(JSON, nullable=True)

    # Follow-up
    response_required = Column(Boolean, default=False, nullable=False)
    response_due_date = Column(Date, nullable=True)

    # Additional metadata
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_reports_type_period", "report_type", "period_start", "period_end"),
        Index("ix_reports_due_date", "due_date"),
    )

    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if report is overdue."""
        return (
            self.due_date
            and self.status != "submitted"
            and date.today() > self.due_date
        )

    def __repr__(self):
        """  Repr   operation."""
        return f"<ComplianceReport(id='{self.report_id}', type='{self.report_type}')>"
