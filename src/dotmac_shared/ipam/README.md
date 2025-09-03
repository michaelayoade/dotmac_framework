# DotMac Shared IPAM

Enhanced IPAM (IP Address Management) system with performance optimizations, advanced features, and enterprise-ready capabilities.

## 🚀 Features

### Performance Optimizations

- **Batch IP Scanning**: 99% reduction in database queries for large networks
- **PostgreSQL INET Types**: Native IP address handling with optimized queries
- **Chunked Processing**: Efficient handling of large network ranges
- **In-Memory Caching**: Reduced database load with intelligent caching

### Security & Audit

- **Comprehensive Audit Trail**: Track all operations with user context
- **Rate Limiting**: Protect against abuse with configurable limits
- **Tenant Isolation**: Multi-tenant security with strict data separation
- **MAC Address Validation**: Robust normalization and validation

### Automation & Maintenance

- **Celery Task System**: Automated cleanup and maintenance
- **Background Analytics**: Utilization reporting and trend analysis
- **Conflict Detection**: Automated IP conflict and integrity checking
- **Scheduled Cleanup**: Automatic expiration of old allocations/reservations

### Advanced Planning

- **Network Hierarchy**: Multi-level subnet organization
- **IP Pools**: Dedicated pools for different service types (DHCP, static, VIP)
- **Growth Forecasting**: Capacity planning with utilization projections
- **Subnet Optimization**: Automatic allocation with multiple strategies

## 📦 Installation

### Basic Installation

```bash
pip install -e ".[database]"
```

### Full Feature Installation

```bash
pip install -e ".[full]"
```

### Development Installation

```bash
pip install -e ".[full,dev,test]"
```

## 🔧 Configuration

### Basic Usage

```python
from dotmac_shared.ipam.enhanced_service import EnhancedIPAMService
from dotmac_shared.ipam.config_example import get_ipam_config

# Get configuration
config = get_ipam_config("production")

# Initialize service
ipam = EnhancedIPAMService(
    database_session=db_session,
    config=config
)
```

### With Rate Limiting

```python
from dotmac_shared.ipam.middleware.rate_limiting import create_redis_rate_limiter

# Setup rate limiter
rate_limiter = create_redis_rate_limiter("redis://localhost:6379/0")

ipam = EnhancedIPAMService(
    database_session=db_session,
    config=config,
    rate_limiter=rate_limiter
)
```

## 📊 Performance Metrics

| Operation | Before | After | Improvement |
|-----------|--------|--------|-------------|
| IP Allocation (/24 network) | 255 DB queries | 2 DB queries | 99.2% reduction |
| IP Allocation (/16 network) | 65,535 DB queries | ~65 DB queries | 99.9% reduction |
| Bulk allocation (50 IPs) | 50+ operations | 1 batch operation | 98% faster |

## 🏗️ Architecture

```
dotmac_shared/ipam/
├── core/                   # Core models and schemas
│   ├── models.py          # SQLAlchemy models with INET/UUID types
│   ├── exceptions.py      # Custom exceptions
│   └── schemas.py         # Pydantic schemas
├── services/              # Business logic
│   └── ipam_service.py    # Enhanced IPAM service with optimizations
├── repositories/          # Data access layer
│   └── ipam_repository.py # Repository pattern implementation
├── middleware/            # Middleware components
│   └── rate_limiting.py   # Rate limiting with Redis/memory backends
├── tasks/                 # Background tasks
│   └── cleanup_tasks.py   # Celery tasks for maintenance
├── planning/              # Network planning
│   └── network_planner.py # Advanced subnet planning and optimization
├── enhanced_service.py    # Production-ready enhanced service
└── config_example.py      # Configuration templates and examples
```

## 🚦 Quick Start

### 1. Network Creation

```python
# Create a network with planning validation
network = await ipam.create_network(
    tenant_id="tenant_123",
    cidr="10.0.1.0/24",
    network_type="customer",
    network_name="Customer Network A",
    enable_planning=True
)
```

### 2. IP Allocation

```python
# Single IP allocation
allocation = await ipam.allocate_ip(
    tenant_id="tenant_123",
    network_id="net_456",
    assigned_to="customer_device_1",
    mac_address="00:11:22:33:44:55"
)

# Bulk IP allocation
bulk_result = await ipam.bulk_allocate_ips(
    tenant_id="tenant_123",
    network_id="net_456",
    count=10
)
```

### 3. Network Planning

```python
# Plan network expansion
requirements = [
    {
        "purpose": "customer",
        "min_hosts": 1000,
        "growth_factor": 1.5,
        "priority": 1
    }
]

plan = await ipam.plan_network_expansion(
    tenant_id="tenant_123",
    requirements=requirements
)
```

### 4. Analytics

```python
# Get network analytics
analytics = await ipam.get_network_analytics(
    tenant_id="tenant_123",
    network_id="net_456"
)

# Cleanup expired resources
cleanup_result = await ipam.cleanup_expired_resources(
    tenant_id="tenant_123",
    dry_run=False
)
```

## 🤖 Background Tasks

### Celery Configuration

```python
from dotmac_shared.ipam.config_example import CELERY_IPAM_CONFIG

# Add to your Celery configuration
beat_schedule = CELERY_IPAM_CONFIG["beat_schedule"]
```

### Available Tasks

- **Cleanup Tasks**: Expire old allocations and reservations
- **Analytics Tasks**: Generate utilization reports
- **Audit Tasks**: Detect conflicts and integrity issues

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest -m unit

# Integration tests (requires Redis/PostgreSQL)
pytest -m integration

# All tests with coverage
pytest --cov=dotmac_shared.ipam
```

### Performance Testing

```bash
# Load testing
python -m dotmac_shared.ipam.tests.performance_tests

# Memory profiling
py-spy record -o profile.svg -- python your_script.py
```

## 📈 Monitoring

### Key Metrics

- IP allocation response time (target: <100ms)
- Database queries per allocation (target: <5)
- Network utilization trends
- Rate limit violations

### Logging

```python
import logging
logging.getLogger("dotmac_shared.ipam").setLevel(logging.INFO)
```

## 🔒 Security

### Rate Limits (Default)

- IP Allocation: 100 requests/hour (burst: 10)
- Network Creation: 10 requests/hour (burst: 2)
- Bulk Operations: 5 requests/hour (burst: 1)

### Audit Features

- Complete operation logging
- User context tracking
- Tenant isolation validation
- MAC address normalization

## 🚀 Production Deployment

### Database Migration

```sql
-- Update existing installations
ALTER TABLE ipam_networks ALTER COLUMN network_id TYPE UUID;
ALTER TABLE ipam_networks ALTER COLUMN cidr TYPE INET;
-- Add audit fields
ALTER TABLE ipam_networks ADD COLUMN created_by VARCHAR(100);
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/ipam

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
IPAM_RATE_LIMITING_ENABLED=true
IPAM_RATE_LIMITING_REDIS_URL=redis://localhost:6379/0

# Performance
IPAM_BATCH_SCANNING_ENABLED=true
IPAM_BATCH_SIZE=1000
```

## 📚 Documentation

- Performance Guide (see platform docs)
- [Configuration Reference](config_example.py)
- API Documentation (see platform docs)
- Migration Guide (see platform docs)

## 🤝 Contributing

1. Install development dependencies: `pip install -e ".[dev,test]"`
2. Run pre-commit: `pre-commit install`
3. Run tests: `pytest`
4. Follow code style: `black . && isort . && flake8`

## 📄 License

MIT License. See repository license for details.

## 🆘 Support

- GitHub Issues: [Report Issues](https://github.com/dotmac-framework/dotmac-framework/issues)
- Documentation: [docs.dotmac-framework.dev](https://docs.dotmac-framework.dev/ipam)
- Community: [Discord Server](https://discord.gg/dotmac-framework)
