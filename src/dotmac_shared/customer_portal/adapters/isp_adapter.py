"""
ISP Framework adapter for customer portal.

Integrates the unified customer portal service with ISP-specific functionality.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from dotmac_isp.core.database import get_db
from dotmac_isp.modules.analytics.service import AnalyticsService
from dotmac_isp.modules.identity.service import CustomerService
from dotmac_isp.modules.services.service import ServiceProvisioningService

from ..core.schemas import (
    ServiceStatus,
    ServiceSummary,
    ServiceUsageData,
    UsageCharge,
    UsageSummary,
)
from .base import CustomerPortalAdapter

logger = logging.getLogger(__name__)


class ISPPortalAdapter(CustomerPortalAdapter):
    """
    ISP Framework-specific adapter for customer portal operations.

    This adapter integrates with ISP Framework services to provide
    customer portal functionality specific to ISP operations.
    """

    def __init__(self, tenant_id: UUID):
        """Initialize ISP adapter."""
        super().__init__(tenant_id)

        # Initialize ISP-specific services
        # Note: In real implementation, these would be dependency-injected
        self.customer_service = None  # Will be initialized per request
        self.billing_service = None
        self.service_provisioning = None
        self.analytics_service = None

    async def get_customer_info(self, customer_id: UUID) -> dict[str, Any]:
        """Get ISP customer information."""
        try:
            # Get database session
            db = next(get_db())

            # Initialize customer service
            customer_service = CustomerService(db, str(self.tenant_id))

            # Get customer from ISP framework
            customer = await customer_service.get_customer(str(customer_id))

            if not customer:
                raise ValueError(f"Customer {customer_id} not found")

            return {
                "account_number": customer.customer_id,
                "status": customer.status,
                "created_at": customer.created_at,
                "customer_type": customer.customer_type,
                "service_address": {
                    "street": customer.service_address,
                    "city": customer.service_city,
                    "state": customer.service_state,
                    "postal_code": customer.service_postal_code,
                },
                "billing_address": {
                    "street": customer.billing_address,
                    "city": customer.billing_city,
                    "state": customer.billing_state,
                    "postal_code": customer.billing_postal_code,
                },
                "connection_type": customer.connection_type,
                "plan_name": customer.plan_name,
                "monthly_rate": customer.monthly_rate,
            }

        except Exception as e:
            logger.error(f"Failed to get ISP customer info for {customer_id}: {e}")
            raise

    async def get_customer_services(self, customer_id: UUID) -> list[ServiceSummary]:
        """Get ISP customer services."""
        try:
            # Get database session
            db = next(get_db())

            # Initialize service provisioning
            service_provisioning = ServiceProvisioningService(db, str(self.tenant_id))

            # Get services from ISP framework
            services = await service_provisioning.get_customer_services(str(customer_id))

            # Convert to standardized format
            service_summaries = []
            for service in services:
                summary = ServiceSummary(
                    service_id=UUID(service.id),
                    service_name=service.service_name,
                    service_type=service.service_type,
                    status=ServiceStatus(service.status.lower()),
                    monthly_cost=Decimal(str(service.monthly_rate)),
                    installation_date=service.installation_date,
                    next_renewal=service.next_billing_date,
                    usage_allowance=(f"{service.data_allowance_gb}GB" if service.data_allowance_gb else None),
                    current_usage=None,  # Will be populated by usage query
                )

                # Get current usage if available
                if service.service_type.lower() in ["internet", "data"]:
                    try:
                        usage = await self._get_current_usage(UUID(service.id))
                        if usage:
                            summary.current_usage = f"{usage:.2f}GB"
                    except Exception as usage_e:
                        logger.warning(f"Failed to get usage for service {service.id}: {usage_e}")

                service_summaries.append(summary)

            return service_summaries

        except Exception as e:
            logger.error(f"Failed to get ISP customer services for {customer_id}: {e}")
            raise

    async def get_usage_summary(self, customer_id: UUID) -> Optional[UsageSummary]:
        """Get ISP customer usage summary."""
        try:
            # Get database session
            db = next(get_db())

            # Initialize analytics service
            analytics_service = AnalyticsService(db, str(self.tenant_id))

            # Get current billing cycle
            now = datetime.now()
            cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = cycle_start.replace(month=cycle_start.month + 1)
            cycle_end = next_month - timedelta(seconds=1)

            # Get usage data from analytics
            usage_data = await analytics_service.get_customer_usage(
                customer_id=str(customer_id), start_date=cycle_start, end_date=cycle_end
            )

            if not usage_data:
                return None

            # Calculate additional charges
            additional_charges = []
            if usage_data.get("overage_gb", 0) > 0:
                overage_gb = Decimal(str(usage_data["overage_gb"]))
                overage_rate = Decimal("5.00")  # $5/GB overage
                additional_charges.append(
                    UsageCharge(
                        charge_type="data_overage",
                        description="Data overage charges",
                        quantity=overage_gb,
                        rate=overage_rate,
                        amount=overage_gb * overage_rate,
                    )
                )

            return UsageSummary(
                billing_cycle_start=cycle_start,
                billing_cycle_end=cycle_end,
                data_usage_gb=Decimal(str(usage_data.get("data_usage_gb", 0))),
                data_allowance_gb=Decimal(str(usage_data.get("data_allowance_gb", 0))),
                voice_minutes=usage_data.get("voice_minutes"),
                voice_allowance=usage_data.get("voice_allowance"),
                additional_charges=additional_charges,
            )

        except Exception as e:
            logger.error(f"Failed to get usage summary for {customer_id}: {e}")
            return None

    async def get_platform_data(self, customer_id: UUID) -> dict[str, Any]:
        """Get ISP-specific platform data."""
        try:
            # Get database session
            next(get_db())

            # Get ISP-specific data
            platform_data = {
                "platform_type": "isp_framework",
                "features": {
                    "network_diagnostics": True,
                    "speed_test": True,
                    "outage_reporting": True,
                    "service_scheduling": True,
                },
            }

            # Get network status if available
            try:
                # This would integrate with network monitoring
                platform_data["network_status"] = {
                    "connection_status": "online",
                    "last_seen": datetime.now(),
                    "signal_strength": "excellent",
                    "download_speed": "100 Mbps",
                    "upload_speed": "10 Mbps",
                }
            except Exception as network_e:
                logger.warning(f"Failed to get network status: {network_e}")
                platform_data["network_status"] = {"connection_status": "unknown"}

            return platform_data

        except Exception as e:
            logger.error(f"Failed to get ISP platform data for {customer_id}: {e}")
            return {"platform_type": "isp_framework"}

    async def update_customer_custom_fields(self, customer_id: UUID, custom_fields: dict[str, Any]) -> bool:
        """Update ISP customer custom fields."""
        try:
            # Get database session
            db = next(get_db())

            # Initialize customer service
            customer_service = CustomerService(db, str(self.tenant_id))

            # Update custom fields (this would be ISP-specific fields)
            await customer_service.update_customer_metadata(customer_id=str(customer_id), metadata=custom_fields)

            return True

        except Exception as e:
            logger.error(f"Failed to update custom fields for {customer_id}: {e}")
            return False

    async def get_service_usage(
        self,
        customer_id: UUID,
        service_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ServiceUsageData:
        """Get detailed service usage data."""
        try:
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date.replace(day=1)

            # Get database session
            db = next(get_db())

            # Initialize analytics service
            analytics_service = AnalyticsService(db, str(self.tenant_id))

            # Get service info
            service_provisioning = ServiceProvisioningService(db, str(self.tenant_id))
            service = await service_provisioning.get_service(str(service_id))

            if not service:
                raise ValueError(f"Service {service_id} not found")

            # Get usage data
            usage_data = await analytics_service.get_service_usage(
                service_id=str(service_id), start_date=start_date, end_date=end_date
            )

            # Calculate overage charges
            overage_charges = []
            if usage_data.get("data_overage_gb", 0) > 0:
                overage_gb = Decimal(str(usage_data["data_overage_gb"]))
                overage_rate = Decimal("5.00")
                overage_charges.append(
                    UsageCharge(
                        charge_type="data_overage",
                        description="Data usage overage",
                        quantity=overage_gb,
                        rate=overage_rate,
                        amount=overage_gb * overage_rate,
                    )
                )

            return ServiceUsageData(
                service_id=service_id,
                service_name=service.service_name,
                billing_period_start=start_date,
                billing_period_end=end_date,
                usage_data={
                    "data_gb": Decimal(str(usage_data.get("data_usage_gb", 0))),
                    "voice_minutes": Decimal(str(usage_data.get("voice_minutes", 0))),
                    "sms_count": Decimal(str(usage_data.get("sms_count", 0))),
                },
                allowances={
                    "data_gb": Decimal(str(service.data_allowance_gb or 0)),
                    "voice_minutes": Decimal(str(service.voice_allowance_minutes or 0)),
                    "sms_count": Decimal(str(service.sms_allowance or 0)),
                },
                overage_charges=overage_charges,
                usage_history=usage_data.get("daily_usage", []),
            )

        except Exception as e:
            logger.error(f"Failed to get service usage for {service_id}: {e}")
            raise

    async def get_available_actions(self, customer_id: UUID) -> list[str]:
        """Get ISP-specific available actions."""
        base_actions = await super().get_available_actions(customer_id)

        # Add ISP-specific actions
        isp_actions = [
            "run_speed_test",
            "report_outage",
            "schedule_technician",
            "view_network_status",
            "modify_services",
            "view_usage_details",
        ]

        return base_actions + isp_actions

    async def _get_current_usage(self, service_id: UUID) -> Optional[float]:
        """Get current month usage for a service."""
        try:
            # Get database session
            db = next(get_db())

            # Initialize analytics service
            analytics_service = AnalyticsService(db, str(self.tenant_id))

            # Get current month usage
            now = datetime.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            usage_data = await analytics_service.get_service_usage(
                service_id=str(service_id), start_date=start_of_month, end_date=now
            )

            return usage_data.get("data_usage_gb", 0.0)

        except Exception as e:
            logger.warning(f"Failed to get current usage for service {service_id}: {e}")
            return None
