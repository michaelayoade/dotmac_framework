# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-09-06

### Added
- Initial release of dotmac-observability package
- MetricsCollector for counters, gauges, histograms, and timers
- HealthMonitor for configurable health checks
- FastAPI middleware integration
- Optional OpenTelemetry bridge
- Type hints and comprehensive documentation

### Features
- In-memory metrics collection
- Health checks with timeout and required/optional support
- FastAPI/Starlette middleware for HTTP metrics
- OpenTelemetry integration as optional extra
- Configurable metric tags and labels
- Context manager for timing operations

### Dependencies
- Core: stdlib only
- FastAPI extra: fastapi, starlette
- OTEL extra: opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp