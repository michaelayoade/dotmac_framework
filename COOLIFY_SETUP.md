# Coolify Production Setup Guide

## 🎯 Overview

Your Coolify instance is now installed and ready at: **https://coolify.dotmac.com**

> **⚠️ SECURITY NOTE**: Replace example IP with your actual production domain. Never use HTTP in production.

This guide walks you through setting up the DotMac Framework production deployment using the recommended single-image, multi-service approach.

## 📋 Pre-Deployment Checklist

✅ **Coolify installed and running**
✅ **Docker production files created**
✅ **GitHub Actions CI/CD pipeline configured**
✅ **Multi-service architecture implemented**

## 🚀 Step-by-Step Deployment

### 1. Access Coolify Dashboard

1. Navigate to: https://coolify.dotmac.com
2. Complete initial setup (create admin account)
3. Verify all services are healthy
4. **Configure SSL**: Ensure Coolify dashboard uses HTTPS with valid certificates

### 2. Create Project

1. Click "Create Project"
2. Name: `DotMac Production`
3. Description: `DotMac ISP Management Framework - Production Environment`

### 3. Add Database Services

#### PostgreSQL Setup
```
Service Type: PostgreSQL
Name: dotmac-postgres
Version: 15
Database Name: dotmac
Username: dotmac_user
Password: [Generate 32-char secure password]
Port: 5432
```

#### Redis Setup
```
Service Type: Redis
Name: dotmac-redis
Version: 7-alpine
Max Memory: 512MB
Max Memory Policy: allkeys-lru
Port: 6379
```

### 4. Deploy Application Services

#### Create Docker Compose Application
1. Click "Add Service" → "Docker Compose"
2. Name: `DotMac Framework`
3. Upload: `docker-compose.coolify.yml`

#### Configure Environment Variables

**Required Variables:**
```bash
# Database Connection (Auto-injected)
DATABASE_URL=postgresql://dotmac_user:password@dotmac-postgres:5432/dotmac

# Redis Connection (Auto-injected)
REDIS_URL=redis://dotmac-redis:6379

# Security
SECRET_KEY=[32-character random string]
WEBHOOK_SECRET=[Generate webhook secret]

# Admin
ADMIN_EMAIL=admin@yourdomain.com

# Optional Performance Tuning
MAX_UPLOAD_SIZE=100MB
RATE_LIMIT_PER_MINUTE=1000
LOG_LEVEL=info
```

### 5. Configure Domains & SSL

#### ISP Service Domain
- **Service**: dotmac-isp
- **Port**: 8000
- **Domain**: isp.yourdomain.com
- **SSL**: Enable Let's Encrypt
- **Force HTTPS**: Yes

#### Management Service Domain
- **Service**: dotmac-management  
- **Port**: 8001
- **Domain**: admin.yourdomain.com
- **SSL**: Enable Let's Encrypt
- **Force HTTPS**: Yes

### 6. Setup CI/CD Webhooks

1. In Coolify, go to Project Settings → Webhooks
2. Generate webhooks for both staging and production
3. Add to GitHub repository secrets:

```bash
COOLIFY_STAGING_WEBHOOK_URL=https://coolify.yourdomain.com/api/v1/webhooks/[staging-id]
COOLIFY_PRODUCTION_WEBHOOK_URL=https://coolify.yourdomain.com/api/v1/webhooks/[production-id]
```

## 🔧 Configuration Files Summary

### Files Created:
- ✅ `Dockerfile.production` - Multi-stage production build
- ✅ `docker/production-entrypoint.sh` - SERVICE_TYPE routing script
- ✅ `docker-compose.coolify.yml` - Coolify deployment configuration  
- ✅ `.github/workflows/build-and-deploy.yml` - CI/CD pipeline
- ✅ `alembic/` - Database migration framework
- ✅ `DEPLOYMENT.md` - Comprehensive deployment guide

### Key Features:
- **Single Image**: One Docker image for both ISP and Management services
- **SERVICE_TYPE Pattern**: Runtime service selection via environment variable
- **Health Checks**: Built-in monitoring and recovery
- **Automatic Migrations**: Database schema updates on deployment
- **Resource Limits**: CPU and memory constraints for stability
- **Volume Persistence**: Logs and uploads preserved across restarts

## 🚦 Deployment Process

### Automatic Deployment Flow:

1. **Code Push** → GitHub repository
2. **CI Pipeline** → Builds Docker image, runs tests
3. **Image Push** → GitHub Container Registry (ghcr.io)
4. **Webhook Trigger** → Notifies Coolify of new image
5. **Deployment** → Coolify pulls image and updates services
6. **Health Checks** → Verifies services are running correctly

### Manual Deployment (if needed):
```bash
# Build and tag image locally
docker build -f Dockerfile.production -t ghcr.io/dotmac/dotmac-framework:latest .

# Push to registry
docker push ghcr.io/dotmac/dotmac-framework:latest

# Trigger deployment via Coolify webhook
curl -X POST "https://coolify.yourdomain.com/api/v1/webhooks/[webhook-id]"
```

## 🎯 Next Steps

### 1. DNS Configuration
Point your domains to the Coolify server:
```bash
isp.yourdomain.com     A    149.102.135.97
admin.yourdomain.com   A    149.102.135.97
```

### 2. GitHub Repository Setup
- Add repository to GitHub Container Registry
- Configure GitHub Actions secrets
- Set up branch protection rules

### 3. Monitoring Setup
- Configure Coolify alerts
- Set up log aggregation
- Monitor resource usage

### 4. Backup Configuration
- Database automatic backups
- Volume snapshot scheduling
- Disaster recovery planning

## 🔒 Security Considerations

- ✅ Non-root container execution
- ✅ Resource limits and quotas
- ✅ Automatic SSL certificates
- ✅ Environment variable encryption
- ✅ Network isolation
- ✅ Health check monitoring

## 📞 Support

For deployment issues:
1. Check Coolify logs in dashboard
2. Verify environment variables
3. Test database connectivity
4. Review GitHub Actions workflow logs

Your Coolify production environment is ready for deployment! 🚀