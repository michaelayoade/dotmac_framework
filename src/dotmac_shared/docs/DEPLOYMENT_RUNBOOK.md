# Deployment Runbook

## Overview

This runbook provides step-by-step procedures for deploying the DotMac Framework using the Intelligent CI/CD Pipeline. It covers normal deployments, emergency procedures, rollback operations, and troubleshooting.

## Table of Contents

- [Quick Reference](#quick-reference)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Normal Deployment Process](#normal-deployment-process)
- [Emergency Deployment](#emergency-deployment)
- [Rollback Procedures](#rollback-procedures)
- [Post-Deployment Verification](#post-deployment-verification)
- [Troubleshooting](#troubleshooting)
- [Escalation Procedures](#escalation-procedures)

## Quick Reference

### Key Commands

```bash
# Trigger deployment
git push origin main

# Check deployment status
gh run list --workflow=intelligent-deployment.yml

# Watch deployment progress
gh run watch

# Manual rollback
gh workflow run rollback.yml -f rollback_to=previous

# Check service health
curl https://api.dotmac.framework/health
```

### Key URLs

- **Monitoring**: <http://localhost:3000> (Grafana)
- **Metrics**: <http://localhost:9090> (Prometheus)
- **Alerts**: <http://localhost:9093> (AlertManager)
- **API Gateway**: <https://api.dotmac.framework>
- **Admin Portal**: <https://admin.dotmac.framework>

### Emergency Contacts

- **DevOps Team**: <devops@dotmac.framework>
- **Security Team**: <security@dotmac.framework>
- **On-Call Engineer**: +1-555-ONCALL

## Pre-Deployment Checklist

### 1. Code and Configuration Review

- [ ] All feature branches merged to `main`
- [ ] Code review completed and approved
- [ ] No merge conflicts in `main` branch
- [ ] Version numbers updated (if applicable)
- [ ] Configuration changes reviewed and approved

### 2. Database and Infrastructure

- [ ] Database migrations tested in staging
- [ ] Schema changes backward compatible
- [ ] Infrastructure capacity sufficient
- [ ] SSL certificates valid (>30 days remaining)
- [ ] External dependencies available

### 3. Testing and Quality

- [ ] All tests passing in staging environment
- [ ] Performance benchmarks met
- [ ] Security scans completed and clean
- [ ] Accessibility compliance verified
- [ ] Load testing completed (if applicable)

### 4. Communication and Documentation

- [ ] Deployment scheduled and communicated
- [ ] Rollback plan documented and ready
- [ ] Monitoring dashboards prepared
- [ ] Incident response team notified
- [ ] Customer communication prepared (if downtime expected)

### 5. Backup and Recovery

- [ ] Database backup completed
- [ ] Configuration backup created
- [ ] Previous deployment artifacts available
- [ ] Rollback scripts tested
- [ ] Recovery procedures documented

## Normal Deployment Process

### Step 1: Initiate Deployment

#### Automatic Deployment (Recommended)

```bash
# Push to main branch triggers automatic deployment
git checkout main
git pull origin main
git merge feature/your-feature
git push origin main
```

#### Manual Deployment (If Needed)

```bash
# Trigger manual deployment via GitHub Actions
gh workflow run intelligent-deployment.yml

# Or via GitHub web interface
# Navigate to Actions tab → Select workflow → Run workflow
```

### Step 2: Monitor Pipeline Progress

```bash
# List recent workflow runs
gh run list --workflow=intelligent-deployment.yml --limit=5

# Watch the current deployment
gh run watch

# View detailed logs (if needed)
gh run view --log
```

#### Expected Pipeline Duration

- **Code Quality Gate**: ~20 minutes
- **Security Validation**: ~25 minutes
- **Unit Tests**: ~20 minutes (parallel)
- **Integration Tests**: ~45 minutes
- **E2E Tests**: ~90 minutes (parallel across browsers)
- **Performance Tests**: ~60 minutes (optional)
- **Accessibility Tests**: ~25 minutes
- **Total Time**: ~3-4 hours (with parallel execution)

### Step 3: Pipeline Stage Monitoring

#### Stage 1: Code Quality Gate

**Watch for:**

- Linting issues
- Type checking errors
- Security scan results
- Code complexity violations

```bash
# If issues detected, pipeline provides detailed output
# Example remediation command
make lint-fix && make format
```

#### Stage 2-7: Comprehensive Testing

**Monitor test results in real-time:**

- Test success/failure counts
- Coverage percentages
- Performance metrics
- Error logs and stack traces

### Step 4: Intelligent Decision Point

The pipeline will automatically:

- **If ALL tests pass (100%)**: Proceed to automatic deployment
- **If ANY tests fail**: Begin automated remediation

#### Decision Engine Output Example

```yaml
🤖 INTELLIGENT DEPLOYMENT DECISION
Decision: REMEDIATE
Overall Score: 97.5%
Blocking Failures: 1 (unit_tests)

Test Results:
✅ Code Quality: 100%
✅ Security: 100%
❌ Unit Tests: 85% (BLOCKING)
✅ Integration: 100%
✅ E2E Tests: 100%
```

### Step 5: Automatic Deployment (If Tests Pass)

When all tests pass, the system automatically:

1. **Builds Applications**
   - Backend services compilation
   - Frontend production builds
   - Docker image creation

2. **Deploys Services**
   - 7 backend microservices
   - 4 frontend portal applications
   - Load balancer configuration

3. **Configures Security**
   - SSL certificate installation
   - Security headers
   - Rate limiting rules

4. **Initializes Monitoring**
   - Metrics collection
   - Dashboard setup
   - Alert configuration

### Step 6: Deployment Verification

The pipeline automatically verifies:

- [ ] All services respond to health checks
- [ ] Database connectivity established
- [ ] Load balancer routing correctly
- [ ] SSL certificates valid
- [ ] Monitoring systems active

## Emergency Deployment

### When to Use Emergency Deployment

- Critical security vulnerability fix
- Production system down
- Data corruption prevention
- Urgent bug fix affecting all users

### Emergency Process

#### Step 1: Assess Urgency

```bash
# Check current system status
curl -I https://api.dotmac.framework/health

# Review monitoring dashboards
# Open http://localhost:3000

# Check error rates
# Prometheus query: rate(http_requests_total{status=~"5.."}[5m])
```

#### Step 2: Prepare Emergency Fix

```bash
# Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# Apply minimal fix
# ... make changes ...

# Test fix locally
make test-unit
make test-integration

# Commit and push
git add .
git commit -m "hotfix: critical security vulnerability fix"
git push origin hotfix/critical-fix
```

#### Step 3: Emergency Deployment Options

##### Option A: Force Deployment (Use with caution)

```bash
# Trigger deployment with force flag
gh workflow run intelligent-deployment.yml \
  -f force_deployment=true \
  -f skip_performance_tests=true
```

##### Option B: Bypass Pipeline (Emergency only)

```bash
# Direct deployment script (use only in extreme cases)
python scripts/emergency-deploy.py \
  --environment=production \
  --skip-tests \
  --confirm-emergency
```

#### Step 4: Monitor Emergency Deployment

- Watch deployment logs continuously
- Monitor system metrics closely
- Prepare rollback if issues detected
- Communicate status to stakeholders

## Rollback Procedures

### Automatic Rollback Triggers

The system automatically initiates rollback when:

- Service health checks fail for >3 consecutive attempts
- Error rate exceeds 10% for >5 minutes
- API response time exceeds 2000ms P95 for >5 minutes
- Critical security alert triggered

### Manual Rollback

#### Step 1: Initiate Rollback

```bash
# Rollback to previous successful deployment
gh workflow run rollback.yml -f rollback_to=previous

# Rollback to specific version
gh workflow run rollback.yml -f rollback_to=v1.2.3

# Rollback specific service only
gh workflow run rollback.yml \
  -f service=api-gateway \
  -f rollback_to=previous
```

#### Step 2: Monitor Rollback Process

```bash
# Watch rollback progress
gh run watch

# Check service status during rollback
watch -n 5 'curl -s https://api.dotmac.framework/health | jq .status'
```

#### Step 3: Verify Rollback Success

```bash
# Confirm version rollback
curl https://api.dotmac.framework/version

# Verify all services healthy
curl https://api.dotmac.framework/health | jq .services

# Check monitoring dashboards
# Ensure error rates return to normal
```

### Database Rollback (If Required)

```bash
# Connect to database
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Check migration status
SELECT version_num FROM alembic_version;

# Rollback to previous migration (if safe)
alembic downgrade -1

# Verify data integrity
SELECT COUNT(*) FROM critical_table;
```

## Post-Deployment Verification

### Automated Verification

The pipeline automatically performs:

- Service health checks
- Database connectivity tests
- Load balancer validation
- SSL certificate verification
- Basic smoke tests

### Manual Verification Checklist

#### 1. Service Health

```bash
# Check all service health endpoints
curl https://api.dotmac.framework/health
curl https://admin.dotmac.framework/api/health
curl https://customer.dotmac.framework/api/health
curl https://reseller.dotmac.framework/api/health
curl https://technician.dotmac.framework/api/health
```

#### 2. Critical User Workflows

- [ ] User registration and login
- [ ] Service provisioning
- [ ] Billing operations
- [ ] Support ticket creation
- [ ] API authentication
- [ ] Cross-portal navigation

#### 3. Performance Verification

```bash
# Check response times
curl -o /dev/null -s -w "%{time_total}\n" https://api.dotmac.framework/health

# Monitor resource usage
htop
iostat -x 1 5
```

#### 4. Security Verification

```bash
# Verify SSL certificates
echo | openssl s_client -connect api.dotmac.framework:443 2>/dev/null | openssl x509 -noout -dates

# Check security headers
curl -I https://api.dotmac.framework | grep -E "(Strict-Transport-Security|Content-Security-Policy|X-Frame-Options)"

# Verify rate limiting
for i in {1..10}; do curl -I https://api.dotmac.framework/health; done
```

#### 5. Monitoring and Alerting

- [ ] Grafana dashboards loading correctly
- [ ] Prometheus targets all UP
- [ ] AlertManager receiving metrics
- [ ] No active alerts in monitoring system
- [ ] Log aggregation functioning

### Performance Baseline Verification

```bash
# API performance check
ab -n 100 -c 10 https://api.dotmac.framework/health

# Database performance
psql -c "EXPLAIN ANALYZE SELECT * FROM users LIMIT 10;"

# Frontend performance
lighthouse https://customer.dotmac.framework --output=json
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Pipeline Stage Failures

##### Code Quality Issues

**Symptoms:** Linting errors, type checking failures

```bash
# Check specific errors
gh run view --log | grep -A 5 -B 5 "error:"

# Apply automated fixes
make lint-fix
make format
```

##### Test Failures

**Symptoms:** Unit/integration/e2e test failures

```bash
# Run tests locally to reproduce
make test
pnpm test

# Check test logs for specific failures
gh run download && unzip test-results.zip

# Review failed test details
cat junit.xml | grep -A 10 "failure"
```

##### Security Scan Issues

**Symptoms:** Vulnerability detection, secret exposure

```bash
# Check security scan results
gh run view --log | grep -A 10 "security"

# Update vulnerable dependencies
npm audit fix
pip install --upgrade -r requirements.txt

# Remove detected secrets
git filter-branch --tree-filter 'rm -f config/secrets.yaml' HEAD
```

#### 2. Deployment Failures

##### Resource Constraints

**Symptoms:** Pod scheduling failures, out of memory errors

```bash
# Check resource usage
kubectl top nodes
kubectl top pods

# Scale up resources
kubectl patch deployment api-gateway -p '{"spec":{"template":{"spec":{"containers":[{"name":"api-gateway","resources":{"limits":{"memory":"2Gi","cpu":"2000m"}}}]}}}}'
```

##### Database Connection Issues

**Symptoms:** Connection timeouts, authentication failures

```bash
# Test database connectivity
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1;"

# Check connection pool status
psql -c "SELECT * FROM pg_stat_activity WHERE datname='dotmac_prod';"

# Restart database connection pool
kubectl rollout restart deployment api-gateway
```

##### SSL Certificate Problems

**Symptoms:** HTTPS errors, certificate expiration warnings

```bash
# Check certificate expiration
echo | openssl s_client -connect api.dotmac.framework:443 2>/dev/null | openssl x509 -noout -dates

# Renew certificates (if using Let's Encrypt)
certbot renew --nginx

# Update certificate in Kubernetes
kubectl create secret tls dotmac-tls --cert=server.crt --key=server.key --dry-run=client -o yaml | kubectl apply -f -
```

#### 3. Performance Issues

##### High Response Times

**Symptoms:** API responses >1000ms, slow page loads

```bash
# Profile API endpoints
curl -w "@curl-format.txt" -o /dev/null -s https://api.dotmac.framework/slow-endpoint

# Check database query performance
psql -c "SELECT query, total_time, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Enable caching
redis-cli config set save "60 100"
```

##### High Resource Usage

**Symptoms:** CPU >80%, memory >90%, disk I/O high

```bash
# Identify resource-hungry processes
top -o %CPU
ps aux --sort=-%mem

# Scale horizontally
kubectl scale deployment api-gateway --replicas=5

# Optimize application
python -m cProfile -o profile.stats main.py
```

### Diagnostic Commands

#### System Health Check

```bash
#!/bin/bash
# comprehensive-health-check.sh

echo "=== System Health Check ==="
echo "Date: $(date)"
echo

echo "=== Service Status ==="
curl -s https://api.dotmac.framework/health | jq .
curl -s https://admin.dotmac.framework/api/health | jq .

echo "=== Database Connectivity ==="
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT version();"

echo "=== Resource Usage ==="
free -h
df -h /
iostat -x 1 1

echo "=== Recent Errors ==="
journalctl -u dotmac-* --since "1 hour ago" --grep="ERROR|CRITICAL"

echo "=== SSL Certificate Status ==="
echo | openssl s_client -connect api.dotmac.framework:443 2>/dev/null | openssl x509 -noout -dates
```

#### Performance Analysis

```bash
#!/bin/bash
# performance-analysis.sh

echo "=== Performance Analysis ==="

echo "=== API Response Times ==="
for endpoint in /health /api/users /api/services; do
  echo "Testing $endpoint"
  curl -w "Time: %{time_total}s\n" -o /dev/null -s https://api.dotmac.framework$endpoint
done

echo "=== Database Performance ==="
psql -c "
SELECT schemaname,tablename,attname,n_distinct,correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC
LIMIT 10;
"

echo "=== Cache Hit Ratio ==="
redis-cli info stats | grep keyspace
```

## Escalation Procedures

### Escalation Matrix

| Severity | Response Time | Escalation Level | Contact |
|----------|---------------|------------------|---------|
| P0 - Critical | 15 minutes | On-call Engineer | +1-555-ONCALL |
| P1 - High | 1 hour | DevOps Team Lead | <devops-lead@dotmac.framework> |
| P2 - Medium | 4 hours | Development Team | <dev-team@dotmac.framework> |
| P3 - Low | 24 hours | Product Owner | <product@dotmac.framework> |

### Severity Definitions

#### P0 - Critical

- Complete system outage
- Data loss or corruption
- Security breach
- >50% of users affected

#### P1 - High

- Major feature unavailable
- Significant performance degradation
- 10-50% of users affected
- Deployment rollback required

#### P2 - Medium

- Minor feature issues
- Moderate performance impact
- <10% of users affected
- Non-critical errors

#### P3 - Low

- Cosmetic issues
- Documentation updates
- Enhancement requests
- No user impact

### Escalation Process

#### Step 1: Initial Response (0-15 minutes)

1. Acknowledge the incident
2. Assess severity level
3. Create incident ticket
4. Notify appropriate team
5. Begin initial triage

#### Step 2: Investigation (15-60 minutes)

1. Gather diagnostic information
2. Identify root cause
3. Estimate impact and timeline
4. Implement temporary fixes if possible
5. Update stakeholders

#### Step 3: Resolution (1-4 hours)

1. Implement permanent fix
2. Test solution thoroughly
3. Deploy fix to production
4. Verify resolution
5. Monitor for regression

#### Step 4: Post-Incident (24-48 hours)

1. Conduct post-mortem review
2. Document lessons learned
3. Update procedures and runbooks
4. Implement preventive measures
5. Communicate findings

### Communication Templates

#### Initial Incident Notification

```
Subject: [P0] Production Incident - DotMac Framework

INCIDENT DETAILS:
- Severity: P0 - Critical
- Start Time: 2025-08-20 14:30 UTC
- Services Affected: Customer Portal, API Gateway
- Impact: 100% of users cannot access customer portal

CURRENT STATUS:
- Investigation in progress
- Rollback initiated
- ETA for resolution: 30 minutes

ACTIONS TAKEN:
- Incident response team activated
- Rollback to previous stable version initiated
- Monitoring increased frequency

NEXT UPDATE: 15 minutes
```

#### Resolution Notification

```
Subject: [RESOLVED] Production Incident - DotMac Framework

INCIDENT RESOLVED:
- Resolution Time: 2025-08-20 15:15 UTC
- Total Downtime: 45 minutes
- Root Cause: Database connection pool exhaustion

RESOLUTION ACTIONS:
- Rolled back to previous stable version
- Increased database connection pool size
- Implemented additional monitoring

POST-INCIDENT:
- Post-mortem scheduled for tomorrow 10:00 UTC
- Preventive measures to be implemented
- Monitoring enhanced for early detection

STATUS: All services operational, monitoring continues
```

## Maintenance Procedures

### Scheduled Maintenance

#### Pre-Maintenance

- [ ] Schedule communicated to users
- [ ] Maintenance window approved
- [ ] Backup procedures completed
- [ ] Rollback plan prepared
- [ ] Team availability confirmed

#### During Maintenance

- [ ] Services gracefully stopped
- [ ] Maintenance banner displayed
- [ ] Updates applied systematically
- [ ] Testing performed after each change
- [ ] Monitoring maintained throughout

#### Post-Maintenance

- [ ] All services restarted and healthy
- [ ] Functionality verification completed
- [ ] Performance baselines re-established
- [ ] Maintenance banner removed
- [ ] Stakeholders notified of completion

### Emergency Maintenance

#### Immediate Actions

1. Assess criticality and impact
2. Implement emergency change
3. Monitor system stability
4. Document changes made
5. Plan follow-up actions

#### Communication

- Immediate notification to stakeholders
- Regular status updates during maintenance
- Clear communication of resolution
- Post-maintenance summary report

---

**Document Version:** 1.0
**Last Updated:** 2025-08-20
**Next Review:** 2025-09-20
**Owner:** DevOps Team
**Reviewers:** Security Team, Development Team
