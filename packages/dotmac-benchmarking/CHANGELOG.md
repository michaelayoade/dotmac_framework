# Changelog

All notable changes to the dotmac-benchmarking package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-06

### Added
- Initial release of dotmac-benchmarking package
- Core benchmarking framework with `BenchmarkRunner`
- HTTP benchmarking module with httpx integration (optional)
- Database benchmarking module with SQLAlchemy support (optional)  
- System monitoring module with psutil integration (optional)
- Benchmark comparison and reporting utilities
- Comprehensive test coverage (>90%)
- Type hints and mypy compliance
- Examples and documentation

### Features
- Async-first design for modern Python applications
- Modular architecture with optional dependencies
- Thread-safe benchmark execution
- Statistical analysis of benchmark results (min, max, avg, percentiles)
- JSON report generation for CI/CD integration
- Resource usage monitoring during benchmarks
- Configurable timeout and retry mechanisms

### Dependencies
- Python 3.9+ support
- Zero runtime dependencies for core functionality
- Optional extras: httpx, sqlalchemy, psutil
- Development dependencies: pytest, mypy, ruff

### Security
- Safe query parameterization for database benchmarks  
- Rate limiting for HTTP benchmarks
- Resource monitoring without sensitive data exposure
- Timeout protections to prevent hanging benchmarks