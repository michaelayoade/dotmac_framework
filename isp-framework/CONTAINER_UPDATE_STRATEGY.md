# Container Update Strategy

## Strategic Container Version Management

This document outlines the strategic approach to container version management to prevent future compatibility issues.

## Version Pinning Policy

### Production Services (Critical - Pin to specific versions)
- **PostgreSQL**: `postgres:15.8-alpine` - Database compatibility is critical
- **Redis**: `redis:7.4-alpine` - Cache/session consistency required
- **Nginx**: `nginx:1.27-alpine` - Stable reverse proxy configuration

### Development Services (Controlled updates)
- **MinIO**: `minio/minio:RELEASE.2024-08-17T01-24-54Z` - S3 API compatibility
- **FreeRADIUS**: `freeradius/freeradius-server:3.2.5` - RADIUS protocol stability
- **OpenBao**: `openbao/openbao:2.3.2` - Secrets management consistency

## Update Schedule

### Monthly Review (Low Risk)
- Check for security updates in pinned versions
- Test updates in staging environment first

### Quarterly Updates (Controlled)
- Update to latest stable minor versions
- Full regression testing required
- Document breaking changes

### Major Version Updates (Planned)
- Schedule during maintenance windows
- Full backup and rollback procedures
- Load testing and compatibility validation

## Update Commands

### Check for updates
```bash
# Check current versions
docker-compose images

# Check for newer versions (manual research required)
# PostgreSQL: https://hub.docker.com/_/postgres/tags
# Redis: https://hub.docker.com/_/redis/tags
# Nginx: https://hub.docker.com/_/nginx/tags
```

### Testing Updates
```bash
# 1. Update versions in docker-compose.yml
# 2. Test in isolated environment
make docker-clean
make docker-build
make docker-run

# 3. Run comprehensive tests
make test-integration
make test-database-all

# 4. Validate health endpoints
curl http://localhost:8001/health
```

### Rollback Procedure
```bash
# 1. Revert docker-compose.yml to previous versions
# 2. Clean and rebuild
make docker-clean
make docker-build
make docker-run

# 3. Restore from backup if needed
# (Database-specific restore procedures)
```

## Version Matrix

| Service | Current Version | Last Updated | Next Review |
|---------|----------------|--------------|-------------|
| PostgreSQL | 15.8-alpine | 2024-08-24 | 2024-11-24 |
| Redis | 7.4-alpine | 2024-08-24 | 2024-11-24 |
| MinIO | RELEASE.2024-08-17T01-24-54Z | 2024-08-24 | 2024-11-24 |
| Nginx | 1.27-alpine | 2024-08-24 | 2024-11-24 |
| FreeRADIUS | 3.2.5 | 2024-08-24 | 2024-11-24 |
| OpenBao | 2.3.2 | 2024-08-24 | 2024-11-24 |

## Automated Checks

### Pre-deployment validation
```bash
# Add to CI/CD pipeline
make validate-container-versions
```

### Health monitoring
```bash
# Monitor container health in production
make monitor-container-health
```

## Security Updates

### Critical Security Updates
- Apply immediately with emergency deployment procedures
- Test in staging first if time permits
- Document all changes

### Regular Security Updates  
- Include in monthly review cycle
- Coordinate with maintenance windows
- Full testing required

## Breaking Change Management

### Before Updates
1. Review changelog for breaking changes
2. Check compatibility with current application code
3. Update documentation if configuration changes

### During Updates
1. Maintain previous version containers during transition
2. Blue-green deployment for zero-downtime updates
3. Monitor metrics during rollout

### After Updates
1. Validate all functionality
2. Update this strategy document
3. Document any configuration changes needed

## Contact & Escalation

- **Container Updates**: Development Team Lead
- **Security Updates**: Security Team
- **Emergency Rollbacks**: Production Operations Team

---
*This strategy prevents the PostgreSQL version compatibility issues we experienced and ensures predictable container behavior across environments.*