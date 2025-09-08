"""
Basic Billing Service Testing
Simple tests for billing functionality to build coverage.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

import pytest


class SubscriptionStatus(Enum):
    """Subscription status enumeration"""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class SimpleBillingService:
    """Simple billing service for testing"""

    def __init__(self):
        self.subscriptions = {}
        self.invoices = {}
        self.payments = {}
        self.next_id = 1

    def create_subscription(self, customer_id: str, plan_id: str, amount: Decimal) -> dict:
        """Create a new subscription"""
        subscription_id = f"sub_{self.next_id}"
        self.next_id += 1

        subscription = {
            "id": subscription_id,
            "customer_id": customer_id,
            "plan_id": plan_id,
            "amount": amount,
            "status": SubscriptionStatus.ACTIVE,
            "created_at": datetime.now(timezone.utc),
            "next_billing_date": datetime.now(timezone.utc) + timedelta(days=30)
        }

        self.subscriptions[subscription_id] = subscription
        return subscription

    def cancel_subscription(self, subscription_id: str) -> dict:
        """Cancel a subscription"""
        if subscription_id not in self.subscriptions:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription = self.subscriptions[subscription_id]
        subscription["status"] = SubscriptionStatus.CANCELLED
        subscription["cancelled_at"] = datetime.now(timezone.utc)

        return subscription

    def generate_invoice(self, subscription_id: str) -> dict:
        """Generate an invoice for a subscription"""
        if subscription_id not in self.subscriptions:
            raise ValueError(f"Subscription {subscription_id} not found")

        subscription = self.subscriptions[subscription_id]

        if subscription["status"] != SubscriptionStatus.ACTIVE:
            raise ValueError("Cannot invoice inactive subscription")

        invoice_id = f"inv_{self.next_id}"
        self.next_id += 1

        invoice = {
            "id": invoice_id,
            "subscription_id": subscription_id,
            "customer_id": subscription["customer_id"],
            "amount": subscription["amount"],
            "amount_due": subscription["amount"],
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "due_date": datetime.now(timezone.utc) + timedelta(days=7)
        }

        self.invoices[invoice_id] = invoice
        return invoice

    def process_payment(self, invoice_id: str, amount: Decimal, payment_method: str = "card") -> dict:
        """Process a payment for an invoice"""
        if invoice_id not in self.invoices:
            raise ValueError(f"Invoice {invoice_id} not found")

        invoice = self.invoices[invoice_id]

        if invoice["status"] != "pending":
            raise ValueError("Invoice is not pending payment")

        if amount < invoice["amount_due"]:
            raise ValueError("Payment amount insufficient")

        payment_id = f"pay_{self.next_id}"
        self.next_id += 1

        payment = {
            "id": payment_id,
            "invoice_id": invoice_id,
            "amount": amount,
            "payment_method": payment_method,
            "status": "completed",
            "processed_at": datetime.now(timezone.utc)
        }

        # Update invoice
        invoice["status"] = "paid"
        invoice["paid_at"] = datetime.now(timezone.utc)
        invoice["amount_due"] = Decimal("0.00")

        self.payments[payment_id] = payment
        return payment

    def get_customer_subscriptions(self, customer_id: str) -> list:
        """Get all subscriptions for a customer"""
        return [
            sub for sub in self.subscriptions.values()
            if sub["customer_id"] == customer_id
        ]

    def calculate_tax(self, amount: Decimal, tax_rate: Decimal = Decimal("0.1")) -> Decimal:
        """Calculate tax amount"""
        return amount * tax_rate


class TestBasicBillingService:
    """Basic billing service tests for coverage"""

    @pytest.fixture
    def billing_service(self):
        """Create billing service instance"""
        return SimpleBillingService()

    def test_create_subscription_success(self, billing_service):
        """Test successful subscription creation"""
        customer_id = "cust_123"
        plan_id = "plan_basic"
        amount = Decimal("29.99")

        subscription = billing_service.create_subscription(customer_id, plan_id, amount)

        assert subscription["customer_id"] == customer_id
        assert subscription["plan_id"] == plan_id
        assert subscription["amount"] == amount
        assert subscription["status"] == SubscriptionStatus.ACTIVE
        assert "id" in subscription
        assert "created_at" in subscription
        assert "next_billing_date" in subscription

    def test_cancel_subscription_success(self, billing_service):
        """Test successful subscription cancellation"""
        # Create subscription first
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))

        # Cancel subscription
        cancelled = billing_service.cancel_subscription(subscription["id"])

        assert cancelled["status"] == SubscriptionStatus.CANCELLED
        assert "cancelled_at" in cancelled

    def test_cancel_nonexistent_subscription(self, billing_service):
        """Test cancellation of nonexistent subscription"""
        with pytest.raises(ValueError) as exc_info:
            billing_service.cancel_subscription("nonexistent_sub")

        assert "not found" in str(exc_info.value)

    def test_generate_invoice_success(self, billing_service):
        """Test successful invoice generation"""
        # Create subscription first
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))

        # Generate invoice
        invoice = billing_service.generate_invoice(subscription["id"])

        assert invoice["subscription_id"] == subscription["id"]
        assert invoice["customer_id"] == subscription["customer_id"]
        assert invoice["amount"] == subscription["amount"]
        assert invoice["amount_due"] == subscription["amount"]
        assert invoice["status"] == "pending"
        assert "id" in invoice
        assert "created_at" in invoice
        assert "due_date" in invoice

    def test_generate_invoice_for_cancelled_subscription(self, billing_service):
        """Test invoice generation for cancelled subscription"""
        # Create and cancel subscription
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))
        billing_service.cancel_subscription(subscription["id"])

        # Try to generate invoice
        with pytest.raises(ValueError) as exc_info:
            billing_service.generate_invoice(subscription["id"])

        assert "inactive subscription" in str(exc_info.value)

    def test_process_payment_success(self, billing_service):
        """Test successful payment processing"""
        # Create subscription and invoice
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))
        invoice = billing_service.generate_invoice(subscription["id"])

        # Process payment
        payment = billing_service.process_payment(invoice["id"], invoice["amount"])

        assert payment["invoice_id"] == invoice["id"]
        assert payment["amount"] == invoice["amount"]
        assert payment["status"] == "completed"
        assert "id" in payment
        assert "processed_at" in payment

        # Check invoice is updated
        updated_invoice = billing_service.invoices[invoice["id"]]
        assert updated_invoice["status"] == "paid"
        assert updated_invoice["amount_due"] == Decimal("0.00")

    def test_process_payment_insufficient_amount(self, billing_service):
        """Test payment processing with insufficient amount"""
        # Create subscription and invoice
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))
        invoice = billing_service.generate_invoice(subscription["id"])

        # Try to pay insufficient amount
        insufficient_amount = invoice["amount"] - Decimal("5.00")

        with pytest.raises(ValueError) as exc_info:
            billing_service.process_payment(invoice["id"], insufficient_amount)

        assert "insufficient" in str(exc_info.value)

    def test_process_payment_for_nonexistent_invoice(self, billing_service):
        """Test payment processing for nonexistent invoice"""
        with pytest.raises(ValueError) as exc_info:
            billing_service.process_payment("nonexistent_inv", Decimal("29.99"))

        assert "not found" in str(exc_info.value)

    def test_get_customer_subscriptions(self, billing_service):
        """Test retrieving customer subscriptions"""
        customer_id = "cust_123"

        # Create multiple subscriptions
        sub1 = billing_service.create_subscription(customer_id, "plan_basic", Decimal("29.99"))
        sub2 = billing_service.create_subscription(customer_id, "plan_premium", Decimal("49.99"))
        sub3 = billing_service.create_subscription("other_customer", "plan_basic", Decimal("29.99"))

        # Get subscriptions for customer
        customer_subs = billing_service.get_customer_subscriptions(customer_id)

        assert len(customer_subs) == 2
        sub_ids = [sub["id"] for sub in customer_subs]
        assert sub1["id"] in sub_ids
        assert sub2["id"] in sub_ids
        assert sub3["id"] not in sub_ids

    def test_calculate_tax(self, billing_service):
        """Test tax calculation"""
        amount = Decimal("100.00")

        # Default tax rate (10%)
        tax = billing_service.calculate_tax(amount)
        assert tax == Decimal("10.00")

        # Custom tax rate (15%)
        tax_custom = billing_service.calculate_tax(amount, Decimal("0.15"))
        assert tax_custom == Decimal("15.00")

    def test_subscription_status_transitions(self, billing_service):
        """Test subscription status transitions"""
        # Create subscription
        subscription = billing_service.create_subscription("cust_123", "plan_basic", Decimal("29.99"))
        assert subscription["status"] == SubscriptionStatus.ACTIVE

        # Cancel subscription
        cancelled = billing_service.cancel_subscription(subscription["id"])
        assert cancelled["status"] == SubscriptionStatus.CANCELLED

    def test_billing_flow_end_to_end(self, billing_service):
        """Test complete billing flow"""
        customer_id = "cust_123"
        plan_id = "plan_basic"
        amount = Decimal("29.99")

        # 1. Create subscription
        subscription = billing_service.create_subscription(customer_id, plan_id, amount)
        assert subscription["status"] == SubscriptionStatus.ACTIVE

        # 2. Generate invoice
        invoice = billing_service.generate_invoice(subscription["id"])
        assert invoice["status"] == "pending"

        # 3. Process payment
        payment = billing_service.process_payment(invoice["id"], invoice["amount"])
        assert payment["status"] == "completed"

        # 4. Verify invoice is paid
        updated_invoice = billing_service.invoices[invoice["id"]]
        assert updated_invoice["status"] == "paid"

        # 5. Verify payment is recorded
        assert payment["id"] in billing_service.payments
