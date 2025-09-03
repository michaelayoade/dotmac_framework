# Changelog

All notable changes to the dotmac-observability package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-09-03

### Added

#### Core Features
- **OpenTelemetry Bootstrap**: Complete OTEL setup with traces, metrics, and logs
- **Unified Metrics Registry**: Abstraction layer over OpenTelemetry and Prometheus
- **Business Metrics & SLO Monitoring**: Tenant-scoped business metrics with SLO evaluation
- **Dashboard Provisioning**: Automated SigNoz/Grafana dashboard creation
- **Health Monitoring**: Built-in health checks for observability components

#### Configuration Management
- Environment-aware configuration (development, staging, production, test)
- Flexible exporter configuration (Console, OTLP HTTP/gRPC, Jaeger, Prometheus)
- Resource attribute management with custom attributes support
- Configurable sampling rates and batch sizes

#### Metrics System
- Default system metrics (HTTP requests, memory, CPU, database)
- Custom metric registration with multiple types (Counter, Gauge, Histogram, UpDownCounter)
- Prometheus metrics exposure with text format generation
- Label-based metric organization with cardinality control

#### Business Intelligence
- Default business metrics (login success rate, API success rate, latency)
- SLO target and threshold configuration
- Automated SLO evaluation with health status
- Error budget tracking and monitoring
- Historical SLO data retention

#### Dashboard Integration
- SigNoz dashboard provisioning via API
- Grafana dashboard provisioning via API  
- Template-based dashboard creation with variables
- Automated datasource creation and management
- Dashboard update and versioning support

#### Health & Monitoring
- Component health checks (OpenTelemetry, metrics registry, tenant metrics)
- Overall system health aggregation
- Health endpoint handler for web applications
- Performance monitoring and diagnostics

#### Developer Experience
- Comprehensive type hints and documentation
- Optional dependency management with extras
- Backward compatibility layer with deprecation warnings
- Integration examples for FastAPI, Django, Flask
- Migration guide from legacy observability modules

### Package Structure
```
dotmac-observability/
├── src/dotmac/observability/
│   ├── __init__.py          # Public API
│   ├── api.py              # Internal API re-exports
│   ├── config.py           # Configuration management
│   ├── bootstrap.py        # OpenTelemetry initialization
│   ├── metrics/
│   │   ├── registry.py     # Metrics registry abstraction
│   │   └── business.py     # Business metrics and SLO monitoring
│   ├── dashboards/
│   │   └── manager.py      # Dashboard provisioning
│   └── health.py           # Health integration
├── tests/                  # Comprehensive test suite
├── pyproject.toml         # Package configuration
├── README.md              # Documentation
└── CHANGELOG.md           # This file
```

### Optional Dependencies
- `otel`: OpenTelemetry SDK and exporters
- `prometheus`: Prometheus client library
- `dashboards`: HTTP client for dashboard provisioning
- `all`: All optional dependencies
- `dev`: Development and testing dependencies

### Default Metrics
- `http_requests_total`: HTTP request counter with method/endpoint/status labels
- `http_request_duration_seconds`: HTTP request duration histogram
- `system_memory_usage_bytes`: Current memory usage gauge
- `system_cpu_usage_percent`: Current CPU usage gauge  
- `database_connections_active`: Active database connections gauge
- `database_query_duration_seconds`: Database query duration histogram

### Default Business Metrics
- `login_success_rate`: User login success rate (99% SLO target)
- `api_request_success_rate`: API request success rate (99.5% SLO target)
- `service_provisioning_success_rate`: Service provisioning success (98% SLO target)
- `api_response_latency`: API response latency P95 (500ms SLO target)
- `database_query_latency`: Database query latency P95 (100ms SLO target)

### Environment Support
- **Development**: Console exporters, full sampling, relaxed budgets
- **Staging**: OTLP exporters, balanced optimization, bundle analysis
- **Production**: OTLP exporters, reduced sampling, strict SLO monitoring
- **Test**: Optimized for CI/CD environments

### Migration Support
- Backward compatibility shims for `dotmac_shared.observability`
- Deprecation warnings with migration guidance
- API compatibility layer for smooth transitions
- Migration helper functions and documentation

### Documentation
- Comprehensive README with examples
- API documentation with type hints
- Integration guides for popular frameworks
- Troubleshooting and performance tuning guides
- Architecture overview and design patterns

### Testing
- Unit tests with pytest
- Integration tests for end-to-end workflows  
- Mock support for external dependencies
- Test markers for optional dependencies (otel, prometheus, dashboards)
- CI/CD pipeline with matrix testing

### Initial Release Notes
This is the initial release of the dotmac-observability package, extracted and enhanced from the DotMac Framework's observability components. The package provides a complete, production-ready observability solution with enterprise-grade features including:

- Multi-tenant business metric tracking
- SLO monitoring with alerting thresholds
- Automated dashboard provisioning
- Health monitoring and diagnostics
- Flexible configuration management

The package is designed for easy integration into existing applications while providing advanced features for complex multi-tenant environments.

### Breaking Changes
- New package name: `dotmac-observability` (was part of `dotmac-shared`)
- Updated import paths: `from dotmac.observability import ...`
- Enhanced configuration system requiring migration from legacy setup
- Improved API with better separation of concerns

### Deprecations
- `dotmac_shared.observability` module is deprecated and will be removed in next minor release
- Legacy configuration patterns are deprecated in favor of new config system
- Direct OTEL imports are deprecated in favor of abstraction layer

### Security
- Safe handling of API keys and credentials
- Input validation for configuration parameters
- Secure dashboard provisioning with authentication
- Resource attribute filtering to prevent information leakage