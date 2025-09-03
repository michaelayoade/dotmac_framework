"""
Test Examples for DotMac Test Data Factory System

Comprehensive examples demonstrating:
- Basic factory usage patterns
- Complex relationship scenarios  
- Multi-tenant test isolation
- Performance testing patterns
- Integration testing approaches
- Custom factory creation
"""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Any, Dict, List

# These examples show how to use the test data factory system
# In actual tests, these would be separate test files


class TestBasicFactoryUsage:
    """Examples of basic factory usage patterns."""
    
    def test_create_single_tenant(self, tenant_factory):
        """Create a single tenant with default values.""" 
        tenant = tenant_factory.create()
        
        assert tenant.id is not None
        assert tenant.name is not None
        assert tenant.status == 'active'
        assert tenant.created_at is not None
        
    def test_create_tenant_with_custom_attributes(self, tenant_factory):
        """Create tenant with specific attributes."""
        tenant = tenant_factory.create(
            name="Acme ISP",
            subdomain="acme",
            plan="enterprise",
            region="us-west-2"
        )
        
        assert tenant.name == "Acme ISP"
        assert tenant.subdomain == "acme"
        assert tenant.plan == "enterprise"
        assert tenant.region == "us-west-2"
        
    def test_create_multiple_tenants(self, tenant_factory):
        """Create multiple tenants with batch creation."""
        tenants = tenant_factory.create_batch(
            count=3,
            plan="professional"
        )
        
        assert len(tenants) == 3
        for tenant in tenants:
            assert tenant.plan == "professional"
            assert tenant.id is not None
            
    def test_build_without_persistence(self, tenant_factory):
        """Build entity without persisting to storage."""
        tenant = tenant_factory.build(
            name="Test Build",
            subdomain="testbuild"
        )
        
        assert tenant.name == "Test Build"
        # This tenant is not in the factory's instances list
        assert tenant not in tenant_factory.instances


class TestRelationshipManagement:
    """Examples of managing entity relationships."""
    
    def test_customer_with_service_relationship(
        self, 
        customer_factory, 
        service_factory,
        basic_tenant_setup
    ):
        """Create customer with related service."""
        tenant_id = basic_tenant_setup['tenant_id']
        
        # Set tenant context
        customer_factory.tenant_id = tenant_id
        service_factory.tenant_id = tenant_id
        
        # Create customer first
        customer = customer_factory.create(
            name="Jane Smith",
            email="jane@example.com"
        )
        
        # Create related service
        service = service_factory.create(
            customer_id=customer.id,
            service_type="internet",
            monthly_rate=Decimal("89.99")
        )
        
        assert service.customer_id == customer.id
        assert service.tenant_id == tenant_id
        assert service.monthly_rate == Decimal("89.99")
        
    def test_customer_with_multiple_services(
        self,
        customer_factory,
        service_factory, 
        basic_tenant_setup
    ):
        """Create customer with multiple services."""
        tenant_id = basic_tenant_setup['tenant_id']
        customer_factory.tenant_id = tenant_id
        service_factory.tenant_id = tenant_id
        
        customer = customer_factory.create(name="Multi Service Customer")
        
        # Create multiple services
        internet = service_factory.create(
            customer_id=customer.id,
            service_type="internet"
        )
        
        phone = service_factory.create(
            customer_id=customer.id,
            service_type="phone"
        )
        
        tv = service_factory.create(
            customer_id=customer.id,
            service_type="tv"
        )
        
        services = [internet, phone, tv]
        assert len(services) == 3
        assert all(s.customer_id == customer.id for s in services)
        
    def test_billing_relationship_chain(
        self,
        customer_with_service,
        billing_factory
    ):
        """Create billing entities with relationship chain."""
        customer = customer_with_service['customer']
        tenant_id = customer_with_service['tenant_id']
        
        billing_factory.tenant_id = tenant_id
        
        # Create billing account
        account = billing_factory.create(
            entity_type="billing_account",
            customer_id=customer.id,
            credit_limit=Decimal("1000.00")
        )
        
        # Create invoice
        invoice = billing_factory.create(
            entity_type="invoice",
            customer_id=customer.id,
            total_amount=Decimal("79.99")
        )
        
        # Create payment
        payment = billing_factory.create(
            entity_type="payment", 
            customer_id=customer.id,
            invoice_id=invoice.id,
            amount=invoice.total_amount
        )
        
        assert account.customer_id == customer.id
        assert invoice.customer_id == customer.id
        assert payment.customer_id == customer.id
        assert payment.invoice_id == invoice.id
        assert payment.amount == invoice.total_amount


class TestTenantIsolation:
    """Examples of multi-tenant test isolation."""
    
    def test_tenant_data_isolation(self, multi_tenant_setup):
        """Verify tenant data isolation."""
        tenant_a = multi_tenant_setup['tenant_a']
        tenant_b = multi_tenant_setup['tenant_b']
        customer_a = multi_tenant_setup['customer_a']
        customer_b = multi_tenant_setup['customer_b']
        
        # Verify customers belong to correct tenants
        assert customer_a.tenant_id == tenant_a.id
        assert customer_b.tenant_id == tenant_b.id
        
        # Verify tenant isolation
        assert customer_a.tenant_id != customer_b.tenant_id
        
    def test_cross_tenant_data_access_prevention(
        self,
        multi_tenant_setup,
        service_factory
    ):
        """Test that cross-tenant relationships are prevented."""
        tenant_a = multi_tenant_setup['tenant_a']
        customer_b = multi_tenant_setup['customer_b']
        
        # Try to create service for customer B using tenant A context
        service_factory.tenant_id = tenant_a.id
        
        service = service_factory.create(
            customer_id=customer_b.id,  # Cross-tenant reference
            service_type="internet"
        )
        
        # The service should be in tenant A context, not customer B's tenant
        assert service.tenant_id == tenant_a.id
        assert service.customer_id == customer_b.id
        # In a real implementation, this would trigger validation errors


class TestBuilderPatterns:
    """Examples using builder patterns for complex scenarios."""
    
    def test_entity_builder_pattern(self, test_data_builder):
        """Use entity builder for fluent configuration."""
        from dotmac_shared.testing.generators import DataType
        
        customer = (test_data_builder
            .entity("customer_factory")
            .with_attribute("name", "Builder Customer")
            .with_attribute("type", "business")
            .with_generated_attribute("email", DataType.EMAIL)
            .with_generated_attribute("phone", DataType.PHONE)
            .build())
            
        assert customer.name == "Builder Customer"
        assert customer.type == "business"
        assert "@" in customer.email
        assert customer.phone is not None
        
    def test_relationship_builder_pattern(self, test_data_builder):
        """Use relationship builder for complex associations."""
        result = (test_data_builder
            .relationship()
            .one_to_many(
                parent_factory="customer_factory",
                child_factory="service_factory", 
                name="customer_services",
                foreign_key="customer_id",
                children_count=2
            )
            .build())
            
        # Should have 1 customer and 2 services
        assert "parent_customer_services" in result
        assert "child_customer_services_0" in result
        assert "child_customer_services_1" in result
        
        customer = result["parent_customer_services"]
        service1 = result["child_customer_services_0"]
        service2 = result["child_customer_services_1"]
        
        assert service1.customer_id == customer.id
        assert service2.customer_id == customer.id
        
    def test_scenario_builder_pattern(self, test_data_builder):
        """Use scenario builder for business workflows.""" 
        context = (test_data_builder
            .scenario("customer_onboarding")
            .describe("Complete customer onboarding with service activation")
            .customer_onboarding_scenario(
                tenant_id="test-tenant-123",
                service_type="internet"
            )
            .build())
            
        assert "customer" in context.entities
        assert "service" in context.entities  
        assert "billing_account" in context.entities
        
        customer = context.entities["customer"]
        service = context.entities["service"]
        
        assert service.customer_id == customer.id
        assert customer.tenant_id == "test-tenant-123"


class TestDataGeneration:
    """Examples of data generation utilities."""
    
    def test_fake_data_generation(self, data_generator):
        """Generate various types of fake data."""
        from dotmac_shared.testing.generators import DataType
        
        name = data_generator.generate(DataType.NAME)
        email = data_generator.generate(DataType.EMAIL)
        company = data_generator.generate(DataType.COMPANY)
        ip_addr = data_generator.generate(DataType.IP_ADDRESS, type='private')
        mac_addr = data_generator.generate(DataType.MAC_ADDRESS, vendor='cisco')
        
        assert isinstance(name, str)
        assert "@" in email
        assert isinstance(company, str)
        assert "." in ip_addr
        assert ":" in mac_addr
        
    def test_sequence_generation(self, data_generator):
        """Generate sequential values for unique identifiers."""
        seq1 = data_generator.next_sequence("test")
        seq2 = data_generator.next_sequence("test") 
        seq3 = data_generator.next_sequence("test")
        
        assert seq1 == 1
        assert seq2 == 2
        assert seq3 == 3
        
    def test_schema_based_generation(self, data_generator):
        """Generate data from schema definition."""
        from dotmac_shared.testing.generators import DataType
        
        schema = {
            'name': DataType.NAME,
            'email': DataType.EMAIL,
            'age': {'type': 'integer', 'kwargs': {'min': 18, 'max': 65}},
            'is_active': DataType.BOOLEAN,
            'company': 'Fixed Company Name'  # Literal value
        }
        
        data = data_generator.generate_dict(schema)
        
        assert 'name' in data
        assert '@' in data['email'] 
        assert 18 <= data['age'] <= 65
        assert isinstance(data['is_active'], bool)
        assert data['company'] == 'Fixed Company Name'


class TestPerformanceTesting:
    """Examples for performance testing scenarios."""
    
    def test_bulk_customer_creation(self, customer_factory, basic_tenant_setup):
        """Create many customers for load testing."""
        tenant_id = basic_tenant_setup['tenant_id']
        customer_factory.tenant_id = tenant_id
        
        # Create 50 customers efficiently
        customers = customer_factory.create_batch(
            count=50,
            type="residential"
        )
        
        assert len(customers) == 50
        assert all(c.tenant_id == tenant_id for c in customers)
        assert len(set(c.email for c in customers)) == 50  # All unique emails
        
    def test_complex_scenario_performance(self, bulk_test_data):
        """Test performance of complex scenario creation."""
        tenant = bulk_test_data['tenant']
        customers = bulk_test_data['customers']
        
        # Verify bulk creation succeeded
        assert tenant is not None
        assert len(customers) == 100
        
        # All customers should be in same tenant
        assert all(c.tenant_id == tenant.id for c in customers)


class TestIntegrationPatterns:
    """Examples for integration testing."""
    
    def test_complete_customer_lifecycle(self, integration_test_environment):
        """Test complete customer lifecycle."""
        customer = integration_test_environment['customer']
        service = integration_test_environment['service']
        invoice = integration_test_environment['invoice'] 
        router = integration_test_environment['router']
        
        # Verify complete setup
        assert customer is not None
        assert service.customer_id == customer.id
        assert invoice.customer_id == customer.id
        assert router.customer_id == customer.id
        
        # Mock external service interactions
        payment_gateway = integration_test_environment['external_services']['payment_gateway']
        email_service = integration_test_environment['external_services']['email_service']
        
        # These would be real service calls in integration tests
        payment_gateway.process_payment.return_value = {'status': 'success'}
        email_service.send_welcome_email.return_value = True
        
    def test_support_workflow_integration(self, support_ticket_scenario):
        """Test support ticket workflow."""
        customer = support_ticket_scenario['customer']
        ticket = support_ticket_scenario['ticket']
        
        assert ticket.customer_id == customer.id
        assert ticket.status == 'open'
        assert ticket.category == 'technical'
        
        # Simulate ticket resolution workflow
        ticket.status = 'in_progress'
        ticket.assigned_to = 'tech_support_agent'
        
        # Later...
        ticket.status = 'resolved'
        ticket.resolution = 'Replaced router, service restored'


class TestCustomFactoryCreation:
    """Examples of creating custom factories."""
    
    def test_custom_factory_implementation(self, factory_registry):
        """Create and register a custom factory."""
        from dotmac_shared.testing.factories import BaseFactory, FactoryMetadata
        from dotmac_shared.testing.entity_factories import MockEntity
        
        class CustomServiceFactory(BaseFactory):
            def _create_metadata(self) -> FactoryMetadata:
                return FactoryMetadata(
                    name="custom_service_factory",
                    entity_type=MockEntity,
                    dependencies={"customer"},
                    provides={"custom_service"}
                )
                
            def _create_instance(self, **kwargs) -> MockEntity:
                defaults = {
                    'id': str(__import__('uuid').uuid4()),
                    'service_type': 'custom',
                    'status': 'active',
                    'custom_field': 'custom_value'
                }
                defaults.update(kwargs)
                return MockEntity(**defaults)
                
            def _persist_instance(self, instance: MockEntity) -> MockEntity:
                return instance
                
            def _cleanup_instance(self, instance: MockEntity) -> None:
                pass
        
        # Register custom factory
        custom_factory = CustomServiceFactory(factory_registry)
        factory_registry.register_factory(custom_factory)
        
        # Use custom factory
        service = custom_factory.create(
            custom_field="specialized_value"
        )
        
        assert service.service_type == 'custom'
        assert service.custom_field == 'specialized_value'
        assert service.status == 'active'


# Example test configuration
@pytest.fixture(autouse=True)
def setup_test_examples(request):
    """Setup for all example tests."""
    # This would run before each test in this module
    pass


if __name__ == "__main__":
    # Example of running tests programmatically
    print("Test Data Factory Examples")
    print("=" * 40)
    print("Run with: pytest src/dotmac_shared/testing/examples.py -v")