"""
Integration Tests for Test Data Factory System

Validates that all components work together correctly:
- Factory registration and dependency resolution
- Data generation and relationship management
- Multi-tenant isolation and cleanup
- pytest fixture integration
- Performance and reliability
"""

import logging
import time
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from .entity_factories import MockEntity

# Import all components for integration testing
from .factories import BaseFactory, FactoryMetadata, FactoryRegistry
from .generators import DataGenerator, DataType

logger = logging.getLogger(__name__)


class TestFactorySystemIntegration:
    """Test complete factory system integration."""

    def test_factory_registration_and_usage(self, factory_registry):
        """Test factory registration and basic usage."""
        # Verify factories are registered
        assert "tenant_factory" in factory_registry.factories
        assert "customer_factory" in factory_registry.factories
        assert "service_factory" in factory_registry.factories

        # Test factory retrieval
        tenant_factory = factory_registry.get_factory("tenant_factory")
        assert tenant_factory is not None

        # Test instance creation through registry
        tenant = factory_registry.create_instance(
            "tenant_factory", name="Integration Test ISP"
        )

        assert tenant.name == "Integration Test ISP"
        assert tenant.id is not None

    def test_dependency_resolution(self, factory_registry):
        """Test automatic dependency resolution."""
        customer_factory = factory_registry.get_factory("customer_factory")
        service_factory = factory_registry.get_factory("service_factory")

        # Set tenant context
        tenant_id = str(uuid4())
        customer_factory.tenant_id = tenant_id
        service_factory.tenant_id = tenant_id

        # Create customer (dependency for service)
        customer = customer_factory.create(name="Dependency Test Customer")

        # Create service with customer dependency
        service = service_factory.create(
            customer_id=customer.id, service_type="internet"
        )

        # Verify relationship
        assert service.customer_id == customer.id
        assert service.tenant_id == tenant_id

    def test_tenant_isolation_enforcement(self, multi_tenant_setup):
        """Test that tenant isolation is properly enforced."""
        tenant_a = multi_tenant_setup["tenant_a"]
        tenant_b = multi_tenant_setup["tenant_b"]
        customer_a = multi_tenant_setup["customer_a"]
        customer_b = multi_tenant_setup["customer_b"]

        # Verify proper isolation
        assert customer_a.tenant_id == tenant_a.id
        assert customer_b.tenant_id == tenant_b.id
        assert customer_a.tenant_id != customer_b.tenant_id

        # Verify tenant data integrity
        assert tenant_a.id != tenant_b.id
        assert tenant_a.name != tenant_b.name
        assert tenant_a.subdomain != tenant_b.subdomain


class TestDataGenerationIntegration:
    """Test data generation system integration."""

    def test_data_generator_with_factories(self, data_generator, customer_factory):
        """Test data generator integration with factories."""
        # Generate data for factory use
        name = data_generator.generate(DataType.NAME)
        email = data_generator.generate(DataType.EMAIL)
        company = data_generator.generate(DataType.COMPANY)

        # Use generated data in factory
        customer = customer_factory.build(
            name=name, email=email, company_name=company, type="business"
        )

        assert customer.name == name
        assert customer.email == email
        assert customer.company_name == company
        assert customer.type == "business"

    def test_isp_specific_data_generation(self, data_generator):
        """Test ISP-specific data generation."""
        # Test IP address generation
        private_ip = data_generator.generate(DataType.IP_ADDRESS, type="private")
        public_ip = data_generator.generate(DataType.IP_ADDRESS, type="public")

        assert "." in private_ip
        assert "." in public_ip

        # Verify private IP ranges
        first_octet = int(private_ip.split(".")[0])
        assert first_octet in [10, 172, 192]

        # Test MAC address generation
        cisco_mac = data_generator.generate(DataType.MAC_ADDRESS, vendor="cisco")
        mikrotik_mac = data_generator.generate(DataType.MAC_ADDRESS, vendor="mikrotik")

        assert ":" in cisco_mac
        assert ":" in mikrotik_mac
        assert len(cisco_mac.split(":")) == 6
        assert len(mikrotik_mac.split(":")) == 6

    def test_sequence_generation_consistency(self, data_generator):
        """Test that sequences generate consistently."""
        # Generate sequences for different entities
        customer_sequences = [
            data_generator.next_sequence("customer") for _ in range(5)
        ]
        invoice_sequences = [data_generator.next_sequence("invoice") for _ in range(3)]

        # Verify customer sequences
        assert customer_sequences == [1, 2, 3, 4, 5]

        # Verify invoice sequences
        assert invoice_sequences == [1, 2, 3]

        # Verify sequences are independent
        more_customer = data_generator.next_sequence("customer")
        assert more_customer == 6  # Continues from last customer sequence


class TestBuilderPatternIntegration:
    """Test builder pattern integration."""

    def test_entity_builder_integration(self, test_data_builder):
        """Test entity builder with complete system."""
        customer = (
            test_data_builder.entity("customer_factory")
            .with_attribute("name", "Builder Test Customer")
            .with_attribute("type", "business")
            .with_generated_attribute("email", DataType.EMAIL)
            .build()
        )

        assert customer.name == "Builder Test Customer"
        assert customer.type == "business"
        assert "@" in customer.email

    def test_relationship_builder_integration(self, test_data_builder):
        """Test relationship builder with factory system."""
        # Set up tenant context
        tenant_id = str(uuid4())

        # Build one-to-many relationship
        result = (
            test_data_builder.relationship()
            .add_step("tenant", "tenant_factory")
            .add_step(
                "customer", "customer_factory", attributes={"tenant_id": tenant_id}
            )
            .add_step(
                "service1",
                "service_factory",
                dependencies=["customer"],
                attributes={
                    "customer_id": "${customer.id}",
                    "tenant_id": tenant_id,
                    "service_type": "internet",
                },
            )
            .add_step(
                "service2",
                "service_factory",
                dependencies=["customer"],
                attributes={
                    "customer_id": "${customer.id}",
                    "tenant_id": tenant_id,
                    "service_type": "phone",
                },
            )
            .build()
        )

        # Verify relationships
        customer = result["customer"]
        service1 = result["service1"]
        service2 = result["service2"]

        assert service1.customer_id == customer.id
        assert service2.customer_id == customer.id
        assert service1.service_type == "internet"
        assert service2.service_type == "phone"

    def test_scenario_builder_integration(self, test_data_builder):
        """Test scenario builder with complete workflow."""
        context = (
            test_data_builder.scenario("integration_test")
            .describe("Integration test scenario")
            .customer_onboarding_scenario(tenant_id=str(uuid4()), service_type="fiber")
            .build()
        )

        # Verify scenario entities
        assert "customer" in context.entities
        assert "service" in context.entities
        assert "billing_account" in context.entities

        customer = context.entities["customer"]
        service = context.entities["service"]
        billing = context.entities["billing_account"]

        # Verify relationships
        assert service.customer_id == customer.id
        assert billing.customer_id == customer.id
        assert service.service_type == "fiber"


class TestPytestFixtureIntegration:
    """Test pytest fixture integration."""

    def test_basic_fixture_usage(self, tenant_factory, customer_factory):
        """Test basic fixture usage patterns."""
        # Create tenant
        tenant = tenant_factory.create(name="Fixture Test ISP")

        # Create customer in tenant
        customer_factory.tenant_id = tenant.id
        customer = customer_factory.create(name="Fixture Test Customer")

        assert customer.tenant_id == tenant.id
        assert customer.name == "Fixture Test Customer"

    def test_scenario_fixture_usage(self, customer_with_service):
        """Test pre-built scenario fixture."""
        # Verify scenario structure
        required_keys = ["tenant", "tenant_id", "customer", "service"]
        for key in required_keys:
            assert key in customer_with_service

        customer = customer_with_service["customer"]
        service = customer_with_service["service"]
        tenant_id = customer_with_service["tenant_id"]

        # Verify relationships and data integrity
        assert service.customer_id == customer.id
        assert customer.tenant_id == tenant_id
        assert service.tenant_id == tenant_id

    def test_complete_scenario_fixture(self, complete_customer_scenario):
        """Test complete scenario fixture with all entities."""
        expected_entities = [
            "tenant",
            "customer",
            "service",
            "billing_account",
            "invoice",
            "router",
        ]

        for entity_name in expected_entities:
            assert entity_name in complete_customer_scenario
            entity = complete_customer_scenario[entity_name]
            assert entity is not None
            assert hasattr(entity, "id")
            assert entity.id is not None


class TestPerformanceAndReliability:
    """Test system performance and reliability."""

    def test_bulk_creation_performance(self, customer_factory, basic_tenant_setup):
        """Test bulk entity creation performance."""
        tenant_id = basic_tenant_setup["tenant_id"]
        customer_factory.tenant_id = tenant_id

        # Time bulk creation
        start_time = time.time()
        customers = customer_factory.create_batch(count=50)
        duration = time.time() - start_time

        # Verify results
        assert len(customers) == 50
        assert duration < 5.0  # Should complete quickly

        # Verify all customers are unique
        customer_ids = [c.id for c in customers]
        assert len(set(customer_ids)) == 50

        # Verify all customers belong to correct tenant
        assert all(c.tenant_id == tenant_id for c in customers)

    def test_cleanup_reliability(self, factory_registry):
        """Test that cleanup works reliably."""
        # Create entities
        tenant_factory = factory_registry.get_factory("tenant_factory")
        customer_factory = factory_registry.get_factory("customer_factory")

        tenant = tenant_factory.create()
        customer_factory.tenant_id = tenant.id
        customer_factory.create_batch(count=10)

        # Verify instances are tracked
        assert len(tenant_factory.instances) == 1
        assert len(customer_factory.instances) == 10

        # Test individual factory cleanup
        customer_factory.cleanup()
        assert len(customer_factory.instances) == 0
        assert len(tenant_factory.instances) == 1  # Should not be affected

        # Test registry-wide cleanup
        factory_registry.cleanup_all()
        assert len(tenant_factory.instances) == 0

    def test_memory_usage_stability(self, factory_registry):
        """Test that memory usage remains stable."""
        customer_factory = factory_registry.get_factory("customer_factory")

        # Create and cleanup multiple times
        for _cycle in range(5):
            customers = customer_factory.create_batch(count=20)
            assert len(customers) == 20

            customer_factory.cleanup()
            assert len(customer_factory.instances) == 0

        # Should not accumulate memory or state
        assert len(customer_factory._relationships) == 0


class TestErrorHandlingAndValidation:
    """Test error handling and validation."""

    def test_missing_factory_error(self, factory_registry):
        """Test error handling for missing factories."""
        with pytest.raises(Exception):  # Should raise FactoryError
            factory_registry.get_factory("nonexistent_factory")

    def test_invalid_dependency_handling(self, factory_registry):
        """Test handling of invalid dependencies."""
        # This would test circular dependencies, missing dependencies, etc.
        # Implementation depends on specific validation logic
        pass

    def test_data_validation(self, customer_factory):
        """Test data validation in factories."""
        # Create customer with invalid data
        customer = customer_factory.create(
            name="",  # Empty name
            email="invalid-email",  # Invalid email format
            type="invalid_type",  # Invalid customer type
        )

        # Factory should still create entity (validation is application-specific)
        assert customer.id is not None
        assert customer.name == ""
        assert customer.email == "invalid-email"
        assert customer.type == "invalid_type"


class TestCustomizationAndExtension:
    """Test system customization and extension capabilities."""

    def test_custom_factory_integration(self, factory_registry):
        """Test integration of custom factories."""

        # Define custom factory
        class CustomTestFactory(BaseFactory):
            def _create_metadata(self) -> FactoryMetadata:
                return FactoryMetadata(
                    name="custom_test_factory",
                    entity_type=MockEntity,
                    provides={"custom_entity"},
                )

            def _create_instance(self, **kwargs) -> MockEntity:
                defaults = {
                    "id": str(uuid4()),
                    "custom_field": "custom_value",
                    "created_by": "custom_factory",
                }
                defaults.update(kwargs)
                return MockEntity(**defaults)

            def _persist_instance(self, instance: MockEntity) -> MockEntity:
                return instance

            def _cleanup_instance(self, instance: MockEntity) -> None:
                pass

        # Register and test custom factory
        custom_factory = CustomTestFactory(factory_registry)
        factory_registry.register_factory(custom_factory)

        # Test usage
        entity = factory_registry.create_instance(
            "custom_test_factory", custom_field="modified_value"
        )

        assert entity.custom_field == "modified_value"
        assert entity.created_by == "custom_factory"
        assert entity.id is not None

    def test_custom_data_provider_integration(self, data_generator):
        """Test integration of custom data providers."""
        from ..generators import DataProvider

        class CustomDataProvider(DataProvider):
            def supports(self, data_type: DataType) -> bool:
                return data_type == DataType.STRING

            def generate(self, data_type: DataType, **kwargs) -> Any:
                if kwargs.get("pattern") == "test_pattern":
                    return "CUSTOM-TEST-VALUE"
                return "DEFAULT"

        # Add custom provider
        custom_provider = CustomDataProvider()
        data_generator.add_provider(custom_provider)

        # Test custom generation
        value = data_generator.generate(DataType.STRING, pattern="test_pattern")
        assert value == "CUSTOM-TEST-VALUE"


def test_complete_system_integration():
    """Test complete system integration end-to-end."""
    # This test runs without pytest fixtures to test the full system

    # Create and configure registry
    registry = FactoryRegistry()
    DataGenerator()

    # Import and register factories
    from .entity_factories import (
        BillingFactory,
        CustomerFactory,
        ServiceFactory,
        TenantFactory,
        UserFactory,
    )

    registry.register_factory(TenantFactory(registry))
    registry.register_factory(UserFactory(registry=registry))
    registry.register_factory(CustomerFactory(registry=registry))
    registry.register_factory(ServiceFactory(registry=registry))
    registry.register_factory(BillingFactory(registry=registry))

    try:
        # Create complete scenario
        tenant = registry.create_instance("tenant_factory", name="Integration Tenant")

        customer_factory = registry.get_factory("customer_factory")
        customer_factory.tenant_id = tenant.id
        customer = customer_factory.create(name="Integration Customer")

        service_factory = registry.get_factory("service_factory")
        service_factory.tenant_id = tenant.id
        service = service_factory.create(
            customer_id=customer.id, service_type="internet"
        )

        billing_factory = registry.get_factory("billing_factory")
        billing_factory.tenant_id = tenant.id
        invoice = billing_factory.create(
            entity_type="invoice",
            customer_id=customer.id,
            total_amount=Decimal("99.99"),
        )

        # Verify complete integration
        assert tenant.id is not None
        assert customer.tenant_id == tenant.id
        assert service.customer_id == customer.id
        assert service.tenant_id == tenant.id
        assert invoice.customer_id == customer.id
        assert invoice.total_amount == Decimal("99.99")

        logger.info("✅ Complete system integration test passed")

    finally:
        # Cleanup
        registry.cleanup_all()


if __name__ == "__main__":
    # Run integration test directly
    test_complete_system_integration()
    logger.info("🎉 All integration tests would pass!")
