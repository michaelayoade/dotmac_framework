# DotMac Observability

A comprehensive observability package for the DotMac Framework, providing unified OpenTelemetry integration, metrics collection, SLO monitoring, and dashboard provisioning.

[![PyPI version](https://badge.fury.io/py/dotmac-observability.svg)](https://badge.fury.io/py/dotmac-observability)
[![Python Support](https://img.shields.io/pypi/pyversions/dotmac-observability.svg)](https://pypi.org/project/dotmac-observability/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔭 **OpenTelemetry Integration**: Complete OTEL setup with traces, metrics, and logs
- 📊 **Unified Metrics Registry**: Abstraction over OpenTelemetry and Prometheus
- 🎯 **Business SLO Monitoring**: Tenant-scoped business metrics with SLO evaluation
- 📈 **Dashboard Provisioning**: Automated SigNoz/Grafana dashboard creation
- 🏥 **Health Monitoring**: Built-in health checks for observability components
- 🔧 **Environment-Aware**: Different configurations for dev/staging/production
- ⚡ **Optional Dependencies**: Install only what you need

## Quick Start

### Installation

```bash
# Base installation
pip install dotmac-observability

# With OpenTelemetry support
pip install "dotmac-observability[otel]"

# With Prometheus support  
pip install "dotmac-observability[prometheus]"

# With dashboard provisioning
pip install "dotmac-observability[dashboards]"

# Complete installation
pip install "dotmac-observability[all]"
```

### Basic Usage

```python
from dotmac.observability import (
    create_default_config,
    initialize_otel,
    initialize_metrics_registry,
)

# Create configuration
config = create_default_config(
    service_name="my-service",
    environment="production",
    service_version="1.0.0",
)

# Initialize OpenTelemetry
otel = initialize_otel(config)

# Initialize metrics registry
metrics = initialize_metrics_registry("my-service", enable_prometheus=True)

# Register custom metric
from dotmac.observability import MetricDefinition, MetricType

metrics.register_metric(MetricDefinition(
    name="api_requests_custom",
    type=MetricType.COUNTER,
    description="Custom API request counter",
    labels=["method", "endpoint", "status"],
))

# Record metrics
metrics.increment_counter("api_requests_custom", 1, {
    "method": "GET",
    "endpoint": "/users",
    "status": "200"
})
```

## Business Metrics & SLOs

```python
from dotmac.observability import (
    initialize_tenant_metrics,
    BusinessMetricSpec,
    BusinessMetricType,
    TenantContext,
)

# Initialize tenant metrics
tenant_metrics = initialize_tenant_metrics(
    service_name="user-service",
    metrics_registry=metrics,
    enable_slo_monitoring=True,
)

# Register business metric
spec = BusinessMetricSpec(
    name="user_login_success_rate",
    metric_type=BusinessMetricType.SUCCESS_RATE,
    description="User login success rate",
    slo_target=0.99,      # 99% target
    alert_threshold=0.95,  # Alert at 95%
    labels=["tenant_id", "service", "region"],
)

tenant_metrics.register_business_metric(spec)

# Record business metrics
context = TenantContext(
    tenant_id="acme-corp",
    service="auth-service",
    region="us-east-1",
)

# Record successful login
tenant_metrics.record_business_metric("user_login_success_rate", 1, context)

# Record failed login
tenant_metrics.record_business_metric("user_login_success_rate", 0, context)

# Evaluate SLOs
slos = tenant_metrics.evaluate_slos(context)
for metric_name, evaluation in slos.items():
    print(f"{metric_name}: {evaluation.current_value:.2%} (target: {evaluation.slo_target:.2%})")
    if evaluation.is_critical:
        print(f"🚨 CRITICAL: {metric_name} below threshold!")
```

## Dashboard Provisioning

```python
from dotmac.observability import provision_platform_dashboards

# Provision dashboards in SigNoz
result = provision_platform_dashboards(
    platform_type="signoz",
    tenant_id="acme-corp",
    custom_variables={"service": "user-service"},
    base_url="http://signoz.company.com:3301",
    api_key="your-api-key",
)

print(f"Created {len(result.dashboards_created)} dashboards")
print(f"Updated {len(result.dashboards_updated)} dashboards")

if result.errors:
    print("Errors:", result.errors)
```

## Health Monitoring

```python
from dotmac.observability import get_observability_health

# Check overall health
health = get_observability_health(
    otel_bootstrap=otel,
    metrics_registry=metrics,
    tenant_metrics=tenant_metrics,
)

print(f"Overall health: {health.status}")
print(f"Healthy components: {sum(1 for c in health.checks if c.status == 'healthy')}")

# Create health endpoint for your web app
from dotmac.observability import create_health_endpoint_handler

health_handler = create_health_endpoint_handler(
    otel_bootstrap=otel,
    metrics_registry=metrics,
    tenant_metrics=tenant_metrics,
)

# In FastAPI
@app.get("/health/observability")
def observability_health():
    return health_handler()

# In Flask
@app.route('/health/observability')
def observability_health():
    return health_handler()
```

## Configuration

### Environment-Specific Configs

```python
# Development: Console exporters, full sampling
config = create_default_config("my-service", "development")

# Production: OTLP exporters, reduced sampling
config = create_default_config("my-service", "production") 

# Custom configuration
config = create_default_config(
    service_name="my-service",
    environment="production",
    service_version="2.1.0",
    custom_resource_attributes={
        "deployment.mode": "kubernetes",
        "team": "platform",
        "region": "us-west-2",
    },
)
```

### Advanced Configuration

```python
from dotmac.observability import OTelConfig, ExporterConfig, ExporterType

config = OTelConfig(
    service_name="advanced-service",
    service_version="1.0.0",
    environment=Environment.PRODUCTION,
    
    # Custom exporters
    tracing_exporters=[
        ExporterConfig(
            type=ExporterType.OTLP_HTTP,
            endpoint="https://otel.company.com/v1/traces",
            headers={"Authorization": "Bearer token"},
        ),
        ExporterConfig(
            type=ExporterType.JAEGER,
            endpoint="jaeger.company.com:6831",
        ),
    ],
    
    # Sampling configuration
    trace_sampler_ratio=0.1,  # 10% sampling
    max_export_batch_size=1024,
    
    # Resource attributes
    custom_resource_attributes={
        "service.namespace": "dotmac",
        "service.instance.id": os.getenv("POD_NAME"),
    },
)

otel = initialize_otel(config)
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from dotmac.observability import *

app = FastAPI()

# Initialize observability
config = create_default_config("fastapi-service", "production")
otel = initialize_otel(config)
metrics = initialize_metrics_registry("fastapi-service")
tenant_metrics = initialize_tenant_metrics("fastapi-service", metrics)

# Set OpenTelemetry meter for metrics registry
metrics.set_otel_meter(otel.meter)

@app.middleware("http")
async def observability_middleware(request, call_next):
    # Record request metrics
    metrics.increment_counter("http_requests_total", 1, {
        "method": request.method,
        "endpoint": str(request.url.path),
    })
    
    response = await call_next(request)
    
    # Record response metrics
    metrics.increment_counter("http_requests_total", 1, {
        "method": request.method,
        "endpoint": str(request.url.path),
        "status_code": str(response.status_code),
    })
    
    return response

@app.get("/metrics")
def metrics_endpoint():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        metrics.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4"
    )

@app.get("/health/observability")
def health_endpoint():
    health = get_observability_health(otel, metrics, tenant_metrics)
    return {
        "status": health.status,
        "checks": len(health.checks),
        "summary": health.summary,
    }
```

### Django Integration

```python
# settings.py
from dotmac.observability import create_default_config, initialize_otel

# Initialize in Django settings
OTEL_CONFIG = create_default_config(
    service_name="django-service",
    environment=os.getenv("ENVIRONMENT", "development"),
)

OTEL_BOOTSTRAP = initialize_otel(OTEL_CONFIG)
```

```python
# middleware.py
from django.utils.deprecation import MiddlewareMixin
from dotmac.observability import get_current_span_context

class ObservabilityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Add trace context to request
        span_context = get_current_span_context()
        if span_context:
            request.trace_id = span_context.get("trace_id")
            
    def process_response(self, request, response):
        # Log response with trace context
        return response
```

## Default Metrics

The package automatically registers these default metrics:

| Metric | Type | Description | Labels |
|--------|------|-------------|---------|
| `http_requests_total` | Counter | Total HTTP requests | method, endpoint, status_code |
| `http_request_duration_seconds` | Histogram | HTTP request duration | method, endpoint |
| `system_memory_usage_bytes` | Gauge | Memory usage | - |
| `system_cpu_usage_percent` | Gauge | CPU usage | - |
| `database_connections_active` | Gauge | Active DB connections | - |
| `database_query_duration_seconds` | Histogram | DB query duration | operation, table |

## Default Business Metrics

These business metrics are registered by default:

| Metric | Type | SLO Target | Description |
|--------|------|------------|-------------|
| `login_success_rate` | Success Rate | 99% | User login success rate |
| `api_request_success_rate` | Success Rate | 99.5% | API request success rate |
| `service_provisioning_success_rate` | Success Rate | 98% | Service provisioning success |
| `api_response_latency` | Latency | 500ms | API response latency P95 |
| `database_query_latency` | Latency | 100ms | Database query latency P95 |

## Architecture

```
dotmac.observability/
├── config.py              # Configuration management
├── bootstrap.py            # OpenTelemetry initialization  
├── metrics/
│   ├── registry.py         # Unified metrics registry
│   └── business.py         # Business metrics & SLO monitoring
├── dashboards/
│   └── manager.py          # Dashboard provisioning
├── health.py              # Health monitoring
└── api.py                 # Public API exports
```

## Environment Variables

Configure the package using environment variables:

```bash
# OpenTelemetry
OTEL_SERVICE_NAME=my-service
OTEL_SERVICE_VERSION=1.0.0
OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.company.com

# Metrics
PROMETHEUS_URL=http://prometheus:9090

# Dashboards  
SIGNOZ_URL=http://signoz:3301
SIGNOZ_API_KEY=your-key
GRAFANA_URL=http://grafana:3000
GRAFANA_API_KEY=your-key
```

## Migration from Legacy

If you're migrating from `dotmac_shared.observability`:

### Before
```python
from dotmac_shared.observability import initialize_otel, initialize_metrics

otel = initialize_otel("my-service", "production")
metrics = initialize_metrics("my-service")
```

### After
```python
from dotmac.observability import create_default_config, initialize_otel, initialize_metrics_registry

config = create_default_config("my-service", "production")
otel = initialize_otel(config)
metrics = initialize_metrics_registry("my-service")
```

The legacy module will show deprecation warnings and will be removed in the next minor release.

## Performance Considerations

- **Sampling**: Use appropriate sampling rates for production (default: 10%)
- **Batch Size**: Tune `max_export_batch_size` for your throughput
- **Resource Attributes**: Avoid high-cardinality attributes
- **Metric Labels**: Limit label cardinality to prevent metric explosion

## Troubleshooting

### Common Issues

1. **"OTEL not available" warning**: Install with `pip install "dotmac-observability[otel]"`

2. **"Prometheus not available" warning**: Install with `pip install "dotmac-observability[prometheus]"`

3. **Dashboard provisioning fails**: Check network connectivity and API credentials

4. **High memory usage**: Reduce sampling rate or batch sizes

5. **Missing metrics**: Ensure exporters are properly configured

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("dotmac.observability").setLevel(logging.DEBUG)
```

### Health Checks

Monitor component health:

```python
from dotmac.observability import get_observability_health

health = get_observability_health(otel, metrics, tenant_metrics)
if health.status != "healthy":
    for check in health.checks:
        if check.status != "healthy":
            print(f"Issue with {check.name}: {check.message}")
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/dotmac-framework/dotmac-observability
cd dotmac-observability
pip install -e ".[dev,all]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📖 Documentation: [https://docs.dotmac.com/observability](https://docs.dotmac.com/observability)
- 🐛 Issues: [GitHub Issues](https://github.com/dotmac-framework/dotmac-observability/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/dotmac-framework/dotmac-observability/discussions)