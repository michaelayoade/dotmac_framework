# ISP Framework - Developer Guide

For complete development guidance, see the main [Developer Guide](../DEVELOPER_GUIDE.md).

## ISP Framework Specific Commands

```bash
# Development setup
cd isp-framework
make install-dev

# Start development server  
make run-dev

# Run tests
make test

# Database operations
make setup-db
make alembic-upgrade
```

## Key Directories

- `modules/` - Business domain modules (billing, identity, networking, etc.)
- `core/` - Shared utilities and configuration
- `portals/` - Portal-specific API endpoints  
- `integrations/` - External system integrations
- `plugins/` - Vendor plugin system

See [main Developer Guide](../DEVELOPER_GUIDE.md) for architecture details, testing strategies, and workflows.