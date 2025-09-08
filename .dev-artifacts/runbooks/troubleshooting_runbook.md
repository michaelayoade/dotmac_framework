# Troubleshooting Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Quick Reference

### Emergency Commands
```bash
# Check all services
sudo docker-compose -f docker-compose.production.yml ps

# View logs
sudo docker logs dotmac-management
sudo docker logs dotmac-postgres

# Restart services
sudo docker-compose -f docker-compose.production.yml restart
```

### Common Issues

#### Saga Execution Failures
```bash
# Check saga status
curl -H "x-internal-request: true" http://localhost:8000/api/workflows/health

# Check database for stuck sagas
sudo docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT * FROM saga_executions WHERE status = 'RUNNING' AND updated_at < NOW() - INTERVAL '1 hour';
```

#### Database Issues
```bash
# Check database connections
sudo docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production
SELECT count(*) FROM pg_stat_activity;

# Restart database if needed
sudo docker restart dotmac-postgres
```

#### High Memory Usage
```bash
# Check memory usage
docker stats --no-stream
free -h

# Restart application to clear memory
sudo docker restart dotmac-management
```
