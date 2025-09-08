"""
Billing domain interfaces (ports).

These interfaces define the contracts that infrastructure components must implement.
The core domain depends only on these abstractions, not concrete implementations.
"""

from abc import abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, Optional, Protocol
from uuid import UUID

from .models import InvoiceStatus, PaymentStatus


class BillingRepository(Protocol):
    """Repository interface for billing data operations."""

    # Customer operations
    @abstractmethod
    async def get_customer(self, customer_id: UUID) -> Any:
        """Get customer by ID."""

    @abstractmethod
    async def create_customer(self, customer_data: dict[str, Any]) -> Any:
        """Create new customer."""

    # Subscription operations
    @abstractmethod
    async def get_subscription(self, subscription_id: UUID) -> Any:
        """Get subscription by ID."""

    @abstractmethod
    async def get_customer_subscriptions(self, customer_id: UUID) -> list[Any]:
        """Get all subscriptions for a customer."""

    @abstractmethod
    async def create_subscription(self, subscription_data: dict[str, Any]) -> Any:
        """Create new subscription."""

    @abstractmethod
    async def update_subscription(self, subscription_id: UUID, data: dict[str, Any]) -> Any:
        """Update subscription."""

    # Invoice operations
    @abstractmethod
    async def get_invoice(self, invoice_id: UUID) -> Any:
        """Get invoice by ID."""

    @abstractmethod
    async def create_invoice(self, invoice_data: dict[str, Any]) -> Any:
        """Create new invoice."""

    @abstractmethod
    async def update_invoice_status(self, invoice_id: UUID, status: InvoiceStatus) -> Any:
        """Update invoice status."""

    @abstractmethod
    async def get_due_subscriptions(self, as_of_date: date) -> list[Any]:
        """Get subscriptions due for billing."""

    # Payment operations
    @abstractmethod
    async def create_payment(self, payment_data: dict[str, Any]) -> Any:
        """Create new payment record."""

    @abstractmethod
    async def get_payment_by_idempotency_key(self, key: str) -> Optional[Any]:
        """Find payment by idempotency key."""

    @abstractmethod
    async def update_payment_status(self, payment_id: UUID, status: PaymentStatus) -> Any:
        """Update payment status."""

    # Usage operations
    @abstractmethod
    async def get_usage_records(
        self,
        subscription_id: UUID,
        start_date: date,
        end_date: date
    ) -> list[Any]:
        """Get usage records for billing period."""


class PaymentGateway(Protocol):
    """Payment gateway interface for processing payments."""

    @abstractmethod
    async def charge(
        self,
        amount: Decimal,
        payment_method_id: str,
        currency: str = "USD",
        description: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Charge a payment method."""

    @abstractmethod
    async def refund(
        self,
        charge_id: str,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """Process a refund."""

    @abstractmethod
    async def get_payment_methods(self, customer_id: str) -> list[dict[str, Any]]:
        """Get payment methods for customer."""


class TaxService(Protocol):
    """Tax calculation service interface."""

    @abstractmethod
    async def calculate_tax(
        self,
        amount: Decimal,
        tax_jurisdiction: Optional[str] = None,
        service_type: Optional[str] = None,
        customer_location: Optional[dict[str, str]] = None,
    ) -> Decimal:
        """Calculate tax amount for a line item."""

    @abstractmethod
    async def get_tax_rate(
        self,
        tax_jurisdiction: Optional[str] = None,
        service_type: Optional[str] = None,
    ) -> Decimal:
        """Get tax rate for jurisdiction and service type."""


class UsageService(Protocol):
    """Usage metering and rating service interface."""

    @abstractmethod
    async def aggregate_usage(
        self,
        subscription_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict[str, Decimal]:
        """Aggregate usage for billing period."""

    @abstractmethod
    async def calculate_usage_charges(
        self,
        usage_data: dict[str, Decimal],
        pricing_tiers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Calculate charges from usage data."""

    @abstractmethod
    async def handle_proration(
        self,
        base_amount: Decimal,
        proration_factor: Decimal,
    ) -> Decimal:
        """Apply proration to base amount."""


class NotificationService(Protocol):
    """Notification service for billing events."""

    @abstractmethod
    async def send_invoice_notification(
        self,
        customer_email: str,
        invoice_data: dict[str, Any],
    ) -> None:
        """Send invoice notification to customer."""

    @abstractmethod
    async def send_payment_notification(
        self,
        customer_email: str,
        payment_data: dict[str, Any],
    ) -> None:
        """Send payment confirmation to customer."""

    @abstractmethod
    async def send_failure_notification(
        self,
        customer_email: str,
        error_details: dict[str, Any],
    ) -> None:
        """Send payment failure notification."""
