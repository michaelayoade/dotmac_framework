# DotMac Observability Package

A comprehensive observability solution for DotMac services providing distributed tracing, metrics collection, health monitoring, and SignOz integration.

## Features

- **Distributed Tracing**: OpenTelemetry-based tracing with correlation ID management
- **Metrics Collection**: Prometheus metrics with tenant isolation and business metrics
- **SignOz Integration**: Unified observability with SignOz as the primary backend
- **Health Monitoring**: Comprehensive health checks for all system components
- **Platform Adapters**: Ready-to-use adapters for ISP and Management platforms
- **CLI Interface**: Command-line tool for managing observability operations

## Installation

The observability package is part of the DotMac shared services and is configured with Poetry dependency management.

### Using Poetry (Recommended)

The observability package dependencies are already configured in the main `pyproject.toml`. Install based on your requirements:

```bash
# Install core observability dependencies (always included)
poetry install

# Install with full SignOz/OpenTelemetry support
poetry install -E observability-full

# Install all optional dependencies
poetry install -E all
```

### Using pip (Manual Installation)

If not using Poetry, install dependencies manually:

```bash
# Core observability (always required)
pip install structlog prometheus-client psutil aiohttp

# For OpenTelemetry/SignOz integration
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

# For comprehensive instrumentation
pip install opentelemetry-instrumentation-fastapi
pip install opentelemetry-instrumentation-sqlalchemy
pip install opentelemetry-instrumentation-redis
# ... additional instrumentations as needed
```

### Poetry Configuration

The observability package is configured with these dependency groups in `pyproject.toml`:

```toml
# Core observability dependencies (always installed)
structlog = "^23.0.0"
prometheus-client = "^0.19.0"
psutil = "^5.9.0"
aiohttp = "^3.9.0"

# OpenTelemetry dependencies (optional - use [observability-full] extra)
opentelemetry-api = {version = "^1.20.0", optional = true}
opentelemetry-sdk = {version = "^1.20.0", optional = true}
opentelemetry-exporter-otlp = {version = "^1.20.0", optional = true}
# ... additional instrumentation packages
```

## Quick Start

### Basic Setup

```python
from dotmac_shared.observability import init_observability

# Initialize observability for your service
observability = init_observability(
    service_name="my-service",
    service_version="1.0.0",
    config={
        "tracing": {"enabled": True},
        "metrics": {"enabled": True},
        "health": {"enabled": True, "auto_start": True},
    }
)
```

### With SignOz Integration

```python
from dotmac_shared.observability import init_observability

observability = init_observability(
    service_name="my-service",
    service_version="1.0.0",
    config={
        "signoz": {
            "enabled": True,
            "endpoint": "localhost:4317",
            "enable_traces": True,
            "enable_metrics": True,
            "enable_logs": True,
        }
    }
)
```

## Components

### Distributed Tracing

```python
from dotmac_shared.observability.core.distributed_tracing import DistributedTracer

tracer = DistributedTracer("my-service", "1.0.0")

# Create a span
span = tracer.start_span("my_operation")
tracer.set_span_tag(span, "user.id", "12345")
tracer.finish_span(span)

# Use context manager (recommended)
async with tracer.span("async_operation") as span:
    # Your code here
    tracer.set_span_tag(span, "result", "success")
```

### Prometheus Metrics

```python
from dotmac_shared.observability.core.prometheus_metrics import get_metrics

metrics = get_metrics("my-service")

# Record HTTP request
metrics.record_http_request(
    method="GET",
    endpoint="/api/users",
    status_code=200,
    duration=0.123,
    tenant_id="tenant-123"
)

# Record business event
metrics.record_tenant_api_call(
    tenant_id="tenant-123",
    service="user_service",
    endpoint="get_user"
)
```

### Health Monitoring

```python
from dotmac_shared.observability.core.health_reporter import get_health_reporter

reporter = get_health_reporter({
    "include_system_metrics": True,
    "include_database_health": True,
    "include_redis_health": True,
})

# Start health reporting
await reporter.start_health_reporting()

# Get health status
health_data = reporter.get_latest_health_data()
summary = reporter.get_health_summary()
```

### SignOz Integration

```python
from dotmac_shared.observability.core.signoz_integration import init_signoz

signoz = init_signoz(
    service_name="my-service",
    service_version="1.0.0",
    signoz_endpoint="localhost:4317"
)

# Record business events
signoz.record_business_event(
    event_type="user_registration",
    tenant_id="tenant-123",
    attributes={"user_type": "premium"}
)

# Record revenue
signoz.record_revenue(
    amount=29.99,
    currency="USD",
    tenant_id="tenant-123"
)

# Instrument FastAPI
app = FastAPI()
signoz.instrument_fastapi(app)
```

## Platform Adapters

### ISP Platform Adapter

```python
from dotmac_shared.observability.adapters.isp_adapter import ISPObservabilityAdapter

adapter = ISPObservabilityAdapter(
    tracer=tracer,
    metrics=metrics,
    health_reporter=reporter,
    signoz=signoz,
    tenant_id="isp-tenant-123"
)

# Record ISP-specific events
adapter.record_customer_event(
    event_type="activation",
    customer_id="customer-456",
    metadata={"service_type": "fiber"}
)

adapter.record_billing_event(
    event_type="payment_received",
    amount=79.99,
    customer_id="customer-456"
)

adapter.record_network_operation(
    operation="device_config",
    device_type="router",
    success=True,
    duration_ms=1234
)
```

### Management Platform Adapter

```python
from dotmac_shared.observability.adapters.management_adapter import ManagementPlatformAdapter

adapter = ManagementPlatformAdapter(
    tracer=tracer,
    metrics=metrics,
    health_reporter=reporter,
    signoz=signoz
)

# Record management platform events
adapter.record_tenant_operation(
    operation="tenant_creation",
    tenant_id="new-tenant-789",
    success=True,
    duration_ms=2345
)

adapter.record_deployment_event(
    deployment_id="deploy-123",
    event_type="completed",
    target_tenant="tenant-789",
    status="success"
)
```

## Configuration

### Environment Variables

```bash
# Service configuration
export SERVICE_NAME=my-service
export SERVICE_VERSION=1.0.0
export ENVIRONMENT=production

# Tracing configuration
export TRACING_ENABLED=true
export TRACING_SAMPLING_RATE=0.1
export OTLP_ENDPOINT=https://signoz.example.com:4317

# Metrics configuration
export METRICS_ENABLED=true
export PROMETHEUS_ENABLED=true
export PROMETHEUS_PORT=8000

# SignOz configuration
export SIGNOZ_ENABLED=true
export SIGNOZ_ENDPOINT=localhost:4317
export SIGNOZ_ACCESS_TOKEN=your-token-here

# Health monitoring
export HEALTH_ENABLED=true
export HEALTH_REPORTING_INTERVAL=60
export HEALTH_AUTO_START=true
```

### Configuration File

```yaml
# observability.yaml
service_name: my-service
service_version: 1.0.0
environment: production

tracing:
  enabled: true
  sampling_rate: 0.1
  otlp_endpoint: https://signoz.example.com:4317

metrics:
  enabled: true
  prometheus_enabled: true
  prometheus_port: 8000
  signoz_enabled: true

health:
  enabled: true
  reporting_interval: 60
  auto_start: true
  include_system_metrics: true
  include_database_health: true
  include_redis_health: true

signoz:
  enabled: true
  endpoint: localhost:4317
  enable_traces: true
  enable_metrics: true
  enable_logs: true
```

## CLI Usage

The observability package includes a comprehensive CLI for managing observability operations:

```bash
# Test all components
python -m dotmac_shared.observability test all

# Check health status
python -m dotmac_shared.observability health status
python -m dotmac_shared.observability health status --summary

# Force health report
python -m dotmac_shared.observability health report

# Start health monitoring daemon
python -m dotmac_shared.observability health start --daemon

# Export Prometheus metrics
python -m dotmac_shared.observability metrics export --output metrics.txt

# Analyze traces
python -m dotmac_shared.observability tracing analyze --trace-id abc-123

# Generate SignOz dashboard
python -m dotmac_shared.observability signoz dashboard --output dashboard.json

# Test SignOz connection
python -m dotmac_shared.observability signoz test --endpoint localhost:4317

# Validate configuration
python -m dotmac_shared.observability config validate --config observability.yaml
python -m dotmac_shared.observability config show --json
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from dotmac_shared.observability import init_observability

app = FastAPI()

# Initialize observability
observability = init_observability(
    service_name="my-api",
    service_version="1.0.0"
)

# Instrument FastAPI with SignOz
if observability.signoz:
    observability.signoz.instrument_fastapi(app)

# Add metrics endpoint
@app.get("/metrics")
async def metrics():
    if observability.metrics:
        return Response(
            content=observability.metrics.generate_metrics(),
            media_type=observability.metrics.get_content_type()
        )
    return {"error": "Metrics not available"}

# Add health endpoint
@app.get("/health")
async def health():
    if observability.health_reporter:
        return observability.health_reporter.get_health_summary()
    return {"status": "unknown"}
```

### Background Task Integration

```python
import asyncio
from dotmac_shared.observability.core.distributed_tracing import trace_async

@trace_async("process_user_data")
async def process_user_data(user_id: str, tenant_id: str):
    # Record business metrics
    if observability.signoz:
        observability.signoz.record_business_event(
            event_type="user_data_processed",
            tenant_id=tenant_id,
            attributes={"user_id": user_id}
        )

    # Your processing logic here
    await asyncio.sleep(1)  # Simulated work

    return {"status": "processed", "user_id": user_id}
```

### Multi-Tenant Monitoring

```python
from dotmac_shared.observability.adapters.isp_adapter import ISPObservabilityAdapter

class TenantService:
    def __init__(self):
        self.observability_adapters = {}

    def get_tenant_adapter(self, tenant_id: str) -> ISPObservabilityAdapter:
        if tenant_id not in self.observability_adapters:
            self.observability_adapters[tenant_id] = ISPObservabilityAdapter(
                tracer=observability.tracer,
                metrics=observability.metrics,
                signoz=observability.signoz,
                tenant_id=tenant_id
            )
        return self.observability_adapters[tenant_id]

    async def create_customer(self, tenant_id: str, customer_data: dict):
        adapter = self.get_tenant_adapter(tenant_id)

        # Record customer creation event
        adapter.record_customer_event(
            event_type="creation",
            customer_id=customer_data["id"],
            metadata=customer_data
        )

        # Your business logic here
        return customer_data
```

## Best Practices

### 1. Service Naming

- Use consistent service names across your observability stack
- Include environment in service names for multi-environment deployments
- Use semantic versioning for service versions

### 2. Tenant Isolation

- Always include tenant_id in metrics and traces
- Use tenant-aware adapters for multi-tenant applications
- Implement tenant-specific dashboards

### 3. Error Handling

- Always wrap observability calls in try-catch blocks
- Gracefully degrade when observability services are unavailable
- Log observability errors but don't let them break your application

### 4. Performance Considerations

- Use appropriate sampling rates for high-traffic services
- Batch metrics and traces when possible
- Monitor the performance impact of observability overhead

### 5. Security

- Use secure connections for production deployments
- Rotate access tokens regularly
- Don't include sensitive data in traces or metrics

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'prometheus_client'**
   - Install Prometheus client: `pip install prometheus_client`

2. **SignOz connection failed**
   - Check endpoint configuration
   - Verify network connectivity
   - Test with insecure connection for debugging

3. **Health checks failing**
   - Check system dependencies (psutil, aiohttp)
   - Verify database and Redis connectivity
   - Review health check thresholds

4. **Metrics not appearing**
   - Verify service is instrumented correctly
   - Check metrics export endpoint
   - Validate Prometheus scraping configuration

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
python -m dotmac_shared.observability --debug test all
```

Or in code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

observability = init_observability(
    service_name="my-service",
    config={"debug": True}
)
```

## Contributing

When contributing to the observability package:

1. Follow the existing code structure
2. Add comprehensive tests for new features
3. Update documentation for any API changes
4. Test with and without optional dependencies
5. Ensure graceful degradation when components are unavailable

## License

This package is part of the DotMac Framework and is licensed under the same terms as the main project.
