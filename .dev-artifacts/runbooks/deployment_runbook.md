# Deployment Runbook: Workflow Orchestration
**Generated**: 2025-09-07 18:03:39

## Quick Deployment Steps

### 1. Pre-deployment
```bash
# Create backup
sudo docker exec dotmac-postgres pg_dump -U dotmac_prod dotmac_production > /tmp/backup.sql

# Stop services
sudo docker-compose -f docker-compose.production.yml down
```

### 2. Deploy
```bash
# Pull latest code
cd /opt/dotmac && git pull origin production

# Run migrations
sudo docker-compose -f docker-compose.production.yml run --rm dotmac-management alembic upgrade head

# Start services
sudo docker-compose -f docker-compose.production.yml up -d
```

### 3. Verify
```bash
# Health checks
curl -f http://localhost:8000/api/workflows/health
curl -f http://localhost:8001/health

# Check logs
docker logs dotmac-management | tail -20
```

## Rollback Procedure
```bash
# Emergency rollback
sudo docker-compose -f docker-compose.production.yml down
sudo -u dotmac git checkout HEAD~1
sudo docker-compose -f docker-compose.production.yml up -d
```
