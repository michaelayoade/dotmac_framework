# Incident Response Runbook: Workflow Orchestration
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
**Generated**: 2025-09-07 18:00:54
**Version**: 1.0
