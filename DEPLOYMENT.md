# DotMac Framework - Production Deployment Guide

This guide covers deploying the DotMac Framework to production using Coolify with the recommended single-image, multi-service approach.

## 🏗️ Architecture Overview

The production deployment uses:
- **Single Docker Image**: Built in CI, tagged, and pushed to registry
- **Multi-Service Pattern**: Same image runs as `dotmac-isp` or `dotmac-management` based on `SERVICE_TYPE` env var
- **Coolify Management**: Handles container orchestration, database/Redis add-ons, and environment variables

## 🚀 Deployment Strategy

### 1. CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/build-and-deploy.yml`) handles:

- **Build**: Creates a single optimized Docker image
- **Test**: Runs tests and security scans
- **Push**: Tags and pushes to GitHub Container Registry
- **Deploy**: Triggers Coolify deployment via webhook

### 2. Service Configuration

Both services use the same image with different `SERVICE_TYPE`:

```yaml
# ISP Service
dotmac-isp:
  image: ghcr.io/dotmac/dotmac-framework:latest
  environment:
    - SERVICE_TYPE=isp
    
# Management Service  
dotmac-management:
  image: ghcr.io/dotmac/dotmac-framework:latest
  environment:
    - SERVICE_TYPE=management
```

## 📋 Prerequisites

1. **Coolify Server**: Installed and accessible
2. **GitHub Container Registry**: Access configured
3. **Domain Names**: For ISP and Management services
4. **SSL Certificates**: Automatic via Coolify/Let's Encrypt

## 🔧 Coolify Setup

### Step 1: Create Project

1. Access Coolify at `http://your-server:8000`
2. Create new project: "DotMac Production"
3. Set up Git repository connection

### Step 2: Add Database Services

Create PostgreSQL add-on:
```bash
Name: dotmac-postgres
Version: 15
Database: dotmac
Username: dotmac_user
Password: [generate secure password]
```

Create Redis add-on:
```bash
Name: dotmac-redis  
Version: 7
Max Memory: 512MB
Policy: allkeys-lru
```

### Step 3: Deploy Compose Application

1. Create new "Docker Compose" application
2. Upload `docker-compose.coolify.yml`
3. Configure environment variables:

#### Required Environment Variables

```bash
# Database (auto-injected by Coolify)
DATABASE_URL=postgresql://dotmac_user:password@dotmac-postgres:5432/dotmac

# Redis (auto-injected by Coolify)
REDIS_URL=redis://dotmac-redis:6379

# Application Security
SECRET_KEY=[generate 32-character secret]
WEBHOOK_SECRET=[generate webhook secret]

# Admin Configuration
ADMIN_EMAIL=admin@yourdomain.com

# Service Endpoints
ISP_DOMAIN=isp.yourdomain.com
MANAGEMENT_DOMAIN=admin.yourdomain.com
```

### Step 4: Configure Domains & SSL

1. **ISP Service**: 
   - Domain: `isp.yourdomain.com`
   - Port: `8000`
   - SSL: Enable Let's Encrypt

2. **Management Service**:
   - Domain: `admin.yourdomain.com` 
   - Port: `8001`
   - SSL: Enable Let's Encrypt

## 🔄 Deployment Process

### Development to Staging

```bash
# Push to develop branch
git push origin develop

# Triggers:
# 1. CI tests and builds image
# 2. Auto-deploy to staging environment
# 3. Staging webhook updates Coolify
```

### Staging to Production  

```bash
# Merge to main or create release tag
git push origin main
# or
git tag v1.0.0 && git push origin v1.0.0

# Triggers:
# 1. CI builds production image
# 2. Auto-deploy to production environment
# 3. Production webhook updates Coolify
```

## 🔒 Security Configuration

### Environment Variables

Store sensitive values in Coolify's environment variable management:

- ✅ **Encrypted**: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`
- ✅ **Scoped**: Per-service environment isolation
- ✅ **Versioned**: Rollback capability

### Network Security

- **Internal Network**: Services communicate via Docker network
- **External Access**: Only through reverse proxy
- **SSL/TLS**: Automatic certificate management

## 📊 Monitoring & Observability

### Built-in Health Checks

```bash
# ISP Service
curl https://isp.yourdomain.com/health

# Management Service  
curl https://admin.yourdomain.com/health
```

### Logging

Coolify automatically collects logs:
- **Application Logs**: `/app/logs/` (persistent volumes)
- **Container Logs**: Docker logging driver
- **Access Logs**: Nginx/Traefik proxy logs

### Metrics

- **Resource Usage**: CPU, Memory, Disk (Coolify dashboard)
- **Application Metrics**: `/api/metrics` endpoint
- **Database Metrics**: PostgreSQL/Redis monitoring

## 🛠️ Maintenance Operations

### Rolling Updates

```bash
# Push new image tag
docker push ghcr.io/dotmac/dotmac-framework:v1.1.0

# Update in Coolify (zero-downtime)
# Services restart with new image automatically
```

### Database Migrations

Handled automatically by the Management service on startup:

```bash
# Runs in production-entrypoint.sh
alembic upgrade head
```

### Scaling

Horizontal scaling per service:
```yaml
# Scale ISP service for high traffic
replicas: 3

# Scale Management service for admin operations  
replicas: 2
```

## 🚨 Troubleshooting

### Common Issues

1. **Service Won't Start**
   ```bash
   # Check logs
   docker logs dotmac-isp
   docker logs dotmac-management
   
   # Verify environment variables
   env | grep DATABASE_URL
   ```

2. **Database Connection**
   ```bash
   # Test database connectivity
   docker exec dotmac-postgres pg_isready
   
   # Check migration status
   docker exec dotmac-management alembic current
   ```

3. **Image Pull Issues**
   ```bash
   # Verify registry access
   docker pull ghcr.io/dotmac/dotmac-framework:latest
   
   # Check Coolify registry configuration
   ```

### Recovery Procedures

1. **Rollback Deployment**
   - Use Coolify's deployment history
   - Select previous successful deployment
   - Click "Rollback"

2. **Database Recovery**
   - Automatic backups via Coolify
   - Point-in-time recovery available
   - Manual backup: `pg_dump`

## 🔄 CI/CD Webhooks

Configure in GitHub repository settings:

```bash
# Staging Webhook
COOLIFY_STAGING_WEBHOOK_URL=https://coolify.yourdomain.com/api/v1/webhooks/staging-id

# Production Webhook  
COOLIFY_PRODUCTION_WEBHOOK_URL=https://coolify.yourdomain.com/api/v1/webhooks/production-id
```

## 📈 Performance Optimization

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'        # Adjust based on load
      memory: 2G         # Monitor usage patterns
    reservations:
      cpus: '0.5'        # Minimum guaranteed
      memory: 512M
```

### Caching Strategy

- **Redis**: Session storage, API responses
- **CDN**: Static assets (Cloudflare/AWS CloudFront)
- **Database**: Connection pooling, query optimization

This deployment strategy provides production-ready infrastructure with proper CI/CD, monitoring, and maintenance capabilities.