"""
Pytest Fixtures for Test Data Factory System

Provides ready-to-use pytest fixtures for:
- Factory registry with pre-registered factories
- Data generators with ISP-specific configurations
- Entity-specific factory fixtures
- Scenario builders for common test patterns
- Automatic cleanup and resource management
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest

from .builders import TestDataBuilder
from .entity_factories import (
    BillingFactory,
    CustomerFactory,
    DeviceFactory,
    ServiceFactory,
    TenantFactory,
    TicketFactory,
    UserFactory,
)
from .factories import FactoryRegistry, cleanup_all_factories
from .generators import DataGenerator, GenerationConfig, ISPDataProvider


@pytest.fixture(scope="session")
def generation_config() -> GenerationConfig:
    """Base configuration for data generation."""
    return GenerationConfig(
        locale="en_US",
        seed=12345,  # For reproducible tests
        unique=True,
        sequence_start=1,
    )


@pytest.fixture(scope="session")
def data_generator(generation_config: GenerationConfig) -> DataGenerator:
    """Configured data generator with ISP-specific providers."""
    generator = DataGenerator(generation_config)

    # Add ISP-specific provider for specialized data
    isp_provider = ISPDataProvider(generation_config)
    generator.add_provider(isp_provider)

    return generator


@pytest.fixture(scope="function")
def factory_registry(data_generator: DataGenerator) -> Generator[FactoryRegistry, None, None]:
    """
    Factory registry with all standard factories pre-registered.

    Provides automatic cleanup after each test function.
    """
    registry = FactoryRegistry()

    # Register all standard factories
    registry.register_factory(TenantFactory(registry))
    registry.register_factory(UserFactory(registry=registry))
    registry.register_factory(CustomerFactory(registry=registry))
    registry.register_factory(ServiceFactory(registry=registry))
    registry.register_factory(BillingFactory(registry=registry))
    registry.register_factory(DeviceFactory(registry=registry))
    registry.register_factory(TicketFactory(registry=registry))

    try:
        yield registry
    finally:
        # Automatic cleanup
        registry.cleanup_all()


@pytest.fixture(scope="function")
def test_data_builder(factory_registry: FactoryRegistry, data_generator: DataGenerator) -> TestDataBuilder:
    """Test data builder with full factory support."""
    return TestDataBuilder(factory_registry, data_generator)


# Entity-specific factory fixtures
@pytest.fixture(scope="function")
def tenant_factory(factory_registry: FactoryRegistry) -> TenantFactory:
    """Tenant factory fixture."""
    return factory_registry.get_factory("tenant_factory")


@pytest.fixture(scope="function")
def user_factory(factory_registry: FactoryRegistry) -> UserFactory:
    """User factory fixture."""
    return factory_registry.get_factory("user_factory")


@pytest.fixture(scope="function")
def customer_factory(factory_registry: FactoryRegistry) -> CustomerFactory:
    """Customer factory fixture."""
    return factory_registry.get_factory("customer_factory")


@pytest.fixture(scope="function")
def service_factory(factory_registry: FactoryRegistry) -> ServiceFactory:
    """Service factory fixture."""
    return factory_registry.get_factory("service_factory")


@pytest.fixture(scope="function")
def billing_factory(factory_registry: FactoryRegistry) -> BillingFactory:
    """Billing factory fixture."""
    return factory_registry.get_factory("billing_factory")


@pytest.fixture(scope="function")
def device_factory(factory_registry: FactoryRegistry) -> DeviceFactory:
    """Device factory fixture."""
    return factory_registry.get_factory("device_factory")


@pytest.fixture(scope="function")
def ticket_factory(factory_registry: FactoryRegistry) -> TicketFactory:
    """Ticket factory fixture."""
    return factory_registry.get_factory("ticket_factory")


# Pre-built test scenarios
@pytest.fixture(scope="function")
def basic_tenant_setup(tenant_factory: TenantFactory) -> dict[str, Any]:
    """Basic tenant with admin user setup."""
    tenant = tenant_factory.create(name="Test ISP", subdomain="testisp", plan="professional")

    return {
        "tenant": tenant,
        "tenant_id": tenant.id,
        "admin_user": None,  # Would create admin user here
    }


@pytest.fixture(scope="function")
def customer_with_service(
    basic_tenant_setup: dict[str, Any], customer_factory: CustomerFactory, service_factory: ServiceFactory
) -> dict[str, Any]:
    """Customer with active internet service."""
    tenant_id = basic_tenant_setup["tenant_id"]

    # Set tenant context for factories
    customer_factory.tenant_id = tenant_id
    service_factory.tenant_id = tenant_id

    customer = customer_factory.create(name="John Doe", email="john@example.com", type="residential")

    service = service_factory.create(customer_id=customer.id, service_type="internet", status="active")

    return {**basic_tenant_setup, "customer": customer, "service": service}


@pytest.fixture(scope="function")
def complete_customer_scenario(
    customer_with_service: dict[str, Any], billing_factory: BillingFactory, device_factory: DeviceFactory
) -> dict[str, Any]:
    """Complete customer scenario with billing and devices."""
    tenant_id = customer_with_service["tenant_id"]
    customer = customer_with_service["customer"]
    customer_with_service["service"]

    # Set tenant context
    billing_factory.tenant_id = tenant_id
    device_factory.tenant_id = tenant_id

    # Create billing account
    billing_account = billing_factory.create(entity_type="billing_account", customer_id=customer.id)

    # Create invoice
    invoice = billing_factory.create(entity_type="invoice", customer_id=customer.id, status="paid")

    # Create customer equipment
    router = device_factory.create(customer_id=customer.id, device_type="router", status="active")

    return {
        **customer_with_service,
        "billing_account": billing_account,
        "invoice": invoice,
        "router": router,
        "devices": [router],
    }


@pytest.fixture(scope="function")
def multi_tenant_setup(tenant_factory: TenantFactory, customer_factory: CustomerFactory) -> dict[str, Any]:
    """Multi-tenant test setup for isolation testing."""
    # Create two separate tenants
    tenant_a = tenant_factory.create(name="ISP Alpha", subdomain="alpha")

    tenant_b = tenant_factory.create(name="ISP Beta", subdomain="beta")

    # Create customers in each tenant
    customer_factory.tenant_id = tenant_a.id
    customer_a = customer_factory.create(name="Alice Alpha")

    customer_factory.tenant_id = tenant_b.id
    customer_b = customer_factory.create(name="Bob Beta")

    return {"tenant_a": tenant_a, "tenant_b": tenant_b, "customer_a": customer_a, "customer_b": customer_b}


@pytest.fixture(scope="function")
def support_ticket_scenario(customer_with_service: dict[str, Any], ticket_factory: TicketFactory) -> dict[str, Any]:
    """Support ticket scenario with customer context."""
    tenant_id = customer_with_service["tenant_id"]
    customer = customer_with_service["customer"]

    ticket_factory.tenant_id = tenant_id

    ticket = ticket_factory.create(
        customer_id=customer.id,
        subject="Internet connection issues",
        description="Customer experiencing slow speeds",
        category="technical",
        priority="medium",
        status="open",
    )

    return {**customer_with_service, "ticket": ticket}


# Mock database fixtures for testing without real DB
@pytest.fixture(scope="function")
def mock_database():
    """Mock database session for testing factories without persistence."""
    db_mock = MagicMock()

    # Mock common database operations
    db_mock.add.return_value = None
    db_mock.commit.return_value = None
    db_mock.rollback.return_value = None
    db_mock.refresh.return_value = None
    db_mock.delete.return_value = None

    # Mock query operations
    db_mock.query.return_value.filter.return_value.first.return_value = None
    db_mock.query.return_value.filter.return_value.all.return_value = []
    db_mock.query.return_value.count.return_value = 0

    return db_mock


@pytest.fixture(scope="function")
def factory_with_mock_db(factory_registry: FactoryRegistry, mock_database):
    """Factory registry configured with mock database."""
    # In a real implementation, you would configure factories to use mock_database
    # For now, factories use in-memory storage
    return factory_registry


# Performance testing fixtures
@pytest.fixture(scope="function")
def bulk_test_data(factory_registry: FactoryRegistry) -> dict[str, list[Any]]:
    """Create bulk test data for performance testing."""
    tenant_factory = factory_registry.get_factory("tenant_factory")
    customer_factory = factory_registry.get_factory("customer_factory")

    # Create tenant
    tenant = tenant_factory.create(name="Bulk Test ISP")
    customer_factory.tenant_id = tenant.id

    # Create bulk customers
    customers = customer_factory.create_batch(count=100, type="residential")

    return {"tenant": tenant, "customers": customers}


# Integration testing fixtures
@pytest.fixture(scope="function")
def integration_test_environment(complete_customer_scenario: dict[str, Any]) -> dict[str, Any]:
    """Complete integration test environment."""
    # This would set up external service mocks, database connections, etc.
    # For now, just return the complete scenario
    return {
        **complete_customer_scenario,
        "external_services": {"payment_gateway": MagicMock(), "email_service": MagicMock(), "sms_service": MagicMock()},
    }


# Cleanup fixtures
@pytest.fixture(autouse=True, scope="function")
def auto_cleanup_factories():
    """Automatically clean up global factory state after each test."""
    yield
    # This runs after each test
    try:
        cleanup_all_factories()
    except Exception as e:
        # Log but don't fail tests due to cleanup issues
        import logging

        logging.getLogger(__name__).warning(f"Factory cleanup failed: {e}")


# Configuration fixtures
@pytest.fixture(scope="session")
def test_config() -> dict[str, Any]:
    """Test configuration settings."""
    return {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/15",
        "test_mode": True,
        "debug": False,
        "factories": {"cleanup_on_exit": True, "validate_relationships": True, "enable_sequence_tracking": True},
    }
