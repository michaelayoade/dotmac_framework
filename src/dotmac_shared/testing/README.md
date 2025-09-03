# DotMac Test Data Factory System

A comprehensive test data factory system for the DotMac framework that provides centralized, consistent, and maintainable test data creation with relationship management and multi-tenant isolation support.

## 🌟 Key Features

- **Factory Pattern**: Abstract factory implementation with lifecycle management
- **Relationship Management**: Handle complex entity relationships and dependencies
- **Multi-Tenant Isolation**: Built-in support for tenant-specific test data
- **Data Generation**: Realistic fake data generation with ISP-specific patterns
- **Builder Patterns**: Fluent APIs for complex test scenarios
- **Automatic Cleanup**: Resource management with proper cleanup
- **Pytest Integration**: Ready-to-use fixtures and test patterns

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Core Components](#core-components)
- [Factory Types](#factory-types)
- [Data Generation](#data-generation)
- [Builder Patterns](#builder-patterns)
- [Multi-Tenant Testing](#multi-tenant-testing)
- [pytest Integration](#pytest-integration)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)

## 🚀 Quick Start

### Basic Usage

```python
import pytest
from dotmac_shared.testing import (
    factory_registry,
    tenant_factory, 
    customer_factory
)

def test_create_customer(tenant_factory, customer_factory):
    # Create tenant
    tenant = tenant_factory.create(
        name="Test ISP",
        subdomain="testisp"
    )
    
    # Create customer in tenant context
    customer_factory.tenant_id = tenant.id
    customer = customer_factory.create(
        name="John Doe",
        email="john@example.com",
        type="residential"
    )
    
    assert customer.tenant_id == tenant.id
    assert customer.name == "John Doe"
```

### Using Pre-built Scenarios

```python
def test_customer_scenario(customer_with_service):
    """Use pre-built customer with service scenario."""
    customer = customer_with_service['customer']
    service = customer_with_service['service']
    tenant = customer_with_service['tenant']
    
    assert service.customer_id == customer.id
    assert customer.tenant_id == tenant.id
```

## 🏗️ Core Components

### BaseFactory

Abstract base class for all factories with standard lifecycle methods:

```python
from dotmac_shared.testing.factories import BaseFactory, FactoryMetadata

class MyEntityFactory(BaseFactory):
    def _create_metadata(self) -> FactoryMetadata:
        return FactoryMetadata(
            name="my_entity_factory",
            entity_type=MyEntity,
            dependencies={"parent_entity"},
            provides={"my_entity"}
        )
    
    def _create_instance(self, **kwargs) -> MyEntity:
        # Create entity instance
        pass
    
    def _persist_instance(self, instance: MyEntity) -> MyEntity:
        # Save to database/storage
        pass
    
    def _cleanup_instance(self, instance: MyEntity) -> None:
        # Clean up resources
        pass
```

### FactoryRegistry

Centralized registry for managing factories and dependencies:

```python
from dotmac_shared.testing import FactoryRegistry

registry = FactoryRegistry()
registry.register_factory(MyEntityFactory())

# Create instances through registry
entity = registry.create_instance("my_entity_factory", name="Test")

# Automatic cleanup
registry.cleanup_all()
```

### RelationshipManager

Manages complex relationships between entities:

```python
from dotmac_shared.testing.factories import RelationshipDefinition

# Define relationship
relationship = RelationshipDefinition(
    name="customer_service",
    source_factory="customer_factory",
    target_factory="service_factory", 
    relationship_type="one_to_many",
    foreign_key="customer_id"
)

registry.register_relationship(relationship)
```

## 🏭 Factory Types

### TenantIsolatedFactory

For entities that require tenant isolation:

```python
from dotmac_shared.testing.factories import TenantIsolatedFactory

class CustomerFactory(TenantIsolatedFactory):
    def __init__(self, tenant_id=None, registry=None):
        super().__init__(tenant_id, registry)
    
    def _create_instance(self, **kwargs):
        # tenant_id is automatically added
        defaults = {
            'tenant_id': self.tenant_id,
            'name': kwargs.get('name', 'Default Customer')
        }
        defaults.update(kwargs)
        return Customer(**defaults)
```

### Pre-built Entity Factories

- **TenantFactory**: ISP/tenant entities
- **UserFactory**: User accounts with roles
- **CustomerFactory**: Customer entities with tenant isolation
- **ServiceFactory**: ISP services (internet, phone, TV)
- **BillingFactory**: Invoices, payments, billing accounts
- **DeviceFactory**: Network equipment and devices
- **TicketFactory**: Support tickets and issues

## 🎲 Data Generation

### Realistic Test Data

```python
from dotmac_shared.testing.generators import DataGenerator, DataType

generator = DataGenerator()

# Generate various data types
name = generator.generate(DataType.NAME)
email = generator.generate(DataType.EMAIL)
company = generator.generate(DataType.COMPANY)
ip_address = generator.generate(DataType.IP_ADDRESS, type='private')
mac_address = generator.generate(DataType.MAC_ADDRESS, vendor='cisco')

# Generate from schema
schema = {
    'customer_name': DataType.NAME,
    'email': DataType.EMAIL,
    'signup_date': DataType.DATE,
    'is_active': DataType.BOOLEAN,
    'plan': 'professional'  # Literal value
}

data = generator.generate_dict(schema)
```

### ISP-Specific Data

```python
# Service IDs
service_id = generator.generate(DataType.STRING, pattern='service_id')  # "SRV-123456"

# Customer numbers  
customer_num = generator.generate(DataType.STRING, pattern='customer_number')  # "CUST-12345"

# Network addresses
private_ip = generator.generate(DataType.IP_ADDRESS, type='private')
public_ip = generator.generate(DataType.IP_ADDRESS, type='public')
cisco_mac = generator.generate(DataType.MAC_ADDRESS, vendor='cisco')
```

### Sequence Generation

```python
from dotmac_shared.testing.generators import SequenceGenerator

seq_gen = SequenceGenerator(start=1000)

# Generate unique sequential values
id1 = seq_gen.next("invoice")  # 1000
id2 = seq_gen.next("invoice")  # 1001
id3 = seq_gen.next("invoice")  # 1002
```

## 🔨 Builder Patterns

### Entity Builder

Fluent API for building single entities:

```python
from dotmac_shared.testing import TestDataBuilder

builder = TestDataBuilder(registry, generator)

customer = (builder
    .entity("customer_factory")
    .with_attribute("name", "Alice Smith")
    .with_attribute("type", "business") 
    .with_generated_attribute("email", DataType.EMAIL)
    .with_generated_attribute("phone", DataType.PHONE)
    .build())
```

### Relationship Builder

For complex entity relationships:

```python
# One-to-many relationship
result = (builder
    .relationship()
    .one_to_many(
        parent_factory="customer_factory",
        child_factory="service_factory",
        name="customer_services", 
        foreign_key="customer_id",
        children_count=3
    )
    .build())

customer = result["parent_customer_services"]
services = [result[f"child_customer_services_{i}"] for i in range(3)]
```

### Scenario Builder

For complete business scenarios:

```python
# Pre-built customer onboarding scenario
context = (builder
    .scenario("customer_onboarding")
    .describe("Complete customer onboarding workflow")
    .customer_onboarding_scenario(
        tenant_id="acme-isp",
        service_type="fiber_internet"
    )
    .build())

customer = context.entities["customer"]
service = context.entities["service"] 
billing_account = context.entities["billing_account"]
```

## 🏢 Multi-Tenant Testing

### Tenant Isolation

```python
def test_tenant_isolation(multi_tenant_setup):
    tenant_a = multi_tenant_setup['tenant_a']
    tenant_b = multi_tenant_setup['tenant_b']
    customer_a = multi_tenant_setup['customer_a'] 
    customer_b = multi_tenant_setup['customer_b']
    
    # Verify isolation
    assert customer_a.tenant_id == tenant_a.id
    assert customer_b.tenant_id == tenant_b.id
    assert customer_a.tenant_id != customer_b.tenant_id
```

### Cross-Tenant Testing

```python
def test_cross_tenant_scenarios(factory_registry):
    # Create multiple tenants
    tenant_factory = factory_registry.get_factory("tenant_factory")
    customer_factory = factory_registry.get_factory("customer_factory")
    
    tenant1 = tenant_factory.create(name="ISP Alpha")
    tenant2 = tenant_factory.create(name="ISP Beta")
    
    # Create customers in different tenants
    customer_factory.tenant_id = tenant1.id
    customer1 = customer_factory.create(name="Customer Alpha")
    
    customer_factory.tenant_id = tenant2.id
    customer2 = customer_factory.create(name="Customer Beta")
    
    assert customer1.tenant_id != customer2.tenant_id
```

## 🧪 pytest Integration

### Using Fixtures

```python
# Basic fixtures
def test_with_tenant(tenant_factory):
    tenant = tenant_factory.create()
    assert tenant.status == 'active'

def test_with_customer(customer_factory, basic_tenant_setup):
    customer_factory.tenant_id = basic_tenant_setup['tenant_id']
    customer = customer_factory.create()
    assert customer.tenant_id == basic_tenant_setup['tenant_id']

# Pre-built scenarios
def test_customer_service_scenario(customer_with_service):
    customer = customer_with_service['customer']
    service = customer_with_service['service']
    assert service.customer_id == customer.id

def test_complete_scenario(complete_customer_scenario):
    # Includes customer, service, billing, and device
    entities = complete_customer_scenario
    assert 'customer' in entities
    assert 'service' in entities
    assert 'billing_account' in entities
    assert 'router' in entities
```

### Available Fixtures

- `factory_registry`: Pre-configured registry with all factories
- `data_generator`: Configured data generator with ISP providers
- `test_data_builder`: Builder pattern interface
- Entity factories: `tenant_factory`, `customer_factory`, `service_factory`, etc.
- Scenarios: `basic_tenant_setup`, `customer_with_service`, `complete_customer_scenario`
- Multi-tenant: `multi_tenant_setup`
- Support: `support_ticket_scenario`

### Custom Fixtures

```python
@pytest.fixture(scope="function")
def my_custom_scenario(customer_factory, service_factory, billing_factory):
    \"\"\"Create custom test scenario.\"\"\"
    customer = customer_factory.create(type="enterprise")
    
    services = []
    for service_type in ["internet", "phone", "tv"]:
        service = service_factory.create(
            customer_id=customer.id,
            service_type=service_type
        )
        services.append(service)
    
    billing_account = billing_factory.create(
        entity_type="billing_account",
        customer_id=customer.id,
        credit_limit=Decimal("5000.00")
    )
    
    return {
        'customer': customer,
        'services': services,
        'billing_account': billing_account
    }
```

## 🔧 Advanced Usage

### Performance Testing

```python
def test_bulk_creation_performance(customer_factory, basic_tenant_setup):
    \"\"\"Test bulk entity creation performance.\"\"\"
    tenant_id = basic_tenant_setup['tenant_id']
    customer_factory.tenant_id = tenant_id
    
    # Create 1000 customers efficiently
    start_time = time.time()
    customers = customer_factory.create_batch(count=1000)
    duration = time.time() - start_time
    
    assert len(customers) == 1000
    assert duration < 10.0  # Should complete in under 10 seconds
```

### Custom Data Providers

```python
from dotmac_shared.testing.generators import DataProvider, DataType

class MyCustomProvider(DataProvider):
    def supports(self, data_type: DataType) -> bool:
        return data_type == DataType.STRING
    
    def generate(self, data_type: DataType, **kwargs) -> Any:
        if kwargs.get('pattern') == 'my_custom_pattern':
            return f"CUSTOM-{secrets.token_hex(4).upper()}"
        return "DEFAULT"

# Add to generator
generator = DataGenerator()
generator.add_provider(MyCustomProvider())
```

### Cleanup Hooks

```python
def test_with_cleanup_hooks(customer_factory):
    # Add custom cleanup logic
    cleanup_called = False
    
    def my_cleanup():
        nonlocal cleanup_called
        cleanup_called = True
        # Custom cleanup logic here
    
    customer_factory.add_cleanup_handler(my_cleanup)
    
    customer = customer_factory.create()
    
    # Cleanup runs automatically at test end
    # or manually: customer_factory.cleanup()
```

### Conditional Entity Creation

```python
from dotmac_shared.testing.builders import ScenarioBuilder

scenario = (ScenarioBuilder("conditional_test", registry)
    .add_step(
        name="premium_customer",
        factory_name="customer_factory",
        condition=lambda: os.getenv("TEST_PREMIUM") == "true",
        attributes={"type": "enterprise"}
    )
    .build())
```

## 📚 API Reference

### Core Classes

#### BaseFactory
- `create(**kwargs) -> T`: Create and persist entity
- `create_batch(count: int, **kwargs) -> List[T]`: Create multiple entities
- `build(**kwargs) -> T`: Build without persisting
- `cleanup() -> None`: Clean up all instances
- `add_cleanup_handler(handler: Callable) -> None`: Add cleanup logic

#### FactoryRegistry
- `register_factory(factory: BaseFactory) -> None`: Register factory
- `get_factory(name: str) -> BaseFactory`: Get factory by name
- `create_instance(factory_name: str, **kwargs) -> Any`: Create through registry
- `cleanup_all() -> None`: Clean up all factories
- `register_relationship(definition: RelationshipDefinition) -> None`: Define relationships

#### DataGenerator
- `generate(data_type: DataType, **kwargs) -> Any`: Generate single value
- `generate_dict(schema: Dict[str, Any]) -> Dict[str, Any]`: Generate from schema
- `add_provider(provider: DataProvider) -> None`: Add custom provider
- `next_sequence(name: str) -> int`: Get next sequence value

### Builder Classes

#### EntityBuilder
- `with_attribute(name: str, value: Any) -> EntityBuilder`: Set attribute
- `with_generated_attribute(name: str, data_type: DataType, **kwargs) -> EntityBuilder`: Generated attribute
- `with_relationship(relationship_name: str) -> EntityBuilder`: Add relationship
- `build() -> Any`: Build entity

#### RelationshipBuilder
- `one_to_one(source: str, target: str, name: str, **kwargs) -> RelationshipBuilder`: 1:1 relationship
- `one_to_many(parent: str, child: str, name: str, **kwargs) -> RelationshipBuilder`: 1:N relationship
- `many_to_many(left: str, right: str, name: str, **kwargs) -> RelationshipBuilder`: N:N relationship
- `build() -> Dict[str, Any]`: Build all entities

#### ScenarioBuilder
- `customer_onboarding_scenario(tenant_id: str, **kwargs) -> ScenarioBuilder`: Pre-built scenario
- `service_provisioning_scenario(customer_id: str, **kwargs) -> ScenarioBuilder`: Service setup
- `add_step(name: str, factory_name: str, **kwargs) -> ScenarioBuilder`: Custom step
- `build() -> ScenarioContext`: Build complete scenario

## 🤝 Contributing

### Adding New Factories

1. Inherit from `BaseFactory` or `TenantIsolatedFactory`
2. Implement required abstract methods
3. Define factory metadata with dependencies
4. Register with factory registry
5. Add pytest fixtures if needed

### Adding Data Providers

1. Inherit from `DataProvider`
2. Implement `supports()` and `generate()` methods
3. Add to data generator configuration
4. Document supported data types and options

### Testing Your Factories

```python
def test_my_factory(factory_registry):
    factory = MyEntityFactory()
    factory_registry.register_factory(factory)
    
    entity = factory.create(name="Test Entity")
    assert entity.name == "Test Entity"
    
    # Test cleanup
    factory.cleanup()
    assert len(factory.instances) == 0
```

## 📄 License

This test data factory system is part of the DotMac framework and follows the same licensing terms.

## 🆘 Support

For questions, issues, or contributions:

1. Check existing documentation and examples
2. Search closed issues for similar problems  
3. Create detailed issue with reproduction steps
4. Include relevant code snippets and error messages

---

*Happy Testing! 🎉*