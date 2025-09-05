"""
Unified Customer Portal Service

Core service that orchestrates customer portal functionality across platforms.
Leverages existing services while providing a unified interface.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from dotmac.platform.auth import get_auth_service
from dotmac_business_logic.billing import BillingService
from dotmac_management.user_management.services.user_service import UserManagementService
from dotmac_shared.monitoring import get_monitoring

from ..adapters.base import CustomerPortalAdapter
from .auth import PortalAuthenticationManager
from .schemas import (
    BillingSummary,
    CustomerDashboardData,
    CustomerPortalConfig,
    CustomerProfileUpdate,
    CustomerStatus,
    PortalSessionData,
    PortalType,
    ServiceUsageData,
)

logger = logging.getLogger(__name__)


class CustomerPortalService:
    """
    Unified customer portal service that orchestrates functionality across platforms.

    This service implements DRY principles by:
    1. Leveraging existing shared services (billing, ticketing, auth, etc.)
    2. Providing platform-specific adapters for ISP/Management differences
    3. Centralizing common portal operations
    4. Maintaining consistent interfaces across platforms
    """

    def __init__(
        self,
        adapter: CustomerPortalAdapter,
        config: CustomerPortalConfig,
        tenant_id: UUID,
    ):
        """Initialize portal service with platform adapter."""
        self.adapter = adapter
        self.config = config
        self.tenant_id = tenant_id

        # Initialize existing services
        self.auth_service = get_auth_service()
        self.billing_service = BillingService(tenant_id=str(tenant_id))
        self.ticket_service = None  # TODO: Implement TicketService(tenant_id=str(tenant_id))
        self.user_service = UserManagementService(tenant_id=str(tenant_id))
        self.monitoring = get_monitoring("customer_portal")

        # Initialize portal auth manager
        self.portal_auth = PortalAuthenticationManager(auth_service=self.auth_service, portal_type=config.portal_type)

        logger.info(f"Initialized CustomerPortalService for {config.portal_type} portal")

    async def get_customer_dashboard(
        self,
        customer_id: UUID,
        include_usage: bool = True,
        include_tickets: bool = True,
    ) -> CustomerDashboardData:
        """Get unified customer dashboard data."""
        start_time = datetime.now()

        # Get base customer information from platform adapter
        customer_info = await self.adapter.get_customer_info(customer_id)

        # Initialize dashboard data
        dashboard = CustomerDashboardData(
            customer_id=customer_id,
            account_number=customer_info.get("account_number", ""),
            account_status=CustomerStatus(customer_info.get("status", "active")),
            portal_type=self.config.portal_type,
        )

        # Get financial summary using shared billing service
        if self.config.billing_enabled:
            billing_summary = await self._get_billing_summary(customer_id)
            dashboard.current_balance = billing_summary.current_balance
            dashboard.next_bill_date = billing_summary.next_bill_date
            if billing_summary.recent_payments:
                latest_payment = billing_summary.recent_payments[0]
                dashboard.last_payment_date = latest_payment.payment_date
                dashboard.last_payment_amount = latest_payment.amount

        # Get services summary using platform adapter
        if self.config.service_management_enabled:
            services = await self.adapter.get_customer_services(customer_id)
            dashboard.services = services
            dashboard.active_services = len([s for s in services if s.status.value == "active"])
            dashboard.total_services = len(services)

        # Get support tickets using shared ticketing service
        if self.config.ticketing_enabled and include_tickets:
            tickets = await self.ticket_service.get_customer_tickets(
                customer_id=str(customer_id), status=["open", "in_progress"], limit=5
            )
            dashboard.open_tickets = len(tickets)
            dashboard.recent_tickets = [
                {
                    "ticket_id": UUID(t.id),
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "created_at": t.created_at,
                    "last_update": t.updated_at,
                    "assigned_to": t.assigned_to,
                }
                for t in tickets[:3]
            ]

        # Get usage summary for ISP customers
        if self.config.portal_type == PortalType.ISP_CUSTOMER and self.config.usage_tracking_enabled and include_usage:
            dashboard.usage_summary = await self.adapter.get_usage_summary(customer_id)

        # Get platform-specific data
        dashboard.platform_data = await self.adapter.get_platform_data(customer_id)

        # Record metrics
        duration = (datetime.now() - start_time).total_seconds()
        self.monitoring.record_operation_duration(
            operation_name="get_customer_dashboard",
            duration=duration,
            success=True,
            labels={
                "portal_type": self.config.portal_type.value,
                "tenant_id": str(self.tenant_id),
            },
        )

        return dashboard

    async def update_customer_profile(
        self, customer_id: UUID, profile_update: CustomerProfileUpdate, updated_by: UUID
    ) -> dict[str, Any]:
        """Update customer profile using shared user management service."""

        # Convert to user management format
        user_update_data = {
            "first_name": profile_update.first_name,
            "last_name": profile_update.last_name,
            "email": profile_update.email,
            "phone": profile_update.phone,
            "address": {
                "street": profile_update.street_address,
                "city": profile_update.city,
                "state": profile_update.state_province,
                "postal_code": profile_update.postal_code,
                "country": profile_update.country,
            },
        }

        # Update through shared user service
        updated_user = await self.user_service.update_user(
            user_id=str(customer_id),
            update_data=user_update_data,
            updated_by=str(updated_by),
        )

        # Update platform-specific fields through adapter
        if profile_update.custom_fields:
            await self.adapter.update_customer_custom_fields(customer_id, profile_update.custom_fields)

        # Record activity
        self.monitoring.record_http_request(
            method="PUT",
            endpoint="customer_profile_update",
            status_code=200,
            duration=0.1,
            tenant_id=str(self.tenant_id),
        )

        return {"success": True, "updated_user": updated_user}

    async def get_service_usage(
        self,
        customer_id: UUID,
        service_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ServiceUsageData:
        """Get service usage data through platform adapter."""
        return await self.adapter.get_service_usage(
            customer_id=customer_id,
            service_id=service_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_billing_summary(self, customer_id: UUID) -> BillingSummary:
        """Get billing summary using shared billing service."""
        return await self._get_billing_summary(customer_id)

    async def create_support_ticket(
        self,
        customer_id: UUID,
        title: str,
        description: str,
        priority: str = "medium",
        category: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create support ticket using shared ticketing service."""

        ticket = await self.ticket_service.create_ticket(
            title=title,
            description=description,
            customer_id=str(customer_id),
            priority=priority,
            category=category,
            source="customer_portal",
            tenant_id=str(self.tenant_id),
        )

        return {
            "ticket_id": ticket.id,
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "created_at": ticket.created_at,
        }

    async def authenticate_customer(
        self, credentials: dict[str, Any], portal_context: dict[str, Any]
    ) -> PortalSessionData:
        """Authenticate customer for portal access."""
        return await self.portal_auth.authenticate_customer(
            credentials=credentials,
            portal_context=portal_context,
            tenant_id=self.tenant_id,
        )

    async def validate_session(self, session_id: UUID) -> Optional[PortalSessionData]:
        """Validate portal session."""
        return await self.portal_auth.validate_session(session_id)

    async def _get_billing_summary(self, customer_id: UUID) -> BillingSummary:
        """Internal method to get billing summary."""
        # Get current balance
        balance = await self.billing_service.get_customer_balance(str(customer_id))

        # Get recent invoices
        invoices = await self.billing_service.get_customer_invoices(customer_id=str(customer_id), limit=5)

        # Get recent payments
        payments = await self.billing_service.get_customer_payments(customer_id=str(customer_id), limit=5)

        # Get payment methods
        payment_methods = await self.billing_service.get_customer_payment_methods(str(customer_id))

        return BillingSummary(
            customer_id=customer_id,
            current_balance=Decimal(str(balance.amount)),
            next_bill_date=balance.next_bill_date,
            estimated_amount=balance.estimated_next_amount,
            recent_invoices=[
                {
                    "invoice_id": UUID(inv.id),
                    "invoice_number": inv.invoice_number,
                    "amount": Decimal(str(inv.total_amount)),
                    "due_date": inv.due_date,
                    "status": inv.status,
                    "created_at": inv.created_at,
                }
                for inv in invoices
            ],
            recent_payments=[
                {
                    "payment_id": UUID(pay.id),
                    "amount": Decimal(str(pay.amount)),
                    "payment_date": pay.payment_date,
                    "payment_method": pay.payment_method,
                    "status": pay.status,
                    "reference_number": pay.reference_number,
                }
                for pay in payments
            ],
            payment_methods=[
                {
                    "payment_method_id": UUID(pm.id),
                    "method_type": pm.method_type,
                    "display_name": pm.display_name,
                    "masked_details": pm.masked_details,
                    "is_default": pm.is_default,
                    "expires_at": pm.expires_at,
                    "status": pm.status,
                }
                for pm in payment_methods
            ],
        )


def create_portal_service(
    portal_type: PortalType,
    tenant_id: UUID,
    platform_config: Optional[dict[str, Any]] = None,
) -> CustomerPortalService:
    """Factory function to create portal service with appropriate adapter."""

    config = CustomerPortalConfig(
        portal_type=portal_type,
        tenant_id=tenant_id,
        platform_id="isp" if portal_type == PortalType.ISP_CUSTOMER else "management",
        **(platform_config or {}),
    )

    # Import and create appropriate adapter
    if portal_type == PortalType.ISP_CUSTOMER:
        from ..adapters.isp_adapter import ISPPortalAdapter

        adapter = ISPPortalAdapter(tenant_id)
    else:
        from ..adapters.management_adapter import ManagementPortalAdapter

        adapter = ManagementPortalAdapter(tenant_id)

    return CustomerPortalService(adapter=adapter, config=config, tenant_id=tenant_id)
