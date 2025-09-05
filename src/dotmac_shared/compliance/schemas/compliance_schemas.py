"""
Shared compliance and regulatory schemas for DotMac Framework.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from dotmac.core.schemas.base_schemas import TenantBaseModel
from pydantic import BaseModel, Field


class ComplianceFramework(str, Enum):
    """Supported compliance frameworks."""

    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    NIST = "nist"
    CCPA = "ccpa"
    PIPEDA = "pipeda"


class ComplianceStatus(str, Enum):
    """Compliance status values."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL_COMPLIANCE = "partial_compliance"
    UNDER_REVIEW = "under_review"
    REMEDIATION_REQUIRED = "remediation_required"


class RiskLevel(str, Enum):
    """Risk assessment levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReportFrequency(str, Enum):
    """Report generation frequencies."""

    REAL_TIME = "real_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_DEMAND = "on_demand"


class DataClassification(str, Enum):
    """Data classification levels."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Data access events
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_EXPORT = "data_export"

    # Authentication events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    AUTH_FAILURE = "auth_failure"

    # Administrative events
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    ROLE_ASSIGNED = "role_assigned"
    PERMISSION_CHANGED = "permission_changed"

    # System events
    SYSTEM_ACCESS = "system_access"
    CONFIG_CHANGED = "config_changed"
    BACKUP_CREATED = "backup_created"

    # Business events
    TRANSACTION_PROCESSED = "transaction_processed"
    REPORT_GENERATED = "report_generated"
    COMPLIANCE_CHECK = "compliance_check"


class ComplianceEvent(TenantBaseModel):
    """Compliance event record."""

    event_id: UUID = Field(..., description="Event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    framework: ComplianceFramework = Field(..., description="Compliance framework")
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    user_id: Optional[UUID] = Field(None, description="User who triggered event")
    session_id: Optional[str] = Field(None, description="Session identifier")
    ip_address: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    risk_level: RiskLevel = Field(default=RiskLevel.LOW, description="Risk assessment")
    data_classification: Optional[DataClassification] = Field(None, description="Data classification")
    details: dict[str, Any] = Field(default_factory=dict, description="Event details")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class AuditEvent(BaseModel):
    """Generic audit event for trail recording."""

    event_id: UUID = Field(..., description="Event identifier")
    event_type: str = Field(..., description="Event type")
    actor: Optional[str] = Field(None, description="Actor performing action")
    resource: Optional[str] = Field(None, description="Target resource")
    action: str = Field(..., description="Action performed")
    outcome: str = Field(..., description="Action outcome")
    risk_score: Optional[int] = Field(None, description="Risk score 0-100")
    compliance_relevant: bool = Field(default=False, description="Compliance relevance")
    context: dict[str, Any] = Field(default_factory=dict, description="Event context")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class ComplianceRule(BaseModel):
    """Compliance rule definition."""

    rule_id: str = Field(..., description="Rule identifier")
    framework: ComplianceFramework = Field(..., description="Associated framework")
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: str = Field(..., description="Rule category")
    severity: RiskLevel = Field(..., description="Rule severity")
    conditions: dict[str, Any] = Field(..., description="Rule conditions")
    remediation: str = Field(..., description="Remediation guidance")
    is_active: bool = Field(default=True, description="Rule is active")


class ComplianceCheck(TenantBaseModel):
    """Compliance check result."""

    check_id: UUID = Field(..., description="Check identifier")
    rule_id: str = Field(..., description="Associated rule ID")
    resource_id: str = Field(..., description="Checked resource")
    resource_type: str = Field(..., description="Resource type")
    status: ComplianceStatus = Field(..., description="Check result")
    score: Optional[float] = Field(None, description="Compliance score 0-100")
    findings: list[str] = Field(default_factory=list, description="Check findings")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")
    evidence: dict[str, Any] = Field(default_factory=dict, description="Supporting evidence")
    next_check_due: Optional[datetime] = Field(None, description="Next check due date")
    checked_at: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")


class RegulatoryReport(TenantBaseModel):
    """Regulatory report structure."""

    report_id: UUID = Field(..., description="Report identifier")
    name: str = Field(..., description="Report name")
    framework: ComplianceFramework = Field(..., description="Target framework")
    report_type: str = Field(..., description="Type of report")
    frequency: ReportFrequency = Field(..., description="Report frequency")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")

    # Report content
    executive_summary: str = Field(..., description="Executive summary")
    compliance_status: ComplianceStatus = Field(..., description="Overall status")
    compliance_score: float = Field(..., description="Compliance score 0-100")

    # Detailed sections
    sections: list[dict[str, Any]] = Field(..., description="Report sections")
    findings: list[dict[str, Any]] = Field(..., description="Key findings")
    recommendations: list[dict[str, Any]] = Field(..., description="Recommendations")
    remediation_plan: list[dict[str, Any]] = Field(..., description="Remediation plan")

    # Metadata
    generated_by: UUID = Field(..., description="User who generated report")
    approved_by: Optional[UUID] = Field(None, description="User who approved report")
    status: str = Field(default="draft", description="Report status")
    version: str = Field(default="1.0", description="Report version")

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation time")
    approved_at: Optional[datetime] = Field(None, description="Approval time")


class ComplianceMetrics(BaseModel):
    """Compliance metrics and KPIs."""

    framework: ComplianceFramework = Field(..., description="Framework")
    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")

    # Overall metrics
    overall_score: float = Field(..., description="Overall compliance score")
    total_checks: int = Field(..., description="Total checks performed")
    passed_checks: int = Field(..., description="Checks passed")
    failed_checks: int = Field(..., description="Checks failed")

    # Risk metrics
    critical_issues: int = Field(..., description="Critical issues found")
    high_risk_issues: int = Field(..., description="High risk issues")
    medium_risk_issues: int = Field(..., description="Medium risk issues")
    low_risk_issues: int = Field(..., description="Low risk issues")

    # Trend data
    score_trend: list[dict[str, Any]] = Field(..., description="Score trend data")
    issue_trend: list[dict[str, Any]] = Field(..., description="Issue trend data")

    # Category breakdown
    category_scores: dict[str, float] = Field(..., description="Scores by category")

    calculated_at: datetime = Field(default_factory=datetime.utcnow, description="Calculation time")


class ComplianceAlert(TenantBaseModel):
    """Compliance alert notification."""

    alert_id: UUID = Field(..., description="Alert identifier")
    rule_id: str = Field(..., description="Triggered rule ID")
    framework: ComplianceFramework = Field(..., description="Associated framework")
    severity: RiskLevel = Field(..., description="Alert severity")
    title: str = Field(..., description="Alert title")
    description: str = Field(..., description="Alert description")
    resource_affected: str = Field(..., description="Affected resource")
    remediation: str = Field(..., description="Remediation steps")

    # Alert lifecycle
    status: str = Field(default="open", description="Alert status")
    assigned_to: Optional[UUID] = Field(None, description="Assigned user")
    acknowledged_by: Optional[UUID] = Field(None, description="User who acknowledged")
    resolved_by: Optional[UUID] = Field(None, description="User who resolved")

    # Timestamps
    triggered_at: datetime = Field(default_factory=datetime.utcnow, description="Trigger time")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment time")
    resolved_at: Optional[datetime] = Field(None, description="Resolution time")

    # Context
    context: dict[str, Any] = Field(default_factory=dict, description="Alert context")


class DataRetentionPolicy(BaseModel):
    """Data retention policy definition."""

    policy_id: str = Field(..., description="Policy identifier")
    name: str = Field(..., description="Policy name")
    framework: ComplianceFramework = Field(..., description="Associated framework")
    data_type: str = Field(..., description="Type of data")
    classification: DataClassification = Field(..., description="Data classification")
    retention_period_days: int = Field(..., description="Retention period in days")
    disposal_method: str = Field(..., description="Data disposal method")
    exceptions: list[str] = Field(default_factory=list, description="Policy exceptions")
    is_active: bool = Field(default=True, description="Policy is active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")


class ComplianceReportRequest(BaseModel):
    """Request for compliance report generation."""

    framework: ComplianceFramework = Field(..., description="Target framework")
    report_type: str = Field(..., description="Report type")
    period_start: datetime = Field(..., description="Report period start")
    period_end: datetime = Field(..., description="Report period end")
    include_sections: list[str] = Field(default_factory=list, description="Sections to include")
    format: str = Field(default="pdf", description="Output format")
    tenant_id: Optional[UUID] = Field(None, description="Tenant scope")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")


class ComplianceSchedule(TenantBaseModel):
    """Compliance check schedule."""

    schedule_id: UUID = Field(..., description="Schedule identifier")
    name: str = Field(..., description="Schedule name")
    framework: ComplianceFramework = Field(..., description="Associated framework")
    rule_ids: list[str] = Field(..., description="Rules to check")
    frequency: str = Field(..., description="Check frequency")
    next_run: datetime = Field(..., description="Next scheduled run")
    is_active: bool = Field(default=True, description="Schedule is active")
    created_by: UUID = Field(..., description="User who created schedule")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
