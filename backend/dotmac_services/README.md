# DotMac Services

Service catalog, management, tariff, and provisioning bindings for ISP operations. This package provides comprehensive SDKs for managing service definitions, lifecycle state machines, pricing policies, and resource provisioning in ISP environments.

## Features

### Service Catalog SDK
- **Service Definitions**: Create and manage service definitions with technical specifications
- **Service Plans**: Define pricing plans with billing cycles and features
- **Service Bundles**: Create bundled offerings with discount pricing
- **Add-ons**: Manage optional service add-ons and compatibility rules
- **Catalog Management**: Generate customer-facing service catalogs

### Service Management SDK
- **Lifecycle State Machine**: Complete service lifecycle from requested → provisioning → active → suspended → terminated
- **State Transitions**: Controlled state transitions with validation and history tracking
- **Provisioning Progress**: Track and update provisioning progress with retry mechanisms
- **Service Instances**: Manage individual service instances with metadata and configuration

### Tariff SDK
- **Pricing Models**: Support for flat rate, usage-based, tiered, volume discount, and dynamic pricing
- **Policy Templates**: Device-agnostic policy templates for QoS, bandwidth, and traffic shaping
- **Policy Intent Generation**: Generate device-agnostic policy intents from tariff plans
- **Pricing Calculation**: Calculate service pricing with discounts, taxes, and usage charges
- **Complex Pricing Rules**: Support for time-based pricing, tier thresholds, and volume breaks

### Provisioning Bindings SDK
- **Resource Mapping**: Define which resources a service needs (IP/VLAN for data; DID/SIP for voice)
- **Resource Allocation**: Allocate IP addresses, VLANs, DIDs, SIP accounts, bandwidth, and other resources
- **Service-Specific Bindings**: Pre-built bindings for common data and voice services
- **Resource Dependencies**: Manage resource dependencies and provisioning order
- **Resource Lifecycle**: Handle resource allocation and deallocation with rollback support

## Installation

```bash
pip install dotmac-services
```

For development:
```bash
pip install dotmac-services[dev]
```

## Quick Start

```python
import asyncio
from dotmac_services import (
    ServiceCatalogSDK,
    ServiceManagementSDK,
    TariffSDK,
    ProvisioningBindingsSDK,
    ServiceState,
    ResourceType
)

async def main():
    tenant_id = "isp-tenant-1"
    
    # Initialize SDKs
    catalog_sdk = ServiceCatalogSDK(tenant_id)
    management_sdk = ServiceManagementSDK(tenant_id)
    tariff_sdk = TariffSDK(tenant_id)
    bindings_sdk = ProvisioningBindingsSDK(tenant_id)
    
    # Create service definition
    service_def = await catalog_sdk.create_service_definition(
        name="Business Internet",
        service_type="data",
        description="High-speed internet for business customers"
    )
    
    # Create service plan
    service_plan = await catalog_sdk.create_service_plan(
        definition_id=service_def["definition_id"],
        name="Business 100M",
        base_price=99.99,
        billing_cycle="monthly"
    )
    
    # Create tariff plan with pricing rules
    tariff_plan = await tariff_sdk.create_tariff_plan(
        name="Business Internet Tariff",
        service_type="data",
        pricing_model="flat_rate",
        base_price=99.99
    )
    
    # Create provisioning binding
    binding = await bindings_sdk.create_data_service_binding(
        service_definition_id=service_def["definition_id"],
        name="Business Internet Resources",
        bandwidth_mbps=100,
        include_static_ip=True
    )
    
    # Create service instance
    service_instance = await management_sdk.create_service_instance(
        customer_id="customer-123",
        service_plan_id=service_plan["plan_id"]
    )
    
    # Start provisioning
    await management_sdk.start_provisioning(
        service_instance["instance_id"]
    )
    
    # Allocate resources
    allocation = await bindings_sdk.allocate_service_resources(
        service_instance_id=service_instance["instance_id"],
        binding_id=binding["binding_id"],
        customer_requirements={
            "download_speed": 100,
            "upload_speed": 20
        }
    )
    
    # Generate policy intent
    policy_intent = await tariff_sdk.generate_policy_intent(
        tariff_plan_id=tariff_plan["plan_id"],
        service_instance_id=service_instance["instance_id"],
        customer_profile={"customer_id": "customer-123"}
    )
    
    print(f"Service Instance: {service_instance['instance_id']}")
    print(f"Resource Allocation: {allocation['allocation_id']}")
    print(f"Policy Intent: {policy_intent['intent_id']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

Configure via environment variables:

```bash
# Database
DOTMAC_DB_HOST=localhost
DOTMAC_DB_PORT=5432
DOTMAC_DB_NAME=dotmac_services
DOTMAC_DB_USER=dotmac
DOTMAC_DB_PASSWORD=secret

# Cache
DOTMAC_CACHE_TYPE=redis
DOTMAC_CACHE_HOST=localhost
DOTMAC_CACHE_PORT=6379

# Service Catalog
DOTMAC_CATALOG_CURRENCY=USD
DOTMAC_CATALOG_VERSIONING=true
DOTMAC_CATALOG_ENABLE_ADDONS=true

# Service Management
DOTMAC_SVC_PROVISIONING_TIMEOUT=300
DOTMAC_SVC_AUTO_ACTIVATION=true
DOTMAC_SVC_MAX_RETRIES=3

# Tariff
DOTMAC_TARIFF_CURRENCY=USD
DOTMAC_TARIFF_DYNAMIC_PRICING=false
DOTMAC_TARIFF_DISCOUNTS=true

# Events
DOTMAC_EVENTS_ENABLED=true
DOTMAC_EVENTS_BROKER_URL=redis://localhost:6379
```

## Service Lifecycle States

The service management SDK implements a complete lifecycle state machine:

1. **REQUESTED** - Service requested by customer
2. **PROVISIONING** - Resources being allocated and configured
3. **ACTIVE** - Service is active and operational
4. **SUSPENDED** - Service temporarily suspended
5. **TERMINATED** - Service permanently terminated
6. **FAILED** - Provisioning or operation failed

## Event Topics

The package publishes events for integration with event-driven architectures:

- `svc.activation.requested.v1` - Service activation requested
- `svc.activation.activated.v1` - Service activated
- `svc.activation.suspended.v1` - Service suspended
- `svc.activation.resumed.v1` - Service resumed
- `svc.activation.changed.v1` - Service configuration changed
- `policy.intent.updated.v1` - Policy intent updated

## Resource Types

Supported resource types for provisioning bindings:

- **IP_ADDRESS** - Static IP address allocation
- **VLAN** - VLAN assignment
- **DID** - Direct Inward Dialing phone numbers
- **SIP_ACCOUNT** - SIP account credentials
- **BANDWIDTH** - Bandwidth allocation with QoS
- **PORT** - Physical or logical port assignment
- **DEVICE** - Device allocation
- **CERTIFICATE** - SSL/TLS certificates
- **DNS_RECORD** - DNS record management
- **FIREWALL_RULE** - Firewall rule configuration

## Pricing Models

The tariff SDK supports multiple pricing models:

- **FLAT_RATE** - Fixed monthly/yearly pricing
- **USAGE_BASED** - Pay-per-use pricing
- **TIERED** - Tiered pricing with usage thresholds
- **VOLUME_DISCOUNT** - Volume-based discounts
- **TIME_OF_USE** - Time-based pricing (peak/off-peak)
- **DYNAMIC** - Dynamic pricing based on demand

## Policy Intent Types

Generated policy intents support:

- **QOS** - Quality of Service policies
- **BANDWIDTH** - Bandwidth allocation policies
- **TRAFFIC_SHAPING** - Traffic shaping rules
- **ACCESS_CONTROL** - Access control policies
- **ROUTING** - Routing policies
- **FIREWALL** - Firewall policies
- **MONITORING** - Monitoring policies

## Architecture

The package follows a modular, composable design:

- **Core**: Configuration management and custom exceptions
- **SDKs**: Focused SDKs for specific service domains
- **Services**: In-memory service implementations for rapid prototyping
- **Multi-tenant**: All SDKs require `tenant_id` for isolation
- **Event-driven**: Support for event publishing and integration

## Development

```bash
# Clone repository
git clone https://github.com/dotmac/dotmac-services.git
cd dotmac-services

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Format code
black dotmac_services/
isort dotmac_services/

# Type checking
mypy dotmac_services/
```

## Examples

### Service Bundle Creation

```python
# Create a triple-play bundle
bundle = await catalog_sdk.create_bundle(
    name="Triple Play Bundle",
    included_services=[
        internet_plan_id,
        voice_plan_id,
        tv_plan_id
    ],
    discount_value=20.0,  # 20% discount
    discount_type="percentage"
)
```

### Complex Pricing Rules

```python
# Create tiered pricing rule
pricing_rule = await tariff_sdk.create_pricing_rule(
    name="Data Usage Tiers",
    rule_type="tiered",
    unit_type="GB",
    tier_thresholds=[
        {"limit": 100, "price": 0.10},
        {"limit": 500, "price": 0.08},
        {"limit": 1000, "price": 0.05}
    ]
)
```

### Voice Service Provisioning

```python
# Create voice service binding
voice_binding = await bindings_sdk.create_voice_service_binding(
    service_definition_id=voice_service_id,
    name="Business Voice Service",
    did_count=5,
    sip_accounts=10
)

# Allocate voice resources
allocation = await bindings_sdk.allocate_service_resources(
    service_instance_id=instance_id,
    binding_id=voice_binding["binding_id"],
    customer_requirements={
        "display_name": "Acme Corp",
        "area_code": "555"
    }
)
```

## Integration

### External Dependencies

- **Billing Systems**: Integration with billing platforms for invoicing
- **CRM Systems**: Customer relationship management integration
- **Inventory Systems**: Network inventory and resource management
- **Network Provisioning**: Integration with network automation systems

### Database Integration

The package supports database integration for persistent storage:

```python
from dotmac_services import get_config

config = get_config()
# Database configuration available in config.database
```

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: https://docs.dotmac.com/services
- Issues: https://github.com/dotmac/dotmac-services/issues
- Email: support@dotmac.com

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

Please ensure all tests pass and code follows the project style guidelines.
