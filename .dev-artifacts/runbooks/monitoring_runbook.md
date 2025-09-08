# Monitoring Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Key Metrics to Monitor

### Application Health
- Saga success rate should be > 95%
- Average response time should be < 2 seconds
- Active sagas should be < 100

### System Health
- CPU usage should be < 80%
- Memory usage should be < 85%
- Disk usage should be < 90%

### Database Health
- Connection pool utilization should be < 80%
- Query duration should be < 1 second
- No long-running queries

## Monitoring Commands
```bash
# Check application health
curl http://localhost:8000/api/workflows/health

# Check system resources
top -n1 -b | head -10
free -h
df -h

# Check database performance
sudo docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM pg_stat_activity WHERE state = 'active';
```

## Alert Thresholds
- Critical: Saga success rate < 95%, System down
- Warning: High CPU/memory usage, Slow response times
- Info: Normal operational metrics
