"""
Service factory for creating platform-specific billing service instances.

This factory provides a unified way to create billing services that work
with different platform configurations while maintaining consistent interfaces.
"""

from typing import Any, Dict, Optional, Type
from uuid import UUID

from ..repositories.billing_repositories import (
    BillingPlanRepository,
    CustomerRepository,
    InvoiceRepository,
    PaymentRepository,
    SubscriptionRepository,
    UsageRepository,
)
from ..services.billing_service import BillingService
from ..services.protocols import (
    BillingServiceProtocol,
    DatabaseSessionProtocol,
    NotificationServiceProtocol,
    PaymentGatewayProtocol,
    PdfGeneratorProtocol,
    TaxCalculationServiceProtocol,
)


class BillingServiceFactory:
    """Factory for creating billing service instances."""

    def __init__(self):
        """Initialize the factory."""
        self._payment_gateways: Dict[str, Type[PaymentGatewayProtocol]] = {}
        self._notification_services: Dict[str, Type[NotificationServiceProtocol]] = {}
        self._tax_services: Dict[str, Type[TaxCalculationServiceProtocol]] = {}
        self._pdf_generators: Dict[str, Type[PdfGeneratorProtocol]] = {}

    def register_payment_gateway(
        self, name: str, gateway_class: Type[PaymentGatewayProtocol]
    ) -> None:
        """Register a payment gateway implementation."""
        self._payment_gateways[name] = gateway_class

    def register_notification_service(
        self, name: str, service_class: Type[NotificationServiceProtocol]
    ) -> None:
        """Register a notification service implementation."""
        self._notification_services[name] = service_class

    def register_tax_service(
        self, name: str, service_class: Type[TaxCalculationServiceProtocol]
    ) -> None:
        """Register a tax calculation service implementation."""
        self._tax_services[name] = service_class

    def register_pdf_generator(
        self, name: str, generator_class: Type[PdfGeneratorProtocol]
    ) -> None:
        """Register a PDF generator implementation."""
        self._pdf_generators[name] = generator_class

    def create_billing_service(
        self,
        db: DatabaseSessionProtocol,
        config: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[UUID] = None,
    ) -> BillingServiceProtocol:
        """
        Create a billing service instance with all dependencies.

        Args:
            db: Database session
            config: Configuration dictionary
            tenant_id: Default tenant ID for operations

        Returns:
            Configured billing service instance
        """
        config = config or {}

        # Create repositories
        customer_repo = CustomerRepository(db)
        plan_repo = BillingPlanRepository(db)
        subscription_repo = SubscriptionRepository(db)
        invoice_repo = InvoiceRepository(db)
        payment_repo = PaymentRepository(db)
        usage_repo = UsageRepository(db)

        # Create external service instances
        payment_gateway = self._create_payment_gateway(
            config.get("payment_gateway", {})
        )
        notification_service = self._create_notification_service(
            config.get("notifications", {})
        )
        tax_service = self._create_tax_service(config.get("tax_calculation", {}))
        pdf_generator = self._create_pdf_generator(config.get("pdf_generation", {}))

        # Create billing service
        billing_service = BillingService(
            db=db,
            customer_repo=customer_repo,
            plan_repo=plan_repo,
            subscription_repo=subscription_repo,
            invoice_repo=invoice_repo,
            payment_repo=payment_repo,
            usage_repo=usage_repo,
            payment_gateway=payment_gateway,
            notification_service=notification_service,
            tax_service=tax_service,
            pdf_generator=pdf_generator,
            default_tenant_id=tenant_id,
        )

        return billing_service

    def _create_payment_gateway(
        self, config: Dict[str, Any]
    ) -> Optional[PaymentGatewayProtocol]:
        """Create payment gateway instance from config."""
        gateway_type = config.get("type")
        if not gateway_type or gateway_type not in self._payment_gateways:
            return None

        gateway_class = self._payment_gateways[gateway_type]
        return gateway_class(**config.get("options", {}))

    def _create_notification_service(
        self, config: Dict[str, Any]
    ) -> Optional[NotificationServiceProtocol]:
        """Create notification service instance from config."""
        service_type = config.get("type")
        if not service_type or service_type not in self._notification_services:
            return None

        service_class = self._notification_services[service_type]
        return service_class(**config.get("options", {}))

    def _create_tax_service(
        self, config: Dict[str, Any]
    ) -> Optional[TaxCalculationServiceProtocol]:
        """Create tax calculation service instance from config."""
        service_type = config.get("type")
        if not service_type or service_type not in self._tax_services:
            return None

        service_class = self._tax_services[service_type]
        return service_class(**config.get("options", {}))

    def _create_pdf_generator(
        self, config: Dict[str, Any]
    ) -> Optional[PdfGeneratorProtocol]:
        """Create PDF generator instance from config."""
        generator_type = config.get("type")
        if not generator_type or generator_type not in self._pdf_generators:
            return None

        generator_class = self._pdf_generators[generator_type]
        return generator_class(**config.get("options", {}))


# Global factory instance
billing_service_factory = BillingServiceFactory()


# Convenience functions for common configurations
def create_basic_billing_service(
    db: DatabaseSessionProtocol, tenant_id: Optional[UUID] = None
) -> BillingServiceProtocol:
    """Create a basic billing service without external integrations."""
    return billing_service_factory.create_billing_service(db, tenant_id=tenant_id)


def create_stripe_billing_service(
    db: DatabaseSessionProtocol,
    stripe_secret_key: str,
    tenant_id: Optional[UUID] = None,
    **kwargs,
) -> BillingServiceProtocol:
    """Create a billing service with Stripe payment integration."""
    config = {
        "payment_gateway": {
            "type": "stripe",
            "options": {"secret_key": stripe_secret_key, **kwargs},
        }
    }
    return billing_service_factory.create_billing_service(db, config, tenant_id)


def create_full_featured_billing_service(
    db: DatabaseSessionProtocol,
    payment_config: Dict[str, Any],
    notification_config: Dict[str, Any],
    tax_config: Optional[Dict[str, Any]] = None,
    pdf_config: Optional[Dict[str, Any]] = None,
    tenant_id: Optional[UUID] = None,
) -> BillingServiceProtocol:
    """Create a fully configured billing service with all integrations."""
    config = {"payment_gateway": payment_config, "notifications": notification_config}

    if tax_config:
        config["tax_calculation"] = tax_config

    if pdf_config:
        config["pdf_generation"] = pdf_config

    return billing_service_factory.create_billing_service(db, config, tenant_id)
