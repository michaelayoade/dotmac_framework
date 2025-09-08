# Performance Optimization Guide: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Performance Monitoring

### Key Metrics
- Response time: < 2 seconds average
- Throughput: > 100 requests/second
- Success rate: > 99%
- CPU usage: < 70%
- Memory usage: < 80%

### Performance Testing
```bash
# Basic load test
for i in {1..100}; do
  curl -s http://localhost:8000/api/workflows/health > /dev/null &
done
wait

# Database performance test
sudo docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM pg_stat_user_tables ORDER BY seq_scan DESC;
```

## Optimization Strategies

### Database Optimization
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_saga_executions_status ON saga_executions(status);
CREATE INDEX CONCURRENTLY idx_saga_executions_created ON saga_executions(created_at);

-- Update table statistics
ANALYZE saga_executions;
ANALYZE idempotent_operations;
```

### Application Optimization
```bash
# Increase worker processes
export UVICORN_WORKERS=4

# Optimize connection pool
export WORKFLOW_DATABASE_POOL_SIZE=20
export WORKFLOW_DATABASE_POOL_TIMEOUT=30
```

### System Optimization
```bash
# Increase file descriptor limits
echo "dotmac soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "dotmac hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
echo "net.core.somaxconn = 65535" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Scaling Guidelines

### Horizontal Scaling
- Add more application instances when CPU > 70%
- Use load balancer for traffic distribution
- Scale database read replicas for heavy queries

### Vertical Scaling
- Increase memory when usage > 80%
- Upgrade CPU when sustained high usage
- Expand disk when usage > 85%
