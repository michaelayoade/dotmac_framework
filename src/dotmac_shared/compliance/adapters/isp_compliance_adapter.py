"""
ISP compliance adapter for backward compatibility with existing ISP analytics.
Eliminates duplicate compliance code while maintaining ISP-specific interfaces.
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


class ISPComplianceAdapter:
    """
    Adapter that provides ISP compliance interface using shared compliance service.
    Maintains backward compatibility with existing ISP compliance API.
    """

    def __init__(
        self,
        tenant_id: str,
        compliance_service: Optional[ComplianceService] = None,
        event_bus: Optional[EventBus] = None,
        cache_service=None,
    ):
        self.tenant_id = tenant_id

        # Initialize shared compliance service
        if compliance_service:
            self.compliance_service = compliance_service
        else:
            config = ComplianceServiceConfig(
                enabled_frameworks=[
                    ComplianceFramework.SOC2,
                    ComplianceFramework.GDPR,
                    ComplianceFramework.PCI_DSS,
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

            logger.info(
                f"✅ ISP Compliance Adapter initialized for tenant {self.tenant_id}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize ISP Compliance Adapter: {e}")
            return False

    # ISP-specific compliance methods

    @standard_exception_handler
    async def track_customer_access(
        self,
        customer_id: str,
        user_id: str,
        access_type: str,
        ip_address: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track customer data access for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.DATA_ACCESS,
            framework=ComplianceFramework.GDPR,  # Customer data access is GDPR relevant
            resource_id=customer_id,
            resource_type="customer",
            user_id=UUID(user_id) if user_id else None,
            ip_address=ip_address,
            risk_level=RiskLevel.MEDIUM,
            details={
                "access_type": access_type,
                "customer_id": customer_id,
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def track_billing_transaction(
        self,
        transaction_id: str,
        customer_id: str,
        amount: float,
        payment_method: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track billing transactions for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.TRANSACTION_PROCESSED,
            framework=ComplianceFramework.PCI_DSS,  # Financial data is PCI relevant
            resource_id=transaction_id,
            resource_type="transaction",
            risk_level=RiskLevel.HIGH,  # Financial transactions are high risk
            details={
                "transaction_id": transaction_id,
                "customer_id": customer_id,
                "amount": amount,
                "payment_method": payment_method,
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def track_service_activation(
        self,
        service_id: str,
        customer_id: str,
        service_type: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Track service activation for compliance."""

        compliance_event = ComplianceEvent(
            event_id=uuid4(),
            tenant_id=self.tenant_id,
            event_type=AuditEventType.SYSTEM_ACCESS,
            framework=ComplianceFramework.SOC2,
            resource_id=service_id,
            resource_type="service",
            risk_level=RiskLevel.LOW,
            details={
                "service_id": service_id,
                "customer_id": customer_id,
                "service_type": service_type,
                "action": "activation",
            },
            metadata=metadata or {},
        )

        return await self.compliance_service.record_compliance_event(compliance_event)

    @standard_exception_handler
    async def generate_soc2_report(
        self,
        period_start: datetime,
        period_end: datetime,
        report_type: str = "type2",
        format: str = "pdf",
    ) -> dict[str, Any]:
        """Generate SOC 2 compliance report for ISP."""

        request = ComplianceReportRequest(
            framework=ComplianceFramework.SOC2,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            format=format,
            tenant_id=UUID(self.tenant_id),
        )

        report = await self.compliance_service.generate_compliance_report(request)

        return {
            "report_id": str(report.report_id),
            "name": report.name,
            "framework": report.framework.value,
            "status": report.compliance_status.value,
            "score": report.compliance_score,
            "executive_summary": report.executive_summary,
            "findings": report.findings,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

    @standard_exception_handler
    async def generate_gdpr_report(
        self,
        period_start: datetime,
        period_end: datetime,
        format: str = "pdf",
    ) -> dict[str, Any]:
        """Generate GDPR compliance report for ISP."""

        request = ComplianceReportRequest(
            framework=ComplianceFramework.GDPR,
            report_type="compliance",
            period_start=period_start,
            period_end=period_end,
            format=format,
            tenant_id=UUID(self.tenant_id),
        )

        report = await self.compliance_service.generate_compliance_report(request)

        return {
            "report_id": str(report.report_id),
            "name": report.name,
            "framework": report.framework.value,
            "status": report.compliance_status.value,
            "score": report.compliance_score,
            "executive_summary": report.executive_summary,
            "findings": report.findings,
            "recommendations": report.recommendations,
            "generated_at": report.generated_at.isoformat(),
        }

    @standard_exception_handler
    async def get_compliance_dashboard(
        self,
        period_days: int = 30,
    ) -> dict[str, Any]:
        """Get ISP compliance dashboard data."""

        dashboard = await self.compliance_service.get_compliance_dashboard(
            period_days=period_days
        )

        # Add ISP-specific formatting
        dashboard["tenant_id"] = self.tenant_id
        dashboard["platform"] = "isp"

        return dashboard

    @standard_exception_handler
    async def get_customer_data_access_log(
        self,
        customer_id: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Get customer data access log for GDPR compliance."""

        # This would typically query stored compliance events
        # For demo, return simulated data

        if not period_start:
            period_start = datetime.now(timezone.utc) - timedelta(days=30)
        if not period_end:
            period_end = datetime.now(timezone.utc)

        # Simulate access log
        access_log = [
            {
                "timestamp": (
                    datetime.now(timezone.utc) - timedelta(hours=i)
                ).isoformat(),
                "event_type": "data_access",
                "resource": f"customer_{customer_id}",
                "user": f"user_{i % 3 + 1}",
                "ip_address": f"192.168.1.{100 + i}",
                "access_type": "view" if i % 2 == 0 else "modify",
            }
            for i in range(5)  # Last 5 accesses
        ]

        return access_log

    @standard_exception_handler
    async def check_pci_compliance(
        self,
        payment_system_id: str,
    ) -> dict[str, Any]:
        """Check PCI DSS compliance for payment systems."""

        results = await self.compliance_service.perform_compliance_check(
            ComplianceFramework.PCI_DSS,
            payment_system_id,
            "payment_system",
            {
                "features": ["encryption", "access_control", "monitoring"],
                "system_type": "payment_processing",
            },
        )

        return {
            "system_id": payment_system_id,
            "framework": "PCI_DSS",
            "checks": results,
            "overall_status": "compliant"
            if all(r["status"] == "compliant" for r in results)
            else "non_compliant",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    @standard_exception_handler
    async def schedule_monthly_soc2_report(
        self,
        recipients: list[str],
        user_id: Optional[UUID] = None,
    ) -> str:
        """Schedule monthly SOC 2 reports."""

        return await self.compliance_service.schedule_report(
            ComplianceFramework.SOC2,
            "type2",
            "monthly",
            recipients,
            user_id,
        )

    async def get_active_compliance_alerts(self) -> list[dict[str, Any]]:
        """Get active compliance alerts for ISP."""

        alerts = await self.compliance_service.get_active_alerts()

        # Format for ISP consumption
        formatted_alerts = []
        for alert in alerts:
            formatted_alerts.append(
                {
                    "alert_id": str(alert.alert_id),
                    "framework": alert.framework.value,
                    "severity": alert.severity.value,
                    "title": alert.title,
                    "description": alert.description,
                    "resource": alert.resource_affected,
                    "status": alert.status,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "remediation": alert.remediation,
                }
            )

        return formatted_alerts

    async def health_check(self) -> dict[str, Any]:
        """Health check for the ISP compliance adapter."""
        try:
            compliance_health = (
                await self.compliance_service._health_check_stateful_service()
            )

            return {
                "adapter": "healthy",
                "tenant_id": self.tenant_id,
                "platform": "isp",
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
async def create_isp_compliance_adapter(
    tenant_id: str,
    compliance_service: Optional[ComplianceService] = None,
    event_bus: Optional[EventBus] = None,
    cache_service=None,
) -> ISPComplianceAdapter:
    """Create and initialize ISP compliance adapter."""

    adapter = ISPComplianceAdapter(
        tenant_id=tenant_id,
        compliance_service=compliance_service,
        event_bus=event_bus,
        cache_service=cache_service,
    )
    await adapter.initialize()
    return adapter
