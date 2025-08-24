# DotMac SaaS Platform Operational Runbooks

**Common scenarios and solutions for SaaS platform owners and developers**

## 🚨 Emergency Procedures

### Platform Down - Complete Outage
```bash
# 1. Check if services are running
make status

# 2. Check health of individual services
make health-check

# 3. View logs for errors
make logs | grep -i error

# 4. Restart everything
make restart

# 5. If still failing, clean restart
make down
docker system prune -f
make up

# 6. Verify recovery
make health-check && make show-endpoints
```

### Database Connection Lost
```bash
# 1. Check PostgreSQL status
docker-compose -f docker-compose.unified.yml logs postgres-shared

# 2. Check if PostgreSQL is responding
docker-compose -f docker-compose.unified.yml exec postgres-shared pg_isready -U dotmac_admin

# 3. Restart PostgreSQL
docker-compose -f docker-compose.unified.yml restart postgres-shared

# 4. Wait for startup and check connections
sleep 10 && make health-check

# 5. If data corruption, restore from backup
make db-backup-restore BACKUP_FILE=latest
```

### Memory/Resource Issues
```bash
# 1. Check resource usage
docker stats --no-stream

# 2. Identify memory hogs
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"

# 3. Free up memory
docker system prune -f
docker volume prune -f

# 4. Restart with resource limits
docker-compose -f docker-compose.production.yml up -d

# 5. Monitor resource usage
watch -n 5 'docker stats --no-stream'
```

## 🔧 Development Scenarios

### First Day - SaaS Platform Developer Setup
```bash
# 1. Clone SaaS platform repository
git clone https://github.com/your-org/dotmac-saas-platform.git
cd dotmac-saas-platform

# 2. Run complete SaaS platform setup
make setup-saas-platform

# 3. Verify everything works
make health-check
make show-platform-endpoints

# 4. Run tests to ensure setup is correct
make test-saas-platform

# 5. Open SaaS platform environment
# - Platform Admin: http://localhost:3000
# - Management API: http://localhost:8000/docs
# - Fleet Monitoring: http://localhost:3301
```

### Working on Tenant Application (ISP Framework)
```bash
# 1. Start lightweight development environment for tenant app
make dev-tenant-app

# 2. Enter ISP Framework directory (tenant application code)
cd isp-framework

# 3. Make changes to tenant application features

# 4. Run tenant application tests
make test-unit

# 5. Test your changes locally
curl http://localhost:8001/health

# 6. View tenant application logs
make logs-tenant-app
```

### Working on SaaS Management Platform
```bash
# 1. Start platform infrastructure and management services
make up-platform-infrastructure
make up-management

# 2. Enter Management Platform directory
cd management-platform

# 3. Make changes to tenant orchestration, billing, etc.

# 4. Run platform tests
make test-saas-platform

# 5. Test your changes
curl http://localhost:8000/health

# 6. View management platform logs
make logs-management-platform
```

### SaaS Platform Frontend Development
```bash
# 1. Start platform backend services
make dev-platform-backend

# 2. Start frontend development
make dev-frontend

# 3. Or start individual portal
cd frontend/apps/admin    # Platform owner admin
cd frontend/apps/reseller # Vendor/reseller portal
pnpm dev

# 4. Access SaaS platform portals
# - Platform Admin: http://localhost:3000
# - Vendor/Reseller: http://localhost:3002
# - Tenant Components: http://localhost:3001 (for testing)
```

### Full Stack SaaS Platform Development
```bash
# 1. Start complete SaaS platform environment
make dev-saas-platform

# 2. Make changes to any platform component

# 3. Run relevant tests
make test-saas-platform    # All platform tests
make test-tenant-isolation # Multi-tenancy tests
make test-revenue-critical # Billing/pricing tests

# 4. Check platform integration
make test-platform-integration
```

## 🐛 Troubleshooting Procedures

### Services Won't Start
```bash
# Problem: Docker containers failing to start

# 1. Check for port conflicts
sudo lsof -i :8000 :8001 :3000 :5434 :6378

# 2. Kill conflicting processes
sudo kill -9 $(sudo lsof -t -i:8000)

# 3. Check disk space
df -h

# 4. Check Docker daemon
sudo systemctl status docker

# 5. Restart Docker if needed
sudo systemctl restart docker

# 6. Try starting again
make up
```

### Database Migration Issues
```bash
# Problem: Database migrations failing

# 1. Check current migration status
cd isp-framework && python -m alembic current
cd ../management-platform && python -m alembic current

# 2. Check for migration conflicts
cd isp-framework && python -m alembic heads
cd ../management-platform && python -m alembic heads

# 3. Fix conflicts manually or reset
make db-reset-all  # WARNING: DESTROYS DATA

# 4. Re-run migrations
make db-migrate-all

# 5. Verify database state
make health-check
```

### Permission Errors
```bash
# Problem: Permission denied errors

# 1. Check file ownership
ls -la

# 2. Fix ownership (Linux/Mac)
sudo chown -R $USER:$USER .

# 3. Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# 4. Restart services
make restart
```

### API Not Responding
```bash
# Problem: API endpoints returning 500/503 errors

# 1. Check service logs
make logs-isp | grep -i error
make logs-mgmt | grep -i error

# 2. Check database connectivity
curl http://localhost:8001/health
curl http://localhost:8000/health

# 3. Check configuration
cat .env.local | grep -i database

# 4. Restart specific service
docker-compose -f docker-compose.unified.yml restart isp-framework
docker-compose -f docker-compose.unified.yml restart management-platform

# 5. Check for startup issues
docker-compose -f docker-compose.unified.yml logs --tail=50 isp-framework
```

### Frontend Build Issues
```bash
# Problem: Frontend applications not building or running

# 1. Check Node.js version
node --version  # Should be 18+
pnpm --version  # Should be 8+

# 2. Clean and reinstall dependencies
cd frontend
rm -rf node_modules
pnpm install

# 3. Check for TypeScript errors
pnpm type-check

# 4. Build applications
pnpm build

# 5. Start development server
pnpm dev
```

## 🔄 Maintenance Procedures

### Daily Development Workflow
```bash
# Morning startup
git pull origin main
make restart
make health-check

# During development
make quick-test        # Before making changes
make test-relevant     # After changes
make logs              # Monitor issues

# End of day
make down              # Stop services
git push               # Push changes
```

### Weekly Maintenance
```bash
# Update dependencies
make update-all

# Clean up Docker resources
docker system prune -f
docker volume prune -f

# Run full test suite
make test-all

# Check security
make security-all

# Backup development data
make backup-dev-data
```

### Updating Platform Version
```bash
# 1. Backup current data
make backup-dev-data

# 2. Pull latest changes
git fetch origin
git pull origin main

# 3. Update dependencies
make install-all

# 4. Run database migrations
make db-migrate-all

# 5. Restart platform
make restart

# 6. Verify update
make health-check
make test-all
```

## 📊 Monitoring Procedures

### Performance Monitoring
```bash
# Check resource usage
docker stats --no-stream

# Monitor API response times
curl -w "@curl-format.txt" http://localhost:8001/health
curl -w "@curl-format.txt" http://localhost:8000/health

# Check database performance
make db-performance-check

# View SignOz dashboard
make monitoring
```

### Log Analysis
```bash
# View real-time logs
make logs

# Filter error logs
make logs | grep -i error

# Check specific service
make logs-isp
make logs-mgmt

# Export logs for analysis
docker-compose -f docker-compose.unified.yml logs --since 1h > last_hour.log
```

### Health Check Procedures
```bash
# Basic health check
make health-check

# Detailed health check
make health-check-detailed

# Check specific components
curl http://localhost:8001/health      # ISP Framework
curl http://localhost:8000/health      # Management Platform
curl http://localhost:8200/v1/sys/health  # OpenBao
curl http://localhost:3301/health      # SignOz
```

## 🚀 Deployment Procedures

### Development to Staging
```bash
# 1. Run full test suite
make full-check

# 2. Build production images
make build-all

# 3. Deploy to staging
make staging

# 4. Run smoke tests
make smoke-test-staging

# 5. Verify deployment
make health-check-staging
```

### Production Deployment
```bash
# 1. Create production backup
make backup-prod

# 2. Deploy using Infrastructure as Code
cd shared/deployments/terraform
terraform plan -var-file="production.tfvars"
terraform apply

# 3. Run health checks
make health-check-prod

# 4. Run smoke tests
make smoke-test-prod

# 5. Monitor deployment
make monitor-deployment
```

### Rollback Procedures
```bash
# Quick rollback (last known good version)
make rollback-previous

# Specific version rollback
make rollback-to-version VERSION=v1.2.3

# Full rollback with data restore
make rollback-full VERSION=v1.2.3 RESTORE_DATA=true

# Verify rollback
make health-check
make smoke-test
```

## 🔐 Security Procedures

### Security Incident Response
```bash
# 1. Immediately secure the environment
make security-lockdown

# 2. Check for unauthorized access
make security-audit

# 3. Review logs for suspicious activity
make security-log-analysis

# 4. Update all secrets
make rotate-all-secrets

# 5. Deploy security patches
make security-update
```

### Regular Security Maintenance
```bash
# Weekly security scan
make security-scan

# Update security dependencies
make security-update

# Rotate development secrets
make rotate-dev-secrets

# Check for vulnerable dependencies
make vulnerability-scan
```

## 📞 Getting Help

### Before Asking for Help
1. Check this runbook for your scenario
2. Run `make health-check` to get system status
3. Check logs with `make logs | grep -i error`
4. Try restarting with `make restart`

### Escalation Path
1. **Documentation**: Check `DEPLOYMENT_GUIDE.md` and `OPERATIONAL_RUNBOOKS.md`
2. **Self-Service**: Try common solutions in this runbook
3. **Team**: Ask in team chat with error logs and steps tried
4. **Emergency**: For production issues, follow incident response procedure

### Information to Include
- Output of `make status`
- Error logs from `make logs`
- Steps that led to the issue
- Expected vs actual behavior
- Environment (development/staging/production)

---

## 🎯 Quick Reference

### Most Common Commands
```bash
make quick-start       # First-time setup
make dev              # Start development
make health-check     # Check system health
make restart          # Restart everything
make logs             # View logs
make test-all         # Run all tests
make down             # Stop everything
```

### Emergency Commands
```bash
make restart          # Quick restart
make db-reset-all     # Reset databases (DESTRUCTIVE)
make clean-restart    # Clean restart with docker cleanup
make backup-now       # Emergency backup
make rollback-previous # Rollback to previous version
```

Remember: When in doubt, restart first, ask questions later!