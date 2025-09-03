# 🔧 DotMac Platform Comprehensive Troubleshooting Guide

Complete troubleshooting guide for common issues, debugging procedures, and maintenance tasks.

## 📋 Table of Contents

- [Quick Diagnostic Commands](#quick-diagnostic-commands)
- [Common Issues & Solutions](#common-issues--solutions)
- [Performance Troubleshooting](#performance-troubleshooting)
- [Database Issues](#database-issues)
- [Network & Connectivity](#network--connectivity)
- [Security Issues](#security-issues)
- [Deployment Problems](#deployment-problems)
- [Monitoring & Alerting](#monitoring--alerting)

## ⚡ Quick Diagnostic Commands

### System Health Check

```bash
#!/bin/bash
# Quick platform health assessment

echo "=== DotMac Platform Health Check ==="
date

# Service status
echo -e "\n🔍 Service Status:"
kubectl get pods -n dotmac-production --field-selector=status.phase!=Running
docker-compose ps | grep -v "Up"

# Health endpoints
echo -e "\n🏥 Health Endpoints:"
curl -f -s https://api.dotmac.platform/health/ready && echo "✅ API Ready" || echo "❌ API Not Ready"
curl -f -s https://app.dotmac.platform/health && echo "✅ Frontend Ready" || echo "❌ Frontend Not Ready"

# Resource usage
echo -e "\n💻 Resource Usage:"
df -h | grep -E "(/$|/var|/opt)"
free -h
top -bn1 | head -n 5

# Database connectivity
echo -e "\n🗄️  Database:"
pg_isready -h $DB_HOST -p 5432 -U $DB_USER && echo "✅ Database Connected" || echo "❌ Database Disconnected"

# Recent errors
echo -e "\n🚨 Recent Errors:"
tail -n 10 /var/log/dotmac/error.log 2>/dev/null || echo "No error log found"

echo -e "\n=== Health Check Complete ==="
```

### Log Analysis

```bash
# Quick log analysis
tail -f /var/log/dotmac/application.log | grep -i error
journalctl -u dotmac-api -f --since "1 hour ago"
kubectl logs -f deployment/dotmac-api -n dotmac-production --tail=100
```

### Performance Snapshot

```bash
# System performance overview
iostat -x 1 5
sar -u 1 5  
vmstat 1 5
netstat -i
ss -tuln
```

## 🐛 Common Issues & Solutions

### 1. Service Won't Start

**Symptoms:**
- HTTP 502/503 errors
- Container restart loops
- Health check failures

**Diagnostic Steps:**
```bash
# Check container status
kubectl describe pod dotmac-api-xxx -n dotmac-production
docker-compose logs api

# Check resource constraints
kubectl top pods -n dotmac-production
docker stats

# Verify configuration
kubectl get configmap dotmac-config -o yaml -n dotmac-production
env | grep -E "(DATABASE|REDIS|SECRET)"
```

**Common Causes & Fixes:**

**A. Database Connection Issues**
```bash
# Check database connectivity
pg_isready -h $DB_HOST -p 5432 -U $DB_USER

# Fix: Restart database
kubectl restart deployment postgres -n dotmac-production
# Or
sudo systemctl restart postgresql

# Check connection pool
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT count(*) FROM pg_stat_activity;"
```

**B. Memory/Resource Limits**
```bash
# Check resource usage
kubectl describe pod dotmac-api-xxx -n dotmac-production | grep -A 5 "Limits"

# Fix: Increase resource limits
kubectl patch deployment dotmac-api -n dotmac-production -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api",
          "resources": {
            "limits": {"memory": "2Gi", "cpu": "1000m"},
            "requests": {"memory": "1Gi", "cpu": "500m"}
          }
        }]
      }
    }
  }
}'
```

**C. Configuration Issues**
```bash
# Check environment variables
kubectl exec deployment/dotmac-api -n dotmac-production -- env | sort

# Fix: Update configuration
kubectl patch configmap dotmac-config -n dotmac-production \
  --patch='{"data":{"DATABASE_URL":"postgresql://user:pass@host:5432/db"}}'
kubectl rollout restart deployment/dotmac-api -n dotmac-production
```

### 2. High Error Rates

**Symptoms:**
- 5xx HTTP status codes
- Timeout errors
- Failed API requests

**Investigation:**
```bash
# Check error patterns
grep -E "5[0-9][0-9]" /var/log/nginx/access.log | tail -20
kubectl logs deployment/dotmac-api -n dotmac-production | grep -i error | tail -10

# Check dependency health
curl -f https://api.stripe.com/healthcheck
nslookup redis.dotmac-production.svc.cluster.local
```

**Solutions:**

**A. Database Performance Issues**
```sql
-- Find slow queries
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check for locks
SELECT pid, usename, query, state 
FROM pg_stat_activity 
WHERE state = 'active' AND query_start < NOW() - INTERVAL '1 minute';

-- Kill problematic queries
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = 12345;
```

**B. Circuit Breaker Activation**
```bash
# Enable circuit breaker for external dependencies
kubectl patch configmap dotmac-config -n dotmac-production \
  --patch='{"data":{"CIRCUIT_BREAKER_ENABLED":"true"}}'

# Monitor circuit breaker status
curl https://api.dotmac.platform/metrics | grep circuit_breaker
```

**C. Rate Limiting Issues**
```bash
# Check rate limit status
redis-cli hgetall "rate_limit:user:12345"

# Increase rate limits temporarily
redis-cli del "rate_limit:*"
kubectl patch configmap dotmac-config -n dotmac-production \
  --patch='{"data":{"RATE_LIMIT_PER_HOUR":"2000"}}'
```

### 3. Slow Response Times

**Symptoms:**
- High latency metrics
- User complaints about slowness
- Timeout errors

**Performance Analysis:**
```bash
# Application response times
curl -w "@curl-format.txt" -o /dev/null -s https://api.dotmac.platform/api/v1/customers

# Database query performance
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "
SELECT substring(query, 1, 50) as query, 
       calls, total_time, mean_time, stddev_time
FROM pg_stat_statements 
WHERE mean_time > 100
ORDER BY mean_time DESC 
LIMIT 10;"

# Cache performance
redis-cli info stats | grep -E "(hits|misses|evicted)"
```

**Optimization Steps:**

**A. Database Optimization**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_customers_email ON customers(email);
CREATE INDEX CONCURRENTLY idx_services_customer_id ON services(customer_id);

-- Update table statistics
ANALYZE customers;
ANALYZE services;

-- Vacuum if needed
VACUUM ANALYZE customers;
```

**B. Application Caching**
```python
# Enable Redis caching
from dotmac_shared.cache import redis_cache

@redis_cache(expire=300)  # 5 minutes
async def get_customer_services(customer_id: UUID):
    return await service.get_customer_services(customer_id)
```

**C. Scale Resources**
```bash
# Horizontal scaling
kubectl scale deployment dotmac-api --replicas=6 -n dotmac-production

# Vertical scaling
kubectl patch deployment dotmac-api -n dotmac-production -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api",
          "resources": {
            "requests": {"cpu": "1000m", "memory": "2Gi"},
            "limits": {"cpu": "2000m", "memory": "4Gi"}
          }
        }]
      }
    }
  }
}'
```

### 4. Authentication Issues

**Symptoms:**
- 401 Unauthorized errors
- JWT token validation failures
- User login problems

**Diagnosis:**
```bash
# Check JWT token validity
python3 -c "
import jwt
token = 'your-jwt-token-here'
try:
    payload = jwt.decode(token, options={'verify_signature': False})
    print('Token payload:', payload)
    print('Expires:', payload.get('exp'))
except Exception as e:
    print('Token error:', e)
"

# Check authentication service
curl -X POST https://api.dotmac.platform/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}'
```

**Solutions:**

**A. JWT Secret Rotation**
```bash
# Generate new JWT secret
NEW_SECRET=$(openssl rand -base64 32)

# Update secret in Kubernetes
kubectl patch secret dotmac-secrets -n dotmac-production \
  --patch="{\"data\":{\"JWT_SECRET\":\"$(echo -n $NEW_SECRET | base64)\"}}"

# Restart services to pick up new secret
kubectl rollout restart deployment/dotmac-api -n dotmac-production
```

**B. Session Cleanup**
```bash
# Clear expired sessions
redis-cli --scan --pattern "session:*" | xargs redis-cli del

# Reset authentication cache
redis-cli flushdb 1  # Auth database
```

### 5. Data Inconsistency

**Symptoms:**
- Mismatched billing amounts
- Missing customer records
- Duplicate entries

**Investigation:**
```sql
-- Check data integrity
SELECT c.id, c.email, COUNT(s.id) as service_count
FROM customers c
LEFT JOIN services s ON c.id = s.customer_id
GROUP BY c.id, c.email
HAVING COUNT(s.id) = 0;  -- Customers with no services

-- Find orphaned records
SELECT s.id, s.customer_id 
FROM services s
LEFT JOIN customers c ON s.customer_id = c.id
WHERE c.id IS NULL;

-- Check billing consistency
SELECT i.id, i.customer_id, i.total_amount, 
       SUM(ili.amount) as line_item_total
FROM invoices i
LEFT JOIN invoice_line_items ili ON i.id = ili.invoice_id
GROUP BY i.id, i.customer_id, i.total_amount
HAVING i.total_amount != COALESCE(SUM(ili.amount), 0);
```

**Data Repair:**
```sql
-- Fix orphaned services (careful!)
DELETE FROM services 
WHERE customer_id NOT IN (SELECT id FROM customers);

-- Recalculate invoice totals
UPDATE invoices 
SET total_amount = (
    SELECT COALESCE(SUM(amount), 0) 
    FROM invoice_line_items 
    WHERE invoice_id = invoices.id
)
WHERE id IN (
    SELECT DISTINCT invoice_id 
    FROM invoice_line_items
);
```

## 📊 Performance Troubleshooting

### CPU Performance Issues

**High CPU Usage Investigation:**
```bash
# Find top CPU consuming processes
top -c -o %CPU
ps aux --sort=-%cpu | head -20

# Kubernetes pod CPU usage
kubectl top pods -n dotmac-production --sort-by=cpu

# Profile application CPU usage
py-spy top --pid $(pgrep -f "python.*dotmac")
```

**Solutions:**
```bash
# Scale horizontally
kubectl patch hpa dotmac-api-hpa -n dotmac-production -p '{"spec":{"maxReplicas":10}}'

# Optimize code (add caching, reduce computations)
# Check for infinite loops or heavy algorithms
```

### Memory Issues

**Memory Leak Detection:**
```bash
# Monitor memory usage over time
watch -n 5 'free -h && kubectl top pods -n dotmac-production | grep dotmac'

# Check for memory leaks in Python
python3 -X tracemalloc=10 app.py

# Analyze memory usage
ps_mem
pmap -d $(pgrep -f python)
```

**Memory Optimization:**
```python
# Add memory monitoring
import tracemalloc
import gc

def monitor_memory():
    tracemalloc.start()
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
    
# Force garbage collection
gc.collect()
```

### Disk I/O Issues

**Disk Performance Analysis:**
```bash
# Check disk usage and I/O
df -h
iotop -a
iostat -x 1 5

# Find large files
find /var/log -name "*.log" -size +100M -exec ls -lh {} \;
find /opt/dotmac -type f -size +100M -exec ls -lh {} \;
```

**Disk Cleanup:**
```bash
# Clean up logs
find /var/log -name "*.log" -mtime +7 -delete
journalctl --vacuum-time=7d

# Clean up Docker
docker system prune -f
docker volume prune -f

# Clean up application data
python3 scripts/cleanup_old_data.py --days=30
```

## 🗄️ Database Issues

### Connection Pool Exhaustion

**Symptoms:**
- "Too many connections" errors
- Application timeouts
- Database connection refused

**Investigation:**
```sql
-- Check current connections
SELECT count(*) as connections, state 
FROM pg_stat_activity 
GROUP BY state;

-- Find long-running connections
SELECT pid, usename, application_name, state, 
       NOW() - state_change as duration,
       query
FROM pg_stat_activity 
WHERE state = 'active' 
ORDER BY duration DESC;
```

**Solutions:**
```sql
-- Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND NOW() - state_change > INTERVAL '1 hour';

-- Increase connection limit (temporary)
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
```

### Slow Queries

**Query Performance Analysis:**
```sql
-- Enable query logging (if not already enabled)
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
SELECT pg_reload_conf();

-- Find slow queries
SELECT substring(query, 1, 100) as query,
       calls, total_time, mean_time, max_time,
       100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) as hit_percent
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
AND n_distinct > 100
AND correlation < 0.1;
```

**Query Optimization:**
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_invoices_customer_date 
ON invoices(customer_id, created_at);

-- Analyze query plans
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM customers c
JOIN services s ON c.id = s.customer_id
WHERE c.status = 'active';
```

### Database Locks

**Lock Detection:**
```sql
-- Find blocking queries
SELECT blocked_locks.pid     AS blocked_pid,
       blocked_activity.usename  AS blocked_user,
       blocking_locks.pid     AS blocking_pid,
       blocking_activity.usename AS blocking_user,
       blocked_activity.query    AS blocked_statement,
       blocking_activity.query   AS current_statement_in_blocking_process
FROM  pg_catalog.pg_locks         blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity  ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks         blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
```

## 🌐 Network & Connectivity

### DNS Resolution Issues

**Symptoms:**
- Service discovery failures
- External API connection timeouts
- Intermittent connectivity

**Diagnosis:**
```bash
# Test DNS resolution
nslookup api.dotmac.platform
dig api.dotmac.platform
host api.dotmac.platform

# Kubernetes DNS
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup kubernetes.default

# Check DNS configuration
cat /etc/resolv.conf
systemctl status systemd-resolved
```

**Solutions:**
```bash
# Flush DNS cache
sudo systemctl flush-dns
sudo systemctl restart systemd-resolved

# Update DNS servers
sudo systemctl edit systemd-resolved
# Add:
# [Resolve]
# DNS=8.8.8.8 8.8.4.4
# FallbackDNS=1.1.1.1 1.0.0.1

# Kubernetes DNS restart
kubectl delete pod -l k8s-app=kube-dns -n kube-system
```

### Load Balancer Issues

**Health Check Failures:**
```bash
# Check load balancer status
kubectl get svc -n dotmac-production
kubectl describe svc dotmac-api -n dotmac-production

# Test health endpoints
curl -v http://api.dotmac.platform/health/ready
curl -v http://10.0.1.100:8000/health/ready  # Direct to backend

# Check nginx status
nginx -t
systemctl status nginx
tail -f /var/log/nginx/error.log
```

**Load Balancer Configuration:**
```nginx
# /etc/nginx/sites-available/dotmac
upstream dotmac_backend {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.dotmac.platform;
    
    location /health {
        proxy_pass http://dotmac_backend;
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }
    
    location / {
        proxy_pass http://dotmac_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Health check
        health_check interval=10s fails=3 passes=2;
    }
}
```

## 🔒 Security Issues

### SSL Certificate Problems

**Certificate Expiry:**
```bash
# Check certificate expiry
echo | openssl s_client -servername api.dotmac.platform -connect api.dotmac.platform:443 2>/dev/null | openssl x509 -noout -dates

# Check all certificates
for cert in /etc/ssl/certs/dotmac/*.pem; do
    echo "=== $cert ==="
    openssl x509 -in "$cert" -noout -dates
done
```

**Certificate Renewal:**
```bash
# Let's Encrypt renewal
certbot renew --dry-run
certbot renew --force-renewal -d api.dotmac.platform

# Update Kubernetes secret
kubectl create secret tls dotmac-tls \
  --cert=/etc/letsencrypt/live/api.dotmac.platform/fullchain.pem \
  --key=/etc/letsencrypt/live/api.dotmac.platform/privkey.pem \
  -n dotmac-production --dry-run=client -o yaml | kubectl apply -f -
```

### Authentication Bypass

**Security Audit:**
```bash
# Check for authentication bypasses
grep -r "skip_auth\|bypass_auth" src/
grep -r "allow_anonymous" src/

# Verify JWT implementation
python3 -c "
import jwt
token = jwt.encode({'test': 'data'}, 'wrong-key', algorithm='HS256')
try:
    jwt.decode(token, 'correct-key', algorithms=['HS256'])
    print('⚠️  JWT verification issue!')
except:
    print('✅ JWT verification working')
"
```

**Security Hardening:**
```bash
# Update security headers
curl -I https://api.dotmac.platform | grep -E "(Strict-Transport|X-Frame|X-Content|Content-Security)"

# Check for SQL injection protection
sqlmap -u "https://api.dotmac.platform/api/v1/customers?search=test" \
  --cookie="session=your-session-cookie"
```

## 🚀 Deployment Problems

### Container Deployment Issues

**Image Pull Errors:**
```bash
# Check image availability
docker pull dotmac/platform:latest

# Kubernetes image pull secrets
kubectl get secret regcred -n dotmac-production -o yaml
kubectl describe pod failing-pod -n dotmac-production
```

**Resource Constraints:**
```bash
# Check resource quotas
kubectl describe quota -n dotmac-production
kubectl describe limitrange -n dotmac-production

# Node resources
kubectl describe nodes
kubectl top nodes
```

### Configuration Drift

**Configuration Validation:**
```bash
# Compare configurations
kubectl get configmap dotmac-config -o yaml -n dotmac-production > current-config.yaml
diff current-config.yaml expected-config.yaml

# Validate environment variables
kubectl exec deployment/dotmac-api -n dotmac-production -- env | sort | grep -E "(DATABASE|REDIS|SECRET)"
```

## 📊 Monitoring & Alerting

### Metrics Collection Issues

**Prometheus Troubleshooting:**
```bash
# Check Prometheus targets
curl http://prometheus:9090/api/v1/targets

# Verify metrics endpoints
curl http://dotmac-api:8000/metrics

# Check metric scraping
curl "http://prometheus:9090/api/v1/query?query=up"
```

**Grafana Dashboard Issues:**
```bash
# Check Grafana connectivity to Prometheus
curl http://prometheus:9090/api/v1/query?query=up

# Import/export dashboards
curl -X GET http://grafana:3000/api/dashboards/uid/abc123 \
  -H "Authorization: Bearer $GRAFANA_TOKEN" > dashboard.json
```

### Alert Manager Configuration

**Alert Routing Issues:**
```yaml
# /etc/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@dotmac.platform'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'ops@dotmac.platform'
    subject: 'DotMac Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## 🤖 AI-First Testing Troubleshooting

### Deployment Readiness Issues

**"Deployment readiness failed - Import errors"**
```bash
# Check exact import that's failing
python -c "from dotmac_isp.main import app; print('Success')"

# Common fixes:
pip install -r requirements.txt  # Missing dependencies
export PYTHONPATH=/path/to/project  # Path issues
alembic upgrade head  # Database not migrated
```

**"Database schema integrity failed"**
```bash
# Check if migrations are current
alembic current
alembic upgrade head

# Check for model/migration mismatches  
make -f Makefile.readiness schema-check
```

**"AI validation performance baseline failed"**
```bash  
# Check system resources
htop
df -h

# Restart services and retest
docker-compose restart
make -f Makefile.readiness deployment-ready
```

**Quick Deployment Readiness Check:**
```bash
# Full validation pipeline
make -f Makefile.readiness deployment-ready

# Quick checks during development
make -f Makefile.readiness startup-check
make -f Makefile.readiness schema-check
```

**Reference**: See [AI-First Testing Strategy](AI_FIRST_TESTING_STRATEGY.md) for complete methodology.

## 📞 Getting Additional Help

### Internal Escalation

**Severity Levels:**
- **P0 (Critical)**: Platform down, data loss, security breach
- **P1 (High)**: Major functionality broken, performance degraded
- **P2 (Medium)**: Minor issues, workarounds available  
- **P3 (Low)**: Enhancement requests, documentation updates

**Escalation Path:**
1. **First Response**: Check this troubleshooting guide
2. **Team Lead**: Escalate if unresolved in 30 minutes (P0/P1)
3. **On-Call Engineer**: Page for P0 issues outside business hours
4. **Engineering Manager**: For coordination of major incidents

### External Support

**Cloud Provider Support:**
- **AWS**: Create support case for infrastructure issues
- **GCP**: Use Cloud Console support for GKE problems
- **Azure**: Submit support ticket for AKS issues

**Vendor Support:**
- **Database**: PostgreSQL community, managed service support
- **Monitoring**: Prometheus/Grafana community slack
- **Security**: OWASP community, security vendor support

### Documentation & Resources

**Internal Resources:**
- [Architecture Documentation](./ARCHITECTURE.md)
- [Production Deployment Runbook](./PRODUCTION_DEPLOYMENT_RUNBOOK.md)
- [Security Production Checklist](./SECURITY_PRODUCTION_CHECKLIST.md)

**External Resources:**
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)

---

**Emergency Contact**: support@dotmac.platform  
**Last Updated**: 2024-12-31  
**Version**: 1.0.0
