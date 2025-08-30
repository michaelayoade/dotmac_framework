"""
ISP Platform Billing Adapter.

This adapter integrates the shared billing service with the ISP Framework,
mapping ISP-specific models and providing ISP-tailored billing functionality.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.service_factory import create_full_featured_billing_service
from ..services.billing_service import BillingService
from ..services.protocols import BillingServiceProtocol, DatabaseSessionProtocol

# ISP Framework imports (these would be the actual imports in practice)
try:
    from dotmac_isp.core.celery_app import celery_app
    from dotmac_isp.core.database import get_async_session
    from dotmac_isp.modules.billing.models import Invoice as ISPInvoice
    from dotmac_isp.modules.billing.models import Payment as ISPPayment
    from dotmac_isp.modules.billing.schemas import (
        BillingPlanResponse,
        InvoiceCreate,
        InvoiceUpdate,
        PaymentCreate,
        SubscriptionResponse,
    )
    from dotmac_isp.modules.identity.models import Customer as ISPCustomer
    from dotmac_isp.modules.services.models import ServiceInstance, ServicePlan
    from dotmac_isp.shared.base_service import BaseTenantService
except ImportError:
    # Fallback types for development/testing
    ISPInvoice = Dict[str, Any]
    ISPPayment = Dict[str, Any]
    ISPCustomer = Dict[str, Any]
    ServiceInstance = Dict[str, Any]
    ServicePlan = Dict[str, Any]


class ISPBillingAdapter:
    """
    Adapter that integrates shared billing service with ISP Framework.

    Provides ISP-specific billing operations while leveraging the shared
    billing service for core functionality.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        payment_gateway_config: Optional[Dict[str, Any]] = None,
        notification_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize ISP billing adapter."""
        self.db_session = db_session
        self.tenant_id = tenant_id

        # Create shared billing service with ISP-specific configuration
        config = self._build_isp_billing_config(
            payment_gateway_config, notification_config
        )
        self.billing_service = create_full_featured_billing_service(
            db=db_session,
            payment_config=config.get("payment_gateway", {}),
            notification_config=config.get("notifications", {}),
            tax_config=config.get("tax_calculation"),
            pdf_config=config.get("pdf_generation"),
            tenant_id=tenant_id,
        )

    def _build_isp_billing_config(
        self,
        payment_config: Optional[Dict[str, Any]] = None,
        notification_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build ISP-specific billing configuration."""
        config = {}

        # Default payment gateway configuration for ISP
        if payment_config:
            config["payment_gateway"] = payment_config
        else:
            # Default to Stripe for ISPs
            config["payment_gateway"] = {
                "type": "stripe",
                "options": {
                    "webhook_endpoint_secret": None,  # Set from environment
                    "automatic_payment_methods": True,
                    "capture_method": "automatic",
                },
            }

        # Default notification configuration for ISP
        if notification_config:
            config["notifications"] = notification_config
        else:
            config["notifications"] = {
                "type": "isp_notifications",
                "options": {
                    "email_provider": "sendgrid",
                    "sms_provider": "twilio",
                    "templates": {
                        "invoice_generated": "isp_invoice_template",
                        "payment_received": "isp_payment_confirmation",
                        "subscription_created": "isp_service_activation",
                        "subscription_cancelled": "isp_service_cancellation",
                        "payment_failed": "isp_payment_failure",
                    },
                },
            }

        # ISP-specific tax configuration
        config["tax_calculation"] = {
            "type": "isp_tax_calculator",
            "options": {
                "include_regulatory_fees": True,
                "telecom_tax_rates": True,
                "local_jurisdiction_lookup": True,
            },
        }

        # ISP-specific PDF generation
        config["pdf_generation"] = {
            "type": "isp_invoice_generator",
            "options": {
                "template": "isp_invoice_template.html",
                "include_service_details": True,
                "include_usage_breakdown": True,
                "company_branding": True,
            },
        }

        return config

    # Service Plan Management
    async def create_service_subscription(
        self,
        customer_id: UUID,
        service_plan: ServicePlan,
        service_instance: ServiceInstance,
        start_date: Optional[date] = None,
        custom_pricing: Optional[Dict[str, Any]] = None,
    ) -> SubscriptionResponse:
        """
        Create subscription for ISP service plan.

        Maps ISP ServicePlan to shared billing plan format.
        """

        # Map ISP ServicePlan to shared billing plan
        plan_id = self._get_or_create_billing_plan(service_plan)

        # Create subscription using shared service
        subscription_data = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "start_date": start_date,
            "quantity": getattr(service_instance, "quantity", 1),
            "metadata": {
                "service_instance_id": str(service_instance.id),
                "service_type": service_plan.service_type.value,
                "installation_address": getattr(
                    service_instance, "installation_address"
                ),
                **(custom_pricing or {}),
            },
        }

        if custom_pricing:
            subscription_data["custom_price"] = Decimal(
                str(custom_pricing.get("custom_price", 0))
            )

        subscription = await self.billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=start_date,
            **subscription_data,
        )

        # Convert to ISP response format
        return self._convert_to_isp_subscription_response(
            subscription, service_instance
        )

    async def cancel_service_subscription(
        self,
        service_instance_id: UUID,
        cancellation_date: Optional[date] = None,
        reason: Optional[str] = None,
    ) -> SubscriptionResponse:
        """Cancel subscription for ISP service instance."""

        # Find subscription by service instance
        subscription_id = await self._get_subscription_by_service_instance(
            service_instance_id
        )

        if not subscription_id:
            raise ValueError(
                f"No subscription found for service instance {service_instance_id}"
            )

        subscription = await self.billing_service.cancel_subscription(
            subscription_id=subscription_id, cancellation_date=cancellation_date
        )

        # Update subscription metadata
        if reason:
            subscription.metadata = subscription.metadata or {}
            subscription.metadata["cancellation_reason"] = reason
            await self.db_session.commit()

        return self._convert_to_isp_subscription_response(subscription)

    # Usage Recording for ISP Services
    async def record_service_usage(
        self,
        service_instance_id: UUID,
        usage_type: str,
        quantity: Decimal,
        usage_date: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record usage for ISP service (bandwidth, minutes, etc.)."""

        subscription_id = await self._get_subscription_by_service_instance(
            service_instance_id
        )

        if not subscription_id:
            raise ValueError(
                f"No subscription found for service instance {service_instance_id}"
            )

        usage_data = {
            "subscription_id": subscription_id,
            "usage_type": usage_type,
            "quantity": quantity,
            "usage_date": usage_date,
            "tenant_id": self.tenant_id,
            "metadata": {
                "service_instance_id": str(service_instance_id),
                **(metadata or {}),
            },
        }

        usage_record = await self.billing_service.record_usage(
            subscription_id, usage_data
        )

        return {
            "usage_record_id": usage_record.id,
            "subscription_id": subscription_id,
            "service_instance_id": service_instance_id,
            "usage_type": usage_type,
            "quantity": float(quantity),
            "recorded_at": usage_record.created_at.isoformat(),
        }

    # ISP-Specific Invoice Operations
    async def generate_service_invoice(
        self,
        subscription_id: UUID,
        billing_period_start: date,
        billing_period_end: date,
        include_usage_details: bool = True,
    ) -> ISPInvoice:
        """Generate invoice with ISP-specific formatting and details."""

        # Calculate billing period
        billing_period = await self._calculate_isp_billing_period(
            subscription_id, billing_period_start, billing_period_end
        )

        # Generate invoice using shared service
        invoice = await self.billing_service.generate_invoice(
            subscription_id, billing_period
        )

        # Enhance with ISP-specific details
        if include_usage_details:
            invoice = await self._add_isp_usage_details(invoice)

        return self._convert_to_isp_invoice(invoice)

    async def process_service_payment(
        self,
        invoice_id: UUID,
        payment_method_id: str,
        amount: Optional[Decimal] = None,
        payment_metadata: Optional[Dict[str, Any]] = None,
    ) -> ISPPayment:
        """Process payment for ISP service invoice."""

        # Add ISP-specific metadata
        metadata = {
            "platform": "isp_framework",
            "payment_source": "customer_portal",
            **(payment_metadata or {}),
        }

        payment = await self.billing_service.process_payment(
            invoice_id=invoice_id, payment_method_id=payment_method_id, amount=amount
        )

        # Add ISP-specific payment metadata
        payment.metadata = payment.metadata or {}
        payment.metadata.update(metadata)
        await self.db_session.commit()

        return self._convert_to_isp_payment(payment)

    # ISP Billing Cycle Management
    async def run_isp_billing_cycle(
        self,
        billing_date: Optional[date] = None,
        service_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run billing cycle for ISP services."""

        if billing_date is None:
            billing_date = date.today()

        # Get ISP-specific billing results
        results = await self.billing_service.run_billing_cycle(
            billing_date, self.tenant_id
        )

        # Enhanced ISP reporting
        isp_results = {
            **results,
            "billing_date": billing_date.isoformat(),
            "service_breakdown": await self._get_service_type_breakdown(results),
            "regulatory_fees_total": await self._calculate_regulatory_fees(results),
            "usage_overages_total": await self._calculate_usage_overages(results),
        }

        # Trigger ISP-specific post-billing tasks
        if results["processed_count"] > 0:
            await self._trigger_isp_post_billing_tasks(isp_results)

        return isp_results

    # Helper Methods
    async def _get_or_create_billing_plan(self, service_plan: ServicePlan) -> UUID:
        """Map ISP ServicePlan to shared billing plan."""
        # This would map ISP service plans to shared billing plans
        # Implementation depends on how ServicePlan maps to BillingPlan
        pass

    async def _get_subscription_by_service_instance(
        self, service_instance_id: UUID
    ) -> Optional[UUID]:
        """Find subscription ID by service instance ID."""
        # Query subscription by service instance metadata
        pass

    def _convert_to_isp_subscription_response(
        self, subscription, service_instance: Optional[ServiceInstance] = None
    ) -> SubscriptionResponse:
        """Convert shared subscription to ISP response format."""
        pass

    def _convert_to_isp_invoice(self, invoice) -> ISPInvoice:
        """Convert shared invoice to ISP invoice format."""
        pass

    def _convert_to_isp_payment(self, payment) -> ISPPayment:
        """Convert shared payment to ISP payment format."""
        pass

    async def _calculate_isp_billing_period(
        self, subscription_id: UUID, start_date: date, end_date: date
    ):
        """Calculate ISP-specific billing period with telecom usage."""
        pass

    async def _add_isp_usage_details(self, invoice):
        """Add ISP-specific usage details to invoice."""
        pass

    async def _get_service_type_breakdown(
        self, billing_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get breakdown by ISP service types."""
        pass

    async def _calculate_regulatory_fees(
        self, billing_results: Dict[str, Any]
    ) -> Decimal:
        """Calculate total regulatory fees for ISP services."""
        pass

    async def _calculate_usage_overages(
        self, billing_results: Dict[str, Any]
    ) -> Decimal:
        """Calculate total usage overages."""
        pass

    async def _trigger_isp_post_billing_tasks(self, billing_results: Dict[str, Any]):
        """Trigger ISP-specific tasks after billing cycle."""
        # Trigger Celery tasks for post-billing operations
        if celery_app:
            # Update service instances
            celery_app.send_task(
                "dotmac_isp.modules.services.tasks.update_service_billing_status",
                args=[billing_results],
            )

            # Send usage alerts
            celery_app.send_task(
                "dotmac_isp.modules.notifications.tasks.send_usage_alerts",
                args=[billing_results],
            )

            # Update customer service intelligence
            celery_app.send_task(
                "dotmac_isp.modules.services.tasks.update_customer_intelligence",
                args=[billing_results],
            )


class ISPBillingService(BaseTenantService):
    """
    ISP Framework billing service that wraps the shared billing adapter.

    This maintains compatibility with existing ISP Framework patterns
    while leveraging the shared billing service.
    """

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[UUID] = None):
        """Initialize ISP billing service."""
        super().__init__(db_session, tenant_id)
        self.adapter = ISPBillingAdapter(db_session, tenant_id)

    async def create_service_subscription(self, *args, **kwargs):
        """Create subscription (delegates to adapter)."""
        return await self.adapter.create_service_subscription(*args, **kwargs)

    async def cancel_service_subscription(self, *args, **kwargs):
        """Cancel subscription (delegates to adapter)."""
        return await self.adapter.cancel_service_subscription(*args, **kwargs)

    async def record_service_usage(self, *args, **kwargs):
        """Record usage (delegates to adapter)."""
        return await self.adapter.record_service_usage(*args, **kwargs)

    async def generate_service_invoice(self, *args, **kwargs):
        """Generate invoice (delegates to adapter)."""
        return await self.adapter.generate_service_invoice(*args, **kwargs)

    async def process_service_payment(self, *args, **kwargs):
        """Process payment (delegates to adapter)."""
        return await self.adapter.process_service_payment(*args, **kwargs)

    async def run_isp_billing_cycle(self, *args, **kwargs):
        """Run billing cycle (delegates to adapter)."""
        return await self.adapter.run_isp_billing_cycle(*args, **kwargs)


# Factory functions for easy integration
def create_isp_billing_adapter(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None, **config_options
) -> ISPBillingAdapter:
    """Create ISP billing adapter with standard configuration."""
    return ISPBillingAdapter(
        db_session=db_session, tenant_id=tenant_id, **config_options
    )


def create_isp_billing_service(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None
) -> ISPBillingService:
    """Create ISP billing service for framework integration."""
    return ISPBillingService(db_session, tenant_id)
