# dotmac-observability

Lightweight metrics and health toolkit for DotMac services.

## Features

- **Metrics Collection**: Counters, gauges, histograms, and timers
- **Health Monitoring**: Configurable health checks with timeout support
- **FastAPI Integration**: Optional middleware for HTTP metrics
- **OpenTelemetry Bridge**: Optional OTEL integration

## Quick Start

```python
from dotmac_observability import get_collector, HealthMonitor

# Metrics
collector = get_collector()
collector.counter("requests_total", tags={"method": "GET"})
collector.gauge("memory_usage", 512.5)

with collector.timer("request_duration"):
    # Your code here
    pass

# Health checks
health = HealthMonitor()
health.add_check("database", lambda: True, required=True)
results = await health.run_checks()
```

## FastAPI Integration

```python
from fastapi import FastAPI
from dotmac_observability import get_collector, create_audit_middleware

app = FastAPI()
collector = get_collector()

# Add metrics middleware
app.add_middleware(create_audit_middleware(collector))

@app.get("/metrics")
async def metrics():
    return collector.get_summary()
```

## Installation

```bash
# Core functionality
pip install dotmac-observability

# With FastAPI support
pip install dotmac-observability[fastapi]

# With OpenTelemetry support
pip install dotmac-observability[otel]

# All extras
pip install dotmac-observability[all]
```

## API Reference

### MetricsCollector

- `counter(name, value=1.0, tags=None)` - Increment a counter
- `gauge(name, value, tags=None)` - Set a gauge value
- `histogram(name, value, tags=None)` - Record a histogram value
- `timer(name, tags=None)` - Context manager for timing operations
- `get_summary()` - Get all metrics as a dictionary

### HealthMonitor

- `add_check(name, check, required=True, timeout=5.0, description="")` - Add a health check
- `run_checks()` - Execute all health checks and return results
- `get_last_results()` - Get results from the last check run

## License

MIT License