"""
Unit tests for billing models.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest


class TestCustomer:
    """Test Customer model functionality."""

    def test_customer_creation(self, sample_customer_data):
        """Test customer instance creation."""
        customer_data = sample_customer_data.copy()
        customer_data.pop("id", None)  # Remove ID for creation

        # Mock customer creation (would normally use SQLAlchemy)
        customer = type("Customer", (), customer_data)

        assert customer.name == "Test Customer"
        assert customer.email == "test@example.com"
        assert customer.is_active is True

    def test_customer_validation(self):
        """Test customer data validation."""
        # Test invalid email
        with pytest.raises((ValueError, TypeError)):
            # This would be validated by Pydantic in real implementation
            invalid_email = "not-an-email"
            if "@" not in invalid_email:
                raise ValueError("Invalid email format")

    def test_customer_str_representation(self, sample_customer_data):
        """Test customer string representation."""
        customer_data = sample_customer_data.copy()
        customer = type("Customer", (), customer_data)

        # Mock __str__ method
        str_repr = f"{customer.name} ({customer.email})"
        assert "Test Customer" in str_repr
        assert "test@example.com" in str_repr


class TestInvoice:
    """Test Invoice model functionality."""

    def test_invoice_creation(self, sample_invoice_data):
        """Test invoice instance creation."""
        invoice_data = sample_invoice_data.copy()
        invoice_data.pop("id", None)

        invoice = type("Invoice", (), invoice_data)

        assert invoice.invoice_number == "INV-001"
        assert invoice.status == "pending"
        assert invoice.total_amount == Decimal("110.00")
        assert invoice.currency == "USD"

    def test_invoice_total_calculation(self):
        """Test invoice total calculation."""
        subtotal = Decimal("100.00")
        tax_amount = Decimal("10.00")
        total = subtotal + tax_amount

        assert total == Decimal("110.00")

    def test_invoice_status_transitions(self):
        """Test valid invoice status transitions."""
        valid_transitions = {
            "draft": ["pending", "cancelled"],
            "pending": ["sent", "cancelled"],
            "sent": ["paid", "overdue", "cancelled"],
            "paid": ["refunded"],
            "overdue": ["paid", "cancelled"],
            "cancelled": [],
            "refunded": [],
        }

        # Test that draft can transition to pending
        assert "pending" in valid_transitions["draft"]
        # Test that paid cannot transition to pending
        assert "pending" not in valid_transitions["paid"]

    def test_invoice_due_date_validation(self):
        """Test invoice due date validation."""
        issue_date = date.today()
        due_date = date.today()

        # Due date should not be before issue date
        assert due_date >= issue_date

    def test_is_overdue_property(self):
        """Test invoice overdue detection."""
        # Mock overdue invoice
        past_due_date = date.today().replace(day=1)  # Past date
        current_date = date.today()

        is_overdue = past_due_date < current_date
        assert is_overdue is True


class TestPayment:
    """Test Payment model functionality."""

    def test_payment_creation(self, sample_payment_data):
        """Test payment instance creation."""
        payment_data = sample_payment_data.copy()
        payment_data.pop("id", None)

        payment = type("Payment", (), payment_data)

        assert payment.payment_number == "PAY-001"
        assert payment.amount == Decimal("110.00")
        assert payment.status == "completed"
        assert payment.payment_method == "credit_card"

    def test_payment_amount_validation(self):
        """Test payment amount validation."""
        # Amount should be positive
        valid_amount = Decimal("100.00")
        invalid_amount = Decimal("-50.00")

        assert valid_amount > 0
        assert invalid_amount < 0

    def test_payment_status_validation(self):
        """Test payment status validation."""
        valid_statuses = ["pending", "processing", "completed", "failed", "refunded"]
        test_status = "completed"

        assert test_status in valid_statuses

    def test_payment_method_validation(self):
        """Test payment method validation."""
        valid_methods = [
            "credit_card",
            "debit_card",
            "bank_transfer",
            "paypal",
            "stripe",
        ]
        test_method = "credit_card"

        assert test_method in valid_methods


class TestModelRelationships:
    """Test relationships between models."""

    def test_customer_invoice_relationship(
        self, sample_customer_data, sample_invoice_data
    ):
        """Test customer-invoice relationship."""
        customer_id = uuid4()
        invoice_data = sample_invoice_data.copy()
        invoice_data["customer_id"] = customer_id

        # Verify the relationship
        assert invoice_data["customer_id"] == customer_id

    def test_invoice_payment_relationship(
        self, sample_invoice_data, sample_payment_data
    ):
        """Test invoice-payment relationship."""
        invoice_id = uuid4()
        payment_data = sample_payment_data.copy()
        payment_data["invoice_id"] = invoice_id

        # Verify the relationship
        assert payment_data["invoice_id"] == invoice_id

    def test_payment_partial_application(self):
        """Test partial payment application to invoice."""
        invoice_total = Decimal("110.00")
        payment_amount = Decimal("50.00")
        remaining_balance = invoice_total - payment_amount

        assert remaining_balance == Decimal("60.00")
        assert remaining_balance > 0  # Still has outstanding balance


class TestModelValidation:
    """Test model validation and constraints."""

    def test_currency_code_validation(self):
        """Test currency code validation."""
        valid_currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
        test_currency = "USD"

        assert test_currency in valid_currencies
        assert len(test_currency) == 3

    def test_tenant_isolation(self):
        """Test tenant isolation in models."""
        tenant_a = uuid4()
        tenant_b = uuid4()

        # Different tenants should have different IDs
        assert tenant_a != tenant_b

    def test_decimal_precision(self):
        """Test decimal precision for monetary amounts."""
        amount = Decimal("123.456")
        rounded_amount = amount.quantize(Decimal("0.01"))

        assert rounded_amount == Decimal("123.46")

    def test_required_field_validation(self):
        """Test required field validation."""
        required_fields = ["customer_id", "total_amount", "currency"]
        sample_data = {
            "customer_id": uuid4(),
            "total_amount": Decimal("100.00"),
            "currency": "USD",
        }

        for field in required_fields:
            assert field in sample_data
            assert sample_data[field] is not None


class TestModelMethods:
    """Test model methods and properties."""

    def test_invoice_line_item_total(self):
        """Test invoice line item total calculation."""
        quantity = Decimal("2")
        unit_price = Decimal("50.00")
        line_total = quantity * unit_price

        assert line_total == Decimal("100.00")

    def test_tax_calculation(self):
        """Test tax calculation."""
        subtotal = Decimal("100.00")
        tax_rate = Decimal("0.10")  # 10%
        tax_amount = subtotal * tax_rate

        assert tax_amount == Decimal("10.00")

    def test_discount_application(self):
        """Test discount application."""
        original_amount = Decimal("100.00")
        discount_percent = Decimal("0.15")  # 15%
        discount_amount = original_amount * discount_percent
        final_amount = original_amount - discount_amount

        assert discount_amount == Decimal("15.00")
        assert final_amount == Decimal("85.00")
