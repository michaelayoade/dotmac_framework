# DotMac Framework Observability Integration Guide

Complete production-ready OpenTelemetry integration with SigNoz for distributed tracing, metrics, and log correlation.

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install \
  opentelemetry-sdk \
  opentelemetry-exporter-otlp \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-asgi \
  opentelemetry-instrumentation-logging \
  opentelemetry-instrumentation-requests \
  opentelemetry-instrumentation-httpx \
  opentelemetry-instrumentation-sqlalchemy
```

### 2. Environment Configuration

Copy and configure your environment:

```bash
cp .env.observability.example .env
```

Key settings:
```env
OTEL_SERVICE_NAME=dotmac-framework
SERVICE_VERSION=1.0.0
ENVIRONMENT=production

OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://signoz-otel-collector:4317
OTEL_EXPORTER_OTLP_METRICS_ENDPOINT=http://signoz-otel-collector:4317
OTEL_TRACES_SAMPLING_RATIO=0.10
```

### 3. Basic Integration

```python
from fastapi import FastAPI
from dotmac_shared.observability import setup_observability
from dotmac_shared.database.session import create_async_database_engine

app = FastAPI()
engine = create_async_database_engine()

# One-line setup for complete observability
setup_observability(app, engine)
```

## 📊 Features Included

### ✅ Automatic Instrumentation
- **FastAPI**: Route tracing, request/response capture
- **SQLAlchemy**: Query monitoring, N+1 detection
- **HTTP Clients**: Requests, HTTPX instrumentation
- **ASGI Middleware**: Low-level request tracing

### ✅ Log-Trace Correlation
- Automatic trace_id/span_id injection
- Structured JSON logging
- Cross-service correlation
- Business context propagation

### ✅ Tenant-Aware Metrics
- Per-tenant operation tracking
- Multi-tenant request correlation
- Tenant-specific dashboards
- Cross-tenant analytics

### ✅ Database Visibility
- Query performance monitoring
- Slow query detection (100ms+ default)
- N+1 pattern detection
- Connection pool metrics

### ✅ Business Metrics
- Partner performance tracking
- Customer lifecycle events
- Commission calculations
- Revenue attribution
- SLA violation monitoring

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  OTel Middleware │────│   SigNoz OTLP   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Database ORM   │────│  Query Monitor  │────│  Traces & Logs  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Business Logic  │────│ Custom Metrics  │────│   Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎯 Usage Examples

### Basic Tracing

```python
from dotmac_shared.observability import get_tracer, get_logger

tracer = get_tracer("dotmac.partners")
logger = get_logger("dotmac.partners")

@app.get("/partners/{partner_id}")
async def get_partner(partner_id: str):
    with tracer.start_as_current_span("get_partner") as span:
        span.set_attribute("partner.id", partner_id)
        
        logger.info("Fetching partner", partner_id=partner_id)
        # ... business logic ...
        
        return partner_data
```

### Database Operations

```python
from dotmac_shared.observability import traced_db_operation, traced_transaction

@traced_db_operation("complex_partner_query")
async def get_partner_metrics(session: AsyncSession, partner_id: str):
    # Automatically traced with query monitoring
    result = await session.execute(
        select(Partner).where(Partner.id == partner_id)
    )
    return result.scalar_one()

# Transaction tracing
async with traced_transaction(session, "update_partner_commission"):
    partner.commission_rate = new_rate
    await session.commit()
```

### Business Metrics

```python
from dotmac_shared.observability.business_metrics import business_metrics

# Record business events
business_metrics.record_partner_signup(
    partner_tier="gold",
    territory="west_coast", 
    signup_source="referral"
)

business_metrics.record_customer_acquisition(
    partner_id="partner_123",
    customer_mrr=99.99,
    service_plan="residential_premium"
)

business_metrics.record_commission_calculation(
    partner_id="partner_123",
    commission_amount=150.00,
    base_amount=500.00,
    commission_rate=0.30
)
```

### Custom Middleware Integration

```python
from dotmac_shared.observability import TenantContextMiddleware

app.add_middleware(
    TenantContextMiddleware,
    tenant_header="x-tenant-id",
    request_id_header="x-request-id", 
    enable_tenant_validation=True
)
```

## 📈 SigNoz Dashboards & Alerts

### Recommended Dashboards

1. **Service Overview Dashboard**
   - P50/P90/P99 latency by route
   - Request rate and error rate
   - Database query performance
   - Top slow queries

2. **Business Metrics Dashboard**  
   - Partner signup trends
   - Customer acquisition rates
   - Commission calculation volumes
   - Revenue attribution by partner

3. **Tenant Analytics Dashboard**
   - Per-tenant request volumes
   - Tenant-specific error rates
   - Cross-tenant performance comparison
   - Tenant resource utilization

### Alert Configuration

```yaml
# High-priority alerts
- name: "API P95 Latency High"
  condition: "http_request_duration_p95 > 800ms for 5m"
  routes: ["/customers/*", "/partners/*"]
  
- name: "Error Rate Spike"  
  condition: "error_rate > 2% for 5m"
  scope: "service-wide"
  
- name: "Database Slow Queries"
  condition: "db_query_duration_p95 > 120ms for 10m"
  
- name: "N+1 Query Pattern Detected"
  condition: "db.n_plus_one.detected > 0"
  
- name: "SLA Violation"
  condition: "dotmac.sla.violations.total > 0"
  priority: "critical"
```

## 🔧 Configuration Details

### Sampling Strategy

```python
# Production: 10% sampling with parent-based
OTEL_TRACES_SAMPLING_RATIO=0.10

# Development: 100% sampling  
OTEL_TRACES_SAMPLING_RATIO=1.0

# Incident response: Temporary 100% sampling
OTEL_TRACES_SAMPLING_RATIO=1.0
```

### Security Configuration

```env
# For SigNoz Cloud
OTEL_EXPORTER_OTLP_INSECURE=false
OTEL_EXPORTER_OTLP_HEADERS=signoz-access-token=YOUR_TOKEN

# For self-hosted SigNoz
OTEL_EXPORTER_OTLP_INSECURE=true
```

### Performance Tuning

```env
# Batch processing configuration
OTEL_BSP_MAX_QUEUE_SIZE=512
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=512
OTEL_BSP_EXPORT_TIMEOUT=30000
OTEL_BSP_SCHEDULE_DELAY=5000

# Metrics export interval
OTEL_METRIC_EXPORT_INTERVAL=60000
```

## 🚀 Deployment Integration

### Docker Compose

```yaml
services:
  dotmac-api:
    build: .
    environment:
      OTEL_SERVICE_NAME: dotmac-framework
      OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: http://signoz-otel-collector:4317
      ENVIRONMENT: production
    depends_on:
      - signoz-otel-collector
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-api
spec:
  template:
    spec:
      containers:
      - name: api
        env:
        - name: OTEL_SERVICE_NAME
          value: "dotmac-framework"
        - name: OTEL_EXPORTER_OTLP_TRACES_ENDPOINT  
          value: "http://signoz-otel-collector:4317"
        - name: ENVIRONMENT
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
```

## 🔍 Troubleshooting

### Common Issues

1. **No traces appearing in SigNoz**
   - Check OTLP endpoint connectivity
   - Verify sampling configuration
   - Confirm service name matches

2. **High memory usage**
   - Reduce sampling ratio
   - Increase batch export size
   - Check for trace leaks

3. **Missing database traces**
   - Verify SQLAlchemy instrumentation
   - Check sync engine setup
   - Confirm event listeners attached

### Debug Endpoints

```python
@app.get("/debug/observability")
async def debug_observability():
    from opentelemetry import trace
    span = trace.get_current_span()
    
    return {
        "trace_id": format(span.get_span_context().trace_id, "032x"),
        "span_id": format(span.get_span_context().span_id, "016x"),
        "sampling_active": span.is_recording(),
    }
```

## 📚 Advanced Usage

### Custom Instrumentation

```python
from dotmac_shared.observability import get_tracer

tracer = get_tracer("dotmac.business")

with tracer.start_as_current_span("complex_calculation") as span:
    span.set_attribute("calculation.type", "commission")
    span.set_attribute("partner.tier", "gold")
    
    # Business logic
    result = calculate_commission(data)
    
    span.set_attribute("calculation.result", result)
    span.add_event("calculation_complete")
```

### Error Handling Integration

```python
from dotmac_shared.observability import get_logger
from dotmac_shared.api.exception_handlers import standard_exception_handler

logger = get_logger("dotmac.api")

@standard_exception_handler
async def api_endpoint():
    try:
        # Business logic
        pass
    except Exception as e:
        # Automatic trace correlation in logs
        logger.error("API operation failed", error=str(e))
        
        # Span automatically marked with error
        raise
```

## 🎖️ Best Practices

### 1. Naming Conventions
- Services: `dotmac-{component}` (e.g., `dotmac-management`)
- Spans: `{domain}.{operation}` (e.g., `partner.create_customer`)
- Metrics: `dotmac.{domain}.{metric}.{unit}` 

### 2. Attribute Standards
- Use consistent attribute keys: `tenant.id`, `user.id`, `partner.id`
- Include business context in spans
- Add debug attributes for troubleshooting

### 3. Performance Guidelines
- Use appropriate sampling rates (10% production, 100% development)
- Batch export for high-throughput scenarios  
- Monitor instrumentation overhead

### 4. Security Considerations
- Sanitize sensitive data in traces
- Use secure OTLP endpoints in production
- Implement proper access controls

---

## 🤝 Support

For issues or questions about observability integration:

1. Check the troubleshooting section above
2. Review logs for instrumentation errors
3. Verify SigNoz collector configuration
4. Contact the DotMac development team

The observability stack provides comprehensive visibility into your DotMac operations with minimal performance overhead and maximum business insight.