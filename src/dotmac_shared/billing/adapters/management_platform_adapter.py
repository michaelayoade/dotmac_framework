"""
Management Platform Billing Adapter.

This adapter integrates the shared billing service with the Management Platform,
providing tenant billing, plugin licensing, and SaaS subscription management.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters.service_factory import create_full_featured_billing_service
from ..services.billing_service import BillingService
from ..services.protocols import BillingServiceProtocol

# Management Platform imports (these would be the actual imports in practice)
try:
    from dotmac_management.core.database import get_async_session
    from dotmac_management.models.billing import (
        PluginLicense,
        ResourceUsage,
        TenantInvoice,
        TenantPayment,
    )
    from dotmac_management.models.tenant import Tenant, TenantSubscription
    from dotmac_management.schemas.billing import (
        BillingReport,
        PluginLicenseCreate,
        ResourceUsageCreate,
        TenantSubscriptionCreate,
    )
    from dotmac_management.services.stripe_service import StripeService
    from dotmac_management.workers.tasks.billing_tasks import (
        process_tenant_billing,
        send_billing_alerts,
        update_resource_limits,
    )
except ImportError:
    # Fallback types for development/testing
    Tenant = Dict[str, Any]
    TenantSubscription = Dict[str, Any]
    PluginLicense = Dict[str, Any]
    ResourceUsage = Dict[str, Any]
    TenantInvoice = Dict[str, Any]
    TenantPayment = Dict[str, Any]


class ManagementPlatformBillingAdapter:
    """
    Adapter that integrates shared billing service with Management Platform.

    Handles tenant subscriptions, plugin licensing, resource usage billing,
    and SaaS-specific billing operations.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        stripe_config: Optional[Dict[str, Any]] = None,
        notification_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Management Platform billing adapter."""
        self.db_session = db_session
        self.tenant_id = tenant_id

        # Create shared billing service with Management Platform configuration
        config = self._build_management_billing_config(
            stripe_config, notification_config
        )
        self.billing_service = create_full_featured_billing_service(
            db=db_session,
            payment_config=config.get("payment_gateway", {}),
            notification_config=config.get("notifications", {}),
            tax_config=config.get("tax_calculation"),
            pdf_config=config.get("pdf_generation"),
            tenant_id=tenant_id,
        )

        # Initialize Stripe service for advanced SaaS features
        if stripe_config:
            self.stripe_service = StripeService(**stripe_config)
        else:
            self.stripe_service = None

    def _build_management_billing_config(
        self,
        stripe_config: Optional[Dict[str, Any]] = None,
        notification_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build Management Platform specific billing configuration."""
        config = {}

        # Stripe payment gateway (primary for SaaS)
        if stripe_config:
            config["payment_gateway"] = {
                "type": "stripe",
                "options": {
                    **stripe_config,
                    "subscription_management": True,
                    "usage_reporting": True,
                    "proration_handling": True,
                },
            }

        # Management Platform notification configuration
        if notification_config:
            config["notifications"] = notification_config
        else:
            config["notifications"] = {
                "type": "management_notifications",
                "options": {
                    "email_provider": "sendgrid",
                    "slack_integration": True,
                    "webhook_notifications": True,
                    "templates": {
                        "tenant_subscription_created": "saas_welcome_template",
                        "subscription_cancelled": "saas_cancellation_template",
                        "payment_failed": "saas_payment_failure",
                        "usage_limit_warning": "saas_usage_warning",
                        "plugin_license_expired": "plugin_renewal_reminder",
                    },
                },
            }

        # SaaS-specific tax configuration
        config["tax_calculation"] = {
            "type": "saas_tax_calculator",
            "options": {
                "digital_services_tax": True,
                "eu_vat_compliance": True,
                "reverse_charge_mechanism": True,
                "tax_exemption_handling": True,
            },
        }

        # SaaS invoice PDF generation
        config["pdf_generation"] = {
            "type": "saas_invoice_generator",
            "options": {
                "template": "saas_invoice_template.html",
                "include_usage_breakdown": True,
                "plugin_license_details": True,
                "white_label_branding": True,
            },
        }

        return config

    # Tenant Subscription Management
    async def create_tenant_subscription(
        self,
        tenant: Tenant,
        plan_type: str,
        billing_cycle: str = "monthly",
        trial_days: int = 14,
        custom_limits: Optional[Dict[str, Any]] = None,
    ) -> TenantSubscription:
        """Create subscription for a tenant with SaaS plan."""

        # Map tenant plan to shared billing plan
        plan_id = await self._get_or_create_saas_billing_plan(plan_type, billing_cycle)

        # Create customer record for tenant
        customer_id = await self._get_or_create_tenant_customer(tenant)

        # Create subscription using shared service
        subscription_data = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "start_date": date.today(),
            "quantity": 1,
            "metadata": {
                "tenant_id": str(tenant.id),
                "platform": "management_platform",
                "plan_type": plan_type,
                "resource_limits": custom_limits or {},
                "trial_days": trial_days,
            },
        }

        subscription = await self.billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=date.today(),
            **subscription_data,
        )

        # Create Management Platform subscription record
        tenant_subscription = await self._create_tenant_subscription_record(
            tenant, subscription, plan_type, custom_limits
        )

        # Set up resource limits
        await self._setup_tenant_resource_limits(tenant.id, custom_limits or {})

        return tenant_subscription

    async def upgrade_tenant_subscription(
        self, tenant_id: UUID, new_plan_type: str, upgrade_date: Optional[date] = None
    ) -> TenantSubscription:
        """Upgrade tenant subscription to a higher plan."""

        # Get current subscription
        current_subscription_id = await self._get_tenant_subscription_id(tenant_id)

        if not current_subscription_id:
            raise ValueError(f"No subscription found for tenant {tenant_id}")

        # Get new plan
        new_plan_id = await self._get_or_create_saas_billing_plan(new_plan_type)

        # Change plan using shared service
        subscription = await self.billing_service.change_plan(
            subscription_id=current_subscription_id,
            new_plan_id=new_plan_id,
            change_date=upgrade_date or date.today(),
        )

        # Update tenant subscription record
        tenant_subscription = await self._update_tenant_subscription_record(
            tenant_id, subscription, new_plan_type
        )

        # Update resource limits
        new_limits = await self._get_plan_resource_limits(new_plan_type)
        await self._setup_tenant_resource_limits(tenant_id, new_limits)

        # Trigger upgrade tasks
        await self._trigger_subscription_upgrade_tasks(tenant_id, new_plan_type)

        return tenant_subscription

    # Plugin License Billing
    async def create_plugin_license(
        self,
        tenant_id: UUID,
        plugin_name: str,
        license_type: str = "monthly",
        seats: int = 1,
        custom_pricing: Optional[Decimal] = None,
    ) -> PluginLicense:
        """Create plugin license subscription for tenant."""

        # Get plugin billing plan
        plan_id = await self._get_or_create_plugin_billing_plan(
            plugin_name, license_type
        )

        # Get tenant's customer ID
        customer_id = await self._get_tenant_customer_id(tenant_id)

        # Create plugin subscription
        subscription_data = {
            "customer_id": customer_id,
            "plan_id": plan_id,
            "start_date": date.today(),
            "quantity": seats,
            "metadata": {
                "tenant_id": str(tenant_id),
                "plugin_name": plugin_name,
                "license_type": license_type,
                "billing_type": "plugin_license",
            },
        }

        if custom_pricing:
            subscription_data["custom_price"] = custom_pricing

        subscription = await self.billing_service.create_subscription(
            customer_id=customer_id,
            plan_id=plan_id,
            start_date=date.today(),
            **subscription_data,
        )

        # Create plugin license record
        plugin_license = await self._create_plugin_license_record(
            tenant_id, plugin_name, subscription, seats
        )

        return plugin_license

    # Resource Usage Billing
    async def record_resource_usage(
        self,
        tenant_id: UUID,
        resource_type: str,
        quantity: Decimal,
        usage_date: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ResourceUsage:
        """Record resource usage for tenant billing."""

        subscription_id = await self._get_tenant_subscription_id(tenant_id)

        if not subscription_id:
            raise ValueError(f"No subscription found for tenant {tenant_id}")

        # Record usage through shared service
        usage_data = {
            "subscription_id": subscription_id,
            "usage_type": resource_type,
            "quantity": quantity,
            "usage_date": usage_date,
            "tenant_id": self.tenant_id,
            "metadata": {
                "tenant_id": str(tenant_id),
                "resource_type": resource_type,
                "platform": "management_platform",
                **(metadata or {}),
            },
        }

        usage_record = await self.billing_service.record_usage(
            subscription_id, usage_data
        )

        # Create Management Platform usage record
        resource_usage = await self._create_resource_usage_record(
            tenant_id, resource_type, quantity, usage_date, usage_record.id
        )

        # Check for usage limits and send alerts
        await self._check_usage_limits(tenant_id, resource_type, quantity)

        return resource_usage

    # SaaS Billing Operations
    async def generate_tenant_invoice(
        self,
        tenant_id: UUID,
        billing_period_start: date,
        billing_period_end: date,
        include_usage_details: bool = True,
    ) -> TenantInvoice:
        """Generate invoice for tenant with all subscriptions and usage."""

        subscription_id = await self._get_tenant_subscription_id(tenant_id)

        if not subscription_id:
            raise ValueError(f"No subscription found for tenant {tenant_id}")

        # Calculate billing period
        billing_period = await self._calculate_saas_billing_period(
            subscription_id, billing_period_start, billing_period_end
        )

        # Generate invoice using shared service
        invoice = await self.billing_service.generate_invoice(
            subscription_id, billing_period
        )

        # Add plugin license charges
        invoice = await self._add_plugin_license_charges(
            invoice, tenant_id, billing_period
        )

        # Add usage-based charges
        if include_usage_details:
            invoice = await self._add_resource_usage_charges(
                invoice, tenant_id, billing_period
            )

        # Create Management Platform invoice record
        tenant_invoice = await self._create_tenant_invoice_record(tenant_id, invoice)

        return tenant_invoice

    async def process_tenant_payment(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        payment_method_id: str,
        amount: Optional[Decimal] = None,
    ) -> TenantPayment:
        """Process payment for tenant invoice."""

        # Process payment through shared service
        payment = await self.billing_service.process_payment(
            invoice_id=invoice_id, payment_method_id=payment_method_id, amount=amount
        )

        # Add Management Platform metadata
        payment.metadata = payment.metadata or {}
        payment.metadata.update(
            {
                "tenant_id": str(tenant_id),
                "platform": "management_platform",
                "payment_source": "tenant_billing",
            }
        )
        await self.db_session.commit()

        # Create tenant payment record
        tenant_payment = await self._create_tenant_payment_record(tenant_id, payment)

        # Update tenant status if needed
        await self._update_tenant_billing_status(tenant_id, payment)

        return tenant_payment

    # SaaS Billing Cycle Management
    async def run_saas_billing_cycle(
        self,
        billing_date: Optional[date] = None,
        tenant_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run billing cycle for SaaS tenants."""

        if billing_date is None:
            billing_date = date.today()

        # Run billing cycle through shared service
        results = await self.billing_service.run_billing_cycle(
            billing_date, self.tenant_id
        )

        # Enhanced SaaS reporting
        saas_results = {
            **results,
            "billing_date": billing_date.isoformat(),
            "tenant_breakdown": await self._get_tenant_billing_breakdown(results),
            "plugin_license_revenue": await self._calculate_plugin_revenue(results),
            "usage_based_revenue": await self._calculate_usage_revenue(results),
            "churn_analysis": await self._calculate_churn_metrics(billing_date),
        }

        # Trigger SaaS-specific post-billing tasks
        if results["processed_count"] > 0:
            await self._trigger_saas_post_billing_tasks(saas_results)

        return saas_results

    # Helper Methods
    async def _get_or_create_saas_billing_plan(
        self, plan_type: str, billing_cycle: str = "monthly"
    ) -> UUID:
        """Get or create SaaS billing plan."""
        pass

    async def _get_or_create_plugin_billing_plan(
        self, plugin_name: str, license_type: str
    ) -> UUID:
        """Get or create plugin billing plan."""
        pass

    async def _get_or_create_tenant_customer(self, tenant: Tenant) -> UUID:
        """Get or create customer record for tenant."""
        pass

    async def _get_tenant_customer_id(self, tenant_id: UUID) -> UUID:
        """Get customer ID for tenant."""
        pass

    async def _get_tenant_subscription_id(self, tenant_id: UUID) -> Optional[UUID]:
        """Get subscription ID for tenant."""
        pass

    async def _create_tenant_subscription_record(
        self,
        tenant: Tenant,
        subscription,
        plan_type: str,
        custom_limits: Optional[Dict[str, Any]],
    ) -> TenantSubscription:
        """Create tenant subscription record."""
        pass

    async def _setup_tenant_resource_limits(
        self, tenant_id: UUID, resource_limits: Dict[str, Any]
    ):
        """Set up resource limits for tenant."""
        pass

    async def _check_usage_limits(
        self, tenant_id: UUID, resource_type: str, quantity: Decimal
    ):
        """Check if tenant is approaching usage limits."""
        pass

    async def _trigger_saas_post_billing_tasks(self, billing_results: Dict[str, Any]):
        """Trigger SaaS-specific tasks after billing cycle."""
        # Trigger async tasks for post-billing operations
        try:
            # Update tenant billing status
            process_tenant_billing.delay(billing_results)

            # Update resource limits based on payments
            update_resource_limits.delay(billing_results)

            # Send billing alerts and notifications
            send_billing_alerts.delay(billing_results)

        except Exception as e:
            # Log error but don't fail billing
            pass


class ManagementPlatformBillingService:
    """
    Management Platform billing service that wraps the shared billing adapter.

    Provides SaaS-specific billing operations while maintaining compatibility
    with existing Management Platform patterns.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        tenant_id: Optional[UUID] = None,
        stripe_config: Optional[Dict[str, Any]] = None,
    ):
        """Initialize Management Platform billing service."""
        self.db_session = db_session
        self.tenant_id = tenant_id
        self.adapter = ManagementPlatformBillingAdapter(
            db_session, tenant_id, stripe_config
        )

    async def create_tenant_subscription(self, *args, **kwargs):
        """Create tenant subscription (delegates to adapter)."""
        return await self.adapter.create_tenant_subscription(*args, **kwargs)

    async def upgrade_tenant_subscription(self, *args, **kwargs):
        """Upgrade tenant subscription (delegates to adapter)."""
        return await self.adapter.upgrade_tenant_subscription(*args, **kwargs)

    async def create_plugin_license(self, *args, **kwargs):
        """Create plugin license (delegates to adapter)."""
        return await self.adapter.create_plugin_license(*args, **kwargs)

    async def record_resource_usage(self, *args, **kwargs):
        """Record resource usage (delegates to adapter)."""
        return await self.adapter.record_resource_usage(*args, **kwargs)

    async def generate_tenant_invoice(self, *args, **kwargs):
        """Generate tenant invoice (delegates to adapter)."""
        return await self.adapter.generate_tenant_invoice(*args, **kwargs)

    async def process_tenant_payment(self, *args, **kwargs):
        """Process tenant payment (delegates to adapter)."""
        return await self.adapter.process_tenant_payment(*args, **kwargs)

    async def run_saas_billing_cycle(self, *args, **kwargs):
        """Run SaaS billing cycle (delegates to adapter)."""
        return await self.adapter.run_saas_billing_cycle(*args, **kwargs)


# Factory functions for easy integration
def create_management_billing_adapter(
    db_session: AsyncSession, tenant_id: Optional[UUID] = None, **config_options
) -> ManagementPlatformBillingAdapter:
    """Create Management Platform billing adapter with standard configuration."""
    return ManagementPlatformBillingAdapter(
        db_session=db_session, tenant_id=tenant_id, **config_options
    )


def create_management_billing_service(
    db_session: AsyncSession,
    tenant_id: Optional[UUID] = None,
    stripe_config: Optional[Dict[str, Any]] = None,
) -> ManagementPlatformBillingService:
    """Create Management Platform billing service."""
    return ManagementPlatformBillingService(db_session, tenant_id, stripe_config)
