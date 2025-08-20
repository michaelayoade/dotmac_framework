# DotMac Platform Automation Guide

## Overview

The DotMac platform includes comprehensive automation tools for development, testing, deployment, and maintenance workflows. This guide covers all automation capabilities and how to use them effectively.

## Quick Start

### Basic Commands

```bash
# Development workflow
make workflow                    # Complete code quality + testing workflow
make workflow-setup             # Set up development environment
make workflow-report            # Generate project health report

# Docker & Deployment
make docker-config              # Generate all Docker configurations
make docker-build               # Build all Docker images
make docker-dev                 # Start development environment
make deploy-dev                 # Deploy to development environment

# Quality Assurance
make check                      # Run all quality checks
make fix                        # Auto-fix code issues
make ci-test                    # Full CI test suite
```

## Automation Scripts

### 1. Development Workflow (`scripts/automation/development_workflow.py`)

Manages the complete development lifecycle with automated quality checks.

#### Features
- **Code Quality**: Formatting, linting, type checking, security scanning
- **Testing**: Unit tests, integration tests, coverage reporting
- **Environment Setup**: Development environment initialization
- **Project Health**: Comprehensive project analysis and reporting

#### Usage

```bash
# Complete workflow (recommended for daily development)
python scripts/automation/development_workflow.py workflow

# Auto-fix issues where possible
python scripts/automation/development_workflow.py workflow --auto-fix

# Specific services only
python scripts/automation/development_workflow.py workflow --services dotmac_platform dotmac_api_gateway

# Skip specific checks
python scripts/automation/development_workflow.py workflow --skip-tests --skip-security

# Set up development environment
python scripts/automation/development_workflow.py setup

# Generate project report
python scripts/automation/development_workflow.py report
```

#### Configuration Options

- `--auto-fix`: Automatically fix issues where possible
- `--services`: Target specific services
- `--skip-formatting`: Skip code formatting check
- `--skip-linting`: Skip linting check
- `--skip-types`: Skip type checking
- `--skip-security`: Skip security scanning
- `--skip-tests`: Skip running tests
- `--skip-coverage`: Skip coverage check

### 2. Deployment Automation (`scripts/automation/deploy.py`)

Handles automated deployment across development, staging, and production environments.

#### Features
- **Pre-deployment Validation**: Environment checks, connectivity tests
- **Automated Backup**: Database and configuration backup before deployment
- **Rolling Deployment**: Zero-downtime deployment with health checks
- **Rollback Support**: Automatic rollback on deployment failure
- **Post-deployment Validation**: Comprehensive health and functionality checks

#### Usage

```bash
# Deploy to development
python scripts/automation/deploy.py development

# Deploy specific services
python scripts/automation/deploy.py staging --services dotmac_platform dotmac_api_gateway

# Deploy without automatic rollback (not recommended)
python scripts/automation/deploy.py production --no-rollback

# Deploy without backup (not recommended for production)
python scripts/automation/deploy.py development --no-backup

# Deploy with custom timeout
python scripts/automation/deploy.py production --timeout 600
```

#### Deployment Process

1. **Pre-deployment Checks**
   - Docker daemon availability
   - Required base images
   - Environment configuration validation
   - Database connectivity
   - Redis connectivity
   - Disk space and network connectivity

2. **Backup Creation**
   - Database dump
   - Redis data backup
   - Configuration files backup

3. **Service Build & Deployment**
   - Generate Docker configurations
   - Build service images
   - Deploy services with rolling updates

4. **Post-deployment Validation**
   - Service health checks
   - Database connectivity validation
   - API endpoint accessibility
   - Inter-service communication tests

5. **Rollback (if needed)**
   - Automatic rollback on validation failure
   - Database and Redis restoration
   - Service revert to previous version

### 3. Docker Configuration Generator (`scripts/generate_docker_configs.py`)

Generates standardized Docker configurations for all services.

#### Features
- **Multi-stage Dockerfiles**: Security, testing, production, development, hardened stages
- **Environment-specific Compose**: Development, staging, production configurations
- **Security-enhanced**: Non-root users, minimal attack surface, security scanning
- **Build Automation**: Automated build scripts for all services

#### Usage

```bash
# Generate all configurations
python scripts/generate_docker_configs.py --all

# Generate for specific service
python scripts/generate_docker_configs.py --service dotmac_platform

# Generate specific environment compose
python scripts/generate_docker_configs.py --environment production

# Generate build scripts only
python scripts/generate_docker_configs.py --build-scripts

# Generate security configurations
python scripts/generate_docker_configs.py --security
```

## Makefile Commands

The enhanced Makefile provides convenient shortcuts for all automation workflows.

### Development Commands

```bash
# Environment setup
make install-dev               # Install development dependencies
make workflow-setup           # Automated development environment setup

# Code quality
make workflow                 # Complete development workflow
make check                    # All quality checks
make fix                      # Auto-fix issues
make lint                     # Linting with complexity checks
make format                   # Code formatting
make type-check               # Type checking
make security                 # Security scanning

# Testing
make test                     # All tests with coverage
make test-unit                # Unit tests only (fast)
make test-integration         # Integration tests
make test-package PACKAGE=dotmac_platform  # Test specific package
```

### Docker & Deployment Commands

```bash
# Docker operations
make docker-config            # Generate Docker configurations
make docker-build             # Build all images
make docker-dev               # Start development environment
make docker-staging           # Start staging environment
make docker-prod              # Start production environment
make docker-stop              # Stop all environments
make docker-clean             # Clean Docker resources

# Deployment
make deploy-dev               # Deploy to development
make deploy-staging           # Deploy to staging
make deploy-prod              # Deploy to production
```

### Utility Commands

```bash
# Project management
make workflow-report          # Project health report
make complexity-report        # Detailed complexity analysis
make clean                    # Clean build artifacts
make deps-check               # Check dependency vulnerabilities
make deps-update              # Update dependencies

# CI/CD
make ci-test                  # Complete CI test suite
make ci-quick                 # Quick CI checks
make ci-install               # Install CI dependencies
```

## Environment-Specific Workflows

### Development Environment

```bash
# Complete development setup
make workflow-setup
make docker-config
make docker-dev

# Daily development workflow
make workflow

# Test changes
make test-package PACKAGE=dotmac_platform
make docker-build
make deploy-dev
```

### Staging Environment

```bash
# Staging deployment with validation
python scripts/automation/deploy.py staging --version v1.2.3

# Run integration tests against staging
make test-integration

# Performance testing
python tests/performance/benchmarks.py
```

### Production Environment

```bash
# Production deployment with full validation
python scripts/automation/deploy.py production --version v1.2.3

# Security scan before deployment
make security-strict
./docker/security/scan-all.sh

# Monitor deployment
make logs
make health
```

## Continuous Integration

### GitHub Actions Integration

```yaml
# .github/workflows/ci.yml example
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: make ci-install
      - run: make ci-test
```

### Local CI Simulation

```bash
# Simulate complete CI pipeline
make ci-test

# Quick feedback cycle
make ci-quick
```

## Monitoring & Observability

### Health Checks

```bash
# Service health monitoring
make health

# View logs
make logs
make logs-service SERVICE=dotmac-platform

# Performance monitoring
python scripts/automation/development_workflow.py report
```

### Security Monitoring

```bash
# Regular security scans
make security
./docker/security/scan-all.sh

# Dependency vulnerability checks
make deps-check

# Generate security report
make security-report
```

## Best Practices

### Development Workflow

1. **Start with setup**: `make workflow-setup`
2. **Daily development**: `make workflow`
3. **Before commits**: `make check`
4. **Pre-deployment**: `make ci-test`

### Deployment Workflow

1. **Test locally**: `make docker-dev`
2. **Deploy to staging**: `make deploy-staging`
3. **Validate staging**: Run integration tests
4. **Deploy to production**: `make deploy-prod`
5. **Monitor production**: Check health and logs

### Code Quality

1. **Use auto-fix**: `make fix`
2. **Check complexity**: `make complexity-report`
3. **Security first**: `make security-strict`
4. **Maintain coverage**: `make test-coverage`

## Troubleshooting

### Common Issues

#### Docker Issues
```bash
# Clean Docker environment
make docker-clean
make docker-stop

# Rebuild from scratch
make clean
make docker-config
make docker-build
```

#### Test Failures
```bash
# Run specific test
make test-package PACKAGE=dotmac_platform

# Check test environment
make workflow-setup

# Debug tests
cd dotmac_platform && python -m pytest tests/ -v --pdb
```

#### Deployment Issues
```bash
# Check deployment logs
python scripts/automation/deploy.py development --no-validation

# Manual rollback
docker-compose -f docker-compose.development.yml down
# Restore from backup manually
```

### Performance Issues

#### Slow Tests
```bash
# Run only unit tests
make test-unit

# Profile specific tests
cd dotmac_platform && python -m pytest tests/test_slow.py --profile
```

#### Build Performance
```bash
# Use Docker build cache
make docker-build

# Build specific services
python scripts/generate_docker_configs.py --service dotmac_platform
```

## Advanced Configuration

### Custom Automation Scripts

Create custom automation by extending the base classes:

```python
# scripts/custom_automation.py
from scripts.automation.development_workflow import DevelopmentWorkflow

class CustomWorkflow(DevelopmentWorkflow):
    def custom_check(self):
        # Implement custom validation
        pass
```

### Environment-Specific Overrides

```bash
# Custom deployment configuration
export DEPLOYMENT_ENV=custom
python scripts/automation/deploy.py custom --config custom-config.yml
```

### Integration with External Tools

```bash
# Integrate with external monitoring
make deploy-prod && curl -X POST https://monitoring.company.com/deployments
```

## References

- [Platform Documentation](PLATFORM_DOCUMENTATION.md)
- [Development Guide](DEVELOPMENT_GUIDE.md)
- [Test Organization Standards](TEST_ORGANIZATION_STANDARDS.md)
- [Docker Security Guide](docker/security/hardening-checklist.md)