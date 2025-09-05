"""
Shared regulatory reporting system with DRY patterns for automated compliance reporting.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac.communications.events import EventBus
from dotmac.core.cache import create_cache_service

from ..schemas.compliance_schemas import (
    ComplianceFramework,
    ComplianceMetrics,
    ComplianceReportRequest,
    ComplianceStatus,
    RegulatoryReport,
    ReportFrequency,
)

logger = logging.getLogger(__name__)


@dataclass
class ReportTemplate:
    """Regulatory report template definition."""

    template_id: str
    name: str
    framework: ComplianceFramework
    report_type: str
    sections: list[dict[str, Any]]
    required_data: list[str]
    output_formats: list[str] = field(default_factory=lambda: ["pdf", "json"])


@dataclass
class ReportingConfig:
    """Configuration for regulatory reporting."""

    enabled_frameworks: list[ComplianceFramework]
    output_directory: str = "/tmp/compliance_reports"
    default_format: str = "pdf"
    templates_directory: Optional[str] = None

    # Automation settings
    auto_generate_enabled: bool = True
    max_concurrent_reports: int = 5
    report_timeout_minutes: int = 30

    # Distribution settings
    email_notifications: bool = True
    webhook_notifications: bool = False

    # Retention settings
    report_retention_days: int = 2555  # 7 years
    archive_old_reports: bool = True

    # Security settings
    encrypt_reports: bool = True
    digital_signatures: bool = False


class RegulatoryReporter:
    """
    Centralized regulatory reporting with DRY patterns.
    Eliminates duplicate reporting code across platforms.
    """

    def __init__(
        self,
        config: ReportingConfig,
        compliance_manager,  # ComplianceManager instance
        tenant_id: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        cache_service=None,
    ):
        self.config = config
        self.compliance_manager = compliance_manager
        self.tenant_id = tenant_id
        self.event_bus = event_bus
        self.cache_service = cache_service or create_cache_service()

        # Report templates and generated reports
        self._templates: dict[str, ReportTemplate] = {}
        self._generated_reports: list[RegulatoryReport] = []
        self._report_jobs: dict[str, dict[str, Any]] = {}

        # Load default templates
        self._load_default_templates()

    async def initialize(self) -> bool:
        """Initialize regulatory reporter."""
        try:
            if self.cache_service:
                await self.cache_service.initialize()

            # Load report templates for enabled frameworks
            for framework in self.config.enabled_frameworks:
                await self._load_framework_templates(framework)

            logger.info(f"✅ Regulatory Reporter initialized with {len(self._templates)} templates")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Regulatory Reporter: {e}")
            return False

    @standard_exception_handler
    async def generate_report(
        self,
        request: ComplianceReportRequest,
        user_id: Optional[UUID] = None,
    ) -> RegulatoryReport:
        """Generate a regulatory compliance report."""

        # Find appropriate template
        template = await self._find_report_template(request.framework, request.report_type)

        if not template:
            raise ValueError(f"No template found for {request.framework.value} {request.report_type}")

        # Collect compliance data
        compliance_data = await self._collect_compliance_data(request, template)

        # Generate report content
        report_content = await self._generate_report_content(template, compliance_data, request)

        # Create report record
        report = RegulatoryReport(
            report_id=uuid4(),
            tenant_id=self.tenant_id,
            name=f"{request.framework.value} {request.report_type} Report",
            framework=request.framework,
            report_type=request.report_type,
            frequency=ReportFrequency.ON_DEMAND,
            period_start=request.period_start,
            period_end=request.period_end,
            executive_summary=report_content["executive_summary"],
            compliance_status=report_content["overall_status"],
            compliance_score=report_content["overall_score"],
            sections=report_content["sections"],
            findings=report_content["findings"],
            recommendations=report_content["recommendations"],
            remediation_plan=report_content["remediation_plan"],
            generated_by=user_id or uuid4(),
        )

        # Store report
        self._generated_reports.append(report)

        # Cache report
        if self.cache_service:
            cache_key = f"regulatory_report:{self.tenant_id}:{report.report_id}"
            await self.cache_service.set(
                cache_key,
                report.model_dump(),
                tenant_id=self.tenant_id,
                expire=3600 * 24,  # 24 hours
            )

        # Export report if needed
        if request.format != "json":
            export_path = await self._export_report(report, request.format)
            # Store export path in report metadata
            report.sections.append({"type": "metadata", "export_path": export_path, "format": request.format})

        # Publish report generated event
        if self.event_bus:
            await self.event_bus.publish(
                "regulatory.report_generated",
                {
                    "report_id": str(report.report_id),
                    "framework": report.framework.value,
                    "report_type": report.report_type,
                    "status": report.compliance_status.value,
                    "score": report.compliance_score,
                    "tenant_id": report.tenant_id,
                },
            )

        return report

    @standard_exception_handler
    async def schedule_report(
        self,
        framework: ComplianceFramework,
        report_type: str,
        frequency: ReportFrequency,
        recipients: list[str],
        user_id: Optional[UUID] = None,
    ) -> str:
        """Schedule automatic report generation."""

        schedule_id = str(uuid4())

        # Calculate next run time
        next_run = self._calculate_next_run(frequency)

        # Create schedule record
        schedule = {
            "schedule_id": schedule_id,
            "framework": framework.value,
            "report_type": report_type,
            "frequency": frequency.value,
            "recipients": recipients,
            "next_run": next_run.isoformat(),
            "is_active": True,
            "created_by": str(user_id) if user_id else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store schedule (in production, this would be in database)
        if self.cache_service:
            cache_key = f"report_schedule:{self.tenant_id}:{schedule_id}"
            await self.cache_service.set(
                cache_key,
                schedule,
                tenant_id=self.tenant_id,
                expire=None,  # No expiration for schedules
            )

        logger.info(f"Scheduled {frequency.value} {framework.value} {report_type} report")

        return schedule_id

    @standard_exception_handler
    async def get_compliance_dashboard_data(
        self,
        frameworks: Optional[list[ComplianceFramework]] = None,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Get compliance dashboard data for multiple frameworks."""

        if not frameworks:
            frameworks = self.config.enabled_frameworks

        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_end = datetime.now(timezone.utc)

        dashboard_data = {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days": period_days,
            },
            "frameworks": {},
            "overall": {
                "average_score": 0.0,
                "total_checks": 0,
                "total_issues": 0,
                "critical_alerts": 0,
            },
        }

        total_scores = []
        total_checks = 0
        total_issues = 0
        critical_alerts = 0

        # Collect metrics for each framework
        for framework in frameworks:
            metrics = await self.compliance_manager.get_compliance_metrics(framework, period_start, period_end)

            alerts = await self.compliance_manager.get_active_alerts(framework)
            critical_framework_alerts = [a for a in alerts if a.severity.value == "critical"]

            framework_data = {
                "framework": framework.value,
                "score": metrics.overall_score,
                "status": self._determine_framework_status(metrics.overall_score),
                "checks": {
                    "total": metrics.total_checks,
                    "passed": metrics.passed_checks,
                    "failed": metrics.failed_checks,
                },
                "issues": {
                    "critical": metrics.critical_issues,
                    "high": metrics.high_risk_issues,
                    "medium": metrics.medium_risk_issues,
                    "low": metrics.low_risk_issues,
                },
                "alerts": len(alerts),
                "critical_alerts": len(critical_framework_alerts),
                "trend": metrics.score_trend,
            }

            dashboard_data["frameworks"][framework.value] = framework_data

            # Aggregate overall metrics
            if metrics.overall_score > 0:
                total_scores.append(metrics.overall_score)
            total_checks += metrics.total_checks
            total_issues += (
                metrics.critical_issues
                + metrics.high_risk_issues
                + metrics.medium_risk_issues
                + metrics.low_risk_issues
            )
            critical_alerts += len(critical_framework_alerts)

        # Calculate overall metrics
        dashboard_data["overall"]["average_score"] = sum(total_scores) / len(total_scores) if total_scores else 0.0
        dashboard_data["overall"]["total_checks"] = total_checks
        dashboard_data["overall"]["total_issues"] = total_issues
        dashboard_data["overall"]["critical_alerts"] = critical_alerts

        return dashboard_data

    async def _load_default_templates(self):
        """Load default report templates."""
        # This would typically load from configuration files or database
        pass

    async def _load_framework_templates(self, framework: ComplianceFramework):
        """Load report templates for a specific framework."""

        if framework == ComplianceFramework.SOC2:
            await self._load_soc2_templates()
        elif framework == ComplianceFramework.GDPR:
            await self._load_gdpr_templates()
        elif framework == ComplianceFramework.HIPAA:
            await self._load_hipaa_templates()

    async def _load_soc2_templates(self):
        """Load SOC2 report templates."""

        template = ReportTemplate(
            template_id="soc2_type2",
            name="SOC 2 Type II Report",
            framework=ComplianceFramework.SOC2,
            report_type="type2",
            sections=[
                {"id": "executive_summary", "title": "Executive Summary", "required": True},
                {"id": "scope", "title": "Scope and Objectives", "required": True},
                {"id": "controls", "title": "Control Environment", "required": True},
                {"id": "testing", "title": "Testing Results", "required": True},
                {"id": "findings", "title": "Findings and Recommendations", "required": True},
            ],
            required_data=["access_controls", "security_monitoring", "change_management"],
        )

        self._templates[template.template_id] = template

    async def _load_gdpr_templates(self):
        """Load GDPR report templates."""

        template = ReportTemplate(
            template_id="gdpr_compliance",
            name="GDPR Compliance Report",
            framework=ComplianceFramework.GDPR,
            report_type="compliance",
            sections=[
                {"id": "executive_summary", "title": "Executive Summary", "required": True},
                {"id": "data_processing", "title": "Data Processing Activities", "required": True},
                {"id": "consent", "title": "Consent Management", "required": True},
                {"id": "rights", "title": "Data Subject Rights", "required": True},
                {"id": "breach", "title": "Data Breach Procedures", "required": True},
            ],
            required_data=["consent_records", "data_inventory", "breach_logs"],
        )

        self._templates[template.template_id] = template

    async def _load_hipaa_templates(self):
        """Load HIPAA report templates."""

        template = ReportTemplate(
            template_id="hipaa_assessment",
            name="HIPAA Risk Assessment Report",
            framework=ComplianceFramework.HIPAA,
            report_type="risk_assessment",
            sections=[
                {"id": "executive_summary", "title": "Executive Summary", "required": True},
                {"id": "phi_inventory", "title": "PHI Inventory", "required": True},
                {"id": "risk_analysis", "title": "Risk Analysis", "required": True},
                {"id": "safeguards", "title": "Administrative Safeguards", "required": True},
                {"id": "technical", "title": "Technical Safeguards", "required": True},
            ],
            required_data=["phi_access_logs", "security_controls", "workforce_training"],
        )

        self._templates[template.template_id] = template

    async def _find_report_template(
        self,
        framework: ComplianceFramework,
        report_type: str,
    ) -> Optional[ReportTemplate]:
        """Find appropriate report template."""

        for template in self._templates.values():
            if template.framework == framework and template.report_type == report_type:
                return template

        return None

    async def _collect_compliance_data(
        self,
        request: ComplianceReportRequest,
        template: ReportTemplate,
    ) -> dict[str, Any]:
        """Collect compliance data needed for report generation."""

        data = {}

        # Get compliance metrics
        metrics = await self.compliance_manager.get_compliance_metrics(
            request.framework, request.period_start, request.period_end
        )
        data["metrics"] = metrics

        # Get compliance alerts
        alerts = await self.compliance_manager.get_active_alerts(request.framework)
        data["alerts"] = alerts

        # Get checks performed in period
        # In production, this would query the database
        data["checks"] = []

        # Collect template-specific data
        for required_data in template.required_data:
            data[required_data] = await self._collect_specific_data(required_data, request, metrics)

        return data

    async def _collect_specific_data(
        self,
        data_type: str,
        request: ComplianceReportRequest,
        metrics: ComplianceMetrics,
    ) -> Any:
        """Collect specific type of compliance data."""

        # Simplified data collection - production would have extensive data gathering
        if data_type == "access_controls":
            return {
                "total_users": 100,
                "privileged_users": 10,
                "access_reviews_completed": 95,
                "failed_logins": 5,
            }
        elif data_type == "security_monitoring":
            return {
                "incidents_detected": 3,
                "incidents_resolved": 3,
                "mean_detection_time": "15 minutes",
                "mean_response_time": "30 minutes",
            }
        elif data_type == "consent_records":
            return {
                "total_consents": 1000,
                "active_consents": 950,
                "withdrawn_consents": 50,
                "consent_rate": 95.0,
            }

        return {}

    async def _generate_report_content(
        self,
        template: ReportTemplate,
        compliance_data: dict[str, Any],
        request: ComplianceReportRequest,
    ) -> dict[str, Any]:
        """Generate report content from template and data."""

        metrics: ComplianceMetrics = compliance_data["metrics"]

        # Generate executive summary
        executive_summary = await self._generate_executive_summary(template, metrics, compliance_data)

        # Determine overall status
        overall_status = self._determine_compliance_status(metrics.overall_score)

        # Generate sections
        sections = []
        for section_def in template.sections:
            section_content = await self._generate_section_content(section_def, compliance_data, request)
            sections.append(section_content)

        # Generate findings
        findings = await self._generate_findings(compliance_data, template.framework)

        # Generate recommendations
        recommendations = await self._generate_recommendations(compliance_data, template.framework)

        # Generate remediation plan
        remediation_plan = await self._generate_remediation_plan(compliance_data, recommendations)

        return {
            "executive_summary": executive_summary,
            "overall_status": overall_status,
            "overall_score": metrics.overall_score,
            "sections": sections,
            "findings": findings,
            "recommendations": recommendations,
            "remediation_plan": remediation_plan,
        }

    async def _generate_executive_summary(
        self,
        template: ReportTemplate,
        metrics: ComplianceMetrics,
        data: dict[str, Any],
    ) -> str:
        """Generate executive summary for the report."""

        framework_name = template.framework.value.upper()

        summary = f"""
Executive Summary - {framework_name} Compliance Report

This report presents the {framework_name} compliance assessment for the period from
{metrics.period_start.strftime('%Y-%m-%d')} to {metrics.period_end.strftime('%Y-%m-%d')}.

Overall Compliance Score: {metrics.overall_score:.1f}%
Total Checks Performed: {metrics.total_checks}
Checks Passed: {metrics.passed_checks}
Issues Identified: {metrics.critical_issues + metrics.high_risk_issues + metrics.medium_risk_issues + metrics.low_risk_issues}

Key Findings:
- Critical Issues: {metrics.critical_issues}
- High Risk Issues: {metrics.high_risk_issues}
- Medium Risk Issues: {metrics.medium_risk_issues}
- Low Risk Issues: {metrics.low_risk_issues}

The organization demonstrates {"strong" if metrics.overall_score >= 85 else "adequate" if metrics.overall_score >= 70 else "needs improvement"}
compliance with {framework_name} requirements based on the assessment conducted.
        """.strip()

        return summary

    async def _generate_section_content(
        self,
        section_def: dict[str, Any],
        data: dict[str, Any],
        request: ComplianceReportRequest,
    ) -> dict[str, Any]:
        """Generate content for a report section."""

        section_id = section_def["id"]

        if section_id == "scope":
            return {
                "id": section_id,
                "title": section_def["title"],
                "content": f"This assessment covers {request.framework.value} compliance for the period from {request.period_start.strftime('%Y-%m-%d')} to {request.period_end.strftime('%Y-%m-%d')}.",
                "subsections": [],
            }
        elif section_id == "controls":
            return {
                "id": section_id,
                "title": section_def["title"],
                "content": "Control environment assessment results and findings.",
                "subsections": [
                    {"title": "Access Controls", "content": "Access control implementation status"},
                    {"title": "Security Controls", "content": "Security control effectiveness"},
                ],
            }

        # Default section content
        return {
            "id": section_id,
            "title": section_def["title"],
            "content": f"Content for {section_def['title']} section.",
            "subsections": [],
        }

    async def _generate_findings(
        self,
        data: dict[str, Any],
        framework: ComplianceFramework,
    ) -> list[dict[str, Any]]:
        """Generate compliance findings."""

        findings = []
        metrics: ComplianceMetrics = data["metrics"]

        if metrics.critical_issues > 0:
            findings.append(
                {
                    "severity": "critical",
                    "title": "Critical Compliance Issues Identified",
                    "description": f"{metrics.critical_issues} critical compliance issues require immediate attention.",
                    "impact": "High risk of regulatory penalties and data exposure",
                    "affected_controls": ["access_control", "data_protection"],
                }
            )

        if metrics.high_risk_issues > 0:
            findings.append(
                {
                    "severity": "high",
                    "title": "High Risk Issues",
                    "description": f"{metrics.high_risk_issues} high risk issues identified.",
                    "impact": "Moderate risk to compliance posture",
                    "affected_controls": ["monitoring", "incident_response"],
                }
            )

        return findings

    async def _generate_recommendations(
        self,
        data: dict[str, Any],
        framework: ComplianceFramework,
    ) -> list[dict[str, Any]]:
        """Generate compliance recommendations."""

        recommendations = []
        metrics: ComplianceMetrics = data["metrics"]

        if metrics.overall_score < 85:
            recommendations.append(
                {
                    "priority": "high",
                    "title": "Enhance Overall Compliance Program",
                    "description": "Implement comprehensive compliance improvement program",
                    "timeline": "3 months",
                    "estimated_effort": "high",
                    "expected_impact": "Improve compliance score by 10-15%",
                }
            )

        if metrics.critical_issues > 0:
            recommendations.append(
                {
                    "priority": "critical",
                    "title": "Address Critical Issues Immediately",
                    "description": "Resolve all critical compliance issues within 30 days",
                    "timeline": "30 days",
                    "estimated_effort": "high",
                    "expected_impact": "Eliminate critical compliance risks",
                }
            )

        return recommendations

    async def _generate_remediation_plan(
        self,
        data: dict[str, Any],
        recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Generate remediation plan based on findings and recommendations."""

        plan = []

        for i, recommendation in enumerate(recommendations, 1):
            plan_item = {
                "phase": i,
                "title": recommendation["title"],
                "description": recommendation["description"],
                "timeline": recommendation["timeline"],
                "owner": "Compliance Team",
                "status": "planned",
                "tasks": [
                    "Assess current state",
                    "Develop implementation plan",
                    "Execute remediation",
                    "Validate effectiveness",
                    "Update documentation",
                ],
            }
            plan.append(plan_item)

        return plan

    def _determine_compliance_status(self, score: float) -> ComplianceStatus:
        """Determine compliance status based on score."""

        if score >= 95:
            return ComplianceStatus.COMPLIANT
        elif score >= 85:
            return ComplianceStatus.PARTIAL_COMPLIANCE
        elif score >= 70:
            return ComplianceStatus.REMEDIATION_REQUIRED
        else:
            return ComplianceStatus.NON_COMPLIANT

    def _determine_framework_status(self, score: float) -> str:
        """Determine framework status string based on score."""

        if score >= 95:
            return "excellent"
        elif score >= 85:
            return "good"
        elif score >= 70:
            return "needs_improvement"
        else:
            return "poor"

    async def _export_report(self, report: RegulatoryReport, format: str) -> str:
        """Export report to specified format."""

        # Simplified export - production would have full formatting
        export_filename = f"{report.framework.value}_{report.report_type}_{report.report_id}.{format}"
        export_path = f"{self.config.output_directory}/{export_filename}"

        if format == "json":
            with open(export_path, "w") as f:
                json.dump(report.model_dump(), f, indent=2, default=str)
        elif format == "pdf":
            # PDF generation would be implemented here
            logger.info(f"PDF export placeholder for {export_path}")

        return export_path

    def _calculate_next_run(self, frequency: ReportFrequency) -> datetime:
        """Calculate next run time for scheduled report."""

        now = datetime.now(timezone.utc)

        if frequency == ReportFrequency.DAILY:
            return now + timedelta(days=1)
        elif frequency == ReportFrequency.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == ReportFrequency.MONTHLY:
            return now + timedelta(days=30)
        elif frequency == ReportFrequency.QUARTERLY:
            return now + timedelta(days=90)
        elif frequency == ReportFrequency.ANNUALLY:
            return now + timedelta(days=365)
        else:
            return now + timedelta(hours=1)  # Default

    async def health_check(self) -> dict[str, Any]:
        """Health check for regulatory reporter."""
        try:
            return {
                "status": "healthy",
                "templates_loaded": len(self._templates),
                "reports_generated": len(self._generated_reports),
                "active_jobs": len(self._report_jobs),
                "frameworks": [f.value for f in self.config.enabled_frameworks],
                "cache_available": self.cache_service is not None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Factory function
async def create_regulatory_reporter(
    config: ReportingConfig,
    compliance_manager,
    tenant_id: Optional[str] = None,
    event_bus: Optional[EventBus] = None,
    cache_service=None,
) -> RegulatoryReporter:
    """Create and initialize regulatory reporter."""

    reporter = RegulatoryReporter(
        config=config,
        compliance_manager=compliance_manager,
        tenant_id=tenant_id,
        event_bus=event_bus,
        cache_service=cache_service,
    )
    await reporter.initialize()
    return reporter
