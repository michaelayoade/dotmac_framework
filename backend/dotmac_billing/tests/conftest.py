"""Pytest configuration for billing tests."""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_payment_gateway():
    """Mock payment gateway."""
    gateway = Mock()
    gateway.charge = Mock(return_value={"status": "success", "transaction_id": "TXN-123"})
    gateway.refund = Mock(return_value={"status": "success", "refund_id": "REF-123"})
    gateway.validate_card = Mock(return_value={"valid": True})
    gateway.tokenize = Mock(return_value={"token": "tok_123456"})
    return gateway


@pytest.fixture
def mock_tax_calculator():
    """Mock tax calculation service."""
    calculator = Mock()
    calculator.calculate = Mock(return_value=Decimal("4.99"))
    calculator.get_rate = Mock(return_value=Decimal("0.08"))
    calculator.validate_exemption = Mock(return_value=False)
    return calculator


@pytest.fixture
def mock_invoice_generator():
    """Mock invoice generation service."""
    generator = Mock()
    generator.generate_pdf = Mock(return_value=b"PDF_CONTENT")
    generator.generate_html = Mock(return_value="<html>Invoice</html>")
    generator.get_template = Mock(return_value="template.html")
    return generator


@pytest.fixture
def mock_email_service():
    """Mock email service."""
    service = AsyncMock()
    service.send = AsyncMock(return_value={"sent": True, "message_id": "MSG-123"})
    service.send_bulk = AsyncMock(return_value={"sent": 10, "failed": 0})
    return service


@pytest.fixture
def mock_database():
    """Mock database connection."""
    db = AsyncMock()
    db.execute = AsyncMock(return_value={"rows_affected": 1})
    db.fetch_one = AsyncMock(return_value={"id": 1, "status": "active"})
    db.fetch_all = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    db.transaction = AsyncMock()
    return db


@pytest.fixture
def sample_customer():
    """Sample customer data."""
    return {
        "id": "CUST-001",
        "name": "John Doe",
        "email": "john@example.com",
        "billing_address": {
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "country": "US"
        },
        "payment_method": {
            "type": "credit_card",
            "last_four": "4242",
            "expiry": "12/25"
        },
        "tax_exempt": False,
        "credit_limit": Decimal("5000.00"),
        "balance": Decimal("125.50")
    }


@pytest.fixture
def sample_invoice():
    """Sample invoice data."""
    return {
        "id": "INV-2024-001",
        "customer_id": "CUST-001",
        "invoice_date": datetime.now(),
        "due_date": datetime.now() + timedelta(days=30),
        "line_items": [
            {
                "description": "Internet Service - Premium",
                "quantity": 1,
                "unit_price": Decimal("79.99"),
                "amount": Decimal("79.99")
            },
            {
                "description": "Equipment Rental - Router",
                "quantity": 1,
                "unit_price": Decimal("10.00"),
                "amount": Decimal("10.00")
            }
        ],
        "subtotal": Decimal("89.99"),
        "tax_rate": Decimal("0.08"),
        "tax_amount": Decimal("7.20"),
        "total": Decimal("97.19"),
        "status": "pending",
        "payment_terms": "net30"
    }


@pytest.fixture
def sample_subscription():
    """Sample subscription data."""
    return {
        "id": "SUB-001",
        "customer_id": "CUST-001",
        "plan_id": "PLAN-PREMIUM",
        "status": "active",
        "start_date": datetime.now() - timedelta(days=60),
        "next_billing_date": datetime.now() + timedelta(days=5),
        "billing_cycle": "monthly",
        "price": Decimal("79.99"),
        "discount_percentage": Decimal("10.00"),
        "features": [
            "unlimited_bandwidth",
            "static_ip",
            "priority_support",
            "99.9_sla"
        ],
        "auto_renew": True,
        "payment_method_id": "pm_123"
    }
