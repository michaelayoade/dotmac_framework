# DotMac Platform Scripts

This directory contains operational and maintenance scripts for the DotMac platform.

## Production Scripts

### Security & SSL
- **`generate_postgres_ssl.sh`** - Generate SSL certificates for PostgreSQL
- **`generate-ssl-certs.sh`** - Generate SSL certificates for web services
- **`security-validation.sh`** - Validate security configurations

### Database Management
- **`setup_pg_auto_failover.sh`** - Configure PostgreSQL automatic failover
- **`setup_pg_replication.sh`** - Set up PostgreSQL replication

### Deployment & Operations
- **`deploy-production.sh`** - Production deployment script
- **`deploy_security_enhancements.sh`** - Deploy security configurations
- **`start-platform.sh`** - Start all platform services
- **`health-check.sh`** - System health monitoring

### Administration
- **`create-admin.sh`** - Create administrative users
- **`generate-secure-env.sh`** - Generate secure environment configurations

### Development & Testing
- **`generate_api_docs.py`** - Generate API documentation
- **`test-observability-pipeline.sh`** - Test monitoring pipeline
- **`validate-ai-workflow.sh`** - Validate AI integration workflows
- **`validate-service-standards.py`** - Validate service compliance

## Usage Guidelines

### Production Environment
1. Always test scripts in staging first
2. Review script contents before execution
3. Ensure proper backup procedures are in place
4. Monitor logs during script execution

### Security Considerations
- Scripts handle sensitive data (certificates, passwords)
- Run with appropriate user permissions
- Store generated secrets securely
- Follow principle of least privilege

### Maintenance
- Scripts are version controlled
- Update documentation when modifying scripts
- Test scripts after system updates
- Archive deprecated scripts properly

## Script Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| **Security** | SSL, certificates, validation | `generate_postgres_ssl.sh` |
| **Database** | PostgreSQL setup, replication | `setup_pg_replication.sh` |
| **Deployment** | Production deployment | `deploy-production.sh` |
| **Monitoring** | Health checks, observability | `health-check.sh` |
| **Development** | Documentation, testing | `generate_api_docs.py` |

## Best Practices

1. **Error Handling**: All scripts include proper error handling
2. **Logging**: Comprehensive logging for troubleshooting
3. **Idempotency**: Scripts can be run multiple times safely
4. **Documentation**: Each script includes usage instructions
5. **Security**: Sensitive operations require explicit confirmation

For detailed usage of individual scripts, see the script files themselves or the main deployment guide.
