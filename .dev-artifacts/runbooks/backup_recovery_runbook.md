# Backup and Recovery Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Daily Backup

### Database Backup
```bash
# Create database backup
sudo docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production | gzip > /opt/dotmac/backups/db_backup_$(date +%Y%m%d).sql.gz

# Verify backup
gunzip -t /opt/dotmac/backups/db_backup_$(date +%Y%m%d).sql.gz
```

### Configuration Backup
```bash
# Backup configuration files
tar -czf /opt/dotmac/backups/config_backup_$(date +%Y%m%d).tar.gz \
    /opt/dotmac/.env.production \
    /opt/dotmac/docker-compose.production.yml \
    /etc/nginx/sites-available/dotmac
```

## Recovery Procedures

### Complete Database Recovery
```bash
# Stop applications
sudo docker-compose -f docker-compose.production.yml stop dotmac-management

# Restore database
gunzip -c /opt/dotmac/backups/latest_backup.sql.gz | \
  sudo docker exec -i dotmac-postgres psql -U dotmac_prod -d dotmac_production

# Start applications
sudo docker-compose -f docker-compose.production.yml start dotmac-management

# Verify recovery
curl -f http://localhost:8000/api/workflows/health
```

### Configuration Recovery
```bash
# Restore configuration
sudo tar -xzf /opt/dotmac/backups/latest_config_backup.tar.gz -C /

# Restart services
sudo docker-compose -f docker-compose.production.yml restart
sudo systemctl reload nginx
```

## Backup Schedule
- Database backup: Daily at 2 AM
- Configuration backup: Daily at 3 AM
- Retention: 30 days local, 90 days offsite
