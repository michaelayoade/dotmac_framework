# Deployment Guide

**Complete deployment guide for the DotMac Platform - choose your deployment method based on your needs**

⚠️ **Status**: This is a DEVELOPMENT platform (47% complete). Production deployment is not yet supported. See [Production Readiness Checklist](PRODUCTION_READINESS_CHECKLIST.md) for current status.

## 🎯 Quick Start (Choose Your Path)

| Goal | Command | When to Use |
|------|---------|-------------|
| **Full platform development** | `make install-dev && make dev` | Complete development environment |
| **Backend API development** | `make dev-backend` | Working on ISP Framework or Management Platform APIs |
| **Frontend portal development** | `make dev-frontend` | Working on customer/admin/reseller portals |
| **Testing environment** | `make staging` | Testing with production-like configuration |

## 🚀 Getting Started (Choose Your Path)

### Quick Development Setup
```bash
# 1. Clone and setup
git clone <repository-url>
cd dotmac-framework

# 2. Complete setup
make install-dev

# 3. Start development environment
make dev

# 4. Access services
make show-endpoints
```

### Platform-Specific Development
```bash
# ISP Framework only
cd isp-framework && make run-dev

# Management Platform only
cd management-platform && make run-api

# Frontend portals only
cd frontend && pnpm dev
```

## 🐳 Docker Deployment Methods

### Development (Recommended)
```bash
# Complete unified environment
docker-compose -f docker-compose.unified.yml up -d
# Includes: Both platforms + databases + monitoring
# Resources: ~8GB RAM, 16GB disk
```

### Basic Development
```bash
# Lightweight setup
docker-compose up -d
# Includes: Core services only
# Resources: ~4GB RAM, 8GB disk
```

### Staging/Testing
```bash
# Production-like configuration
docker-compose -f docker-compose.production.yml up -d
# Includes: Security hardening, SSL, monitoring
# Resources: ~12GB RAM, 32GB disk
```

### ⚠️ Production Deployment (NOT READY)

Production deployment is **not yet supported**. The platform is at 47% completion.

**Missing for Production:**
- Auto-scaling infrastructure
- Load balancing
- SSL certificate management  
- Backup/recovery procedures
- Security hardening
- Multi-region deployment

See [Production Readiness Checklist](PRODUCTION_READINESS_CHECKLIST.md) for full status.

## ⚙️ Configuration

### Environment Files
```
.env.local          # Local overrides (git-ignored)
.env.development    # Development defaults
.env.production     # Production settings (when available)
```

### Setup Process
```bash
# 1. Install dependencies
make install-dev

# 2. Start infrastructure (databases, monitoring)
make up-infrastructure

# 3. Start applications
make up

# 4. Verify health
make health-check
```

## 🌐 Service Ports

| Service | Port | Purpose |
|---------|------|----------|
| ISP Framework API | 8001 | Main ISP operations API |
| Management Platform API | 8000 | Multi-tenant management |
| Admin Portal | 3000 | Platform administration |
| Customer Portal | 3001 | Customer self-service |
| Reseller Portal | 3002 | Partner management |
| Technician Portal | 3003 | Field operations |
| PostgreSQL | 5432 | Main database |
| Redis | 6379 | Cache and sessions |
| SignOz | 3301 | Monitoring dashboard |

## 🔍 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Services Not Starting
```bash
# Check service status
make status

# View logs
make logs

# Restart everything
make restart

# Clean restart
make down && docker system prune -f && make up
```

#### 2. Port Conflicts
```bash
# Check what's using ports
sudo lsof -i :8000
sudo lsof -i :8001

# Kill conflicting processes
sudo kill -9 $(sudo lsof -t -i:8000)

# Use different ports
export ISP_FRAMEWORK_PORT=8101
export MANAGEMENT_PLATFORM_PORT=8100
make up
```

#### 3. Database Connection Issues
```bash
# Reset databases
make db-reset-all

# Check database logs
docker-compose -f docker-compose.unified.yml logs postgres-shared

# Manual database setup
make db-setup
make db-migrate-all
```

#### 4. Memory Issues
```bash
# Check resource usage
docker stats

# Free up memory
docker system prune -f
docker volume prune -f

# Use lighter development setup
make dev-simple  # New lightweight option
```

#### 5. OpenBao/Secrets Issues
```bash
# Restart OpenBao
docker-compose -f docker-compose.unified.yml restart openbao-shared

# Check OpenBao status
curl http://localhost:8200/v1/sys/health

# Reinitialize secrets (development only)
make secrets-reset
```

### Health Check Commands

```bash
# Check all services
make health-check

# Check specific service
curl http://localhost:8001/health  # ISP Framework
curl http://localhost:8000/health  # Management Platform
curl http://localhost:3301/health  # SignOz

# Detailed health check
make health-check-detailed
```

## 📊 Monitoring

**SignOz Dashboard:** http://localhost:3301

```bash
make monitoring          # Open dashboard
make logs                # View all logs
make logs-isp            # ISP Framework logs only
make logs-mgmt           # Management Platform logs only
```

## 🔐 Security

**Development:** Relaxed security for easier development  
**Production:** Not yet implemented (47% platform completion)

```bash
make security            # Run security scans
make secrets-scan        # Check for exposed secrets
```

## 🚀 Development Workflow

```bash
# Setup (first time only)
make install-dev

# Daily development
make up                  # Start services
make test                # Run tests  
make dev                 # Start development mode

# Testing
make staging             # Start staging environment
make health-check        # Verify all services
```

## 🔄 Maintenance

```bash
# Update dependencies
make update-dependencies

# Update to latest version
git pull origin main
make update-all
make test-all
```

## 📚 Resources

- [Developer Guide](DEVELOPER_GUIDE.md) - Development setup and workflows
- [Production Readiness](PRODUCTION_READINESS_CHECKLIST.md) - Current completion status
- [API Documentation](docs/api/) - Generated OpenAPI specs

## 🆘 Getting Help

1. Check this guide for common issues
2. Run `make health-check`
3. View logs with `make logs`
4. Check [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for detailed setup

**Start simple**: `make install-dev && make dev`