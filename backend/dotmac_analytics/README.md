# DotMac Analytics

**Analytics and Business Intelligence for ISP Operations**

DotMac Analytics is a comprehensive analytics platform designed specifically for Internet Service Provider (ISP) operations. It provides real-time data collection, processing, visualization, and reporting capabilities to help ISPs make data-driven decisions and optimize their services.

## Features

### 🚀 Core Capabilities
- **Real-time Event Tracking** - Track user interactions, system events, and business metrics
- **Flexible Metrics System** - Define custom KPIs with counters, gauges, and histograms
- **Interactive Dashboards** - Create beautiful visualizations with customizable widgets
- **Automated Reporting** - Generate and schedule reports with multiple output formats
- **Customer Segmentation** - Build dynamic user segments based on behavior and attributes
- **Data Processing Pipelines** - Transform and aggregate data with configurable workflows

### 🏗️ Architecture
- **Multi-tenant** - Isolated data and resources per tenant
- **Scalable** - Built for high-volume data ingestion and processing
- **Extensible** - Plugin architecture for custom integrations
- **Production-ready** - Comprehensive monitoring, logging, and error handling

### 🔧 Technology Stack
- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, PostgreSQL
- **Processing**: Celery, Redis, Pandas, NumPy
- **APIs**: REST APIs with OpenAPI documentation
- **SDK**: Async Python SDK with type hints
- **CLI**: Rich command-line interface with Typer

## Quick Start

### Installation

```bash
# Install from PyPI
pip install dotmac-analytics

# Or install from source
git clone https://github.com/dotmac/isp-framework.git
cd isp-framework/dotmac_analytics
pip install -e .
```

### Basic Usage

```python
import asyncio
from dotmac_analytics import AnalyticsClient
from dotmac_analytics.models.enums import EventType, MetricType

async def main():
    # Initialize client
    async with AnalyticsClient("your_tenant_id") as client:
        # Track events
        await client.events.track_page_view(
            page_url="/dashboard",
            user_id="user_123"
        )
        
        # Create metrics
        await client.metrics.create_metric(
            name="active_users",
            display_name="Active Users",
            metric_type=MetricType.GAUGE
        )
        
        # Record metric values
        await client.metrics.set_gauge("active_users", 150)

asyncio.run(main())
```

### CLI Usage

```bash
# Initialize database
dotmac-analytics init-db

# Initialize tenant
dotmac-analytics init-tenant --tenant-id your_tenant

# Track an event
dotmac-analytics track-event "user_login" --user-id user123

# Create a metric
dotmac-analytics create-metric "response_time" "Response Time" --metric-type histogram

# Check health
dotmac-analytics health
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/analytics
DB_POOL_SIZE=10

# Redis Cache
REDIS_URL=redis://localhost:6379
CACHE_DEFAULT_TTL=3600

# Processing
PROCESSING_BATCH_SIZE=1000
PROCESSING_MAX_WORKERS=4

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# Features
ENABLE_REAL_TIME=true
ENABLE_QUERY_CACHE=true
```

### Configuration File

```python
from dotmac_analytics.core.config import AnalyticsConfig

config = AnalyticsConfig(
    environment="production",
    database=AnalyticsConfig.DatabaseConfig(
        url="postgresql://localhost/analytics",
        pool_size=20
    ),
    processing=AnalyticsConfig.ProcessingConfig(
        batch_size=5000,
        max_workers=8
    )
)
```

## API Documentation

### Events API

Track and query analytics events:

```python
# Track single event
POST /events/track
{
    "event_type": "page_view",
    "event_name": "dashboard_view",
    "user_id": "user_123",
    "properties": {"page": "/dashboard"}
}

# Track batch events
POST /events/track/batch
{
    "events": [...],
    "source": "web_app"
}

# Query events
POST /events/query
{
    "event_type": "page_view",
    "start_time": "2024-01-01T00:00:00Z",
    "limit": 100
}
```

### Metrics API

Manage metrics and KPIs:

```python
# Create metric
POST /metrics/
{
    "name": "response_time",
    "display_name": "Response Time",
    "metric_type": "histogram",
    "unit": "milliseconds"
}

# Record value
POST /metrics/values
{
    "metric_id": "response_time",
    "value": 120.5,
    "dimensions": {"endpoint": "/api/users"}
}

# Aggregate metrics
POST /metrics/aggregate
{
    "metric_id": "response_time",
    "aggregation_method": "avg",
    "granularity": "hour",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-01T23:59:59Z"
}
```

## SDK Reference

### AnalyticsClient

Main client for all analytics operations:

```python
from dotmac_analytics import AnalyticsClient

# Initialize with tenant ID
client = AnalyticsClient("tenant_123")

# Access SDK modules
await client.events.track(...)
await client.metrics.create_metric(...)
await client.dashboards.create_dashboard(...)
await client.reports.generate_report(...)
await client.segments.create_segment(...)
```

### Events SDK

Track and analyze user events:

```python
# Track events
await client.events.track(
    event_type=EventType.PAGE_VIEW,
    event_name="home_page",
    user_id="user_123",
    properties={"referrer": "google.com"}
)

# Convenience methods
await client.events.track_page_view("/home", user_id="user_123")
await client.events.track_click("button_1", user_id="user_123")
await client.events.track_conversion("purchase", value=99.99)

# Query events
events = await client.events.get_events(
    event_type=EventType.PAGE_VIEW,
    start_time=datetime.now(timezone.utc) - timedelta(days=1)
)

# Funnel analysis
funnel = await client.events.funnel_analysis(
    funnel_steps=["page_view", "click", "conversion"],
    start_time=start_time,
    end_time=end_time
)
```

### Metrics SDK

Manage KPIs and business metrics:

```python
# Create metrics
await client.metrics.create_metric(
    name="active_users",
    display_name="Active Users",
    metric_type=MetricType.GAUGE,
    unit="users"
)

# Record values
await client.metrics.record_value(
    metric_id="active_users",
    value=150,
    dimensions={"region": "us-east"}
)

# Convenience methods
await client.metrics.increment("page_views", value=1)
await client.metrics.set_gauge("cpu_usage", value=75.5)
await client.metrics.record_timing("response_time", duration_ms=120)

# Aggregation
aggregates = await client.metrics.aggregate(
    metric_id="page_views",
    aggregation_method=AggregationMethod.SUM,
    granularity=TimeGranularity.HOUR,
    start_time=start_time,
    end_time=end_time
)
```

## Data Models

### Events

Track user interactions and system events:

```python
class AnalyticsEvent:
    id: UUID
    tenant_id: str
    event_type: str          # page_view, click, conversion, etc.
    event_name: str          # specific event identifier
    user_id: Optional[str]   # user identifier
    session_id: Optional[str] # session identifier
    properties: Dict[str, Any] # event-specific data
    context: Dict[str, Any]   # environmental data
    timestamp: datetime
```

### Metrics

Define and track KPIs:

```python
class Metric:
    id: UUID
    tenant_id: str
    name: str                # unique metric name
    display_name: str        # human-readable name
    metric_type: str         # counter, gauge, histogram
    unit: Optional[str]      # measurement unit
    dimensions: List[str]    # grouping dimensions
    tags: Dict[str, str]     # metadata tags
```

### Dashboards

Organize visualizations:

```python
class Dashboard:
    id: UUID
    tenant_id: str
    name: str
    display_name: str
    description: Optional[str]
    layout: Dict[str, Any]   # grid layout config
    widgets: List[Widget]    # dashboard widgets
    is_public: bool
    owner_id: str
```

## Examples

### Real-time Analytics Dashboard

```python
async def create_realtime_dashboard():
    async with AnalyticsClient("isp_tenant") as client:
        # Create dashboard
        dashboard = await client.dashboards.create_dashboard(
            name="realtime_ops",
            display_name="Real-time Operations",
            category="operations"
        )
        
        # Add widgets
        await client.dashboards.create_widget(
            dashboard_id=dashboard["dashboard_id"],
            name="active_users",
            title="Active Users",
            widget_type="gauge",
            query_config={
                "metric": "active_users",
                "aggregation": "last"
            }
        )
```

### Customer Segmentation

```python
async def create_user_segments():
    async with AnalyticsClient("isp_tenant") as client:
        # Create segment
        segment = await client.segments.create_segment(
            name="high_value_customers",
            display_name="High Value Customers",
            entity_type="customer"
        )
        
        # Add rules
        await client.segments.add_segment_rule(
            segment_id=segment["segment_id"],
            field_name="monthly_revenue",
            operator=SegmentOperator.GREATER_THAN,
            value=500
        )
```

### Automated Reporting

```python
async def setup_automated_reports():
    async with AnalyticsClient("isp_tenant") as client:
        # Create report
        report = await client.reports.create_report(
            name="weekly_summary",
            display_name="Weekly Summary Report",
            report_type=ReportType.ANALYTICS,
            query_config={
                "metrics": ["active_users", "revenue", "churn_rate"],
                "time_range": "7d"
            }
        )
        
        # Subscribe to notifications
        await client.reports.subscribe_to_report(
            report_id=report["report_id"],
            user_id="admin",
            email="admin@isp.com"
        )
```

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=dotmac_analytics --cov-report=html

# Run specific test categories
pytest tests/test_sdk_integration.py -v
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/dotmac/isp-framework.git
cd isp-framework/dotmac_analytics

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Format code
black dotmac_analytics/
isort dotmac_analytics/

# Lint code
flake8 dotmac_analytics/
mypy dotmac_analytics/

# Run all checks
pre-commit run --all-files
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "dotmac_analytics.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dotmac-analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dotmac-analytics
  template:
    metadata:
      labels:
        app: dotmac-analytics
    spec:
      containers:
      - name: analytics
        image: dotmac/analytics:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: analytics-secrets
              key: database-url
```

## Performance

### Optimization Tips

1. **Database Indexing**: Ensure proper indexes on frequently queried columns
2. **Connection Pooling**: Configure appropriate database pool sizes
3. **Caching**: Enable Redis caching for frequently accessed data
4. **Batch Processing**: Use batch APIs for high-volume data ingestion
5. **Async Operations**: Leverage async/await for I/O operations

### Monitoring

```python
# Built-in health checks
GET /health/
GET /health/detailed
GET /health/ready
GET /health/live

# Metrics endpoint for Prometheus
GET /metrics
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Reporting Issues

- Use GitHub Issues for bug reports and feature requests
- Provide detailed reproduction steps
- Include relevant logs and configuration

### Pull Requests

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://docs.dotmac.com/analytics](https://docs.dotmac.com/analytics)
- **Issues**: [GitHub Issues](https://github.com/dotmac/isp-framework/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dotmac/isp-framework/discussions)
- **Email**: support@dotmac.com

## Changelog

### v1.0.0 (2024-01-XX)

**Initial Release**

- ✨ Complete analytics platform for ISP operations
- 🚀 Real-time event tracking and processing
- 📊 Flexible metrics and KPI management
- 📈 Interactive dashboards and visualizations
- 📋 Automated report generation and scheduling
- 👥 Customer segmentation and analysis
- 🔧 Comprehensive SDK and REST APIs
- 🎯 Multi-tenant architecture with data isolation
- 📱 Rich CLI for management and operations
- 🧪 Extensive test coverage and examples
- 📚 Complete documentation and guides

---

**Built with ❤️ by the DotMac Team**
