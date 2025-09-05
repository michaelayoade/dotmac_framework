"""
Real-Time Usage Billing Integration

Leverages existing commission_automation.py with DRY principles for usage-based billing.
Integrates with existing commission system for automated revenue tracking.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from dotmac_shared.core.logging import get_logger
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import standard_exception_handler

from .commission_automation import CommissionAutomationEngine
from .commission_system import CommissionService
from .services_complete import ResellerService

logger = get_logger(__name__)


class UsageMetric:
    """Real-time usage metric with billing calculation."""

    def __init__(
        self,
        tenant_id: str,
        metric_type: str,
        value: float,
        timestamp: Optional[datetime] = None,
    ):
        self.tenant_id = tenant_id
        self.metric_type = metric_type  # bandwidth, storage, api_calls, users, etc.
        self.value = value
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.billing_rate = self._get_billing_rate(metric_type)

    def _get_billing_rate(self, metric_type: str) -> Decimal:
        """Get billing rate for metric type."""
        rates = {
            "bandwidth_gb": Decimal("0.10"),  # $0.10 per GB
            "storage_gb": Decimal("0.25"),  # $0.25 per GB
            "api_calls_1000": Decimal("0.05"),  # $0.05 per 1000 calls
            "active_users": Decimal("2.50"),  # $2.50 per active user
            "email_sends_1000": Decimal("0.15"),  # $0.15 per 1000 emails
            "sms_sends": Decimal("0.02"),  # $0.02 per SMS
        }
        return rates.get(metric_type, Decimal("0.00"))

    def calculate_cost(self) -> Decimal:
        """Calculate cost for this usage metric."""
        return Decimal(str(self.value)) * self.billing_rate


class RealtimeUsageBillingEngine:
    """
    Real-time usage billing engine that integrates with existing commission automation.

    Leverages existing commission_automation.py for DRY billing workflow integration.
    """

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id

        # Leverage existing commission services (DRY)
        self.commission_automation = CommissionAutomationEngine(db, tenant_id)
        self.commission_service = CommissionService(db, tenant_id)
        self.reseller_service = ResellerService(db, tenant_id)

        # Usage tracking state
        self.usage_buffer = {}  # Buffer usage metrics before processing
        self.billing_thresholds = {
            "buffer_size": 100,  # Process every 100 metrics
            "time_threshold": 300,  # Process every 5 minutes
            "cost_threshold": Decimal("10.00"),  # Process when cost reaches $10
        }

        # Real-time processing task
        self._processing_task = None

    async def initialize(self):
        """Initialize real-time usage billing engine."""
        # Start background processing task
        self._processing_task = asyncio.create_task(self._process_usage_buffer())
        logger.info("Real-time usage billing engine initialized")

    @standard_exception_handler
    async def track_usage(
        self,
        tenant_id: str,
        metric_type: str,
        value: float,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Track real-time usage metric and trigger billing if thresholds met.

        Leverages existing commission system for DRY billing integration.
        """
        usage_metric = UsageMetric(tenant_id, metric_type, value)

        # Add to buffer
        if tenant_id not in self.usage_buffer:
            self.usage_buffer[tenant_id] = []

        self.usage_buffer[tenant_id].append(
            {
                "metric": usage_metric,
                "metadata": metadata or {},
                "tracked_at": datetime.now(timezone.utc),
            }
        )

        # Check if immediate processing needed
        should_process = await self._should_process_immediately(tenant_id)

        if should_process:
            await self._process_tenant_usage(tenant_id)

        return {
            "tenant_id": tenant_id,
            "metric_type": metric_type,
            "value": value,
            "cost": float(usage_metric.calculate_cost()),
            "tracked_at": usage_metric.timestamp.isoformat(),
            "processed": should_process,
        }

    async def _should_process_immediately(self, tenant_id: str) -> bool:
        """Check if usage should be processed immediately."""
        tenant_buffer = self.usage_buffer.get(tenant_id, [])

        if not tenant_buffer:
            return False

        # Check buffer size threshold
        if len(tenant_buffer) >= self.billing_thresholds["buffer_size"]:
            return True

        # Check time threshold
        oldest_metric = min(tenant_buffer, key=lambda x: x["tracked_at"])
        age_seconds = (
            datetime.now(timezone.utc) - oldest_metric["tracked_at"]
        ).total_seconds()
        if age_seconds >= self.billing_thresholds["time_threshold"]:
            return True

        # Check cost threshold
        total_cost = sum(item["metric"].calculate_cost() for item in tenant_buffer)
        if total_cost >= self.billing_thresholds["cost_threshold"]:
            return True

        return False

    @standard_exception_handler
    async def _process_tenant_usage(self, tenant_id: str) -> dict[str, Any]:
        """
        Process buffered usage for a tenant and create commission records.

        Integrates with existing commission_automation.py for DRY workflow.
        """
        tenant_buffer = self.usage_buffer.get(tenant_id, [])
        if not tenant_buffer:
            return {"processed": 0, "total_cost": 0}

        try:
            # Calculate total usage costs
            total_cost = Decimal("0.00")
            usage_summary = {}

            for item in tenant_buffer:
                metric = item["metric"]
                cost = metric.calculate_cost()
                total_cost += cost

                if metric.metric_type not in usage_summary:
                    usage_summary[metric.metric_type] = {
                        "count": 0,
                        "total_value": 0,
                        "total_cost": Decimal("0.00"),
                    }

                usage_summary[metric.metric_type]["count"] += 1
                usage_summary[metric.metric_type]["total_value"] += metric.value
                usage_summary[metric.metric_type]["total_cost"] += cost

            # Get reseller for this tenant
            reseller_id = await self._get_reseller_for_tenant(tenant_id)
            if not reseller_id:
                logger.warning(f"No reseller found for tenant {tenant_id}")
                return {"error": "No reseller found for tenant"}

            # Create commission record using existing commission service (DRY)
            commission = await self.commission_service.create_commission_record(
                reseller_id=reseller_id,
                commission_type="usage_based",
                base_amount=total_cost,
                service_period_start=min(
                    item["tracked_at"] for item in tenant_buffer
                ).date(),
                service_period_end=datetime.now(timezone.utc).date(),
                customer_id=tenant_id,
                additional_data={
                    "usage_summary": {
                        k: {
                            "count": v["count"],
                            "total_value": v["total_value"],
                            "total_cost": float(v["total_cost"]),
                        }
                        for k, v in usage_summary.items()
                    },
                    "billing_type": "real_time_usage",
                    "processed_metrics": len(tenant_buffer),
                    "processing_timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            # Clear processed buffer
            self.usage_buffer[tenant_id] = []

            logger.info(
                f"Processed real-time usage for tenant {tenant_id}",
                extra={
                    "total_cost": float(total_cost),
                    "commission_id": commission.commission_id,
                    "metrics_processed": len(tenant_buffer),
                },
            )

            return {
                "tenant_id": tenant_id,
                "processed_metrics": len(tenant_buffer),
                "total_cost": float(total_cost),
                "commission_id": commission.commission_id,
                "commission_amount": float(commission.commission_amount),
                "usage_summary": usage_summary,
            }

        except Exception as e:
            logger.error(f"Failed to process usage for tenant {tenant_id}: {e}")
            raise

    async def _get_reseller_for_tenant(self, tenant_id: str) -> Optional[str]:
        """Get reseller ID for a tenant (leverages existing data relationships)."""
        try:
            # In production, this would query the tenant->reseller relationship
            # For now, simulate the lookup
            return "RSL_001"  # Placeholder
        except Exception as e:
            logger.error(f"Failed to get reseller for tenant {tenant_id}: {e}")
            return None

    async def _process_usage_buffer(self):
        """Background task to process buffered usage metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Process every minute

                for tenant_id in list(self.usage_buffer.keys()):
                    if await self._should_process_immediately(tenant_id):
                        await self._process_tenant_usage(tenant_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in usage buffer processing: {e}")
                await asyncio.sleep(10)  # Back off on error

    @standard_exception_handler
    async def create_usage_based_billing_run(
        self, reseller_ids: Optional[list[str]] = None, period_hours: int = 24
    ) -> dict[str, Any]:
        """
        Create usage-based billing run leveraging existing commission automation.

        Integrates with commission_automation.py workflow system for DRY processing.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=period_hours)

        # Use existing commission automation workflow (DRY)
        billing_run = await self.commission_automation.schedule_monthly_commission_run(
            target_date=end_time.date(), reseller_ids=reseller_ids
        )

        # Enhance with usage-specific data
        billing_run.update(
            {
                "billing_type": "usage_based",
                "period_hours": period_hours,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "real_time_processing": True,
            }
        )

        return billing_run

    @standard_exception_handler
    async def get_usage_billing_analytics(
        self, reseller_id: str, days: int = 30
    ) -> dict[str, Any]:
        """
        Get usage billing analytics leveraging existing commission reporting.

        Uses existing commission_system.py for DRY analytics generation.
        """
        # Get commission summary using existing service (DRY)
        commission_summary = (
            await self.commission_service.get_reseller_commission_summary(
                reseller_id, last_n_months=1
            )
        )

        # Filter for usage-based commissions
        usage_commissions = []
        total_usage_revenue = Decimal("0.00")

        for commission in commission_summary.get("recent_commissions", []):
            if commission.get("commission_type") == "usage_based":
                usage_commissions.append(commission)
                total_usage_revenue += Decimal(
                    str(commission.get("commission_amount", 0))
                )

        # Usage breakdown by metric type
        usage_breakdown = {}
        for commission in usage_commissions:
            usage_data = commission.get("additional_data", {}).get("usage_summary", {})
            for metric_type, data in usage_data.items():
                if metric_type not in usage_breakdown:
                    usage_breakdown[metric_type] = {
                        "total_cost": 0,
                        "total_usage": 0,
                        "count": 0,
                    }

                usage_breakdown[metric_type]["total_cost"] += data["total_cost"]
                usage_breakdown[metric_type]["total_usage"] += data["total_value"]
                usage_breakdown[metric_type]["count"] += data["count"]

        return {
            "reseller_id": reseller_id,
            "period_days": days,
            "total_usage_revenue": float(total_usage_revenue),
            "total_usage_commissions": len(usage_commissions),
            "usage_breakdown": usage_breakdown,
            "avg_daily_revenue": float(total_usage_revenue / days) if days > 0 else 0,
            "commission_summary": commission_summary,  # Include existing summary
            "top_usage_types": sorted(
                usage_breakdown.items(), key=lambda x: x[1]["total_cost"], reverse=True
            )[:5],
        }

    async def cleanup(self):
        """Clean up background tasks."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Real-time usage billing engine cleaned up")


class UsageBillingIntegrationService:
    """
    Integration service that connects usage billing with existing commission system.

    Provides a clean interface for portal and API integration.
    """

    def __init__(self, db: AsyncSession, tenant_id: Optional[str] = None):
        self.db = db
        self.tenant_id = tenant_id
        self.usage_engine = RealtimeUsageBillingEngine(db, tenant_id)

    async def initialize(self):
        """Initialize integration service."""
        await self.usage_engine.initialize()

    @standard_exception_handler
    async def track_api_usage(
        self, tenant_id: str, endpoint: str, requests: int
    ) -> dict[str, Any]:
        """Track API usage for billing."""
        return await self.usage_engine.track_usage(
            tenant_id=tenant_id,
            metric_type="api_calls_1000",
            value=requests / 1000,  # Bill per 1000 calls
            metadata={"endpoint": endpoint},
        )

    @standard_exception_handler
    async def track_bandwidth_usage(
        self, tenant_id: str, bytes_transferred: int
    ) -> dict[str, Any]:
        """Track bandwidth usage for billing."""
        gb_transferred = bytes_transferred / (1024**3)  # Convert to GB
        return await self.usage_engine.track_usage(
            tenant_id=tenant_id, metric_type="bandwidth_gb", value=gb_transferred
        )

    @standard_exception_handler
    async def track_storage_usage(
        self, tenant_id: str, bytes_stored: int
    ) -> dict[str, Any]:
        """Track storage usage for billing."""
        gb_stored = bytes_stored / (1024**3)  # Convert to GB
        return await self.usage_engine.track_usage(
            tenant_id=tenant_id, metric_type="storage_gb", value=gb_stored
        )

    @standard_exception_handler
    async def track_user_activity(
        self, tenant_id: str, active_users: int
    ) -> dict[str, Any]:
        """Track active user count for billing."""
        return await self.usage_engine.track_usage(
            tenant_id=tenant_id, metric_type="active_users", value=active_users
        )

    async def get_realtime_usage_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get real-time usage summary for tenant."""
        buffered_usage = self.usage_engine.usage_buffer.get(tenant_id, [])

        if not buffered_usage:
            return {"tenant_id": tenant_id, "current_usage": {}, "pending_cost": 0}

        usage_summary = {}
        total_cost = Decimal("0.00")

        for item in buffered_usage:
            metric = item["metric"]
            if metric.metric_type not in usage_summary:
                usage_summary[metric.metric_type] = {
                    "value": 0,
                    "cost": Decimal("0.00"),
                }

            usage_summary[metric.metric_type]["value"] += metric.value
            usage_summary[metric.metric_type]["cost"] += metric.calculate_cost()
            total_cost += metric.calculate_cost()

        return {
            "tenant_id": tenant_id,
            "current_usage": {
                k: {"value": v["value"], "cost": float(v["cost"])}
                for k, v in usage_summary.items()
            },
            "pending_cost": float(total_cost),
            "buffered_metrics": len(buffered_usage),
            "oldest_metric": min(
                item["tracked_at"] for item in buffered_usage
            ).isoformat()
            if buffered_usage
            else None,
        }


# Global usage billing service factory
_usage_billing_service: Optional[UsageBillingIntegrationService] = None


async def get_usage_billing_service(db: AsyncSession) -> UsageBillingIntegrationService:
    """Get singleton usage billing integration service."""
    global _usage_billing_service

    if _usage_billing_service is None:
        _usage_billing_service = UsageBillingIntegrationService(db)
        await _usage_billing_service.initialize()

    return _usage_billing_service
