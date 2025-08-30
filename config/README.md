# DotMac Framework Configuration

This directory contains centralized configuration files for the entire DotMac Framework.

## Configuration Structure

### Core Configuration Files

- **`shared_settings.py`** - Centralized settings shared across all services
- **`logging.conf`** - Unified logging configuration
- **Service-specific settings** are located in each service's `core/settings.py`

### Service Configuration Files

#### Communication & Integration

- **`communication_plugins.yml`** - Plugin configuration for communication channels
- **`universal_communication.yaml`** - Universal communication settings

#### Infrastructure Services

- **`redis.conf`** - Redis cache configuration
- **`backup-config.yml`** - System backup configuration

#### Network Services (ISP Framework)

- **`freeradius/`** - FreeRADIUS authentication server configuration
- **`snmp/`** - SNMP monitoring configuration

#### Monitoring & Observability

- **`signoz/`** - SignOz observability stack configuration
  - `clickhouse-config.xml` - ClickHouse database settings
  - `otel-collector-config.yaml` - OpenTelemetry collector
  - `prometheus.yml` - Prometheus metrics collection

#### Security

- **`openbao/`** - OpenBao secrets management configuration
- **`shared/openbao.hcl`** - Shared OpenBao policies

## Usage

### Loading Configuration in Services

```python
# ISP Framework
from dotmac_isp.core.settings import get_settings as get_isp_settings

# Management Platform
from dotmac_management.core.settings import get_settings as get_mgmt_settings

# Shared configuration
from config.shared_settings import get_shared_settings
```

### Environment Variables

Configuration supports environment variable overrides:

```bash
# Core settings
export ENVIRONMENT=production
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...

# Service-specific ports
export ISP_PORT=8001
export MANAGEMENT_PORT=8002

# Security
export SECRET_KEY=your-secret-key
export JWT_SECRET_KEY=your-jwt-secret
```

### Logging Configuration

Logging is centrally configured in `logging.conf` with:

- **Console output** for development
- **Rotating file logs** for production
- **Separate audit logs** for compliance
- **Service-specific loggers** with appropriate levels

## Production Considerations

1. **Security**: Ensure all secret keys are properly set via environment variables
2. **Logging**: Log files are rotated to prevent disk space issues
3. **Monitoring**: SignOz configuration provides comprehensive observability
4. **Backup**: Backup configuration ensures data persistence

## Configuration Validation

All configuration classes use Pydantic for:

- Type validation
- Environment variable loading
- Default value management
- Runtime configuration validation
