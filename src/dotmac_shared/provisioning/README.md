# DotMac Shared Container Provisioning Service

Automated ISP container provisioning system supporting the "4-minute deployment" business requirement.

## Features

- **Fast Provisioning**: Complete ISP Framework container deployment in under 4 minutes
- **Intelligent Resource Allocation**: Dynamic CPU/memory allocation based on customer count (50-10,000+)
- **Health Validation**: Comprehensive container health checks during and after provisioning
- **Rollback Capability**: Automatic rollback on provisioning failure
- **Multi-Platform Support**: Kubernetes and Docker deployment adapters

## Quick Start

```python
from uuid import UUID
from dotmac_shared.provisioning import provision_isp_container
from dotmac_shared.provisioning.core.models import ISPConfig

# Basic provisioning
result = await provision_isp_container(
    isp_id=UUID("12345678-1234-5678-9012-123456789abc"),
    customer_count=500,
    config=ISPConfig(
        tenant_name="acme-isp",
        plan_type="premium",
        features=["billing", "customer_portal", "technician_portal"]
    )
)

if result.success:
    print(f"✅ ISP Framework deployed at {result.endpoint_url}")
    print(f"⏱️  Deployment time: {result.deployment_duration}s")
else:
    print(f"❌ Deployment failed: {result.error_message}")
```

## Advanced Usage

### Custom Resource Allocation

```python
from dotmac_shared.provisioning.core.models import ResourceRequirements

custom_resources = ResourceRequirements(
    cpu_cores=2.0,
    memory_gb=4.0,
    storage_gb=20.0,
    max_connections=200
)

result = await provision_isp_container(
    isp_id=isp_id,
    customer_count=1000,
    config=config,
    custom_resources=custom_resources
)
```

### Health Monitoring

```python
from dotmac_shared.provisioning import validate_container_health

health_status = await validate_container_health(
    container_id="isp-framework-acme-isp"
)

print(f"Health: {health_status.overall_status}")
print(f"Database: {'✅' if health_status.database_healthy else '❌'}")
print(f"API: {'✅' if health_status.api_healthy else '❌'}")
```

## Architecture

### Core Components

- **Provisioner**: Main orchestration engine (`core/provisioner.py`)
- **Templates**: Container template management (`core/templates.py`)
- **Validators**: Health validation system (`core/validators.py`)
- **Exceptions**: Error handling (`core/exceptions.py`)

### Adapters

- **Kubernetes**: Production Kubernetes deployment (`adapters/kubernetes_adapter.py`)
- **Docker**: Development Docker deployment (`adapters/docker_adapter.py`)
- **Resource Calculator**: Dynamic resource allocation (`adapters/resource_calculator.py`)

## Resource Calculation

The service automatically calculates optimal resource allocation based on:

- **Customer Count**: Linear scaling from 50 to 10,000+ customers
- **Plan Type**: Standard/Premium/Enterprise tiers
- **Feature Set**: Additional resources for analytics, bulk operations, etc.

### Scaling Formula

```
CPU = base_cpu + (customers / 1000) * cpu_multiplier
Memory = base_memory + (customers / 500) * memory_increment
Connections = min(customers * 2, max_connections)
```

## Deployment Timeline

Target deployment timeline for 4-minute requirement:

1. **Infrastructure Provisioning** (60s): Kubernetes namespace, volumes, networking
2. **Container Deployment** (90s): Image pull, container creation, environment setup
3. **Service Configuration** (45s): Database setup, SSL certificates, ingress rules
4. **Health Validation** (45s): Comprehensive health checks and smoke tests

## Error Handling & Rollback

The service provides automatic rollback on failure:

```python
try:
    result = await provision_isp_container(isp_id, customer_count, config)
except ProvisioningError as e:
    # Automatic rollback initiated
    print(f"Provisioning failed: {e}")
    print(f"Rollback status: {e.rollback_completed}")
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dotmac_shared.provisioning

# Run specific test categories
pytest -m "unit"
pytest -m "integration"
pytest -m "performance"
```

## Configuration

Environment variables:

```bash
# Kubernetes
KUBECONFIG=/path/to/kubeconfig
KUBERNETES_NAMESPACE=dotmac-tenants

# Docker (development)
DOCKER_REGISTRY=registry.dotmac.app
DOCKER_TAG=latest

# Resource Limits
MAX_CPU_CORES=4.0
MAX_MEMORY_GB=8.0
MAX_STORAGE_GB=50.0

# Timeouts
PROVISIONING_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_TIMEOUT=60   # 1 minute
ROLLBACK_TIMEOUT=120      # 2 minutes
```

## Performance Targets

- **Provisioning Time**: < 4 minutes (240 seconds)
- **Resource Efficiency**: Optimal allocation within 5% of actual usage
- **Success Rate**: > 99.5% successful deployments
- **Rollback Time**: < 2 minutes on failure

## Support

For issues or questions:

- GitHub Issues: <https://github.com/dotmac/framework/issues>
- Documentation: <https://docs.dotmac.app/shared-services/provisioning>
- Slack: #dotmac-provisioning
