"""
Management Platform adapter for customer portal.

Integrates the unified customer portal service with Management Platform functionality.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from dotmac_shared.logging import get_logger

from ..core.schemas import ServiceStatus, ServiceSummary, ServiceUsageData, UsageSummary
from .base import CustomerPortalAdapter

try:
    from dotmac_management.services.customer_service import CustomerManagementService
    from dotmac_management.services.partner_service import PartnerService

    MANAGEMENT_SERVICES_AVAILABLE = True
except ImportError:
    MANAGEMENT_SERVICES_AVAILABLE = False
    logging.getLogger(__name__).warning("Management platform services not available")

logger = get_logger(__name__)


class ManagementPortalAdapter(CustomerPortalAdapter):
    """
    Management Platform-specific adapter for customer portal operations.

    This adapter provides customer portal functionality for Management Platform
    customers (partners, resellers, etc.) with different business logic than ISP customers.
    """

    def __init__(self, tenant_id: UUID):
        """Initialize Management Platform adapter."""
        super().__init__(tenant_id)

        # Management platform typically deals with business customers/partners
        self.customer_service = None
        self.partner_service = None

    async def get_customer_info(self, customer_id: UUID) -> dict[str, Any]:
        """Get Management Platform customer information."""
        try:
            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Return mock data for demonstration
                return {
                    "account_number": f"MGMT-{str(customer_id)[:8]}",
                    "status": "active",
                    "created_at": datetime.now() - timedelta(days=365),
                    "account_type": "business",
                    "company_name": "Customer Business LLC",
                    "business_type": "partner",
                    "partner_tier": "silver",
                    "territory": "North Region",
                }

            # Real implementation would use Management Platform services
            customer_service = CustomerManagementService(str(self.tenant_id))
            customer = await customer_service.get_customer(str(customer_id))

            if not customer:
                raise ValueError(f"Customer {customer_id} not found")

            return {
                "account_number": customer.account_number,
                "status": customer.status,
                "created_at": customer.created_at,
                "account_type": customer.account_type,
                "company_name": customer.company_name,
                "business_type": customer.business_type,
                "partner_tier": customer.partner_tier,
                "territory": customer.territory,
                "commission_rate": customer.commission_rate,
                "monthly_targets": customer.monthly_targets,
            }

        except Exception as e:
            logger.error(
                f"Failed to get Management Platform customer info for {customer_id}: {e}"
            )
            raise

    async def get_customer_services(self, customer_id: UUID) -> list[ServiceSummary]:
        """Get Management Platform customer services."""
        try:
            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Return mock services for demonstration
                return [
                    ServiceSummary(
                        service_id=UUID("11111111-1111-1111-1111-111111111111"),
                        service_name="Partner Management Platform",
                        service_type="saas_platform",
                        status=ServiceStatus.ACTIVE,
                        monthly_cost=Decimal("299.00"),
                        installation_date=datetime.now() - timedelta(days=180),
                        next_renewal=datetime.now() + timedelta(days=15),
                        usage_allowance="Unlimited Users",
                        current_usage="25 Active Users",
                    ),
                    ServiceSummary(
                        service_id=UUID("22222222-2222-2222-2222-222222222222"),
                        service_name="Advanced Analytics Package",
                        service_type="analytics",
                        status=ServiceStatus.ACTIVE,
                        monthly_cost=Decimal("99.00"),
                        installation_date=datetime.now() - timedelta(days=90),
                        next_renewal=datetime.now() + timedelta(days=15),
                        usage_allowance="10GB Storage",
                        current_usage="3.2GB Used",
                    ),
                ]

            # Real implementation
            customer_service = CustomerManagementService(str(self.tenant_id))
            services = await customer_service.get_customer_services(str(customer_id))

            service_summaries = []
            for service in services:
                summary = ServiceSummary(
                    service_id=UUID(service.id),
                    service_name=service.service_name,
                    service_type=service.service_type,
                    status=ServiceStatus(service.status.lower()),
                    monthly_cost=Decimal(str(service.monthly_cost)),
                    installation_date=service.created_at,
                    next_renewal=service.next_billing_date,
                    usage_allowance=service.usage_limit_description,
                    current_usage=service.current_usage_description,
                )
                service_summaries.append(summary)

            return service_summaries

        except Exception as e:
            logger.error(
                f"Failed to get Management Platform services for {customer_id}: {e}"
            )
            raise

    async def get_usage_summary(self, customer_id: UUID) -> Optional[UsageSummary]:
        """
        Get usage summary for Management Platform customer.

        Note: Management Platform customers typically don't have traditional
        "usage" like ISP customers, but they may have API usage, storage usage, etc.
        """
        try:
            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Management Platform customers don't typically have usage tracking
                # like ISP customers, so this may return None or API/storage usage
                return None

            # For business customers, usage might be API calls, storage, etc.
            # This would depend on the specific Management Platform implementation
            return None

        except Exception as e:
            logger.error(f"Failed to get usage summary for {customer_id}: {e}")
            return None

    async def get_platform_data(self, customer_id: UUID) -> dict[str, Any]:
        """Get Management Platform-specific data."""
        try:
            platform_data = {
                "platform_type": "management_platform",
                "features": {
                    "partner_dashboard": True,
                    "commission_tracking": True,
                    "territory_management": True,
                    "customer_provisioning": True,
                    "reporting_suite": True,
                },
            }

            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Add mock platform-specific data
                platform_data.update(
                    {
                        "partner_metrics": {
                            "total_customers": 150,
                            "active_customers": 142,
                            "monthly_revenue": "$45,750.00",
                            "commission_earned": "$4,575.00",
                            "territory_coverage": "85%",
                        },
                        "recent_activity": [
                            {
                                "type": "customer_signup",
                                "description": "New customer onboarded",
                                "timestamp": datetime.now() - timedelta(hours=2),
                            },
                            {
                                "type": "commission_payment",
                                "description": "Monthly commission processed",
                                "timestamp": datetime.now() - timedelta(days=1),
                            },
                        ],
                    }
                )
                return platform_data

            # Real implementation would get partner/business metrics
            partner_service = PartnerService(str(self.tenant_id))
            partner_metrics = await partner_service.get_customer_metrics(
                str(customer_id)
            )

            platform_data["partner_metrics"] = partner_metrics

            return platform_data

        except Exception as e:
            logger.error(
                f"Failed to get Management Platform data for {customer_id}: {e}"
            )
            return {"platform_type": "management_platform"}

    async def update_customer_custom_fields(
        self, customer_id: UUID, custom_fields: dict[str, Any]
    ) -> bool:
        """Update Management Platform customer custom fields."""
        try:
            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Mock successful update
                logger.info(
                    f"Mock update of custom fields for {customer_id}: {custom_fields}"
                )
                return True

            # Real implementation
            customer_service = CustomerManagementService(str(self.tenant_id))
            await customer_service.update_customer_metadata(
                customer_id=str(customer_id), metadata=custom_fields
            )

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
        """
        Get service usage for Management Platform services.

        This might track API usage, storage usage, user activity, etc.
        """
        try:
            # Set default date range
            if not end_date:
                end_date = datetime.now()
            if not start_date:
                start_date = end_date.replace(day=1)

            if not MANAGEMENT_SERVICES_AVAILABLE:
                # Return mock usage data
                return ServiceUsageData(
                    service_id=service_id,
                    service_name="Partner Management Platform",
                    billing_period_start=start_date,
                    billing_period_end=end_date,
                    usage_data={
                        "api_calls": Decimal("12450"),
                        "storage_gb": Decimal("3.2"),
                        "active_users": Decimal("25"),
                        "reports_generated": Decimal("47"),
                    },
                    allowances={
                        "api_calls": Decimal("50000"),
                        "storage_gb": Decimal("10"),
                        "active_users": Decimal("100"),
                        "reports_generated": Decimal("1000"),
                    },
                    overage_charges=[],
                    usage_history=[
                        {
                            "date": (start_date + timedelta(days=i)).isoformat(),
                            "api_calls": 400 + (i * 10),
                            "storage_gb": 3.0 + (i * 0.01),
                            "active_users": 20 + (i % 10),
                        }
                        for i in range((end_date - start_date).days)
                    ],
                )

            # Real implementation would get platform-specific usage
            # This might involve API usage tracking, storage usage, etc.
            raise NotImplementedError(
                "Real Management Platform usage tracking not implemented"
            )

        except Exception as e:
            logger.error(f"Failed to get service usage for {service_id}: {e}")
            raise

    async def get_available_actions(self, customer_id: UUID) -> list[str]:
        """Get Management Platform-specific available actions."""
        base_actions = await super().get_available_actions(customer_id)

        # Add Management Platform-specific actions
        mgmt_actions = [
            "view_commission_report",
            "manage_territory",
            "provision_customer",
            "view_partner_dashboard",
            "generate_report",
            "update_business_profile",
        ]

        return base_actions + mgmt_actions

    async def validate_customer_access(
        self, customer_id: UUID, requesting_user_id: UUID
    ) -> bool:
        """
        Validate access for Management Platform customers.

        Management Platform may have more complex access patterns
        (e.g., partners can access their sub-customers).
        """
        # Basic validation - same as base
        if customer_id == requesting_user_id:
            return True

        # Check if requesting user is a partner with access to this customer
        if not MANAGEMENT_SERVICES_AVAILABLE:
            # Mock logic - in real implementation, check partner relationships
            return True

        try:
            partner_service = PartnerService(str(self.tenant_id))
            has_access = await partner_service.can_access_customer(
                partner_id=str(requesting_user_id), customer_id=str(customer_id)
            )
            return has_access
        except Exception as e:
            logger.error(f"Failed to validate access: {e}")
            return False
