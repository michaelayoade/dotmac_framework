"""
Compliance Engine

Provides comprehensive compliance monitoring and audit capabilities
for regulatory frameworks like GDPR, HIPAA, SOC2, ISO 27001, and PCI DSS.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from ..observability import MonitoringStack


class RegulatoryFramework(str, Enum):
    """Supported regulatory frameworks."""

    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO_27001 = "iso_27001"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"
    SOX = "sox"
    NIST = "nist"


class ComplianceStatus(str, Enum):
    """Compliance check status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNKNOWN = "unknown"
    REMEDIATION_REQUIRED = "remediation_required"


@dataclass
class ComplianceRule:
    """Individual compliance rule definition."""

    id: str
    framework: RegulatoryFramework
    category: str
    title: str
    description: str
    severity: str
    requirement: str
    control_objective: str
    implementation_guidance: str
    test_procedures: list[str]
    remediation_steps: list[str]
    automated_check: bool = False
    frequency: str = "daily"  # daily, weekly, monthly, quarterly
    tags: set[str] = field(default_factory=set)
    references: list[str] = field(default_factory=list)


@dataclass
class ComplianceCheck:
    """Result of a compliance rule check."""

    rule_id: str
    status: ComplianceStatus
    timestamp: datetime
    details: str
    evidence: dict[str, Any] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
    risk_score: float = 0.0
    remediation_timeline: Optional[str] = None
    assigned_to: Optional[str] = None


@dataclass
class AuditEvent:
    """Audit trail event."""

    id: str
    timestamp: datetime
    event_type: str
    source: str
    user_id: Optional[str]
    resource: str
    action: str
    outcome: str
    details: dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    compliance_relevant: bool = True


@dataclass
class ComplianceReport:
    """Comprehensive compliance report."""

    id: str
    framework: RegulatoryFramework
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    total_rules: int
    compliant_rules: int
    non_compliant_rules: int
    partially_compliant_rules: int
    unknown_status_rules: int
    overall_score: float
    checks: list[ComplianceCheck]
    recommendations: list[str] = field(default_factory=list)
    executive_summary: str = ""
    risk_assessment: dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceStandard:
    """Complete compliance standard definition."""

    framework: RegulatoryFramework
    version: str
    rules: list[ComplianceRule]
    metadata: dict[str, Any] = field(default_factory=dict)


class AuditTrail:
    """Manages audit trail collection and storage."""

    def __init__(self, monitoring: MonitoringStack):
        self.monitoring = monitoring
        self.logger = logging.getLogger(__name__)
        self.events: list[AuditEvent] = []
        self._event_filters: list[callable] = []

    def log_event(
        self,
        event_type: str,
        source: str,
        resource: str,
        action: str,
        outcome: str,
        user_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditEvent:
        """Log an audit event."""
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            event_type=event_type,
            source=source,
            user_id=user_id,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
        )

        # Apply filters to determine compliance relevance
        for filter_func in self._event_filters:
            if not filter_func(event):
                event.compliance_relevant = False
                break

        self.events.append(event)

        # Emit monitoring metrics
        self.monitoring.increment_counter(
            "audit_events_total",
            {
                "event_type": event_type,
                "source": source,
                "outcome": outcome,
                "compliance_relevant": str(event.compliance_relevant),
            },
        )

        self.logger.info(f"Audit event logged: {event_type} - {resource} - {action} - {outcome}")
        return event

    def add_event_filter(self, filter_func: callable):
        """Add an event filter for compliance relevance."""
        self._event_filters.append(filter_func)

    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[list[str]] = None,
        compliance_relevant_only: bool = False,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """Retrieve audit events with filtering."""
        filtered_events = self.events.copy()

        # Time filtering
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        # Event type filtering
        if event_types:
            filtered_events = [e for e in filtered_events if e.event_type in event_types]

        # Compliance relevance filtering
        if compliance_relevant_only:
            filtered_events = [e for e in filtered_events if e.compliance_relevant]

        # Sort by timestamp descending and apply limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        return filtered_events[:limit]

    def get_compliance_events_for_period(
        self, framework: RegulatoryFramework, start_time: datetime, end_time: datetime
    ) -> list[AuditEvent]:
        """Get compliance-relevant events for a specific period and framework."""
        events = self.get_events(start_time=start_time, end_time=end_time, compliance_relevant_only=True)

        # Filter by framework-specific requirements
        # This would be implemented based on each framework's requirements
        return events


class ComplianceEngine:
    """Main compliance monitoring and checking engine."""

    def __init__(
        self, monitoring: MonitoringStack, audit_trail: AuditTrail, standards: Optional[list[ComplianceStandard]] = None
    ):
        self.monitoring = monitoring
        self.audit_trail = audit_trail
        self.standards = {s.framework: s for s in (standards or [])}
        self.logger = logging.getLogger(__name__)
        self._check_results: dict[str, list[ComplianceCheck]] = {}
        self._automated_checkers: dict[str, callable] = {}

        # Setup default compliance standards
        if not standards:
            self._initialize_default_standards()

    def register_standard(self, standard: ComplianceStandard):
        """Register a compliance standard."""
        self.standards[standard.framework] = standard
        self.logger.info(f"Registered compliance standard: {standard.framework}")

    def register_automated_checker(self, rule_id: str, checker_func: callable):
        """Register an automated compliance checker function."""
        self._automated_checkers[rule_id] = checker_func
        self.logger.info(f"Registered automated checker for rule: {rule_id}")

    async def run_compliance_check(
        self, framework: RegulatoryFramework, rule_id: Optional[str] = None
    ) -> list[ComplianceCheck]:
        """Run compliance checks for a framework or specific rule."""
        if framework not in self.standards:
            raise ValueError(f"Compliance standard not registered: {framework}")

        standard = self.standards[framework]
        rules_to_check = [r for r in standard.rules if not rule_id or r.id == rule_id]

        if not rules_to_check:
            return []

        results = []

        for rule in rules_to_check:
            try:
                with self.monitoring.create_span("compliance_check", framework) as span:
                    span.set_tag("rule_id", rule.id)
                    span.set_tag("framework", framework)

                    check_result = await self._execute_rule_check(rule)
                    results.append(check_result)

                    # Store result
                    if framework not in self._check_results:
                        self._check_results[framework] = []
                    self._check_results[framework].append(check_result)

                    # Emit metrics
                    self.monitoring.increment_counter(
                        "compliance_checks_total",
                        {
                            "framework": framework,
                            "rule_id": rule.id,
                            "status": check_result.status,
                            "severity": rule.severity,
                        },
                    )

                    if check_result.risk_score > 0:
                        self.monitoring.record_gauge(
                            "compliance_risk_score",
                            check_result.risk_score,
                            {"framework": framework, "rule_id": rule.id},
                        )

            except Exception as e:
                self.logger.error(f"Failed to check rule {rule.id}: {str(e)}")

                # Create failed check result
                failed_check = ComplianceCheck(
                    rule_id=rule.id,
                    status=ComplianceStatus.UNKNOWN,
                    timestamp=datetime.now(),
                    details=f"Check failed: {str(e)}",
                    risk_score=5.0,  # High risk for failed checks
                )
                results.append(failed_check)

        self.logger.info(f"Completed {len(results)} compliance checks for {framework}")
        return results

    async def generate_compliance_report(
        self,
        framework: RegulatoryFramework,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> ComplianceReport:
        """Generate comprehensive compliance report."""
        if framework not in self.standards:
            raise ValueError(f"Compliance standard not registered: {framework}")

        period_end = period_end or datetime.now()
        period_start = period_start or (period_end - timedelta(days=30))

        # Run fresh compliance checks
        checks = await self.run_compliance_check(framework)

        # Calculate compliance metrics
        total_rules = len(self.standards[framework].rules)
        compliant_rules = len([c for c in checks if c.status == ComplianceStatus.COMPLIANT])
        non_compliant_rules = len([c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT])
        partially_compliant_rules = len([c for c in checks if c.status == ComplianceStatus.PARTIALLY_COMPLIANT])
        unknown_status_rules = len([c for c in checks if c.status == ComplianceStatus.UNKNOWN])

        # Calculate overall compliance score
        if total_rules > 0:
            overall_score = (compliant_rules + (partially_compliant_rules * 0.5)) / total_rules * 100
        else:
            overall_score = 0.0

        # Generate executive summary
        executive_summary = self._generate_executive_summary(framework, checks, overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(checks)

        # Perform risk assessment
        risk_assessment = self._perform_risk_assessment(checks)

        report = ComplianceReport(
            id=str(uuid.uuid4()),
            framework=framework,
            period_start=period_start,
            period_end=period_end,
            generated_at=datetime.now(),
            total_rules=total_rules,
            compliant_rules=compliant_rules,
            non_compliant_rules=non_compliant_rules,
            partially_compliant_rules=partially_compliant_rules,
            unknown_status_rules=unknown_status_rules,
            overall_score=overall_score,
            checks=checks,
            recommendations=recommendations,
            executive_summary=executive_summary,
            risk_assessment=risk_assessment,
        )

        self.logger.info(f"Generated compliance report for {framework}: {overall_score:.1f}% compliant")
        return report

    async def _execute_rule_check(self, rule: ComplianceRule) -> ComplianceCheck:
        """Execute a compliance rule check."""
        if rule.automated_check and rule.id in self._automated_checkers:
            # Use automated checker
            checker_func = self._automated_checkers[rule.id]
            return await checker_func(rule, self.audit_trail)
        else:
            # Manual check - return unknown status with guidance
            return ComplianceCheck(
                rule_id=rule.id,
                status=ComplianceStatus.UNKNOWN,
                timestamp=datetime.now(),
                details=f"Manual review required. {rule.implementation_guidance}",
                remediation_timeline="Review required within 7 days",
            )

    def _generate_executive_summary(
        self, framework: RegulatoryFramework, checks: list[ComplianceCheck], overall_score: float
    ) -> str:
        """Generate executive summary for compliance report."""
        non_compliant_count = len([c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT])
        high_risk_count = len([c for c in checks if c.risk_score >= 7.0])

        summary_parts = [
            f"Compliance Assessment Summary for {framework.value.upper()}:",
            f"Overall compliance score: {overall_score:.1f}%",
            f"Total controls assessed: {len(checks)}",
        ]

        if overall_score >= 90:
            summary_parts.append("Status: EXCELLENT - Organization demonstrates strong compliance posture.")
        elif overall_score >= 80:
            summary_parts.append("Status: GOOD - Minor gaps identified that should be addressed.")
        elif overall_score >= 70:
            summary_parts.append("Status: ADEQUATE - Several compliance gaps require attention.")
        else:
            summary_parts.append("Status: NEEDS IMPROVEMENT - Significant compliance gaps require immediate attention.")

        if non_compliant_count > 0:
            summary_parts.append(
                f"Critical Finding: {non_compliant_count} non-compliant controls require immediate remediation."
            )

        if high_risk_count > 0:
            summary_parts.append(f"Risk Alert: {high_risk_count} high-risk findings require priority attention.")

        return " ".join(summary_parts)

    def _generate_recommendations(self, checks: list[ComplianceCheck]) -> list[str]:
        """Generate recommendations based on compliance check results."""
        recommendations = []

        # Group by status and analyze patterns
        non_compliant_checks = [c for c in checks if c.status == ComplianceStatus.NON_COMPLIANT]
        high_risk_checks = [c for c in checks if c.risk_score >= 7.0]

        if non_compliant_checks:
            recommendations.append(
                f"Prioritize remediation of {len(non_compliant_checks)} non-compliant controls "
                "to reduce regulatory risk and potential penalties."
            )

        if high_risk_checks:
            recommendations.append(
                f"Address {len(high_risk_checks)} high-risk findings within 30 days "
                "to prevent potential security incidents or compliance violations."
            )

        # Add framework-specific recommendations
        unknown_checks = [c for c in checks if c.status == ComplianceStatus.UNKNOWN]
        if len(unknown_checks) > len(checks) * 0.3:  # More than 30% unknown
            recommendations.append(
                "Implement automated compliance monitoring to reduce manual assessment overhead "
                "and improve continuous compliance visibility."
            )

        if not recommendations:
            recommendations.append(
                "Maintain current compliance posture through regular monitoring and "
                "periodic reassessment of controls."
            )

        return recommendations

    def _perform_risk_assessment(self, checks: list[ComplianceCheck]) -> dict[str, Any]:
        """Perform risk assessment based on compliance results."""
        risk_scores = [c.risk_score for c in checks if c.risk_score > 0]

        if not risk_scores:
            return {"overall_risk": "LOW", "average_risk_score": 0.0}

        avg_risk_score = sum(risk_scores) / len(risk_scores)
        max_risk_score = max(risk_scores)
        critical_findings = len([s for s in risk_scores if s >= 9.0])
        high_findings = len([s for s in risk_scores if 7.0 <= s < 9.0])

        if max_risk_score >= 9.0 or critical_findings > 0:
            overall_risk = "CRITICAL"
        elif max_risk_score >= 7.0 or high_findings > 2:
            overall_risk = "HIGH"
        elif avg_risk_score >= 5.0:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        return {
            "overall_risk": overall_risk,
            "average_risk_score": avg_risk_score,
            "maximum_risk_score": max_risk_score,
            "critical_findings": critical_findings,
            "high_risk_findings": high_findings,
            "total_risk_findings": len(risk_scores),
        }

    def _initialize_default_standards(self):
        """Initialize default compliance standards."""
        # GDPR Standard
        gdpr_rules = [
            ComplianceRule(
                id="gdpr_art_25",
                framework=RegulatoryFramework.GDPR,
                category="privacy_by_design",
                title="Data Protection by Design and by Default",
                description="Implement appropriate technical and organisational measures to ensure data protection principles are integrated into processing activities.",
                severity="high",
                requirement="Article 25 - Data protection by design and by default",
                control_objective="Ensure privacy protection is built into systems and processes from the ground up.",
                implementation_guidance="Implement privacy controls at the system design level, use data minimization, and ensure default settings protect privacy.",
                test_procedures=[
                    "Review system architecture for privacy controls",
                    "Verify data minimization practices",
                    "Check default privacy settings",
                ],
                remediation_steps=[
                    "Conduct privacy impact assessment",
                    "Implement technical privacy controls",
                    "Update system documentation",
                ],
                automated_check=True,
                tags={"privacy", "design", "technical_measures"},
            ),
            ComplianceRule(
                id="gdpr_art_30",
                framework=RegulatoryFramework.GDPR,
                category="records_of_processing",
                title="Records of Processing Activities",
                description="Maintain records of all processing activities under responsibility of the controller.",
                severity="medium",
                requirement="Article 30 - Records of processing activities",
                control_objective="Maintain comprehensive records of all data processing activities.",
                implementation_guidance="Document all processing activities, legal basis, data categories, and retention periods.",
                test_procedures=[
                    "Review processing activity records",
                    "Verify completeness of documentation",
                    "Check regular updates to records",
                ],
                remediation_steps=[
                    "Create processing activity inventory",
                    "Document legal basis for each activity",
                    "Establish regular review process",
                ],
                automated_check=False,
                tags={"documentation", "processing_records"},
            ),
        ]

        # SOC 2 Standard
        soc2_rules = [
            ComplianceRule(
                id="soc2_cc6_1",
                framework=RegulatoryFramework.SOC2,
                category="logical_physical_access",
                title="Logical and Physical Access Controls",
                description="Implement controls to restrict logical and physical access to system resources.",
                severity="high",
                requirement="CC6.1 - Logical and Physical Access Controls",
                control_objective="Restrict access to system resources to authorized individuals.",
                implementation_guidance="Implement role-based access controls, multi-factor authentication, and regular access reviews.",
                test_procedures=[
                    "Test access control implementation",
                    "Review user access permissions",
                    "Verify authentication mechanisms",
                ],
                remediation_steps=[
                    "Implement RBAC system",
                    "Deploy MFA for all users",
                    "Conduct quarterly access reviews",
                ],
                automated_check=True,
                tags={"access_control", "authentication", "authorization"},
            )
        ]

        # PCI DSS Standard
        pci_rules = [
            ComplianceRule(
                id="pci_req_3",
                framework=RegulatoryFramework.PCI_DSS,
                category="cardholder_data_protection",
                title="Protect Stored Cardholder Data",
                description="Protect stored cardholder data through strong cryptography and security management.",
                severity="critical",
                requirement="Requirement 3 - Protect stored cardholder data",
                control_objective="Ensure cardholder data is protected with appropriate encryption.",
                implementation_guidance="Encrypt all stored cardholder data, implement key management, and minimize data retention.",
                test_procedures=[
                    "Verify encryption implementation",
                    "Test key management procedures",
                    "Review data retention policies",
                ],
                remediation_steps=[
                    "Implement strong encryption",
                    "Deploy key management system",
                    "Update data retention policies",
                ],
                automated_check=True,
                tags={"encryption", "cardholder_data", "key_management"},
            )
        ]

        # Register default standards
        self.register_standard(ComplianceStandard(framework=RegulatoryFramework.GDPR, version="2018", rules=gdpr_rules))

        self.register_standard(ComplianceStandard(framework=RegulatoryFramework.SOC2, version="2017", rules=soc2_rules))

        self.register_standard(
            ComplianceStandard(framework=RegulatoryFramework.PCI_DSS, version="3.2.1", rules=pci_rules)
        )


# Automated Compliance Checkers


async def gdpr_data_protection_by_design_checker(rule: ComplianceRule, audit_trail: AuditTrail) -> ComplianceCheck:
    """Automated checker for GDPR Article 25 - Data Protection by Design."""
    findings = []
    risk_score = 0.0

    # Check for privacy controls in recent system changes
    recent_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=30),
        event_types=["system_deployment", "configuration_change", "data_schema_change"],
    )

    privacy_review_events = [
        e for e in recent_events if "privacy_review" in e.details or "privacy_impact_assessment" in e.details
    ]

    if len(recent_events) > 0 and len(privacy_review_events) == 0:
        findings.append("Recent system changes detected without documented privacy review")
        risk_score += 3.0

    # Check for data minimization evidence
    data_access_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=7), event_types=["data_access", "data_export"]
    )

    excessive_access_events = [
        e
        for e in data_access_events
        if e.details.get("record_count", 0) > 10000  # Large data exports
    ]

    if len(excessive_access_events) > 5:
        findings.append("Multiple large data access events may indicate lack of data minimization")
        risk_score += 2.0

    # Determine compliance status
    if risk_score == 0:
        status = ComplianceStatus.COMPLIANT
        details = "Privacy by design controls appear to be functioning correctly."
    elif risk_score <= 3:
        status = ComplianceStatus.PARTIALLY_COMPLIANT
        details = "Some privacy by design gaps identified that should be addressed."
    else:
        status = ComplianceStatus.NON_COMPLIANT
        details = "Significant privacy by design gaps require immediate attention."

    return ComplianceCheck(
        rule_id=rule.id,
        status=status,
        timestamp=datetime.now(),
        details=details,
        findings=findings,
        risk_score=risk_score,
        remediation_timeline="30 days" if status != ComplianceStatus.COMPLIANT else None,
    )


async def soc2_access_control_checker(rule: ComplianceRule, audit_trail: AuditTrail) -> ComplianceCheck:
    """Automated checker for SOC 2 CC6.1 - Logical and Physical Access Controls."""
    findings = []
    risk_score = 0.0

    # Check for failed authentication attempts
    auth_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=7), event_types=["authentication", "authorization"]
    )

    failed_auth_events = [e for e in auth_events if e.outcome == "failure"]
    successful_auth_events = [e for e in auth_events if e.outcome == "success"]

    if len(failed_auth_events) > len(successful_auth_events) * 0.1:  # >10% failure rate
        findings.append("High authentication failure rate detected")
        risk_score += 4.0

    # Check for privileged access activities
    privileged_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=30), event_types=["admin_access", "privileged_operation"]
    )

    unreviewed_privileged = [
        e for e in privileged_events if "reviewed" not in e.details and "approved" not in e.details
    ]

    if len(unreviewed_privileged) > 0:
        findings.append(f"{len(unreviewed_privileged)} privileged operations without documented review")
        risk_score += 3.0

    # Check for access without MFA
    auth_without_mfa = [e for e in successful_auth_events if not e.details.get("mfa_used", False)]

    if len(auth_without_mfa) > len(successful_auth_events) * 0.05:  # >5% without MFA
        findings.append("Authentication events without MFA detected")
        risk_score += 5.0

    # Determine compliance status
    if risk_score == 0:
        status = ComplianceStatus.COMPLIANT
        details = "Access controls are functioning effectively."
    elif risk_score <= 5:
        status = ComplianceStatus.PARTIALLY_COMPLIANT
        details = "Access control improvements needed to meet SOC 2 requirements."
    else:
        status = ComplianceStatus.NON_COMPLIANT
        details = "Access control deficiencies present significant compliance risk."

    return ComplianceCheck(
        rule_id=rule.id,
        status=status,
        timestamp=datetime.now(),
        details=details,
        findings=findings,
        risk_score=risk_score,
        remediation_timeline="14 days" if status != ComplianceStatus.COMPLIANT else None,
    )


async def pci_encryption_checker(rule: ComplianceRule, audit_trail: AuditTrail) -> ComplianceCheck:
    """Automated checker for PCI DSS Requirement 3 - Protect Stored Cardholder Data."""
    findings = []
    risk_score = 0.0

    # Check for unencrypted data access
    data_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=7), event_types=["data_access", "database_query", "file_access"]
    )

    unencrypted_access = [
        e
        for e in data_events
        if ("cardholder" in str(e.details).lower() or "payment" in str(e.details).lower())
        and not e.details.get("encrypted", False)
    ]

    if len(unencrypted_access) > 0:
        findings.append(f"{len(unencrypted_access)} unencrypted cardholder data access events")
        risk_score += 8.0  # Critical for PCI

    # Check for key management events
    key_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=30), event_types=["key_generation", "key_rotation", "key_access"]
    )

    if len(key_events) == 0:
        findings.append("No key management activities detected in the past 30 days")
        risk_score += 4.0

    # Check for data retention violations
    retention_events = audit_trail.get_events(
        start_time=datetime.now() - timedelta(days=30), event_types=["data_deletion", "data_archival"]
    )

    if len(retention_events) == 0:
        findings.append("No data retention/deletion activities detected")
        risk_score += 2.0

    # Determine compliance status
    if risk_score == 0:
        status = ComplianceStatus.COMPLIANT
        details = "Cardholder data protection controls are functioning correctly."
    elif risk_score <= 5:
        status = ComplianceStatus.PARTIALLY_COMPLIANT
        details = "Some cardholder data protection improvements needed."
    else:
        status = ComplianceStatus.NON_COMPLIANT
        details = "Critical cardholder data protection deficiencies require immediate remediation."

    return ComplianceCheck(
        rule_id=rule.id,
        status=status,
        timestamp=datetime.now(),
        details=details,
        findings=findings,
        risk_score=risk_score,
        remediation_timeline="7 days" if status == ComplianceStatus.NON_COMPLIANT else "30 days",
    )


class ComplianceEngineFactory:
    """Factory for creating compliance engine instances."""

    @staticmethod
    def create_comprehensive_engine(monitoring: MonitoringStack) -> ComplianceEngine:
        """Create comprehensive compliance engine with all frameworks."""
        audit_trail = AuditTrail(monitoring)
        engine = ComplianceEngine(monitoring, audit_trail)

        # Register automated checkers
        engine.register_automated_checker("gdpr_art_25", gdpr_data_protection_by_design_checker)
        engine.register_automated_checker("soc2_cc6_1", soc2_access_control_checker)
        engine.register_automated_checker("pci_req_3", pci_encryption_checker)

        # Add audit event filters for compliance relevance
        audit_trail.add_event_filter(lambda event: _is_compliance_relevant_event(event))

        return engine

    @staticmethod
    def create_gdpr_engine(monitoring: MonitoringStack) -> ComplianceEngine:
        """Create GDPR-focused compliance engine."""
        audit_trail = AuditTrail(monitoring)

        # Create GDPR-specific standard with more comprehensive rules
        gdpr_standard = _create_comprehensive_gdpr_standard()

        engine = ComplianceEngine(monitoring, audit_trail, [gdpr_standard])
        engine.register_automated_checker("gdpr_art_25", gdpr_data_protection_by_design_checker)

        return engine

    @staticmethod
    def create_soc2_engine(monitoring: MonitoringStack) -> ComplianceEngine:
        """Create SOC 2-focused compliance engine."""
        audit_trail = AuditTrail(monitoring)

        # Create SOC 2-specific standard
        soc2_standard = _create_comprehensive_soc2_standard()

        engine = ComplianceEngine(monitoring, audit_trail, [soc2_standard])
        engine.register_automated_checker("soc2_cc6_1", soc2_access_control_checker)

        return engine


def _is_compliance_relevant_event(event: AuditEvent) -> bool:
    """Determine if an audit event is relevant for compliance monitoring."""
    # Events that are always compliance-relevant
    compliance_event_types = {
        "authentication",
        "authorization",
        "data_access",
        "data_export",
        "data_deletion",
        "admin_access",
        "privileged_operation",
        "system_deployment",
        "configuration_change",
        "key_management",
        "privacy_review",
        "audit_log_access",
    }

    if event.event_type in compliance_event_types:
        return True

    # Events involving sensitive data
    sensitive_keywords = ["personal", "cardholder", "payment", "health", "financial"]
    event_text = f"{event.resource} {event.action} {json.dumps(event.details)}".lower()

    if any(keyword in event_text for keyword in sensitive_keywords):
        return True

    # Failed operations are generally compliance-relevant
    if event.outcome in ["failure", "denied", "blocked"]:
        return True

    return False


def _create_comprehensive_gdpr_standard() -> ComplianceStandard:
    """Create comprehensive GDPR compliance standard."""
    # This would include all GDPR articles and requirements
    # Simplified version for demonstration
    return ComplianceStandard(
        framework=RegulatoryFramework.GDPR,
        version="2018",
        rules=[
            # Article 25 already defined above
            # Add more comprehensive GDPR rules here
        ],
    )


def _create_comprehensive_soc2_standard() -> ComplianceStandard:
    """Create comprehensive SOC 2 compliance standard."""
    # This would include all SOC 2 trust service criteria
    # Simplified version for demonstration
    return ComplianceStandard(
        framework=RegulatoryFramework.SOC2,
        version="2017",
        rules=[
            # CC6.1 already defined above
            # Add more comprehensive SOC 2 rules here
        ],
    )


# Convenience function for easy setup
async def setup_compliance_monitoring(
    monitoring: MonitoringStack, frameworks: Optional[list[RegulatoryFramework]] = None
) -> ComplianceEngine:
    """Setup compliance monitoring with specified frameworks."""
    factory = ComplianceEngineFactory()

    if not frameworks:
        # Default to comprehensive engine
        return factory.create_comprehensive_engine(monitoring)

    if RegulatoryFramework.GDPR in frameworks and len(frameworks) == 1:
        return factory.create_gdpr_engine(monitoring)
    elif RegulatoryFramework.SOC2 in frameworks and len(frameworks) == 1:
        return factory.create_soc2_engine(monitoring)
    else:
        return factory.create_comprehensive_engine(monitoring)
