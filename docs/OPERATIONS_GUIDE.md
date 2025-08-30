# DotMac Framework Operations Guide

## 📋 Overview

This guide provides comprehensive documentation for all operational aspects of the DotMac Framework, including monitoring, deployment, security, backup, performance, and development workflows.

## 🗂️ Documentation Structure

### Core Documentation

- **[Operations Guide](./OPERATIONS_GUIDE.md)** - This comprehensive guide (you are here)
- **[Security Implementation](./security/SECURITY_IMPLEMENTATION.md)** - Security hardening and validation
- **[API Documentation](./api/README.md)** - Complete API documentation for both services

### Specialized Documentation

- **[Deployment Guide](#deployment)** - Production deployment procedures
- **[Monitoring Setup](#monitoring)** - Monitoring and alerting configuration
- **[Backup & Recovery](#backup-recovery)** - Backup and disaster recovery procedures
- **[Performance Optimization](#performance)** - Performance tuning and optimization
- **[Development Environment](#development)** - Development setup and workflows

---

## 🚀 Deployment

### Production Deployment

**Primary Script**: `deployment/scripts/deploy.sh`

```bash
# Full production deployment
sudo bash deployment/scripts/deploy.sh

# Options
sudo bash deployment/scripts/deploy.sh production false false    # Skip backup & tests
sudo bash deployment/scripts/deploy.sh production true true true # Force with all options
```

**What it does**:

- ✅ Validates system requirements and environment
- ✅ Creates required directories with proper permissions
- ✅ Sets up SSL certificates (self-signed for testing)
- ✅ Backs up existing deployment
- ✅ Runs pre-deployment validation tests
- ✅ Builds optimized Docker images
- ✅ Deploys infrastructure services (PostgreSQL, Redis, OpenBao)
- ✅ Runs database migrations
- ✅ Deploys application services
- ✅ Verifies deployment health

**Key Files**:

- `deployment/production/docker-compose.prod.yml` - Production container orchestration
- `deployment/production/nginx/nginx.conf` - Production Nginx configuration
- `deployment/production/.env.production` - Production environment variables

### Rollback Procedures

**Primary Script**: `deployment/scripts/rollback.sh`

```bash
# List available backups
bash deployment/scripts/rollback.sh --list

# Rollback to specific backup
bash deployment/scripts/rollback.sh 20241225_143000

# Force rollback without confirmation
bash deployment/scripts/rollback.sh --force 20241225_143000
```

---

## 📊 Monitoring

### Monitoring Stack Setup

**Primary Script**: `monitoring/setup_monitoring.sh`

```bash
# Setup complete monitoring stack
bash monitoring/setup_monitoring.sh

# Setup with custom retention
bash monitoring/setup_monitoring.sh --retention-days 60

# Setup with Slack notifications
SLACK_WEBHOOK="https://hooks.slack.com/..." bash monitoring/setup_monitoring.sh
```

**Components**:

- **Prometheus** - Metrics collection and storage
- **Grafana** - Visualization and dashboards
- **AlertManager** - Alert routing and notifications
- **Node Exporter** - System metrics
- **cAdvisor** - Container metrics

**Access Points**:

- Grafana Dashboard: `http://localhost:3000` (admin/admin)
- Prometheus: `http://localhost:9090`
- AlertManager: `http://localhost:9093`

**Key Files**:

- `monitoring/prometheus/prometheus.yml` - Prometheus configuration
- `monitoring/grafana/dashboards/` - Pre-configured dashboards
- `monitoring/alertmanager/alertmanager-flexible.yml` - Alert routing

### Custom Monitoring

**Health Checks**:

```bash
# Kubernetes health probes (Production-ready)
curl http://localhost:8000/health/live      # ISP Framework liveness
curl http://localhost:8000/health/ready     # ISP Framework readiness
curl http://localhost:8000/health/startup   # ISP Framework startup

curl http://localhost:8001/health/live      # Management Platform liveness
curl http://localhost:8001/health/ready     # Management Platform readiness
curl http://localhost:8001/health/startup   # Management Platform startup

# Legacy compatibility
curl http://localhost:8000/health           # ISP Framework (legacy)
curl http://localhost:8001/health           # Management Platform (legacy)
```

**Metrics Endpoints**:

- Application metrics: `http://localhost:8000/metrics`
- Container metrics: `http://localhost:8080/metrics` (cAdvisor)
- System metrics: `http://localhost:9100/metrics` (Node Exporter)

---

## 🔒 Security

### Security Hardening

**Validation Script**: `scripts/validate_security.py`

```bash
# Check current security status
python3 scripts/validate_security.py

# Generates detailed report: security_validation_report.json
```

**Implementation Script**: `scripts/apply_security_hardening.py`

```bash
# Dry run to see what would be changed
python3 scripts/apply_security_hardening.py --dry-run

# Apply all security hardening measures
python3 scripts/apply_security_hardening.py --force
```

**Security Features**:

- ✅ UFW firewall configuration
- ✅ SSH hardening (disable root login, limit attempts)
- ✅ fail2ban intrusion prevention
- ✅ Audit logging with auditd
- ✅ Docker security configuration
- ✅ System hardening (kernel parameters)
- ✅ Log rotation and security monitoring

**Security Validation Results**:

- Firewall status and rules
- SSH configuration hardening
- Intrusion prevention status
- Audit logging configuration
- Docker security settings
- File integrity monitoring
- System security limits

**Key Files**:

- `docs/security/SECURITY_IMPLEMENTATION.md` - Detailed security documentation
- `security/hardening/security-checklist.md` - Security checklist
- `/etc/ufw/` - Firewall configuration
- `/etc/fail2ban/jail.local` - Intrusion prevention
- `/etc/audit/rules.d/dotmac.rules` - Audit rules

---

## 💾 Backup & Recovery

### Automated Backup System

**Setup Script**: `deployment/scripts/setup_backups.sh`

```bash
# Setup daily backups with 30-day retention
sudo bash deployment/scripts/setup_backups.sh

# Setup weekly backups with encryption
sudo bash deployment/scripts/setup_backups.sh --schedule weekly --encrypt

# Setup with remote storage
sudo bash deployment/scripts/setup_backups.sh --remote-storage s3 --monitor
```

**Manual Backup**: `deployment/scripts/backup.sh`

```bash
# Full system backup
bash deployment/scripts/backup.sh --type full --verify

# Configuration only backup
bash deployment/scripts/backup.sh --type config

# Emergency backup (databases + configs)
bash deployment/scripts/backup.sh --type emergency --compress --encrypt
```

**Backup Types**:

- **Full**: Databases, configs, application data, logs
- **Incremental**: Databases, configs, recent logs
- **Config**: Configuration files only
- **Emergency**: Critical data (databases + configs)

### Disaster Recovery

**Recovery Script**: `deployment/scripts/disaster_recovery.py`

```bash
# List available backups
python3 deployment/scripts/disaster_recovery.py --list-backups

# Full system recovery
python3 deployment/scripts/disaster_recovery.py --backup /path/to/backup --type full

# Database-only recovery
python3 deployment/scripts/disaster_recovery.py --backup /path/to/backup --type database
```

**Recovery Types**:

- **full_system**: Complete system restoration
- **database_only**: Database restoration only
- **configuration**: Configuration files only
- **application_data**: Application data restoration
- **emergency**: Critical components only

**Key Files**:

- `/etc/cron.d/dotmac-backups` - Automated backup scheduling
- `/etc/dotmac/backup.conf` - Backup configuration
- `/opt/dotmac/backups/` - Backup storage location

---

## ⚡ Performance

### Performance Optimization

**Optimization Script**: `scripts/optimize_performance.py`

```bash
# Full performance optimization
python3 scripts/optimize_performance.py

# Test performance only
python3 scripts/optimize_performance.py --test-only

# Dry run to see what would be optimized
python3 scripts/optimize_performance.py --dry-run
```

**Optimizations Applied**:

- ✅ PostgreSQL query optimization and indexing
- ✅ Redis caching configuration and memory optimization
- ✅ Nginx performance tuning (HTTP/2, compression)
- ✅ Docker container resource limits
- ✅ Application-level caching strategies

**Performance Configurations**:

- `deployment/production/redis/redis-performance.conf` - Redis optimization
- `deployment/production/nginx/nginx-performance.conf` - Nginx optimization
- `deployment/production/docker-compose.performance.yml` - Container optimization
- `deployment/production/configs/caching.json` - Application caching config

### Performance Monitoring

**Key Metrics**:

- Database query performance
- Cache hit rates
- HTTP response times
- Container resource usage
- System load and memory

**Grafana Dashboards**:

- System Overview
- Application Performance
- Database Metrics
- Cache Performance

---

## 📚 API Documentation

### Automated Documentation Generation

**Documentation Generator**: `scripts/generate_api_docs.py`

```bash
# Generate complete API documentation
python3 scripts/generate_api_docs.py

# Custom output directory
python3 scripts/generate_api_docs.py --output-dir /custom/path
```

**Generated Documentation**:

- **Markdown Documentation**: Human-readable API docs
- **Postman Collections**: Ready-to-import API testing collections
- **OpenAPI Specifications**: Raw API specifications for tooling

**Available APIs**:

- **ISP Framework API**: `http://localhost:8001` (development)
- **Management Platform API**: `http://localhost:8000` (development)

**Documentation Files**:

- `docs/api/isp-framework-api.md` - ISP Framework documentation
- `docs/api/management-platform-api.md` - Management Platform documentation
- `docs/api/*-postman.json` - Postman collections
- `docs/api/*-openapi.json` - OpenAPI specifications

---

## 📝 Logging & Auditing

### Advanced Logging System

**Setup Script**: `scripts/setup_advanced_logging.py`

```bash
# Setup complete logging system
python3 scripts/setup_advanced_logging.py

# Dry run to see what would be configured
python3 scripts/setup_advanced_logging.py --dry-run
```

**Logging Features**:

- ✅ Centralized logging configuration
- ✅ Comprehensive audit trail system
- ✅ Automatic log monitoring and alerting
- ✅ Structured logging with JSON format
- ✅ Security event tracking
- ✅ Log rotation and retention

### Log Monitoring

**Monitor Script**: `scripts/monitor_logs.py`

```bash
# One-time log monitoring
python3 scripts/monitor_logs.py

# Continuous monitoring
python3 scripts/monitor_logs.py --continuous --interval 300
```

**Audit Logging Usage**:

```python
from shared.audit_logger import audit_logger

# Manual audit logging
audit_logger.log_authentication(user_id="123", action="login", status="success")

# Decorator-based auditing
@audit_api_call(resource_type='user', action='create')
def create_user():
    pass
```

**Log Files**:

- `/opt/dotmac/logs/application.log` - Application logs
- `/opt/dotmac/logs/errors.log` - Error logs
- `/opt/dotmac/logs/audit.log` - Audit trail
- `/opt/dotmac/logs/structured.log` - Structured JSON logs

---

## 💻 Development Environment

### Development Setup

**Setup Script**: `scripts/setup_dev_environment.sh`

```bash
# Interactive setup
bash scripts/setup_dev_environment.sh

# Full development setup
bash scripts/setup_dev_environment.sh --full

# Minimal setup (Docker only)
bash scripts/setup_dev_environment.sh --minimal
```

**Development Environment Includes**:

- ✅ Python virtual environment with dev dependencies
- ✅ Docker services (PostgreSQL, Redis, MailHog)
- ✅ VS Code configuration
- ✅ Development scripts and tools
- ✅ Pre-commit hooks setup

**Development Services**:

- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **MailHog**: `http://localhost:8025` (email testing)

**Development Scripts**:

- `dev-scripts/start-services.sh` - Start development services
- `dev-scripts/stop-services.sh` - Stop development services
- `dev-scripts/reset-db.sh` - Reset development database
- `dev-scripts/run-tests.sh` - Run all tests

### Testing & Validation

**Validation Scripts**:

```bash
# Import validation
python3 scripts/validate_imports.py

# Environment validation
python3 scripts/validate_environment.py

# Container smoke tests
python3 scripts/container_smoke_tests.py

# Security validation
python3 scripts/validate_security.py
```

---

## 🔧 Management Commands

### Service Management

```bash
# Check service status
cd deployment/production
docker-compose -f docker-compose.prod.yml ps

# View service logs
docker-compose -f docker-compose.prod.yml logs -f [service-name]

# Restart specific service
docker-compose -f docker-compose.prod.yml restart [service-name]

# Scale service
docker-compose -f docker-compose.prod.yml up -d --scale isp-framework=3
```

### Database Management

```bash
# Connect to production database
docker exec -it dotmac-postgres-prod psql -U dotmac_admin

# Database backup
docker exec dotmac-postgres-prod pg_dumpall -U dotmac_admin > backup.sql

# View database logs
docker logs dotmac-postgres-prod
```

### Cache Management

```bash
# Connect to Redis
docker exec -it dotmac-redis-prod redis-cli

# View Redis info
docker exec dotmac-redis-prod redis-cli INFO

# Clear cache
docker exec dotmac-redis-prod redis-cli FLUSHDB
```

---

## 🚨 Troubleshooting

### Common Issues

**Services Won't Start**:

```bash
# Check Docker status
docker info

# Check service logs
docker-compose -f docker-compose.prod.yml logs [service]

# Check disk space
df -h

# Check memory usage
free -m
```

**Database Connection Issues**:

```bash
# Check PostgreSQL status
docker exec dotmac-postgres-prod pg_isready -U dotmac_admin

# Check database logs
docker logs dotmac-postgres-prod

# Reset database connection
docker-compose -f docker-compose.prod.yml restart postgres-shared
```

**Performance Issues**:

```bash
# Check resource usage
docker stats

# Check system load
htop

# Check disk I/O
iotop

# Run performance validation
python3 scripts/optimize_performance.py --test-only
```

### Emergency Procedures

**System Recovery**:

1. Check service status: `docker-compose ps`
2. Check logs: `docker-compose logs`
3. Restart services: `docker-compose restart`
4. If needed, rollback: `bash deployment/scripts/rollback.sh --list`

**Security Incident**:

1. Check security logs: `/opt/dotmac/logs/audit.log`
2. Check fail2ban status: `fail2ban-client status`
3. Review monitoring alerts in Grafana
4. Run security validation: `python3 scripts/validate_security.py`

**Data Recovery**:

1. List backups: `python3 deployment/scripts/disaster_recovery.py --list-backups`
2. Choose recovery type and backup
3. Execute recovery: `python3 deployment/scripts/disaster_recovery.py --backup [path] --type [type]`

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Daily**:

- Monitor system health via Grafana dashboards
- Check backup completion
- Review security alerts

**Weekly**:

- Run security validation: `python3 scripts/validate_security.py`
- Review audit logs
- Update dependencies if needed

**Monthly**:

- System updates: `apt update && apt upgrade`
- Review and clean old backups
- Performance optimization review

### Getting Help

**Log Locations**:

- Application logs: `/opt/dotmac/logs/`
- System logs: `/var/log/`
- Docker logs: `docker logs [container]`

**Configuration Files**:

- Production config: `deployment/production/.env.production`
- Docker compose: `deployment/production/docker-compose.prod.yml`
- Nginx config: `deployment/production/nginx/nginx.conf`

**Validation Commands**:

- System health: `python3 scripts/validate_imports.py`
- Security status: `python3 scripts/validate_security.py`
- Performance test: `python3 scripts/optimize_performance.py --test-only`

---

## 📈 Monitoring & Metrics

### Key Performance Indicators

**System Metrics**:

- CPU usage < 80%
- Memory usage < 85%
- Disk usage < 90%
- Network latency < 100ms

**Application Metrics**:

- API response time < 200ms
- Database query time < 100ms
- Cache hit rate > 90%
- Error rate < 1%

**Security Metrics**:

- Failed login attempts < 10/hour
- Security patches applied within 72 hours
- Audit log completeness > 99%
- Firewall blocks monitored

### Alerting Rules

**Critical Alerts** (Immediate response):

- Service down
- Database connection failure
- Disk space > 95%
- Security incident

**Warning Alerts** (Monitor closely):

- High resource usage
- Slow response times
- Failed backups
- Certificate expiration

---

This operations guide provides comprehensive coverage of all DotMac Framework operational procedures. For specific implementation details, refer to the individual script files and their embedded documentation.
