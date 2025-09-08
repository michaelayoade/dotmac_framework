# Maintenance Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Weekly Maintenance

### System Health Check
```bash
# Check services
sudo docker-compose -f docker-compose.production.yml ps
curl -f http://localhost:8000/api/workflows/health

# Check logs
docker logs --tail=100 dotmac-management | grep -i error
docker logs --tail=100 dotmac-postgres | grep -i error
```

### Database Maintenance
```bash
# Connect to database
sudo docker exec -it dotmac-postgres psql -U dotmac_prod -d dotmac_production

# Run maintenance
ANALYZE;
REINDEX TABLE saga_executions;
VACUUM ANALYZE saga_executions;

# Clean old records
DELETE FROM saga_executions WHERE status = 'COMPLETED' AND updated_at < NOW() - INTERVAL '30 days';
DELETE FROM idempotent_operations WHERE status = 'COMPLETED' AND created_at < NOW() - INTERVAL '7 days';
```

### Log Cleanup
```bash
# Rotate logs
sudo logrotate -f /etc/logrotate.d/dotmac

# Clean old Docker logs
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

## Monthly Maintenance

### Security Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
sudo docker-compose -f docker-compose.production.yml pull
sudo docker-compose -f docker-compose.production.yml up -d
```

### Backup Verification
```bash
# Check backup files
ls -la /opt/dotmac/backups/
gzip -t /opt/dotmac/backups/*.gz
```
