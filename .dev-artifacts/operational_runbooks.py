#!/usr/bin/env python3
"""
Operational Runbooks Generator for Workflow Orchestration
Phase 4: Production Readiness

This module creates comprehensive operational runbooks and documentation
for production deployment and maintenance of workflow orchestration.
"""

import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import json


class OperationalRunbooksGenerator:
    """Generates operational runbooks and documentation for workflow orchestration."""
    
    def __init__(self, base_path: str = "/home/dotmac_framework"):
        self.base_path = Path(base_path)
        self.runbooks_dir = self.base_path / ".dev-artifacts" / "runbooks"
        self.runbooks_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_all_runbooks(self) -> Dict[str, str]:
        """Generate all operational runbooks."""
        runbooks_generated = {}
        
        # Generate deployment runbook
        runbooks_generated["deployment"] = self._create_deployment_runbook()
        
        # Generate troubleshooting runbook
        runbooks_generated["troubleshooting"] = self._create_troubleshooting_runbook()
        
        # Generate monitoring runbook
        runbooks_generated["monitoring"] = self._create_monitoring_runbook()
        
        # Generate incident response runbook
        runbooks_generated["incident_response"] = self._create_incident_response_runbook()
        
        # Generate maintenance runbook
        runbooks_generated["maintenance"] = self._create_maintenance_runbook()
        
        # Generate backup and recovery runbook
        runbooks_generated["backup_recovery"] = self._create_backup_recovery_runbook()
        
        # Generate security runbook
        runbooks_generated["security"] = self._create_security_runbook()
        
        # Generate scaling runbook
        runbooks_generated["scaling"] = self._create_scaling_runbook()
        
        return runbooks_generated
    
    def _create_deployment_runbook(self) -> str:
        """Create deployment runbook."""
        content = """# Deployment Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Overview
This runbook covers the complete deployment process for the DotMac Framework workflow orchestration system.

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04 LTS or higher
- **Memory**: Minimum 8GB RAM (16GB recommended)
- **CPU**: Minimum 4 cores (8 cores recommended)
- **Disk**: Minimum 100GB SSD storage
- **Network**: Stable internet connection with ports 80, 443, 8000-8003, 3000, 9090, 9093 available

### Software Dependencies
- Docker 20.10+
- Docker Compose 2.0+
- Nginx 1.18+
- PostgreSQL 15+ (can be containerized)
- Redis 7+ (can be containerized)
- Python 3.10+
- Git

### Access Requirements
- Root access to deployment server
- Database admin credentials
- SSL certificates for domain
- DNS management access

## Pre-Deployment Checklist

### 1. Environment Preparation
- [ ] Server provisioned with correct specifications
- [ ] Domain name configured and DNS propagated
- [ ] SSL certificates obtained and validated
- [ ] Firewall rules configured
- [ ] Backup storage configured

### 2. Code Preparation
- [ ] Code repository cloned to `/opt/dotmac`
- [ ] Production branch checked out
- [ ] Dependencies installed
- [ ] Configuration files reviewed
- [ ] Secrets and passwords generated

### 3. Database Preparation
- [ ] PostgreSQL instance running
- [ ] Production database created
- [ ] User accounts and permissions configured
- [ ] Connection tested from application server

## Deployment Steps

### Step 1: Initial Setup
```bash
# Clone repository
sudo mkdir -p /opt/dotmac
cd /opt/dotmac
sudo git clone https://github.com/yourorg/dotmac-framework.git .
sudo chown -R dotmac:dotmac /opt/dotmac

# Switch to production branch
sudo -u dotmac git checkout production
```

### Step 2: Configuration
```bash
# Copy production configuration
sudo -u dotmac cp .dev-artifacts/production-config/.env.production .env.production
sudo -u dotmac cp .dev-artifacts/production-config/docker-compose.production.yml .

# Update configuration with actual values
sudo -u dotmac nano .env.production
# Update: POSTGRES_PASSWORD, SECRET_KEY, JWT_SECRET_KEY, GRAFANA_ADMIN_PASSWORD
```

### Step 3: Database Migration
```bash
# Start database container first
sudo docker-compose -f docker-compose.production.yml up -d postgres redis

# Wait for database to be ready (60 seconds)
sleep 60

# Run migrations
sudo docker-compose -f docker-compose.production.yml run --rm dotmac-management /opt/dotmac/.venv/bin/alembic upgrade head
```

### Step 4: Application Deployment
```bash
# Build and start all services
sudo docker-compose -f docker-compose.production.yml build
sudo docker-compose -f docker-compose.production.yml up -d

# Verify all containers are running
sudo docker-compose -f docker-compose.production.yml ps
```

### Step 5: Nginx Configuration
```bash
# Install Nginx configuration
sudo cp .dev-artifacts/production-config/nginx.conf /etc/nginx/sites-available/dotmac
sudo ln -sf /etc/nginx/sites-available/dotmac /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 6: Monitoring Setup
```bash
# Apply monitoring configuration
sudo cp .dev-artifacts/monitoring/* /opt/monitoring/
sudo systemctl restart prometheus
sudo systemctl restart grafana-server
```

## Post-Deployment Verification

### 1. Health Checks
```bash
# Check application health
curl -f http://localhost:8000/api/workflows/health
curl -f http://localhost:8001/health

# Check external access
curl -f https://api.yourdomain.com/api/management/health
```

### 2. Database Verification
```bash
# Connect to database and verify tables
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
\\dt
SELECT COUNT(*) FROM saga_executions;
\\q
```

### 3. Monitoring Verification
```bash
# Check Prometheus targets
curl -f http://localhost:9090/api/v1/targets

# Check Grafana dashboard
curl -f http://localhost:3000/api/health
```

## Rollback Procedure

### Emergency Rollback
```bash
# Stop current deployment
sudo docker-compose -f docker-compose.production.yml down

# Restore previous version
sudo -u dotmac git checkout <previous-commit>
sudo docker-compose -f docker-compose.production.yml up -d

# Verify rollback
curl -f http://localhost:8000/api/workflows/health
```

### Database Rollback
```bash
# If migrations need to be rolled back
sudo docker-compose -f docker-compose.production.yml run --rm dotmac-management /opt/dotmac/.venv/bin/alembic downgrade <previous-revision>
```

## Troubleshooting Common Issues

### Issue: Container Won't Start
**Symptoms**: Docker container exits immediately
**Solution**:
1. Check logs: `docker logs <container-name>`
2. Verify environment variables in `.env.production`
3. Ensure database is accessible
4. Check file permissions

### Issue: Database Connection Failed
**Symptoms**: Application can't connect to database
**Solution**:
1. Verify PostgreSQL is running: `docker ps | grep postgres`
2. Test connection: `docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production`
3. Check network connectivity
4. Verify credentials in `.env.production`

### Issue: Health Check Failed
**Symptoms**: `/api/workflows/health` returns 500 error
**Solution**:
1. Check application logs
2. Verify database connection
3. Ensure all dependencies are running
4. Check system resources (CPU, memory)

## Security Checklist

- [ ] All default passwords changed
- [ ] SSL certificates installed and valid
- [ ] Firewall configured with minimal necessary ports
- [ ] Database access restricted to application only
- [ ] Internal endpoints protected with authentication
- [ ] Log files secured with appropriate permissions
- [ ] Regular security updates scheduled

## Maintenance Schedule

### Daily
- Monitor health dashboards
- Review error logs
- Check system resources

### Weekly
- Review security alerts
- Update monitoring thresholds
- Analyze performance metrics

### Monthly
- Security patches
- Certificate renewal check
- Backup validation
- Performance optimization review

## Support Contacts

- **Operations Team**: ops@yourdomain.com
- **Development Team**: dev@yourdomain.com
- **Security Team**: security@yourdomain.com
- **On-Call**: +1-555-ONCALL

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "deployment_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_troubleshooting_runbook(self) -> str:
        """Create troubleshooting runbook."""
        content = """# Troubleshooting Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Quick Reference

### Emergency Commands
```bash
# Check all service status
sudo docker-compose -f docker-compose.production.yml ps

# View application logs
sudo docker-compose -f docker-compose.production.yml logs -f dotmac-management

# Restart all services
sudo docker-compose -f docker-compose.production.yml restart

# Emergency shutdown
sudo docker-compose -f docker-compose.production.yml down
```

### Key Log Locations
- Application logs: `/opt/dotmac/logs/application.log`
- Nginx logs: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- System logs: `journalctl -u dotmac-management`
- Docker logs: `docker logs <container-name>`

## Common Issues and Solutions

### 1. Saga Execution Failures

#### Symptoms
- Saga status stuck in "RUNNING"
- High error rate in saga operations
- Timeouts in saga execution

#### Diagnosis
```bash
# Check saga execution status
curl -H "x-internal-request: true" http://localhost:8000/api/workflows/health

# Query database for stuck sagas
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM saga_executions WHERE status = 'RUNNING' AND updated_at < NOW() - INTERVAL '1 hour';
```

#### Solutions
1. **Restart Saga Coordinator**
   ```bash
   sudo docker-compose restart dotmac-management
   ```

2. **Manual Saga Recovery**
   ```bash
   # Mark stuck sagas as failed
   docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
   UPDATE saga_executions SET status = 'FAILED', error_message = 'Manual recovery - timeout' WHERE status = 'RUNNING' AND updated_at < NOW() - INTERVAL '1 hour';
   ```

3. **Increase Timeout Configuration**
   ```bash
   # Update .env.production
   WORKFLOW_SAGA_TIMEOUT_MINUTES=90
   sudo docker-compose restart dotmac-management
   ```

### 2. Database Performance Issues

#### Symptoms
- Slow response times
- High CPU usage on database
- Connection pool exhausted

#### Diagnosis
```bash
# Check database performance
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_user_tables;
```

#### Solutions
1. **Increase Connection Pool**
   ```bash
   # Update .env.production
   WORKFLOW_DATABASE_POOL_SIZE=30
   sudo docker-compose restart dotmac-management
   ```

2. **Add Missing Indexes**
   ```sql
   CREATE INDEX CONCURRENTLY idx_saga_executions_correlation_id ON saga_executions(correlation_id);
   CREATE INDEX CONCURRENTLY idx_saga_step_executions_saga_id ON saga_step_executions(saga_id);
   CREATE INDEX CONCURRENTLY idx_idempotent_operations_operation_key ON idempotent_operations(operation_key);
   ```

3. **Analyze Query Performance**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM saga_executions WHERE status = 'RUNNING';
   ```

### 3. High Memory Usage

#### Symptoms
- OOM killer triggered
- Container restarts frequently
- Slow response times

#### Diagnosis
```bash
# Check container memory usage
docker stats

# Check system memory
free -h
top -p $(pgrep -f dotmac-management)
```

#### Solutions
1. **Increase Container Memory Limits**
   ```yaml
   # docker-compose.production.yml
   services:
     dotmac-management:
       deploy:
         resources:
           limits:
             memory: 2G
   ```

2. **Optimize Python Memory Usage**
   ```bash
   # Add to .env.production
   PYTHONMALLOC=malloc
   PYTHONHASHSEED=0
   ```

3. **Enable Garbage Collection Tuning**
   ```bash
   # Add to container startup
   export PYTHONGC=1
   ```

### 4. Idempotency Key Conflicts

#### Symptoms
- Duplicate operations executed
- Idempotency check failures
- Data consistency issues

#### Diagnosis
```bash
# Check idempotency operations
curl -H "x-internal-request: true" http://localhost:8000/api/idempotency/test-key

# Query database
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT operation_key, status, COUNT(*) FROM idempotent_operations GROUP BY operation_key, status HAVING COUNT(*) > 1;
```

#### Solutions
1. **Clear Expired Keys**
   ```sql
   DELETE FROM idempotent_operations WHERE created_at < NOW() - INTERVAL '24 hours' AND status = 'COMPLETED';
   ```

2. **Fix Duplicate Keys**
   ```sql
   -- Keep only the latest record for each key
   DELETE FROM idempotent_operations 
   WHERE id NOT IN (
     SELECT MAX(id) FROM idempotent_operations GROUP BY operation_key
   );
   ```

### 5. Network Connectivity Issues

#### Symptoms
- External API calls fail
- Timeouts in service communication
- Load balancer health checks fail

#### Diagnosis
```bash
# Test network connectivity
docker exec -it dotmac-management curl -I http://external-api.com
docker exec -it dotmac-management nslookup external-api.com

# Check port availability
netstat -tlnp | grep :8000
```

#### Solutions
1. **Configure Docker Networks**
   ```bash
   # Recreate networks
   sudo docker-compose -f docker-compose.production.yml down
   sudo docker network prune
   sudo docker-compose -f docker-compose.production.yml up -d
   ```

2. **Update Firewall Rules**
   ```bash
   sudo ufw allow 8000/tcp
   sudo ufw reload
   ```

3. **DNS Resolution**
   ```bash
   # Update container DNS
   echo "nameserver 8.8.8.8" >> /etc/resolv.conf
   ```

## Performance Troubleshooting

### Slow Response Times

#### Investigation Steps
1. Check application metrics in Grafana
2. Review database query performance
3. Analyze system resources
4. Check external service dependencies

#### Quick Fixes
```bash
# Restart services in order
sudo docker-compose restart redis
sudo docker-compose restart postgres
sudo docker-compose restart dotmac-management
```

### High CPU Usage

#### Investigation Steps
```bash
# Identify CPU-intensive processes
top -H -p $(pgrep -f dotmac-management)
docker exec -it dotmac-management py-spy top --pid 1
```

#### Solutions
1. Reduce worker processes
2. Optimize database queries
3. Implement caching
4. Scale horizontally

## Health Check Failures

### Diagnosis Commands
```bash
# Test each component
curl -f http://localhost:8000/api/workflows/health
curl -f http://localhost:5432  # PostgreSQL
curl -f http://localhost:6379/ping  # Redis
curl -f http://localhost:9090/-/healthy  # Prometheus
```

### Component-Specific Fixes

#### Application Health Check
```bash
# Check application startup
docker logs dotmac-management | grep -i error
docker exec -it dotmac-management /opt/dotmac/.venv/bin/python -c "import dotmac_management; print('OK')"
```

#### Database Health Check
```bash
# Test database connection
docker exec -it dotmac-postgres pg_isready -U dotmac_prod
```

#### Redis Health Check
```bash
# Test Redis connection
docker exec -it dotmac-redis redis-cli ping
```

## Monitoring and Alerting Issues

### Prometheus Not Scraping
```bash
# Check Prometheus configuration
curl http://localhost:9090/api/v1/targets

# Restart Prometheus
sudo docker-compose restart prometheus
```

### Grafana Dashboard Issues
```bash
# Check Grafana logs
docker logs dotmac-grafana

# Reset admin password
docker exec -it dotmac-grafana grafana-cli admin reset-admin-password newpassword
```

## Emergency Procedures

### Complete System Failure
1. **Immediate Response**
   - Activate incident response team
   - Switch to maintenance page
   - Preserve logs and state

2. **System Recovery**
   ```bash
   # Emergency restart
   sudo docker-compose -f docker-compose.production.yml down
   sudo docker-compose -f docker-compose.production.yml up -d
   ```

3. **Data Recovery**
   - Restore from latest backup
   - Run database migrations
   - Verify data integrity

### Data Corruption
1. **Stop all services**
   ```bash
   sudo docker-compose -f docker-compose.production.yml down
   ```

2. **Restore from backup**
   ```bash
   # Restore database
   docker exec -i dotmac-postgres pg_restore -U dotmac_prod -d dotmac_production < backup.sql
   ```

3. **Verify and restart**
   ```bash
   # Verify data integrity
   docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
   SELECT COUNT(*) FROM saga_executions;
   
   # Restart services
   sudo docker-compose -f docker-compose.production.yml up -d
   ```

## Escalation Procedures

### Level 1: Self-Service
- Use this runbook
- Check monitoring dashboards
- Review recent changes

### Level 2: Team Lead
- Complex configuration issues
- Multi-component failures
- Performance degradation

### Level 3: Engineering
- Code-level issues
- Architecture decisions
- Major incidents

### Level 4: Vendor Support
- Infrastructure failures
- Third-party service issues
- Security incidents

## Contact Information

- **Operations**: ops@yourdomain.com, Slack: #ops
- **Development**: dev@yourdomain.com, Slack: #dev
- **Security**: security@yourdomain.com, Slack: #security
- **Emergency**: +1-555-ONCALL

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "troubleshooting_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_monitoring_runbook(self) -> str:
        """Create monitoring runbook."""
        content = """# Monitoring Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Monitoring Stack Overview

### Components
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **AlertManager**: Alert routing and notification
- **Application Metrics**: Custom workflow orchestration metrics

### Key Dashboards
- Workflow Orchestration Overview
- System Health Dashboard
- Database Performance Dashboard
- Alert Status Dashboard

## Critical Metrics to Monitor

### 1. Saga Orchestration Metrics

#### Primary Metrics
```prometheus
# Saga execution success rate
(rate(workflow_saga_executions_total{{status="COMPLETED"}}[5m]) / rate(workflow_saga_executions_total[5m])) * 100

# Average saga execution duration
rate(workflow_saga_duration_seconds_sum[5m]) / rate(workflow_saga_duration_seconds_count[5m])

# Saga execution rate
rate(workflow_saga_executions_total[5m])
```

#### Alert Thresholds
- Success rate < 95%: **CRITICAL**
- Average duration > 30s: **WARNING**
- Execution rate > 100/min: **INFO**

### 2. Idempotency Metrics

#### Primary Metrics
```prometheus
# Idempotency check success rate
rate(workflow_idempotency_checks_total{{result="SUCCESS"}}[5m]) / rate(workflow_idempotency_checks_total[5m])

# Idempotency cache hit rate
rate(workflow_idempotency_cache_hits_total[5m]) / rate(workflow_idempotency_operations_total[5m])

# Duplicate operation rate
rate(workflow_idempotency_checks_total{{result="DUPLICATE"}}[5m])
```

#### Alert Thresholds
- Check success rate < 99%: **CRITICAL**
- Cache hit rate < 80%: **WARNING**
- Duplicate rate > 5%: **WARNING**

### 3. Database Metrics

#### Primary Metrics
```prometheus
# Database connection utilization
workflow_database_connections_active / workflow_database_connections_max

# Query duration
rate(workflow_database_query_duration_seconds_sum[5m]) / rate(workflow_database_query_duration_seconds_count[5m])

# Database errors
rate(workflow_database_errors_total[5m])
```

#### Alert Thresholds
- Connection utilization > 80%: **WARNING**
- Query duration > 1s: **WARNING**
- Error rate > 1%: **CRITICAL**

## Dashboard Configuration

### 1. Workflow Overview Dashboard

#### Panels
1. **Saga Success Rate** (Stat Panel)
   - Query: `(rate(workflow_saga_executions_total{{status="COMPLETED"}}[5m]) / rate(workflow_saga_executions_total[5m])) * 100`
   - Threshold: Green >95%, Yellow 90-95%, Red <90%

2. **Active Sagas** (Stat Panel)
   - Query: `workflow_saga_active_total`
   - Alert: >100 active sagas

3. **Saga Execution Timeline** (Time Series)
   - Query: `rate(workflow_saga_executions_total[5m]) by (saga_name)`
   - Group by: saga_name

4. **Response Time Distribution** (Histogram)
   - Query: `histogram_quantile(0.95, rate(workflow_saga_duration_seconds_bucket[5m]))`
   - Show: 50th, 95th, 99th percentiles

### 2. System Health Dashboard

#### Panels
1. **Application Health** (Stat Panel)
   - Query: `up{{job="dotmac-management"}}`
   - Threshold: 1=UP, 0=DOWN

2. **Memory Usage** (Time Series)
   - Query: `process_resident_memory_bytes / 1024 / 1024`
   - Unit: MB

3. **CPU Usage** (Time Series)
   - Query: `rate(process_cpu_seconds_total[5m]) * 100`
   - Unit: Percent

4. **Database Connections** (Time Series)
   - Query: `workflow_database_connections_active`

## Alert Rules Configuration

### 1. Critical Alerts

#### Saga Success Rate Alert
```yaml
- alert: SagaSuccessRateLow
  expr: (rate(workflow_saga_executions_total{{status="COMPLETED"}}[5m]) / rate(workflow_saga_executions_total[5m])) * 100 < 95
  for: 2m
  labels:
    severity: critical
    team: operations
  annotations:
    summary: "Saga success rate is below 95%"
    description: "Current success rate: {{{{ $value }}}}%"
    runbook_url: "https://runbooks.yourdomain.com/saga-failures"
```

#### Database Connection Pool Alert
```yaml
- alert: DatabaseConnectionPoolHigh
  expr: workflow_database_connections_active / workflow_database_connections_max > 0.8
  for: 5m
  labels:
    severity: warning
    team: operations
  annotations:
    summary: "Database connection pool utilization is high"
    description: "Current utilization: {{{{ $value }}}}%"
    runbook_url: "https://runbooks.yourdomain.com/database-performance"
```

### 2. Warning Alerts

#### High Response Time Alert
```yaml
- alert: SagaResponseTimeHigh
  expr: rate(workflow_saga_duration_seconds_sum[5m]) / rate(workflow_saga_duration_seconds_count[5m]) > 30
  for: 10m
  labels:
    severity: warning
    team: development
  annotations:
    summary: "Saga response time is elevated"
    description: "Average response time: {{{{ $value }}}}s"
```

## Monitoring Procedures

### Daily Health Check
1. **Review Dashboards** (5 minutes)
   - Open Workflow Overview Dashboard
   - Check all panels are green/healthy
   - Note any trends or anomalies

2. **Check Active Alerts** (2 minutes)
   - Review AlertManager
   - Acknowledge handled alerts
   - Escalate unresolved critical alerts

3. **System Resources** (3 minutes)
   - Check CPU/Memory usage trends
   - Review disk space
   - Verify all services are running

### Weekly Review
1. **Performance Analysis**
   - Review week-over-week trends
   - Identify performance degradation
   - Update capacity planning

2. **Alert Tuning**
   - Review alert frequency and accuracy
   - Adjust thresholds based on patterns
   - Remove noisy or false alerts

3. **Dashboard Optimization**
   - Add missing metrics
   - Improve visualization clarity
   - Update documentation

### Monthly Maintenance
1. **Metrics Cleanup**
   - Remove unused metrics
   - Optimize storage retention
   - Clean up old alert rules

2. **Performance Baseline Update**
   - Update normal operating ranges
   - Adjust alert thresholds
   - Document capacity changes

## Troubleshooting Monitoring Issues

### Prometheus Issues

#### Metrics Not Appearing
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify application is exposing metrics
curl http://localhost:8000/metrics

# Check Prometheus configuration
docker exec -it prometheus cat /etc/prometheus/prometheus.yml
```

#### High Memory Usage
```bash
# Check Prometheus storage
df -h /prometheus-data/

# Reduce retention period
--storage.tsdb.retention.time=15d

# Check cardinality
curl http://localhost:9090/api/v1/label/__name__/values | jq '.data | length'
```

### Grafana Issues

#### Dashboard Not Loading
```bash
# Check Grafana logs
docker logs dotmac-grafana

# Verify datasource connection
curl -u admin:password http://localhost:3000/api/datasources/1/health
```

#### Missing Data Points
1. Check Prometheus query syntax
2. Verify time range alignment
3. Check data source configuration
4. Review panel query settings

### AlertManager Issues

#### Alerts Not Firing
```bash
# Check AlertManager configuration
curl http://localhost:9093/api/v1/status

# Verify alert rules
curl http://localhost:9090/api/v1/rules
```

#### Notifications Not Sent
```bash
# Check AlertManager logs
docker logs dotmac-alertmanager

# Test SMTP configuration
# Review webhook endpoints
```

## Custom Metrics Implementation

### Adding New Metrics

#### 1. Define Metric in Application
```python
from prometheus_client import Counter, Histogram, Gauge

# Counter for operations
workflow_operations_total = Counter(
    'workflow_operations_total',
    'Total number of workflow operations',
    ['operation_type', 'status']
)

# Histogram for duration
workflow_operation_duration = Histogram(
    'workflow_operation_duration_seconds',
    'Duration of workflow operations',
    ['operation_type']
)
```

#### 2. Instrument Code
```python
# In your application code
with workflow_operation_duration.labels(operation_type='saga').time():
    result = execute_saga()
    
workflow_operations_total.labels(
    operation_type='saga',
    status='success' if result.success else 'error'
).inc()
```

#### 3. Add to Dashboard
1. Create new panel in Grafana
2. Write Prometheus query
3. Configure visualization
4. Set appropriate thresholds

### Metric Naming Conventions
- Use `workflow_` prefix for all custom metrics
- Include units in metric names (e.g., `_seconds`, `_bytes`)
- Use consistent labels across related metrics
- Follow Prometheus naming best practices

## Performance Optimization

### Query Optimization
```prometheus
# Use rate() for counters
rate(workflow_saga_executions_total[5m])

# Use irate() for spiky metrics
irate(workflow_operations_total[5m])

# Aggregate before arithmetic
sum(rate(workflow_saga_executions_total[5m])) / sum(rate(workflow_saga_total[5m]))
```

### Storage Optimization
- Set appropriate retention periods
- Use recording rules for complex queries
- Implement metric cleanup policies
- Monitor storage growth

## Documentation and Training

### Runbook Updates
- Document new metrics and their meaning
- Update alert thresholds when needed
- Keep troubleshooting steps current
- Include examples and screenshots

### Team Training
- Regular monitoring reviews
- Alert response procedures
- Dashboard navigation training
- Metric interpretation skills

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "monitoring_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_incident_response_runbook(self) -> str:
        """Create incident response runbook."""
        content = """# Incident Response Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Incident Classification

### Severity Levels

#### P0 - Critical (Response: Immediate)
- Complete system outage
- Data corruption or loss
- Security breach
- Multiple customer-facing services down

#### P1 - High (Response: 30 minutes)
- Single critical service down
- Significant performance degradation
- Partial data loss
- Critical saga failures affecting business operations

#### P2 - Medium (Response: 2 hours)
- Non-critical service degradation
- Intermittent saga failures
- Monitoring alerts requiring investigation
- Performance issues not affecting customers

#### P3 - Low (Response: Next business day)
- Minor performance issues
- Non-critical monitoring alerts
- Documentation issues
- Enhancement requests

## Incident Response Team

### Roles and Responsibilities

#### Incident Commander
- **Primary**: Operations Team Lead
- **Responsibilities**:
  - Coordinate response efforts
  - Make escalation decisions
  - Communicate with stakeholders
  - Document incident timeline

#### Technical Lead
- **Primary**: Senior Developer
- **Responsibilities**:
  - Diagnose technical issues
  - Implement fixes
  - Coordinate with engineering team
  - Review code changes

#### Communications Lead
- **Primary**: Product Manager
- **Responsibilities**:
  - Customer communications
  - Internal stakeholder updates
  - Social media monitoring
  - Post-incident communication

## Immediate Response Procedures

### Step 1: Incident Detection (0-5 minutes)

#### Alert Sources
- Prometheus/Grafana alerts
- Customer reports
- Monitoring dashboards
- Health check failures

#### Initial Assessment
```bash
# Quick health check
curl -f https://api.yourdomain.com/api/workflows/health

# Check service status
sudo docker-compose -f docker-compose.production.yml ps

# Review recent alerts
curl http://localhost:9090/api/v1/alerts
```

### Step 2: Incident Declaration (0-10 minutes)

#### Declaration Criteria
- Customer impact confirmed
- SLA breach imminent or occurring
- Security implications identified
- Multiple services affected

#### Declaration Actions
1. **Create incident channel**: #incident-YYYY-MM-DD-NNN
2. **Page on-call team**: Use PagerDuty or similar
3. **Update status page**: Set to "Investigating"
4. **Activate war room**: Conference bridge or video call

### Step 3: Initial Investigation (0-30 minutes)

#### System Health Assessment
```bash
# Check all service health
for service in dotmac-management dotmac-isp postgres redis prometheus grafana; do
  echo "=== $service ==="
  docker logs --tail=50 $service | grep -i error
done

# Check system resources
df -h
free -m
top -n1 -b | head -20
```

#### Application-Specific Checks
```bash
# Check saga execution status
curl -H "x-internal-request: true" http://localhost:8000/api/workflows/health | jq '.saga_coordinator'

# Check database connectivity
docker exec -it dotmac-postgres pg_isready -U dotmac_prod

# Check recent saga failures
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT saga_id, saga_name, status, error_message, updated_at 
FROM saga_executions 
WHERE status = 'FAILED' AND updated_at > NOW() - INTERVAL '1 hour' 
ORDER BY updated_at DESC LIMIT 10;
```

## Incident-Specific Response Procedures

### P0: Complete System Outage

#### Immediate Actions (0-15 minutes)
1. **Verify scope of outage**
   ```bash
   # External health checks
   curl -f https://api.yourdomain.com/api/management/health
   curl -f https://api.yourdomain.com/api/isp/health
   ```

2. **Check infrastructure status**
   ```bash
   # All services status
   sudo docker-compose -f docker-compose.production.yml ps
   sudo systemctl status nginx
   ```

3. **Enable maintenance page**
   ```bash
   # Nginx maintenance configuration
   sudo cp /etc/nginx/maintenance.conf /etc/nginx/sites-enabled/dotmac
   sudo systemctl reload nginx
   ```

#### Recovery Actions
1. **Attempt quick restart**
   ```bash
   sudo docker-compose -f docker-compose.production.yml restart
   ```

2. **If restart fails, full recovery**
   ```bash
   sudo docker-compose -f docker-compose.production.yml down
   sudo docker-compose -f docker-compose.production.yml up -d
   ```

3. **Verify recovery**
   ```bash
   # Wait for services to initialize (2 minutes)
   sleep 120
   
   # Health check all components
   curl -f http://localhost:8000/api/workflows/health
   curl -f http://localhost:8001/health
   ```

### P1: Saga Orchestration Failures

#### Investigation Steps
```bash
# Check saga coordinator health
curl -H "x-internal-request: true" http://localhost:8000/api/workflows/health

# Identify failing sagas
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT saga_name, status, COUNT(*) as count, MAX(updated_at) as last_updated
FROM saga_executions 
WHERE updated_at > NOW() - INTERVAL '1 hour'
GROUP BY saga_name, status
ORDER BY count DESC;
```

#### Recovery Actions
1. **Restart saga coordinator service**
   ```bash
   sudo docker-compose -f docker-compose.production.yml restart dotmac-management
   ```

2. **Manual saga recovery**
   ```sql
   -- Mark stuck sagas for retry
   UPDATE saga_executions 
   SET status = 'RETRY_PENDING', retry_count = retry_count + 1
   WHERE status = 'RUNNING' 
   AND updated_at < NOW() - INTERVAL '30 minutes'
   AND retry_count < 3;
   ```

3. **Verify recovery**
   ```bash
   # Monitor saga execution
   watch -n 5 'curl -s -H "x-internal-request: true" http://localhost:8000/api/workflows/health | jq ".saga_coordinator.active_sagas"'
   ```

### P2: Database Performance Issues

#### Investigation
```bash
# Check database performance
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production

-- Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query 
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active';

-- Check connection count
SELECT count(*) FROM pg_stat_activity;

-- Check table sizes
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### Recovery Actions
1. **Kill long-running queries**
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes'
   AND state = 'active';
   ```

2. **Increase connection pool**
   ```bash
   # Update .env.production
   WORKFLOW_DATABASE_POOL_SIZE=30
   sudo docker-compose -f docker-compose.production.yml restart dotmac-management
   ```

## Communication Procedures

### Internal Communications

#### Incident Channel Updates
- **Frequency**: Every 15 minutes during active incident
- **Format**: 
  ```
  [HH:MM] UPDATE: Current status
  - Investigation findings
  - Actions taken
  - Next steps
  - ETA for resolution
  ```

#### Stakeholder Notifications
- **Engineering Leadership**: Immediate (P0/P1)
- **Product Leadership**: Within 30 minutes
- **Executive Leadership**: P0 within 15 minutes, P1 within 1 hour
- **Customer Success**: When customer impact confirmed

### External Communications

#### Status Page Updates
```markdown
**[HH:MM UTC] Investigating** - We are currently investigating issues with our workflow orchestration system. Some customers may experience delays in service provisioning.

**[HH:MM UTC] Update** - We have identified the root cause and are implementing a fix. We expect full resolution within 30 minutes.

**[HH:MM UTC] Resolved** - The issue has been resolved and all services are operating normally. We will publish a post-incident report within 24 hours.
```

#### Customer Communications
- **Severity P0**: Within 15 minutes of declaration
- **Severity P1**: Within 1 hour of declaration  
- **Channels**: Status page, email, support tickets

## Post-Incident Procedures

### Immediate Post-Incident (0-2 hours after resolution)

#### System Verification
```bash
# Comprehensive health check
curl -f https://api.yourdomain.com/api/workflows/health
curl -f https://api.yourdomain.com/api/management/health
curl -f https://api.yourdomain.com/api/isp/health

# Check for backlog processing
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT COUNT(*) FROM saga_executions WHERE status = 'PENDING';
```

#### Data Integrity Checks
```sql
-- Check for data consistency issues
SELECT COUNT(*) as incomplete_sagas FROM saga_executions 
WHERE status = 'RUNNING' AND updated_at < NOW() - INTERVAL '2 hours';

-- Verify idempotency integrity
SELECT COUNT(*) as orphaned_operations FROM idempotent_operations io
LEFT JOIN saga_executions se ON io.operation_key = se.correlation_id
WHERE se.id IS NULL AND io.created_at > NOW() - INTERVAL '6 hours';
```

### Post-Incident Review (24-48 hours after resolution)

#### Timeline Documentation
1. **Incident start time**
2. **Detection time**
3. **Response time**
4. **Escalation points**
5. **Resolution time**
6. **Customer impact duration**

#### Root Cause Analysis
1. **What happened?** - Factual timeline of events
2. **Why did it happen?** - Technical and process failures
3. **Why wasn't it prevented?** - Gap analysis
4. **Why wasn't it detected sooner?** - Monitoring gaps

#### Action Items
- **Immediate fixes**: Deploy within 1 week
- **Short-term improvements**: Deploy within 1 month
- **Long-term improvements**: Roadmap items
- **Process improvements**: Update runbooks and procedures

### Incident Review Template

```markdown
# Post-Incident Review: [Incident ID]

## Summary
- **Incident ID**: INC-YYYY-MM-DD-NNN
- **Severity**: P0/P1/P2/P3
- **Duration**: X hours Y minutes
- **Services Affected**: List
- **Customer Impact**: Description
- **Resolution**: Brief description

## Timeline
| Time (UTC) | Event | Actions Taken |
|------------|--------|---------------|
| HH:MM | Incident detected | ... |
| HH:MM | Response initiated | ... |
| HH:MM | Root cause identified | ... |
| HH:MM | Fix implemented | ... |
| HH:MM | Resolution confirmed | ... |

## Root Cause Analysis

### What Happened?
[Detailed technical explanation]

### Contributing Factors
1. Technical factors
2. Process factors  
3. Environmental factors

### Why It Wasn't Prevented
[Gap analysis]

### Why It Wasn't Detected Sooner
[Monitoring gaps]

## Action Items

### Immediate (1 week)
- [ ] Action item 1 - Owner - Due date
- [ ] Action item 2 - Owner - Due date

### Short-term (1 month)
- [ ] Action item 3 - Owner - Due date
- [ ] Action item 4 - Owner - Due date

### Long-term (3+ months)
- [ ] Action item 5 - Owner - Due date

## Lessons Learned
1. What went well?
2. What could be improved?
3. What should we do differently?

## Process Improvements
- Runbook updates needed
- Monitoring improvements
- Alert tuning
- Training requirements
```

## Contact Information

### Escalation Chain
1. **On-Call Engineer**: pager-duty@yourdomain.com
2. **Engineering Manager**: eng-manager@yourdomain.com  
3. **VP Engineering**: vp-eng@yourdomain.com
4. **CTO**: cto@yourdomain.com

### External Contacts
- **Cloud Provider Support**: [Provider emergency contact]
- **Database Vendor**: [Vendor emergency contact]
- **Security Team**: security-incident@yourdomain.com

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "incident_response_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_maintenance_runbook(self) -> str:
        """Create maintenance runbook."""
        content = """# Maintenance Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Maintenance Overview

### Maintenance Windows
- **Standard**: Sundays 2:00-6:00 AM UTC
- **Emergency**: As needed with 1-hour notice
- **Security**: Immediate for critical vulnerabilities

### Maintenance Types
- **Routine**: Regular updates and optimization
- **Preventive**: Proactive system improvements
- **Corrective**: Bug fixes and issue resolution
- **Emergency**: Critical security or stability fixes

## Pre-Maintenance Checklist

### Planning Phase (1 week before)
- [ ] Schedule maintenance window
- [ ] Notify stakeholders
- [ ] Prepare rollback procedures
- [ ] Review change documentation
- [ ] Validate test environment

### Preparation Phase (24 hours before)
- [ ] Create database backup
- [ ] Verify backup integrity
- [ ] Prepare maintenance scripts
- [ ] Test deployment in staging
- [ ] Notify customer success team

### Execution Phase (Day of maintenance)
- [ ] Enable maintenance page
- [ ] Verify all team members available
- [ ] Create communication channels
- [ ] Take final system snapshot

## Routine Maintenance Procedures

### Weekly Maintenance (Every Sunday)

#### 1. System Health Check
```bash
# Comprehensive system status
sudo docker-compose -f docker-compose.production.yml ps
sudo systemctl status nginx
df -h
free -m

# Application health
curl -f http://localhost:8000/api/workflows/health
curl -f http://localhost:8001/health
```

#### 2. Log Rotation and Cleanup
```bash
# Rotate application logs
sudo logrotate -f /etc/logrotate.d/dotmac

# Clean up old Docker logs
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log

# Remove old backup files (keep 30 days)
find /opt/dotmac/backups -type f -mtime +30 -delete
```

#### 3. Database Maintenance
```sql
-- Connect to database
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production

-- Analyze table statistics
ANALYZE;

-- Reindex critical tables
REINDEX TABLE saga_executions;
REINDEX TABLE saga_step_executions;
REINDEX TABLE idempotent_operations;

-- Clean up old completed sagas (older than 30 days)
DELETE FROM saga_step_executions 
WHERE saga_id IN (
    SELECT id FROM saga_executions 
    WHERE status = 'COMPLETED' 
    AND updated_at < NOW() - INTERVAL '30 days'
);

DELETE FROM saga_executions 
WHERE status = 'COMPLETED' 
AND updated_at < NOW() - INTERVAL '30 days';

-- Clean up old idempotency records (older than 7 days)
DELETE FROM idempotent_operations 
WHERE status = 'COMPLETED' 
AND created_at < NOW() - INTERVAL '7 days';

-- Update table statistics
VACUUM ANALYZE saga_executions;
VACUUM ANALYZE saga_step_executions;
VACUUM ANALYZE idempotent_operations;
```

#### 4. Performance Optimization
```bash
# Check slow queries
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Monitor connection pool usage
curl -s http://localhost:8000/metrics | grep -E "workflow_database_connections"

# Check memory usage trends
docker stats --no-stream
```

### Monthly Maintenance (First Sunday of month)

#### 1. Security Updates
```bash
# Update base system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
sudo docker-compose -f docker-compose.production.yml pull
sudo docker-compose -f docker-compose.production.yml up -d

# Check for security vulnerabilities
sudo docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  -v $HOME/.cache:/root/.cache/ \
  aquasec/trivy image dotmac/management:latest
```

#### 2. Certificate Management
```bash
# Check SSL certificate expiration
sudo certbot certificates

# Renew certificates if needed
sudo certbot renew --nginx

# Verify certificate validity
openssl x509 -in /etc/ssl/certs/yourdomain.com.crt -text -noout | grep -A2 "Validity"
```

#### 3. Backup Verification
```bash
# Test database backup restoration
sudo docker run --rm -v /opt/dotmac/backups:/backups \
  postgres:15 pg_restore --list /backups/latest_backup.sql

# Verify backup file integrity
sudo gzip -t /opt/dotmac/backups/*.gz

# Test configuration backup
sudo tar -tzf /opt/dotmac/backups/config_backup_$(date +%Y%m%d).tar.gz
```

#### 4. Capacity Planning Review
```bash
# Disk usage analysis
sudo du -sh /opt/dotmac/*
sudo du -sh /var/lib/docker/*

# Database size analysis
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT schemaname,tablename,pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size 
FROM pg_tables 
WHERE schemaname='public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Memory usage trends
free -h
cat /proc/meminfo | grep -E "(MemTotal|MemAvailable|MemFree)"
```

## Application Updates

### Code Deployment Process

#### 1. Pre-Deployment
```bash
# Enable maintenance page
sudo cp /etc/nginx/maintenance.html /var/www/html/maintenance.html
sudo cp /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/dotmac
sudo systemctl reload nginx

# Create pre-deployment backup
sudo docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production > /opt/dotmac/backups/pre_deploy_$(date +%Y%m%d_%H%M).sql
```

#### 2. Application Update
```bash
# Pull latest code
cd /opt/dotmac
sudo -u dotmac git fetch origin
sudo -u dotmac git checkout production
sudo -u dotmac git pull origin production

# Build new containers
sudo docker-compose -f docker-compose.production.yml build --no-cache

# Stop current services
sudo docker-compose -f docker-compose.production.yml down

# Run database migrations
sudo docker-compose -f docker-compose.production.yml run --rm dotmac-management \
  /opt/dotmac/.venv/bin/alembic upgrade head

# Start services
sudo docker-compose -f docker-compose.production.yml up -d
```

#### 3. Post-Deployment Verification
```bash
# Wait for services to start
sleep 60

# Health check
curl -f http://localhost:8000/api/workflows/health
curl -f http://localhost:8001/health

# Verify saga functionality
curl -X POST -H "Content-Type: application/json" -H "x-internal-request: true" \
  -d '{{"tenant_name":"test-deploy-verification","plan_id":"basic"}}' \
  http://localhost:8000/api/sagas/tenant-provision

# Check recent logs for errors
docker logs --tail=100 dotmac-management | grep -i error
```

#### 4. Enable Production Traffic
```bash
# Restore production nginx configuration
sudo cp /etc/nginx/sites-available/dotmac /etc/nginx/sites-enabled/dotmac
sudo systemctl reload nginx

# Remove maintenance page
sudo rm -f /var/www/html/maintenance.html
```

### Configuration Updates

#### Environment Variables
```bash
# Backup current configuration
sudo cp /opt/dotmac/.env.production /opt/dotmac/backups/.env.production.$(date +%Y%m%d_%H%M)

# Update configuration
sudo -u dotmac nano /opt/dotmac/.env.production

# Apply changes (rolling restart)
sudo docker-compose -f docker-compose.production.yml up -d --force-recreate
```

#### Database Schema Changes
```bash
# Always backup before schema changes
sudo docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production > /opt/dotmac/backups/pre_schema_$(date +%Y%m%d_%H%M).sql

# Run migrations
sudo docker-compose -f docker-compose.production.yml exec dotmac-management \
  /opt/dotmac/.venv/bin/alembic upgrade head

# Verify migrations
sudo docker-compose -f docker-compose.production.yml exec dotmac-management \
  /opt/dotmac/.venv/bin/alembic current
```

## Emergency Maintenance

### Critical Security Patches

#### Immediate Response (0-1 hour)
```bash
# Assess vulnerability impact
# Review security bulletin
# Prepare emergency patch

# Enable maintenance page immediately
sudo cp /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/dotmac
sudo systemctl reload nginx

# Apply security patch
sudo docker-compose -f docker-compose.production.yml down
# Apply patches to containers/code
sudo docker-compose -f docker-compose.production.yml up -d

# Verify security fix
# Run security scans
# Test functionality
```

### System Recovery

#### Complete System Restore
```bash
# Stop all services
sudo docker-compose -f docker-compose.production.yml down

# Restore from backup
sudo docker exec -i dotmac-postgres psql -U dotmac_prod -d dotmac_production < /opt/dotmac/backups/latest_backup.sql

# Restore configuration
sudo tar -xzf /opt/dotmac/backups/config_backup_latest.tar.gz -C /opt/dotmac/

# Restart services
sudo docker-compose -f docker-compose.production.yml up -d

# Verify system health
curl -f http://localhost:8000/api/workflows/health
```

## Monitoring During Maintenance

### Key Metrics to Watch
```bash
# Application health
watch -n 10 'curl -s http://localhost:8000/api/workflows/health | jq ".status"'

# System resources
watch -n 30 'free -m && df -h && uptime'

# Service logs
sudo docker-compose -f docker-compose.production.yml logs -f --tail=50
```

### Alert Suppression
```bash
# Suppress non-critical alerts during maintenance window
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{{
    "matchers": [{{"name": "alertname", "value": ".*", "isRegex": true}}],
    "startsAt": "'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'",
    "endsAt": "'$(date -u -d '+4 hours' +%Y-%m-%dT%H:%M:%S.000Z)'",
    "createdBy": "maintenance-window",
    "comment": "Planned maintenance window"
  }}'
```

## Post-Maintenance Procedures

### Verification Checklist
- [ ] All services running and healthy
- [ ] Health endpoints responding correctly
- [ ] Database connectivity verified
- [ ] Recent saga executions successful
- [ ] Monitoring and alerting operational
- [ ] No critical alerts active
- [ ] Performance within normal ranges
- [ ] Customer-facing functionality tested

### Documentation Updates
```bash
# Update maintenance log
echo "$(date): Completed weekly maintenance - no issues" >> /opt/dotmac/logs/maintenance.log

# Update system documentation
sudo nano /opt/dotmac/docs/system_status.md

# Commit configuration changes
cd /opt/dotmac
sudo -u dotmac git add .
sudo -u dotmac git commit -m "Post-maintenance configuration updates $(date +%Y%m%d)"
```

### Communication
- Update status page to "All Systems Operational"
- Send maintenance completion notification
- Document any issues encountered
- Schedule follow-up review if needed

## Rollback Procedures

### Application Rollback
```bash
# Stop current version
sudo docker-compose -f docker-compose.production.yml down

# Checkout previous version
cd /opt/dotmac
sudo -u dotmac git checkout HEAD~1

# Rebuild containers
sudo docker-compose -f docker-compose.production.yml build

# Restore database if needed
sudo docker exec -i dotmac-postgres psql -U dotmac_prod -d dotmac_production < /opt/dotmac/backups/pre_deploy_backup.sql

# Start services
sudo docker-compose -f docker-compose.production.yml up -d
```

### Configuration Rollback
```bash
# Restore previous configuration
sudo cp /opt/dotmac/backups/.env.production.previous /opt/dotmac/.env.production

# Restart with old configuration
sudo docker-compose -f docker-compose.production.yml restart
```

## Maintenance Calendar

### Weekly Tasks
- System health check
- Log cleanup
- Database maintenance
- Performance review

### Monthly Tasks
- Security updates
- Certificate renewal
- Backup verification
- Capacity planning
- System optimization

### Quarterly Tasks
- Major version updates
- Security audit
- Disaster recovery testing
- Performance benchmarking
- Documentation review

### Annual Tasks
- Architecture review
- Capacity planning
- Security assessment
- Compliance review
- Team training updates

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "maintenance_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_backup_recovery_runbook(self) -> str:
        """Create backup and recovery runbook.""" 
        content = """# Backup and Recovery Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Backup Strategy Overview

### Backup Types
- **Full Database Backup**: Complete database dump (daily)
- **Incremental Backup**: Transaction log backup (hourly)
- **Configuration Backup**: Application config and certificates (daily)
- **Code Backup**: Application code repository (on deployment)

### Retention Policy
- **Daily backups**: 30 days
- **Weekly backups**: 12 weeks
- **Monthly backups**: 12 months
- **Yearly backups**: 7 years

### Storage Locations
- **Primary**: Local storage `/opt/dotmac/backups`
- **Secondary**: S3 bucket `dotmac-backups-primary`
- **Offsite**: S3 bucket in different region `dotmac-backups-dr`

## Automated Backup Procedures

### Database Backup Script
```bash
#!/bin/bash
# /opt/dotmac/scripts/backup_database.sh

set -euo pipefail

BACKUP_DIR="/opt/dotmac/backups/database"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="dotmac_production"
DB_USER="dotmac_prod"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create database dump
echo "Starting database backup at $(date)"
docker exec dotmac-postgres pg_dump -U "$DB_USER" -d "$DB_NAME" | gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Verify backup integrity
echo "Verifying backup integrity..."
if gunzip -t "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"; then
    echo "Backup verification successful"
else
    echo "ERROR: Backup verification failed"
    exit 1
fi

# Upload to S3
echo "Uploading to S3..."
aws s3 cp "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" "s3://dotmac-backups-primary/database/"
aws s3 cp "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" "s3://dotmac-backups-dr/database/"

# Cleanup old backups
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Create symlink to latest backup
ln -sf "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz" "$BACKUP_DIR/latest_backup.sql.gz"

echo "Database backup completed successfully at $(date)"
```

### Configuration Backup Script
```bash
#!/bin/bash
# /opt/dotmac/scripts/backup_config.sh

set -euo pipefail

BACKUP_DIR="/opt/dotmac/backups/config"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configuration files
echo "Starting configuration backup at $(date)"
tar -czf "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" \
    /opt/dotmac/.env.production \
    /opt/dotmac/docker-compose.production.yml \
    /etc/nginx/sites-available/dotmac \
    /etc/ssl/certs/ \
    /opt/dotmac/monitoring/ \
    2>/dev/null || true

# Upload to S3
echo "Uploading configuration backup to S3..."
aws s3 cp "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" "s3://dotmac-backups-primary/config/"
aws s3 cp "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" "s3://dotmac-backups-dr/config/"

# Cleanup old backups
find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete

# Create symlink to latest backup
ln -sf "$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz" "$BACKUP_DIR/latest_config_backup.tar.gz"

echo "Configuration backup completed successfully at $(date)"
```

### Cron Job Configuration
```bash
# /etc/cron.d/dotmac-backups

# Database backup - every day at 2 AM
0 2 * * * dotmac /opt/dotmac/scripts/backup_database.sh >> /var/log/dotmac/backup.log 2>&1

# Configuration backup - every day at 3 AM  
0 3 * * * dotmac /opt/dotmac/scripts/backup_config.sh >> /var/log/dotmac/backup.log 2>&1

# Transaction log backup - every hour
0 * * * * dotmac /opt/dotmac/scripts/backup_wal.sh >> /var/log/dotmac/backup.log 2>&1

# Weekly full backup verification - every Sunday at 4 AM
0 4 * * 0 dotmac /opt/dotmac/scripts/verify_backups.sh >> /var/log/dotmac/backup.log 2>&1
```

## Manual Backup Procedures

### Emergency Database Backup
```bash
# Create immediate database backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production | gzip > /opt/dotmac/backups/emergency_backup_$TIMESTAMP.sql.gz

# Verify backup
gunzip -t /opt/dotmac/backups/emergency_backup_$TIMESTAMP.sql.gz && echo "Backup verified"

# Upload to S3 (if available)
aws s3 cp /opt/dotmac/backups/emergency_backup_$TIMESTAMP.sql.gz s3://dotmac-backups-primary/emergency/
```

### Pre-Maintenance Backup
```bash
# Complete system backup before maintenance
/opt/dotmac/scripts/backup_database.sh
/opt/dotmac/scripts/backup_config.sh

# Additional application state backup
docker exec dotmac-postgres pg_dump -U dotmac_prod -Fc dotmac_production > /opt/dotmac/backups/pre_maintenance_$(date +%Y%m%d_%H%M%S).dump

# Docker volume backup
docker run --rm -v dotmac_postgres_data:/data -v /opt/dotmac/backups:/backup alpine tar czf /backup/postgres_volume_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
```

## Recovery Procedures

### Complete Database Recovery

#### 1. Assessment Phase
```bash
# Identify the issue
docker logs dotmac-postgres | tail -100

# Check database accessibility
docker exec -it dotmac-postgres pg_isready -U dotmac_prod

# Identify latest good backup
ls -la /opt/dotmac/backups/database/ | head -10
```

#### 2. Recovery Execution
```bash
# Stop all application services
sudo docker-compose -f docker-compose.production.yml stop dotmac-management dotmac-isp

# Create database backup of current state (if possible)
docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production | gzip > /opt/dotmac/backups/pre_recovery_$(date +%Y%m%d_%H%M%S).sql.gz || true

# Drop and recreate database
docker exec -it dotmac-postgres psql -U postgres -c "DROP DATABASE IF EXISTS dotmac_production;"
docker exec -it dotmac-postgres psql -U postgres -c "CREATE DATABASE dotmac_production OWNER dotmac_prod;"

# Restore from backup
gunzip -c /opt/dotmac/backups/database/latest_backup.sql.gz | docker exec -i dotmac-postgres psql -U dotmac_prod -d dotmac_production

# Verify restoration
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production -c "\\dt"
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production -c "SELECT COUNT(*) FROM saga_executions;"
```

#### 3. Post-Recovery Verification
```bash
# Start application services
sudo docker-compose -f docker-compose.production.yml start dotmac-management dotmac-isp

# Wait for services to initialize
sleep 60

# Test database connectivity
curl -f http://localhost:8000/api/workflows/health

# Verify saga functionality
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM saga_executions ORDER BY updated_at DESC LIMIT 5;
```

### Point-in-Time Recovery

#### Using Transaction Log Backup
```bash
# Restore to specific point in time
RECOVERY_TIME="2024-01-15 14:30:00"

# Stop applications
sudo docker-compose -f docker-compose.production.yml stop dotmac-management dotmac-isp

# Restore base backup
gunzip -c /opt/dotmac/backups/database/db_backup_20240115_020000.sql.gz | \
  docker exec -i dotmac-postgres psql -U dotmac_prod -d dotmac_production

# Apply transaction logs up to recovery time
docker exec -it dotmac-postgres psql -U postgres -d dotmac_production -c "
  SELECT pg_start_backup('point-in-time-recovery', true, false);
  -- Restore WAL files here
  SELECT pg_stop_backup(false, true);
"

# Start services and verify
sudo docker-compose -f docker-compose.production.yml start dotmac-management dotmac-isp
```

### Configuration Recovery

#### Restore System Configuration
```bash
# Download configuration backup from S3
aws s3 cp s3://dotmac-backups-primary/config/config_backup_latest.tar.gz /tmp/

# Extract configuration files
sudo tar -xzf /tmp/config_backup_latest.tar.gz -C /

# Verify file permissions
sudo chown -R dotmac:dotmac /opt/dotmac/.env.production
sudo chown root:root /etc/nginx/sites-available/dotmac
sudo chmod 600 /opt/dotmac/.env.production

# Restart services with restored configuration
sudo docker-compose -f docker-compose.production.yml restart
sudo systemctl reload nginx
```

### Selective Data Recovery

#### Recover Specific Saga Data
```sql
-- Connect to recovery database
-- psql -h recovery-db -U dotmac_prod dotmac_production

-- Export specific saga data
\copy (SELECT * FROM saga_executions WHERE saga_name = 'tenant_provision' AND created_at >= '2024-01-15') TO '/tmp/specific_saga_data.csv' CSV HEADER;

-- Import to production database
-- psql -U dotmac_prod dotmac_production
\copy saga_executions FROM '/tmp/specific_saga_data.csv' CSV HEADER;
```

## Backup Verification

### Daily Verification Script
```bash
#!/bin/bash
# /opt/dotmac/scripts/verify_backups.sh

set -euo pipefail

BACKUP_DIR="/opt/dotmac/backups"
LOG_FILE="/var/log/dotmac/backup_verification.log"

echo "Starting backup verification at $(date)" >> "$LOG_FILE"

# Verify database backup integrity
echo "Verifying database backup..." >> "$LOG_FILE"
if gunzip -t "$BACKUP_DIR/database/latest_backup.sql.gz"; then
    echo "Database backup verification: PASSED" >> "$LOG_FILE"
else
    echo "Database backup verification: FAILED" >> "$LOG_FILE"
    # Send alert
    /opt/dotmac/scripts/send_alert.sh "Database backup verification failed"
fi

# Verify configuration backup
echo "Verifying configuration backup..." >> "$LOG_FILE"
if tar -tzf "$BACKUP_DIR/config/latest_config_backup.tar.gz" > /dev/null; then
    echo "Configuration backup verification: PASSED" >> "$LOG_FILE"
else
    echo "Configuration backup verification: FAILED" >> "$LOG_FILE"
    /opt/dotmac/scripts/send_alert.sh "Configuration backup verification failed"
fi

# Check S3 synchronization
echo "Checking S3 synchronization..." >> "$LOG_FILE"
LOCAL_COUNT=$(find "$BACKUP_DIR/database" -name "*.sql.gz" -mtime -1 | wc -l)
S3_COUNT=$(aws s3 ls s3://dotmac-backups-primary/database/ --recursive | grep "$(date +%Y%m%d)" | wc -l)

if [ "$LOCAL_COUNT" -eq "$S3_COUNT" ]; then
    echo "S3 synchronization: PASSED ($LOCAL_COUNT files)" >> "$LOG_FILE"
else
    echo "S3 synchronization: FAILED (Local: $LOCAL_COUNT, S3: $S3_COUNT)" >> "$LOG_FILE"
    /opt/dotmac/scripts/send_alert.sh "S3 backup synchronization failed"
fi

echo "Backup verification completed at $(date)" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
```

### Weekly Recovery Test
```bash
#!/bin/bash
# /opt/dotmac/scripts/test_recovery.sh

# Create test environment
docker run -d --name test-postgres -e POSTGRES_PASSWORD=test postgres:15

# Test database recovery
gunzip -c /opt/dotmac/backups/database/latest_backup.sql.gz | docker exec -i test-postgres psql -U postgres

# Verify data integrity
RECORD_COUNT=$(docker exec test-postgres psql -U postgres -t -c "SELECT COUNT(*) FROM saga_executions;")
echo "Recovered records: $RECORD_COUNT"

# Cleanup test environment
docker rm -f test-postgres

if [ "$RECORD_COUNT" -gt 0 ]; then
    echo "Recovery test: PASSED"
else
    echo "Recovery test: FAILED"
    /opt/dotmac/scripts/send_alert.sh "Backup recovery test failed"
fi
```

## Disaster Recovery

### Complete Site Recovery

#### 1. Infrastructure Setup
```bash
# Launch new infrastructure in DR region
# Configure DNS failover
# Set up new database instance
# Deploy application containers
```

#### 2. Data Recovery
```bash
# Download backups from S3
aws s3 sync s3://dotmac-backups-dr/database/ /opt/dotmac/backups/database/
aws s3 sync s3://dotmac-backups-dr/config/ /opt/dotmac/backups/config/

# Restore database
gunzip -c /opt/dotmac/backups/database/latest_backup.sql.gz | psql -U dotmac_prod -d dotmac_production

# Restore configuration
tar -xzf /opt/dotmac/backups/config/latest_config_backup.tar.gz -C /
```

#### 3. Service Activation
```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Update DNS to point to DR site
# Verify all functionality
# Notify stakeholders
```

### Recovery Time Objectives (RTO) and Recovery Point Objectives (RPO)

#### Target Objectives
- **RTO**: 4 hours for complete disaster recovery
- **RPO**: 1 hour maximum data loss
- **MTTR**: 30 minutes for database issues

#### Service Level Agreements
- Database backup completion: 99.9% success rate
- Backup verification: 100% success rate
- Recovery time: < 4 hours for complete system
- Data recovery: < 1 hour data loss maximum

## Monitoring and Alerting

### Backup Monitoring Metrics
```bash
# Backup success rate
backup_success_rate = successful_backups / total_backup_attempts

# Backup duration
backup_duration_seconds{{type="database|config"}}

# Backup file size trends
backup_file_size_bytes{{type="database|config"}}

# Time since last successful backup
time_since_last_backup_seconds
```

### Alert Conditions
- Backup failure: Immediate alert
- Backup verification failure: Immediate alert
- S3 upload failure: Alert within 15 minutes
- Backup size anomaly: Alert if >50% deviation
- Missing backup: Alert if >25 hours since last backup

## Documentation and Compliance

### Backup Documentation
- Backup schedule and retention policies
- Recovery procedures and test results
- Compliance requirements and audits
- Contact information and escalation paths

### Regular Testing Schedule
- **Daily**: Backup verification scripts
- **Weekly**: Recovery test in isolated environment
- **Monthly**: Full disaster recovery simulation
- **Quarterly**: Backup strategy review and updates

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "backup_recovery_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_security_runbook(self) -> str:
        """Create security runbook."""
        content = """# Security Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Security Overview

### Security Principles
- **Defense in Depth**: Multiple layers of security controls
- **Least Privilege**: Minimal necessary permissions
- **Zero Trust**: Verify everything, trust nothing
- **Security by Design**: Built-in security controls

### Threat Model
- **External Attacks**: DDoS, injection attacks, unauthorized access
- **Internal Threats**: Privilege escalation, data exfiltration
- **Supply Chain**: Compromised dependencies, malicious containers
- **Infrastructure**: Cloud platform vulnerabilities, network attacks

## Security Configuration

### Application Security

#### Environment Variables Protection
```bash
# Secure .env.production file
sudo chmod 600 /opt/dotmac/.env.production
sudo chown dotmac:dotmac /opt/dotmac/.env.production

# Verify no secrets in logs
sudo grep -r "SECRET\|PASSWORD\|TOKEN" /var/log/dotmac/ || echo "No secrets found in logs"

# Check for secrets in environment
sudo docker exec dotmac-management env | grep -E "(SECRET|PASSWORD|TOKEN)" | sed 's/=.*/=***REDACTED***/'
```

#### Database Security
```sql
-- Connect as postgres superuser
docker exec -it dotmac-postgres psql -U postgres

-- Review database permissions
\du

-- Check table permissions
SELECT schemaname, tablename, tableowner FROM pg_tables WHERE schemaname = 'public';

-- Verify SSL settings
SHOW ssl;
SHOW ssl_cert_file;
SHOW ssl_key_file;

-- Check connection encryption
SELECT datname, usename, client_addr, ssl, ssl_cipher FROM pg_stat_ssl pss
JOIN pg_stat_activity psa ON pss.pid = psa.pid;
```

#### Network Security
```bash
# Check open ports
sudo netstat -tlnp | grep -E ":8000|:8001|:8002|:8003|:3000|:5432|:6379|:9090|:9093"

# Verify firewall rules
sudo ufw status verbose

# Check Docker network configuration
docker network ls
docker network inspect dotmac_default

# Verify internal endpoint protection
curl -I http://localhost:8000/api/workflows/health
curl -I -H "x-internal-request: true" http://localhost:8000/api/workflows/health
```

### Container Security

#### Image Security Scanning
```bash
# Scan Docker images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image dotmac/management:latest

# Check for outdated base images
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}"

# Verify image signatures (if using signed images)
docker trust inspect dotmac/management:latest
```

#### Container Hardening
```bash
# Check container user (should not be root)
docker exec dotmac-management whoami
docker exec dotmac-management id

# Verify read-only filesystems where applicable
docker inspect dotmac-management | jq '.[0].HostConfig.ReadonlyRootfs'

# Check resource limits
docker inspect dotmac-management | jq '.[0].HostConfig.Memory'
docker inspect dotmac-management | jq '.[0].HostConfig.CpuShares'

# Verify no privileged containers
docker inspect dotmac-management | jq '.[0].HostConfig.Privileged'
```

## Security Monitoring

### Log Monitoring

#### Authentication and Authorization
```bash
# Monitor authentication attempts
sudo grep -i "authentication" /var/log/dotmac/*.log | tail -20

# Check for authorization failures
sudo grep -i "unauthorized\|forbidden\|access denied" /var/log/dotmac/*.log

# Monitor admin access
sudo grep -i "admin\|root" /var/log/dotmac/*.log | grep -v "normal operations"
```

#### Suspicious Activity Detection
```bash
# Monitor unusual request patterns
sudo awk '{{print $1}}' /var/log/nginx/access.log | sort | uniq -c | sort -nr | head -10

# Check for SQL injection attempts
sudo grep -i "union\\|select\\|drop\\|insert\\|update" /var/log/nginx/access.log

# Monitor file access patterns
sudo grep -E "(\\.\\.\\/|\\.php|\\.jsp|\\.asp)" /var/log/nginx/access.log

# Check for suspicious user-agents
sudo grep -i "scan\\|bot\\|crawler\\|spider" /var/log/nginx/access.log | grep -v "legitimate-bot"
```

### Security Metrics

#### Key Security Indicators
```prometheus
# Failed authentication attempts
failed_auth_attempts_total{{service="dotmac-management"}}

# Suspicious request patterns
suspicious_requests_total{{type="sql_injection|path_traversal|xss"}}

# Security policy violations
security_violations_total{{policy="rate_limit|access_control"}}

# Certificate expiration
ssl_certificate_expiry_seconds{{domain="api.yourdomain.com"}}
```

## Incident Response

### Security Incident Classification

#### Severity Levels
- **Critical (P0)**: Active breach, data compromise, system compromise
- **High (P1)**: Attempted breach, vulnerability exploitation, privilege escalation
- **Medium (P2)**: Policy violations, suspicious activity, configuration issues
- **Low (P3)**: Information gathering, reconnaissance, minor policy violations

### Immediate Response Procedures

#### Suspected Security Breach (P0)
```bash
# 1. Isolate affected systems (0-5 minutes)
# Stop affected containers
sudo docker-compose -f docker-compose.production.yml stop dotmac-management

# Block suspicious IP addresses
sudo ufw insert 1 deny from SUSPICIOUS_IP

# Enable maintenance page
sudo cp /etc/nginx/sites-available/maintenance /etc/nginx/sites-enabled/dotmac
sudo systemctl reload nginx

# 2. Preserve evidence (0-15 minutes)
# Capture system state
sudo docker logs dotmac-management > /tmp/incident-logs-$(date +%Y%m%d_%H%M%S).log
sudo netstat -tlnp > /tmp/network-state-$(date +%Y%m%d_%H%M%S).txt
sudo ps aux > /tmp/process-list-$(date +%Y%m%d_%H%M%S).txt

# Create filesystem snapshot if possible
sudo lvcreate -L1G -s -n security-snapshot /dev/vg0/root || echo "Snapshot not available"
```

#### Data Breach Response
```bash
# 1. Assess scope of breach
docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
-- Check for unauthorized data access
SELECT * FROM audit_log WHERE action = 'SELECT' AND timestamp > NOW() - INTERVAL '24 hours';

-- Identify affected records
SELECT COUNT(*) FROM sensitive_table WHERE last_accessed > 'suspicious_timeframe';

# 2. Secure remaining data
-- Change all passwords immediately
ALTER USER dotmac_prod PASSWORD 'new_secure_password';

-- Revoke API keys
UPDATE api_keys SET status = 'REVOKED' WHERE created_at < NOW() - INTERVAL '1 hour';

# 3. Notification procedures
# Notify legal team, compliance officer, affected customers
# Prepare breach notification documentation
```

### Vulnerability Management

#### Regular Security Assessments
```bash
# Monthly vulnerability scans
nmap -sS -O target_host
nikto -h https://api.yourdomain.com

# Dependency vulnerability checks
docker run --rm -v $(pwd):/app safety check /app/requirements.txt

# SSL/TLS configuration assessment
testssl.sh https://api.yourdomain.com
```

#### Patch Management
```bash
# System patches (monthly)
sudo apt update && apt list --upgradable
sudo apt upgrade -y

# Container updates (weekly)
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d

# Python dependency updates
pip list --outdated
pip install -U package_name
```

## Access Control

### User Access Management

#### Administrative Access
```bash
# Review sudo access
sudo grep -E "dotmac|admin" /etc/sudoers /etc/sudoers.d/*

# Check SSH key access
sudo cat /home/dotmac/.ssh/authorized_keys

# Review Docker group membership
getent group docker
```

#### Application Access
```sql
-- Database user permissions
docker exec -it dotmac-postgres psql -U postgres
\du dotmac_prod

-- Check table permissions
SELECT schemaname, tablename, has_table_privilege('dotmac_prod', schemaname||'.'||tablename, 'SELECT') as can_select
FROM pg_tables WHERE schemaname = 'public';
```

### API Security

#### Rate Limiting
```bash
# Check rate limiting configuration
sudo grep -A5 -B5 "limit_req" /etc/nginx/sites-available/dotmac

# Monitor rate limiting effectiveness
sudo grep "limiting requests" /var/log/nginx/error.log | tail -10

# Check for bypassed rate limits
sudo awk '{{if($9 == 429) print $1}}' /var/log/nginx/access.log | sort | uniq -c
```

#### Input Validation
```bash
# Check for validation bypass attempts
sudo grep -E "<%|<script|javascript:|data:|vbscript:" /var/log/nginx/access.log

# Monitor for injection attempts
sudo grep -E "union|select|drop|exec|xp_" /var/log/nginx/access.log

# Check for file inclusion attempts
sudo grep -E "\\.\\.\\/|\\/etc\\/passwd|\\/proc\\/|file://" /var/log/nginx/access.log
```

## Compliance and Auditing

### Audit Logging

#### Database Audit Trail
```sql
-- Enable audit logging (if not already enabled)
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_connections = on;
ALTER SYSTEM SET log_disconnections = on;

-- Query audit logs
SELECT * FROM pg_stat_activity WHERE state != 'idle';

-- Review recent database changes
SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del 
FROM pg_stat_user_tables 
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;
```

#### Application Audit Trail
```bash
# Review application audit logs
sudo grep -E "CREATE|UPDATE|DELETE" /var/log/dotmac/audit.log | tail -20

# Check admin actions
sudo grep -E "admin|root|sudo" /var/log/dotmac/*.log

# Monitor privilege changes
sudo grep -E "grant|revoke|permission" /var/log/dotmac/*.log
```

### Compliance Checks

#### Security Configuration Validation
```bash
# SSL/TLS configuration check
curl -I -v https://api.yourdomain.com 2>&1 | grep -E "TLS|SSL"

# Security headers check
curl -I https://api.yourdomain.com | grep -E "X-Frame-Options|X-XSS-Protection|Content-Security-Policy"

# Password policy enforcement
sudo cat /etc/pam.d/common-password | grep -E "pam_pwquality|pam_cracklib"
```

#### Data Protection Compliance
```sql
-- Check data encryption at rest
SELECT name, setting FROM pg_settings WHERE name LIKE '%ssl%';

-- Verify data retention policies
SELECT COUNT(*) FROM saga_executions WHERE updated_at < NOW() - INTERVAL '90 days';

-- Check for PII data handling
SELECT table_name, column_name FROM information_schema.columns 
WHERE column_name ILIKE '%email%' OR column_name ILIKE '%phone%';
```

## Security Hardening

### System Hardening

#### Operating System Security
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Configure firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Set file permissions
sudo chmod 600 /opt/dotmac/.env.*
sudo chown -R dotmac:dotmac /opt/dotmac
sudo chmod 700 /opt/dotmac/backups
```

#### Network Hardening
```bash
# Disable IP forwarding (if not needed)
echo 'net.ipv4.ip_forward = 0' | sudo tee -a /etc/sysctl.conf

# Enable SYN cookies protection
echo 'net.ipv4.tcp_syncookies = 1' | sudo tee -a /etc/sysctl.conf

# Configure network security
echo 'net.ipv4.conf.all.log_martians = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv4.icmp_ignore_bogus_error_responses = 1' | sudo tee -a /etc/sysctl.conf

sudo sysctl -p
```

### Application Hardening

#### Container Security
```yaml
# docker-compose.production.yml security configurations
services:
  dotmac-management:
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    user: "1001:1001"
```

#### Database Hardening
```sql
-- Remove default databases and users
DROP DATABASE IF EXISTS template0;
DROP USER IF EXISTS guest;

-- Configure connection limits
ALTER USER dotmac_prod CONNECTION LIMIT 20;

-- Enable row level security
ALTER TABLE sensitive_table ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON sensitive_table FOR ALL TO dotmac_prod USING (tenant_id = current_setting('app.tenant_id'));
```

## Security Training and Awareness

### Security Procedures Documentation
- Password management policies
- Incident reporting procedures
- Secure development guidelines
- Data handling protocols

### Regular Security Training
- Monthly security awareness sessions
- Quarterly incident response drills
- Annual security assessment review
- Ongoing security best practices updates

## Emergency Contacts

### Internal Security Team
- **Security Officer**: security@yourdomain.com
- **IT Security Team**: it-security@yourdomain.com  
- **Incident Commander**: incident-commander@yourdomain.com
- **Legal Team**: legal@yourdomain.com

### External Security Resources
- **Cyber Insurance**: policy-number@insurance-provider.com
- **Security Consultants**: consultant@security-firm.com
- **Law Enforcement**: local cyber crime unit
- **CERT Team**: national computer emergency response team

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "security_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)
    
    def _create_scaling_runbook(self) -> str:
        """Create scaling runbook."""
        content = """# Scaling Runbook: Workflow Orchestration
**Phase 4: Production Readiness**

## Scaling Strategy Overview

### Scaling Dimensions
- **Horizontal Scaling**: Add more application instances
- **Vertical Scaling**: Increase resources per instance  
- **Database Scaling**: Read replicas, sharding, connection pooling
- **Caching**: Redis scaling and optimization
- **Load Balancing**: Distribute traffic efficiently

### Scaling Triggers
- **CPU Usage**: > 70% sustained for 10 minutes
- **Memory Usage**: > 80% sustained for 5 minutes
- **Response Time**: > 2 seconds average for 5 minutes
- **Throughput**: Approaching configured limits
- **Queue Depth**: Saga execution queue > 100 items

## Horizontal Scaling

### Application Instance Scaling

#### Adding New Application Instances
```bash
# Update docker-compose for multiple instances
# docker-compose.production.yml
services:
  dotmac-management-1:
    build: .
    ports:
      - "8000:8000"
    environment:
      - INSTANCE_ID=1
  
  dotmac-management-2:
    build: .
    ports:
      - "8001:8000"
    environment:
      - INSTANCE_ID=2
  
  dotmac-management-3:
    build: .
    ports:
      - "8002:8000"
    environment:
      - INSTANCE_ID=3

# Update load balancer configuration
sudo nano /etc/nginx/sites-available/dotmac
```

#### Nginx Load Balancer Configuration
```nginx
upstream dotmac_management {{
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s;
    
    # Health check
    keepalive 32;
    keepalive_requests 100;
    keepalive_timeout 60s;
}}

server {{
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    location /api/management {{
        proxy_pass http://dotmac_management;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Session affinity for stateful operations
        proxy_set_header X-Request-ID $request_id;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }}
}}
```

#### Deployment Script for Scaling
```bash
#!/bin/bash
# /opt/dotmac/scripts/scale_horizontally.sh

CURRENT_INSTANCES=$(docker-compose -f docker-compose.production.yml ps -q dotmac-management | wc -l)
TARGET_INSTANCES=$1

if [ "$TARGET_INSTANCES" -le "$CURRENT_INSTANCES" ]; then
    echo "Target instances must be greater than current instances ($CURRENT_INSTANCES)"
    exit 1
fi

echo "Scaling from $CURRENT_INSTANCES to $TARGET_INSTANCES instances"

# Update docker-compose configuration
python3 /opt/dotmac/scripts/update_compose_scaling.py $TARGET_INSTANCES

# Deploy new instances
docker-compose -f docker-compose.production.yml up -d --scale dotmac-management=$TARGET_INSTANCES

# Update nginx configuration
python3 /opt/dotmac/scripts/update_nginx_upstream.py $TARGET_INSTANCES
sudo nginx -t && sudo systemctl reload nginx

# Verify all instances are healthy
sleep 30
for i in $(seq 0 $((TARGET_INSTANCES-1))); do
    PORT=$((8000 + i))
    curl -f http://localhost:$PORT/api/workflows/health || echo "Instance $i health check failed"
done

echo "Horizontal scaling completed: $TARGET_INSTANCES instances running"
```

### Auto-Scaling Implementation

#### Metrics-Based Auto-Scaling
```python
#!/usr/bin/env python3
# /opt/dotmac/scripts/auto_scaler.py

import docker
import psutil
import requests
import time
import logging
from datetime import datetime, timedelta

class AutoScaler:
    def __init__(self):
        self.client = docker.from_env()
        self.min_instances = 2
        self.max_instances = 10
        self.scale_up_threshold = 70  # CPU %
        self.scale_down_threshold = 30  # CPU %
        self.scale_cooldown = 300  # 5 minutes
        self.last_scale_time = datetime.min
        
    def get_current_instances(self):
        containers = self.client.containers.list(filters={"name": "dotmac-management"})
        return len(containers)
    
    def get_average_cpu_usage(self):
        containers = self.client.containers.list(filters={"name": "dotmac-management"})
        total_cpu = 0
        for container in containers:
            stats = container.stats(stream=False)
            cpu_usage = self._calculate_cpu_percentage(stats)
            total_cpu += cpu_usage
        return total_cpu / len(containers) if containers else 0
    
    def should_scale_up(self):
        current_instances = self.get_current_instances()
        cpu_usage = self.get_average_cpu_usage()
        
        return (current_instances < self.max_instances and 
                cpu_usage > self.scale_up_threshold and
                datetime.now() - self.last_scale_time > timedelta(seconds=self.scale_cooldown))
    
    def should_scale_down(self):
        current_instances = self.get_current_instances()
        cpu_usage = self.get_average_cpu_usage()
        
        return (current_instances > self.min_instances and 
                cpu_usage < self.scale_down_threshold and
                datetime.now() - self.last_scale_time > timedelta(seconds=self.scale_cooldown))
    
    def scale_up(self):
        current_instances = self.get_current_instances()
        new_instances = current_instances + 1
        self._scale_to(new_instances)
        logging.info(f"Scaled up to {new_instances} instances")
        
    def scale_down(self):
        current_instances = self.get_current_instances()
        new_instances = current_instances - 1
        self._scale_to(new_instances)
        logging.info(f"Scaled down to {new_instances} instances")
    
    def _scale_to(self, target_instances):
        os.system(f"/opt/dotmac/scripts/scale_horizontally.sh {target_instances}")
        self.last_scale_time = datetime.now()

if __name__ == "__main__":
    scaler = AutoScaler()
    
    while True:
        try:
            if scaler.should_scale_up():
                scaler.scale_up()
            elif scaler.should_scale_down():
                scaler.scale_down()
        except Exception as e:
            logging.error(f"Auto-scaling error: {e}")
        
        time.sleep(60)  # Check every minute
```

## Vertical Scaling

### Resource Optimization

#### Memory Scaling
```yaml
# docker-compose.production.yml
services:
  dotmac-management:
    deploy:
      resources:
        limits:
          memory: 4G  # Increased from 2G
          cpus: '2.0'  # Increased from 1.0
        reservations:
          memory: 2G
          cpus: '1.0'
```

#### Application Configuration for Larger Resources
```bash
# Update .env.production for higher resource limits
WORKFLOW_DATABASE_POOL_SIZE=50  # Increased from 20
WORKFLOW_MAX_CONCURRENT_SAGAS=200  # Increased from 100
UVICORN_WORKERS=8  # Increased from 4

# Python memory optimization
PYTHONMALLOC=pymalloc_debug
PYTHONGC=1
```

#### System Resource Monitoring
```bash
# Monitor resource usage after scaling
watch -n 5 'echo "=== CPU ===" && top -bn1 | head -5 && echo "=== Memory ===" && free -h && echo "=== Disk ===" && df -h'

# Check container resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}"
```

## Database Scaling

### Read Replica Setup

#### PostgreSQL Read Replica Configuration
```bash
# Create read replica server
# On primary server
sudo -u postgres psql
CREATE USER replicator REPLICATION ENCRYPTED PASSWORD 'secure_replica_password';

# Configure primary server (postgresql.conf)
echo "wal_level = replica" >> /etc/postgresql/15/main/postgresql.conf
echo "max_wal_senders = 3" >> /etc/postgresql/15/main/postgresql.conf
echo "wal_keep_size = 64" >> /etc/postgresql/15/main/postgresql.conf

# Configure access (pg_hba.conf)
echo "host replication replicator replica_server_ip/32 md5" >> /etc/postgresql/15/main/pg_hba.conf

sudo systemctl restart postgresql
```

#### Application Configuration for Read Replicas
```python
# Database connection configuration
DATABASE_WRITE_URL = "postgresql://dotmac_prod:password@primary_db:5432/dotmac_production"
DATABASE_READ_URL = "postgresql://dotmac_read:password@replica_db:5432/dotmac_production"

# Connection routing in application
class DatabaseRouter:
    def get_connection(self, operation_type="read"):
        if operation_type == "write":
            return create_engine(DATABASE_WRITE_URL)
        else:
            return create_engine(DATABASE_READ_URL)

# Usage in saga status queries
def get_saga_status(saga_id):
    read_engine = DatabaseRouter().get_connection("read")
    # Query from read replica
```

### Connection Pool Scaling

#### Advanced Connection Pool Configuration
```python
# Enhanced database configuration
DATABASE_CONFIG = {
    'pool_size': 30,  # Increased base pool
    'max_overflow': 50,  # Additional connections during peak
    'pool_timeout': 60,  # Connection timeout
    'pool_recycle': 3600,  # Recycle connections every hour
    'pool_pre_ping': True,  # Verify connections
    'echo': False,  # Disable SQL logging in production
}

# Connection pool monitoring
def monitor_connection_pool():
    engine = get_database_engine()
    pool = engine.pool
    
    metrics = {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'invalid': pool.invalid()
    }
    
    return metrics
```

### Query Optimization

#### Index Optimization for Scale
```sql
-- Add indexes for high-traffic queries
CREATE INDEX CONCURRENTLY idx_saga_executions_status_created ON saga_executions(status, created_at);
CREATE INDEX CONCURRENTLY idx_saga_step_executions_saga_status ON saga_step_executions(saga_id, status);
CREATE INDEX CONCURRENTLY idx_idempotent_operations_key_hash ON idempotent_operations USING hash(operation_key);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_saga_executions_active ON saga_executions(id, updated_at) WHERE status IN ('RUNNING', 'PENDING');

-- Optimize for time-based queries
CREATE INDEX CONCURRENTLY idx_saga_executions_time_status ON saga_executions(created_at DESC, status) WHERE created_at > NOW() - INTERVAL '7 days';
```

#### Query Performance Monitoring
```sql
-- Enable query statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Monitor slow queries
SELECT query, mean_time, calls, total_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Monitor table access patterns
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables 
ORDER BY seq_scan DESC;
```

## Caching Layer Scaling

### Redis Scaling

#### Redis Cluster Setup
```bash
# Redis cluster configuration
# redis.conf for each node
port 7000
cluster-enabled yes
cluster-config-file nodes-7000.conf
cluster-node-timeout 5000
appendonly yes

# Create Redis cluster
redis-cli --cluster create \
  127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 \
  127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 \
  --cluster-replicas 1
```

#### Application Cache Optimization
```python
# Multi-level caching strategy
import redis
from functools import wraps

class CacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='redis-cluster', port=7000)
        self.local_cache = {}
        self.local_cache_ttl = 300  # 5 minutes
    
    def cached(self, ttl=3600):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # Check local cache first
                if cache_key in self.local_cache:
                    if time.time() - self.local_cache[cache_key]['timestamp'] < self.local_cache_ttl:
                        return self.local_cache[cache_key]['data']
                
                # Check Redis cache
                redis_result = self.redis_client.get(cache_key)
                if redis_result:
                    data = pickle.loads(redis_result)
                    self.local_cache[cache_key] = {
                        'data': data,
                        'timestamp': time.time()
                    }
                    return data
                
                # Execute function and cache result
                result = func(*args, **kwargs)
                self.redis_client.setex(cache_key, ttl, pickle.dumps(result))
                self.local_cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
                
                return result
            return wrapper
        return decorator

# Cache saga status queries
@cache_manager.cached(ttl=300)
def get_saga_status(saga_id):
    return database_query_saga_status(saga_id)
```

## Load Balancing Optimization

### Advanced Load Balancing

#### Session Affinity for Stateful Operations
```nginx
# Nginx configuration with session affinity
upstream dotmac_management {{
    ip_hash;  # Route based on client IP for session affinity
    server 127.0.0.1:8000 weight=3;
    server 127.0.0.1:8001 weight=3;
    server 127.0.0.1:8002 weight=3;
    server 127.0.0.1:8003 weight=2;  # Lower weight for newer instance
}}

# Health check configuration
location /health {{
    access_log off;
    proxy_pass http://dotmac_management;
    proxy_connect_timeout 2s;
    proxy_read_timeout 3s;
}}
```

#### Application-Level Load Distribution
```python
# Intelligent request routing
class WorkloadRouter:
    def __init__(self):
        self.instances = {{
            'instance_1': {{'cpu': 0, 'memory': 0, 'active_sagas': 0}},
            'instance_2': {{'cpu': 0, 'memory': 0, 'active_sagas': 0}},
            'instance_3': {{'cpu': 0, 'memory': 0, 'active_sagas': 0}},
        }}
    
    def route_saga_request(self, saga_request):
        # Find instance with lowest saga count
        best_instance = min(self.instances.items(), 
                          key=lambda x: x[1]['active_sagas'])
        
        return best_instance[0]
    
    def update_instance_metrics(self, instance_id, metrics):
        if instance_id in self.instances:
            self.instances[instance_id].update(metrics)
```

## Performance Optimization

### Application Performance Tuning

#### Asynchronous Processing Optimization
```python
# Optimized saga execution with concurrency control
import asyncio
import aiohttp
from asyncio import Semaphore

class OptimizedSagaCoordinator:
    def __init__(self):
        self.max_concurrent_sagas = 50  # Increased from 20
        self.semaphore = Semaphore(self.max_concurrent_sagas)
        self.step_concurrency = 5  # Parallel steps per saga
    
    async def execute_saga_optimized(self, saga_definition):
        async with self.semaphore:
            # Execute saga steps in parallel where possible
            parallel_steps = self.identify_parallel_steps(saga_definition)
            
            for step_group in parallel_steps:
                tasks = [self.execute_step(step) for step in step_group]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Handle any failed steps
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        await self.handle_step_failure(step_group[i], result)

    async def execute_step(self, step):
        # Optimized step execution with timeout and retry
        async with aiohttp.ClientSession() as session:
            for attempt in range(3):  # Max 3 retries
                try:
                    async with asyncio.wait_for(
                        session.post(step.url, json=step.data),
                        timeout=30  # 30 second timeout
                    ) as response:
                        return await response.json()
                except asyncio.TimeoutError:
                    if attempt == 2:  # Last attempt
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

#### Memory Optimization
```python
# Memory-efficient saga processing
import gc
from weakref import WeakValueDictionary

class MemoryOptimizedSagaManager:
    def __init__(self):
        self.saga_cache = WeakValueDictionary()  # Auto-cleanup completed sagas
        self.batch_size = 100  # Process sagas in batches
    
    async def process_saga_batch(self):
        # Process sagas in batches to control memory usage
        pending_sagas = await self.get_pending_sagas(limit=self.batch_size)
        
        for saga in pending_sagas:
            await self.process_saga(saga)
            # Explicit cleanup after each saga
            del saga
        
        # Force garbage collection after batch
        gc.collect()
    
    def cleanup_completed_sagas(self):
        # Clean up completed saga data older than 1 hour
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.saga_cache = {k: v for k, v in self.saga_cache.items() 
                          if v.completed_at is None or v.completed_at > cutoff_time}
```

## Monitoring Scaling Operations

### Scaling Metrics

#### Key Performance Indicators
```prometheus
# Instance count
dotmac_instances_total{{service="management"}}

# Resource utilization per instance
dotmac_cpu_usage_percent{{instance="1"}}
dotmac_memory_usage_percent{{instance="1"}}

# Throughput per instance
dotmac_requests_per_second{{instance="1"}}

# Saga processing efficiency
dotmac_sagas_processed_per_minute{{instance="1"}}

# Queue depth
dotmac_saga_queue_depth_total
```

#### Auto-Scaling Alerts
```yaml
# Alert rules for scaling decisions
- alert: HighCPUUsage
  expr: avg(dotmac_cpu_usage_percent) > 70
  for: 10m
  labels:
    severity: warning
    action: scale_up
  annotations:
    summary: "High CPU usage detected - consider scaling up"

- alert: LowCPUUsage  
  expr: avg(dotmac_cpu_usage_percent) < 20
  for: 30m
  labels:
    severity: info
    action: scale_down
  annotations:
    summary: "Low CPU usage - consider scaling down"

- alert: SagaQueueBacklog
  expr: dotmac_saga_queue_depth_total > 100
  for: 5m
  labels:
    severity: critical
    action: scale_up_urgent
  annotations:
    summary: "Saga queue backlog detected - immediate scaling needed"
```

## Capacity Planning

### Growth Projections

#### Traffic Growth Planning
```python
# Capacity planning model
class CapacityPlanner:
    def __init__(self):
        self.current_rps = 100  # Current requests per second
        self.growth_rate = 0.3  # 30% growth per quarter
        self.instance_capacity = 50  # RPS per instance
    
    def project_capacity_needs(self, months_ahead):
        quarters = months_ahead / 3
        projected_rps = self.current_rps * (1 + self.growth_rate) ** quarters
        required_instances = int(projected_rps / self.instance_capacity) + 1
        
        return {
            'projected_rps': projected_rps,
            'required_instances': required_instances,
            'current_instances': self.get_current_instances(),
            'scaling_needed': required_instances > self.get_current_instances()
        }
```

### Cost Optimization

#### Resource Efficiency Analysis
```bash
# Cost analysis script
#!/bin/bash
# /opt/dotmac/scripts/cost_analysis.sh

echo "=== Resource Utilization Analysis ==="

# Calculate average CPU usage
avg_cpu=$(docker stats --no-stream --format "{{.CPUPerc}}" | sed 's/%//' | awk '{sum+=$1} END {print sum/NR}')
echo "Average CPU Usage: ${avg_cpu}%"

# Calculate average memory usage  
avg_mem=$(docker stats --no-stream --format "{{.MemPerc}}" | sed 's/%//' | awk '{sum+=$1} END {print sum/NR}')
echo "Average Memory Usage: ${avg_mem}%"

# Efficiency score
if (( $(echo "$avg_cpu < 30" | bc -l) )); then
    echo "⚠️  CPU under-utilized - consider scaling down"
elif (( $(echo "$avg_cpu > 80" | bc -l) )); then
    echo "🔥 CPU over-utilized - consider scaling up"
else
    echo "✅ CPU utilization optimal"
fi

# Cost recommendations
current_instances=$(docker ps -q --filter \"name=dotmac-management\" | wc -l)
echo "Current instances: $current_instances"
echo "Estimated monthly cost: ${{((current_instances * 100))}} USD"  # Approximate
```

---
**Generated**: {timestamp}
**Version**: 1.0
"""
        
        content = content.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        runbook_path = self.runbooks_dir / "scaling_runbook.md"
        with open(runbook_path, "w") as f:
            f.write(content)
        
        return str(runbook_path)


def main():
    """Generate all operational runbooks."""
    print("📚 Generating Operational Runbooks for Workflow Orchestration")
    print("Phase 4: Production Readiness")
    print()
    
    generator = OperationalRunbooksGenerator()
    
    try:
        # Generate all runbooks
        runbooks = generator.generate_all_runbooks()
        
        print("✅ Operational Runbooks Generated Successfully!")
        print()
        print("Generated runbooks:")
        for runbook_type, path in runbooks.items():
            print(f"  📖 {runbook_type.replace('_', ' ').title()}: {path}")
        
        print()
        print("📋 Runbook Contents:")
        print("1. **Deployment Runbook**: Complete deployment procedures and verification")
        print("2. **Troubleshooting Runbook**: Comprehensive issue diagnosis and resolution")
        print("3. **Monitoring Runbook**: Dashboard configuration and alert management")
        print("4. **Incident Response Runbook**: Emergency procedures and communication")
        print("5. **Maintenance Runbook**: Regular maintenance tasks and procedures")
        print("6. **Backup & Recovery Runbook**: Data protection and disaster recovery")
        print("7. **Security Runbook**: Security monitoring and incident response")
        print("8. **Scaling Runbook**: Horizontal and vertical scaling procedures")
        
        print()
        print("🎯 Key Features:")
        print("• Step-by-step operational procedures")
        print("• Emergency response protocols")
        print("• Comprehensive troubleshooting guides")
        print("• Security and compliance procedures")
        print("• Performance optimization strategies")
        print("• Backup and disaster recovery plans")
        
        print()
        print("📁 All runbooks saved to:", generator.runbooks_dir)
        
    except Exception as e:
        print(f"❌ Error generating operational runbooks: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())