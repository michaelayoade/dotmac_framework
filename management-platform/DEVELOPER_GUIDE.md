# Management Platform - Developer Guide

For complete development guidance, see the main [Developer Guide](../DEVELOPER_GUIDE.md).

## Management Platform Specific Commands

```bash
# Development setup
cd management-platform
make install-dev

# Start API server
make run-api

# Start background workers
make run-worker

# Run tests
make test

# Database operations
make db-migrate
make db-reset
```

## Key Directories

- `app/services/` - Core SaaS orchestration services
- `portals/` - Multi-tenant portal interfaces
- `deployment/` - Infrastructure as Code templates
- `config/` - Configuration management

See [main Developer Guide](../DEVELOPER_GUIDE.md) for architecture details, testing strategies, and workflows.