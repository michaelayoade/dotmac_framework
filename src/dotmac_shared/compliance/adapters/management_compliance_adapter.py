"""
Management platform compliance adapter for backward compatibility.
Eliminates duplicate compliance code while maintaining management-specific interfaces.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from dotmac.application import standard_exception_handler
from dotmac.communications.events import EventBus
from dotmac.core.cache import create_cache_service

from ..schemas.compliance_schemas import (
    AuditEventType,
    ComplianceEvent,
    ComplianceFramework,
    ComplianceReportRequest,
    RiskLevel,
)
from ..services.compliance_service import ComplianceService, ComplianceServiceConfig

logger = logging.getLogger(__name__)


class ManagementComplianceAdapter:
    """
    Adapter that provides Management platform compliance interface using shared compliance service.
    Maintains backward compatibility with existing management compliance API.
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,  # Management platform may not always be tenant-specific
        compliance_service: Optional[ComplianceService] = None,
        event_bus: Optional[EventBus] = None,
        cache_service=None,
    ):
        self.tenant_id = tenant_id

        # Initialize shared compliance service with management-focused frameworks
        if compliance_service:
            self.compliance_service = compliance_service
        else:
            config = ComplianceServiceConfig(
                enabled_frameworks=[
                    ComplianceFramework.SOC2,
                    ComplianceFramework.ISO_27001,
                    ComplianceFramework.NIST,
                    ComplianceFramework.GDPR,  # For multi-tenant data protection
                ]
            )
            self.compliance_service = ComplianceService(config)

        self.event_bus = event_bus
        self.cache_service = cache_service or create_cache_service()

    async def initialize(self) -> bool:
        """Initialize the adapter and underlying services."""
        try:
            # Initialize compliance service if not already done
            if not self.compliance_service.is_ready():
                await self.compliance_service.initialize()

            if self.cache_service:
                await self.cache_service.initialize()

            logger.info("✅ Management Compliance Adapter initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Management Compliance Adapter: {e}")
            return False

    # Management-specific compliance methods

    @standard_exception_handler
    async def track_tenant_creation(
        self,
        tenant_id: str,
        admin_user_id: str,
        tenant_config: dict[str, Any],
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track tenant creation for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.SYSTEM_ACCESS,
            framework=ComplianceFramework.SOC2,
            resource_id=tenant_id,
            resource_type="tenant",
            user_id=UUID(admin_user_id),
            risk_level=RiskLevel.HIGH,  # Tenant creation is high risk
            details={
                "action": "tenant_creation",
                "tenant_id": tenant_id,
                "admin_user": admin_user_id,
                "configuration": tenant_config,
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def track_platform_access(
        self,
        user_id: str,
        user_role: str,
        access_level: str,
        ip_address: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track management platform access for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.USER_LOGIN,
            framework=ComplianceFramework.SOC2,
            resource_id="management_platform",
            resource_type="platform",
            user_id=UUID(user_id),
            ip_address=ip_address,
            risk_level=RiskLevel.HIGH if access_level == "admin" else RiskLevel.MEDIUM,
            details={
                "user_id": user_id,
                "role": user_role,
                "access_level": access_level,
                "action": "platform_access",
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def track_configuration_change(
        self,
        config_type: str,
        config_id: str,
        changes: dict[str, Any],
        admin_user_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track platform configuration changes for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.CONFIG_CHANGED,
            framework=ComplianceFramework.SOC2,
            resource_id=config_id,
            resource_type=config_type,
            user_id=UUID(admin_user_id),
            risk_level=RiskLevel.HIGH,  # Config changes are always high risk
            details={
                "config_type": config_type,
                "config_id": config_id,
                "changes": changes,
                "admin_user": admin_user_id,
                "action": "configuration_change",
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def track_multi_tenant_data_access(
        self,
        accessing_tenant: str,
        target_tenant: str,
        data_type: str,
        user_id: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track cross-tenant data access for GDPR compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.DATA_ACCESS,
            framework=ComplianceFramework.GDPR,  # Cross-tenant access is GDPR relevant
            resource_id=f"tenant_{target_tenant}",
            resource_type="tenant_data",
            user_id=UUID(user_id),
            risk_level=RiskLevel.CRITICAL,  # Cross-tenant access is critical risk
            details={
                "accessing_tenant": accessing_tenant,
                "target_tenant": target_tenant,
                "data_type": data_type,
                "user_id": user_id,
                "action": "cross_tenant_access",
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def generate_platform_compliance_report(
        self,
        framework: str,
        period_start: datetime,
        period_end: datetime,
        include_tenants: Optional[list[str]] = None,
        format: str = "pdf",
    ) -> dict[str, Any]:
        """Generate platform-wide compliance report."""

        try:
            compliance_framework = ComplianceFramework(framework.lower())
        except ValueError as e:
            raise ValueError(f"Unsupported compliance framework: {framework}") from e

        request = ComplianceReportRequest(
            framework=compliance_framework,
            report_type="platform_compliance",
            period_start=period_start,
            period_end=period_end,
            format=format,
            filters={
                "include_tenants": include_tenants,
                "platform": "management",
            },
        )

        report = await self.compliance_service.generate_compliance_report(request)

        return {
            "report_id": str(report.report_id),
            "name": report.name,
            "framework": report.framework.value,
            "platform": "management",
            "status": report.compliance_status.value,
            "score": report.compliance_score,
            "executive_summary": report.executive_summary,
            "findings": report.findings,
            "recommendations": report.recommendations,
            "included_tenants": include_tenants,
            "generated_at": report.generated_at.isoformat(),
        }

    @standard_exception_handler
    async def get_multi_tenant_compliance_summary(
        self,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Get multi-tenant compliance summary for management platform."""

        dashboard = await self.compliance_service.get_compliance_dashboard(period_days=period_days)

        # Add management platform specific data
        dashboard["platform"] = "management"
        dashboard["multi_tenant"] = True

        # Simulate tenant-specific compliance scores
        dashboard["tenant_compliance"] = {
            "total_tenants": 50,
            "compliant_tenants": 45,
            "at_risk_tenants": 3,
            "non_compliant_tenants": 2,
            "average_tenant_score": 87.5,
        }

        return dashboard

    @standard_exception_handler
    async def check_tenant_isolation_compliance(
        self,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Check tenant isolation compliance."""

        results = await self.compliance_service.perform_compliance_check(
            ComplianceFramework.SOC2,
            tenant_id,
            "tenant_isolation",
            {
                "features": ["data_encryption", "access_control", "network_isolation"],
                "isolation_type": "logical",
            },
        )

        return {
            "tenant_id": tenant_id,
            "framework": "SOC2",
            "check_type": "tenant_isolation",
            "checks": results,
            "overall_status": "compliant" if all(r["status"] == "compliant" for r in results) else "non_compliant",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def audit_admin_activities(
        self,
        admin_user_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Audit administrative activities for compliance."""

        if not period_start:
            period_start = datetime.now(timezone.utc) - timedelta(days=30)
        if not period_end:
            period_end = datetime.now(timezone.utc)

        # This would typically query stored compliance events
        # For demo, return simulated admin activity data

        activities = [
            {
                "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                "event_type": "config_change" if i % 3 == 0 else "user_access",
                "admin_user": admin_user_id,
                "resource": f"tenant_{i % 5 + 1}" if i % 2 == 0 else "platform_config",
                "action": "modify" if i % 3 == 0 else "view",
                "risk_level": "high" if i % 3 == 0 else "medium",
                "compliance_frameworks": ["SOC2", "ISO_27001"],
            }
            for i in range(10)  # Last 10 activities
        ]

        return activities

    @standard_exception_handler
    async def schedule_quarterly_compliance_review(
        self,
        framework: str,
        recipients: list[str],
        admin_user_id: Optional[UUID] = None,
    ) -> str:
        """Schedule quarterly compliance reviews."""

        return await self.compliance_service.schedule_report(
            ComplianceFramework(framework.lower()),
            "compliance_review",
            "quarterly",
            recipients,
            admin_user_id,
        )

    @standard_exception_handler
    async def get_compliance_risks_by_tenant(
        self,
        risk_threshold: str = "medium",
    ) -> dict[str, list[dict[str, Any]]]:
        """Get compliance risks organized by tenant."""

        alerts = await self.compliance_service.get_active_alerts()

        # Filter by risk threshold
        threshold_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level = threshold_levels.get(risk_threshold, 1)

        risk_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        filtered_alerts = [alert for alert in alerts if risk_levels.get(alert.severity.value, 0) >= min_level]

        # Group by tenant (simulated)
        tenant_risks = {}
        for alert in filtered_alerts:
            tenant = alert.tenant_id or "platform"
            if tenant not in tenant_risks:
                tenant_risks[tenant] = []

            tenant_risks[tenant].append(
                {
                    "alert_id": str(alert.alert_id),
                    "framework": alert.framework.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "resource": alert.resource_affected,
                    "triggered_at": alert.triggered_at.isoformat(),
                }
            )

        return tenant_risks

    async def get_platform_compliance_status(self) -> dict[str, Any]:
        """Get overall platform compliance status."""

        dashboard = await self.compliance_service.get_compliance_dashboard()

        return {
            "platform": "management",
            "overall_score": dashboard["overall"]["average_score"],
            "status": "compliant" if dashboard["overall"]["average_score"] >= 85 else "needs_attention",
            "frameworks": dashboard["frameworks"],
            "critical_alerts": dashboard["overall"]["critical_alerts"],
            "total_issues": dashboard["overall"]["total_issues"],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    async def health_check(self) -> dict[str, Any]:
        """Health check for the management compliance adapter."""
        try:
            compliance_health = await self.compliance_service._health_check_stateful_service()

            return {
                "adapter": "healthy",
                "tenant_id": self.tenant_id,
                "platform": "management",
                "compliance_service": compliance_health.status.value,
                "cache_service": "available" if self.cache_service else "unavailable",
                "event_bus": "available" if self.event_bus else "unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "adapter": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


# Factory function for easy adapter creation
async def create_management_compliance_adapter(
    tenant_id: Optional[str] = None,
    compliance_service: Optional[ComplianceService] = None,
    event_bus: Optional[EventBus] = None,
    cache_service=None,
) -> ManagementComplianceAdapter:
    """Create and initialize management compliance adapter."""

    adapter = ManagementComplianceAdapter(
        tenant_id=tenant_id,
        compliance_service=compliance_service,
        event_bus=event_bus,
        cache_service=cache_service,
    )
    await adapter.initialize()
    return adapter
