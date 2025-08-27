"""
Tests for customer repository.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from repositories.customer import CustomerRepository, CustomerServiceRepository
from models.customer import (
    Customer, CustomerService, CustomerUsageRecord, ServiceUsageRecord,
    CustomerStatus, ServiceStatus
)


@pytest.fixture
def db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def customer_repo(db_session):
    """Customer repository fixture."""
    return CustomerRepository(db_session)


@pytest.fixture
def customer_service_repo(db_session):
    """Customer service repository fixture."""
    return CustomerServiceRepository(db_session)


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID fixture."""
    return uuid4()


@pytest.fixture
def sample_customer(sample_tenant_id):
    """Sample customer fixture."""
    return Customer(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        company_name="Test Corp",
        phone="+1-555-0123",
        status=CustomerStatus.ACTIVE,
        address_line1="123 Main St",
        address_line2="Suite 100",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="US",
        account_number="ACC-001",
        customer_since=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc),
        payment_status="current",
        last_payment_date=datetime.now(timezone.utc),
        next_billing_date=datetime.now(timezone.utc) + timedelta(days=30),
        notes="Test customer",
        tags=["vip", "enterprise"],
        preferences={"email_notifications": True, "sms_alerts": False}
    )


@pytest.fixture
def sample_customer_service(sample_tenant_id):
    """Sample customer service fixture."""
    return CustomerService(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        customer_id=uuid4(),
        service_name="High-Speed Internet",
        service_type="internet",
        service_plan="Fiber 1000",
        status=ServiceStatus.ACTIVE,
        activation_date=datetime.now(timezone.utc),
        suspension_date=None,
        cancellation_date=None,
        configuration={"speed": "1000mbps", "connection_type": "fiber"},
        technical_details={"modem": "XG1v4", "router": "XB7"},
        monthly_cost=Decimal("99.99"),
        setup_fee=Decimal("0.00"),
        notes="Premium fiber service",
        tags=["fiber", "high_speed"]
    )


@pytest.fixture
def sample_usage_record(sample_tenant_id):
    """Sample usage record fixture."""
    period_start = datetime.now(timezone.utc) - timedelta(days=30)
    period_end = datetime.now(timezone.utc)
    
    return CustomerUsageRecord(
        id=uuid4(),
        tenant_id=sample_tenant_id,
        customer_id=uuid4(),
        period_start=period_start,
        period_end=period_end,
        data_usage_gb=Decimal("125.5"),
        api_requests=1500,
        login_sessions=45,
        support_tickets=2,
        uptime_percentage=Decimal("99.8"),
        avg_response_time_ms=Decimal("45.2"),
        peak_concurrent_users=8,
        base_cost=Decimal("99.99"),
        usage_charges=Decimal("15.50"),
        overage_charges=Decimal("5.25"),
        total_cost=Decimal("120.74"),
        usage_by_service={"internet": {"data_gb": 125.5, "sessions": 45}},
        daily_breakdown=[
            {"date": "2023-01-01", "data_gb": 4.2, "sessions": 2},
            {"date": "2023-01-02", "data_gb": 3.8, "sessions": 1}
        ]
    )


class TestCustomerRepository:
    """Test cases for CustomerRepository."""

    @pytest.mark.asyncio
    async def test_get_by_email_success(self, customer_repo, sample_customer, sample_tenant_id):
        """Test successful customer retrieval by email."""
        # Mock database execution
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_customer
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_by_email(sample_tenant_id, "test@example.com")
        
        assert result == sample_customer
        customer_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, customer_repo, sample_tenant_id):
        """Test customer retrieval by email when not found."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_by_email(sample_tenant_id, "nonexistent@example.com")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_tenant_customers_with_pagination(self, customer_repo, sample_tenant_id, sample_customer):
        """Test getting paginated tenant customers."""
        # Mock database execution for main query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_customer]
        
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        customer_repo.db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])
        
        result = await customer_repo.get_tenant_customers(
            tenant_id=sample_tenant_id,
            page=1,
            page_size=20,
            search="test",
            status_filter="active",
            sort_by="created_at",
            sort_order="desc"
        )
        
        assert result["customers"] == [sample_customer]
        assert result["total_count"] == 1
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_get_tenant_customers_with_search(self, customer_repo, sample_tenant_id):
        """Test customer search functionality."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        customer_repo.db.execute = AsyncMock(side_effect=[mock_count_result, mock_result])
        
        result = await customer_repo.get_tenant_customers(
            tenant_id=sample_tenant_id,
            search="john doe"
        )
        
        assert len(result["customers"]) == 0
        assert result["total_count"] == 0

    @pytest.mark.asyncio
    async def test_get_customer_metrics(self, customer_repo, sample_tenant_id):
        """Test customer metrics calculation."""
        # Mock multiple queries for different metrics
        mock_results = [
            MagicMock(scalar=lambda: 100),  # total_customers
            MagicMock(scalar=lambda: 85),   # active_customers
            MagicMock(scalar=lambda: 15),   # new_customers
            MagicMock(scalar=lambda: 5),    # churned_customers
            MagicMock(scalar=lambda: 8500.0), # total_mrr
            MagicMock(scalar=lambda: 95)    # previous_period_customers
        ]
        
        customer_repo.db.execute = AsyncMock(side_effect=mock_results)
        
        result = await customer_repo.get_customer_metrics(sample_tenant_id, period_days=30)
        
        assert result["total_customers"] == 100
        assert result["active_customers"] == 85
        assert result["new_customers"] == 15
        assert result["churned_customers"] == 5
        assert result["total_monthly_revenue"] == 8500.0
        assert result["previous_period_customers"] == 195  # 95 + 100

    @pytest.mark.asyncio
    async def test_get_customer_with_services(self, customer_repo, sample_tenant_id, sample_customer):
        """Test getting customer with services loaded."""
        customer_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_customer
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_customer_with_services(sample_tenant_id, customer_id)
        
        assert result == sample_customer
        customer_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_services(self, customer_repo, sample_tenant_id, sample_customer_service):
        """Test getting customer services."""
        customer_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_customer_service]
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_customer_services(sample_tenant_id, customer_id)
        
        assert result == [sample_customer_service]
        customer_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_usage_summary(self, customer_repo, sample_tenant_id, sample_usage_record):
        """Test getting customer usage summary."""
        customer_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = sample_usage_record
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_customer_usage_summary(
            sample_tenant_id, customer_id, period_days=30
        )
        
        assert result == sample_usage_record
        customer_repo.db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_usage_summary_not_found(self, customer_repo, sample_tenant_id):
        """Test getting customer usage summary when not found."""
        customer_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_repo.get_customer_usage_summary(
            sample_tenant_id, customer_id, period_days=30
        )
        
        assert result is None

    def test_customer_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = CustomerRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == Customer


class TestCustomerServiceRepository:
    """Test cases for CustomerServiceRepository."""

    @pytest.mark.asyncio
    async def test_get_service_usage_stats_success(self, customer_service_repo, sample_tenant_id):
        """Test successful service usage stats retrieval."""
        service_id = uuid4()
        
        # Mock service usage record
        mock_usage = MagicMock()
        mock_usage.data_usage_gb = Decimal("150.5")
        mock_usage.monthly_usage_gb = Decimal("500.0")
        mock_usage.peak_usage_date = datetime.now(timezone.utc).date()
        mock_usage.uptime_percentage = Decimal("99.95")
        mock_usage.last_usage = datetime.now(timezone.utc)
        mock_usage.response_time_ms = Decimal("32.5")
        mock_usage.error_count = 2
        mock_usage.success_count = 998
        mock_usage.service_metrics = {"avg_speed": "985mbps", "peak_speed": "1000mbps"}
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_usage
        customer_service_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_service_repo.get_service_usage_stats(sample_tenant_id, service_id)
        
        assert result["data_usage_gb"] == 150.5
        assert result["monthly_usage_gb"] == 500.0
        assert result["uptime_percentage"] == 99.95
        assert result["response_time_ms"] == 32.5
        assert result["error_count"] == 2
        assert result["success_count"] == 998
        assert result["service_metrics"]["avg_speed"] == "985mbps"

    @pytest.mark.asyncio
    async def test_get_service_usage_stats_no_data(self, customer_service_repo, sample_tenant_id):
        """Test service usage stats when no data exists."""
        service_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        customer_service_repo.db.execute = AsyncMock(return_value=mock_result)
        
        result = await customer_service_repo.get_service_usage_stats(sample_tenant_id, service_id)
        
        # Should return default values
        assert result["data_usage_gb"] == 0.0
        assert result["monthly_usage_gb"] == 0.0
        assert result["uptime_percentage"] == 100.0
        assert result["response_time_ms"] == 0.0
        assert result["error_count"] == 0
        assert result["success_count"] == 0
        assert result["service_metrics"] == {}

    def test_customer_service_repository_initialization(self, db_session):
        """Test repository initialization."""
        repo = CustomerServiceRepository(db_session)
        
        assert repo.db == db_session
        assert repo.model == CustomerService


class TestCustomerModels:
    """Test customer model properties and methods."""

    def test_customer_full_name_property(self, sample_customer):
        """Test customer full_name property."""
        assert sample_customer.full_name == "John Doe"

    def test_customer_display_name_with_company(self, sample_customer):
        """Test customer display_name with company name."""
        assert sample_customer.display_name == "Test Corp"

    def test_customer_display_name_without_company(self, sample_customer):
        """Test customer display_name without company name."""
        sample_customer.company_name = None
        assert sample_customer.display_name == "John Doe"

    def test_customer_address_property(self, sample_customer):
        """Test customer address property."""
        address = sample_customer.address
        
        assert address["line1"] == "123 Main St"
        assert address["line2"] == "Suite 100"
        assert address["city"] == "Test City"
        assert address["state"] == "TS"
        assert address["postal_code"] == "12345"
        assert address["country"] == "US"

    def test_customer_service_is_active_property(self, sample_customer_service):
        """Test customer service is_active property."""
        assert sample_customer_service.is_active is True
        
        sample_customer_service.status = ServiceStatus.INACTIVE
        assert sample_customer_service.is_active is False

    def test_customer_status_enum_values(self):
        """Test customer status enum values."""
        assert CustomerStatus.ACTIVE == "active"
        assert CustomerStatus.INACTIVE == "inactive"
        assert CustomerStatus.SUSPENDED == "suspended"
        assert CustomerStatus.CANCELLED == "cancelled"

    def test_service_status_enum_values(self):
        """Test service status enum values."""
        assert ServiceStatus.ACTIVE == "active"
        assert ServiceStatus.INACTIVE == "inactive"
        assert ServiceStatus.PROVISIONING == "provisioning"
        assert ServiceStatus.SUSPENDED == "suspended"
        assert ServiceStatus.CANCELLED == "cancelled"
        assert ServiceStatus.MAINTENANCE == "maintenance"


@pytest.mark.integration
class TestCustomerRepositoryIntegration:
    """Integration tests for customer repository."""
    
    @pytest.mark.asyncio
    async def test_customer_lifecycle_integration(self, customer_repo, sample_tenant_id):
        """Test complete customer lifecycle."""
        # Mock customer creation and retrieval
        customer_data = {
            "tenant_id": sample_tenant_id,
            "email": "integration@test.com",
            "first_name": "Integration",
            "last_name": "Test",
            "status": CustomerStatus.ACTIVE
        }
        
        created_customer = Customer(id=uuid4(), **customer_data)
        
        # Mock repository create method
        customer_repo.create = AsyncMock(return_value=created_customer)
        
        # Mock get by email
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = created_customer
        customer_repo.db.execute = AsyncMock(return_value=mock_result)
        
        # Test customer creation
        result_create = await customer_repo.create(customer_data, "test_user")
        assert result_create.email == "integration@test.com"
        
        # Test customer retrieval
        result_get = await customer_repo.get_by_email(sample_tenant_id, "integration@test.com")
        assert result_get.email == "integration@test.com"

    @pytest.mark.asyncio
    async def test_customer_metrics_calculation_integration(self, customer_repo, sample_tenant_id):
        """Test customer metrics calculation with realistic data."""
        # Mock realistic metrics data
        mock_results = [
            MagicMock(scalar=lambda: 1000),   # total_customers
            MagicMock(scalar=lambda: 850),    # active_customers  
            MagicMock(scalar=lambda: 50),     # new_customers
            MagicMock(scalar=lambda: 25),     # churned_customers
            MagicMock(scalar=lambda: 85000.0), # total_mrr
            MagicMock(scalar=lambda: 975)     # previous_period_customers
        ]
        
        customer_repo.db.execute = AsyncMock(side_effect=mock_results)
        
        metrics = await customer_repo.get_customer_metrics(sample_tenant_id, period_days=30)
        
        # Verify realistic metrics
        assert metrics["total_customers"] == 1000
        assert metrics["active_customers"] == 850
        assert metrics["new_customers"] == 50
        assert metrics["churned_customers"] == 25
        assert metrics["total_monthly_revenue"] == 85000.0
        
        # Calculate expected growth
        expected_previous_total = 975 + 1000  # previous + current
        assert metrics["previous_period_customers"] == expected_previous_total