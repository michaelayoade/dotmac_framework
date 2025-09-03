# Coolify Production Deployment Guide

## 🎯 Overview

This guide walks you through deploying the DotMac Framework to production using Coolify with your production requirements:

- ✅ **ENVIRONMENT=production**
- ✅ **STRICT_PROD_BASELINE=true** 
- ✅ **PostgreSQL** (non-SQLite) with RLS
- ✅ **Redis** cache layer
- ✅ **OpenBao** secrets provider
- ✅ **Comprehensive monitoring** with Prometheus alerts

## 📋 Pre-Deployment Checklist

✅ **Coolify installed** at: https://coolify.dotmac.com  
✅ **Production environment variables** created (`.env.coolify.production`)  
✅ **Docker Compose configuration** ready (`docker-compose.coolify.yml`)  
✅ **Monitoring alerts** configured (`monitoring/prometheus/alerts.yml`)  

## 🚀 Step-by-Step Coolify Deployment

### 1. Access Coolify Dashboard

Navigate to: **https://coolify.dotmac.com**

### 2. Create Production Project

1. Click **"Create Project"**
2. **Name**: `DotMac Production`
3. **Description**: `DotMac ISP Management Framework - Production Environment`

### 3. Deploy Required Services

#### PostgreSQL Database
```yaml
Service Type: PostgreSQL
Name: dotmac-postgres
Version: 15
Database Name: dotmac_production
Username: dotmac_user
Password: [Generate 32-char secure password]
Port: 5432
```

#### Redis Cache
```yaml
Service Type: Redis
Name: dotmac-redis
Version: 7-alpine
Max Memory: 1GB
Max Memory Policy: allkeys-lru
Port: 6379
Password: [Generate secure Redis password]
```

### 4. Deploy DotMac Application

#### Create Docker Compose Application
1. Click **"Add Service"** → **"Docker Compose"**
2. **Name**: `DotMac Framework`
3. **Repository**: Upload or link your `docker-compose.coolify.yml`

#### Configure Production Environment Variables

Copy variables from `.env.coolify.production` and update these **CRITICAL VALUES**:

**🔒 SECURITY - MUST REPLACE:**
```bash
SECRET_KEY=[Generate 64-character secure key]
JWT_SECRET=[Generate 64-character secure key] 
ENCRYPTION_KEY=[Generate 32-character key]
WEBHOOK_SECRET=[Generate secure webhook secret]
OPENBAO_TOKEN=[Your actual OpenBao token]
```

**🌐 DOMAINS - UPDATE TO YOUR DOMAINS:**
```bash
OPENBAO_URL=https://vault.yourdomain.com
ADMIN_EMAIL=admin@yourdomain.com
CORS_ORIGINS=["https://admin.yourdomain.com","https://reseller.yourdomain.com","https://api.yourdomain.com"]
```

**📊 AUTO-INJECTED BY COOLIFY:**
```bash
DATABASE_URL=[Auto-injected from PostgreSQL service]
REDIS_URL=[Auto-injected from Redis service]
```

### 5. Configure Domains & SSL

Configure these domains in Coolify:

#### ISP Service (Port 8000)
- **Domain**: `isp.yourdomain.com`
- **SSL**: ✅ Enable Let's Encrypt
- **Force HTTPS**: ✅ Yes

#### Management API (Port 8001)  
- **Domain**: `api.yourdomain.com`
- **SSL**: ✅ Enable Let's Encrypt
- **Force HTTPS**: ✅ Yes

### 6. Deploy Monitoring Stack

#### Add Prometheus Service
```yaml
Service Type: Custom Docker
Image: prom/prometheus:latest
Name: prometheus
Port: 9090
Volumes:
  - ./monitoring/prometheus:/etc/prometheus
```

#### Add Alertmanager Service
```yaml
Service Type: Custom Docker  
Image: prom/alertmanager:latest
Name: alertmanager
Port: 9093
```

### 7. Setup CI/CD Integration

#### Generate Webhooks
1. Go to **Project Settings** → **Webhooks**
2. Generate webhook for production environment
3. Add to GitHub repository secrets:

```bash
COOLIFY_PRODUCTION_WEBHOOK_URL=https://coolify.yourdomain.com/api/v1/webhooks/[production-id]
```

## 🔧 Production Validation

### 1. Health Checks

Once deployed, verify all services:

```bash
# ISP Service Health
curl https://isp.yourdomain.com/health

# Management API Health  
curl https://api.yourdomain.com/health

# Database Connection
curl https://api.yourdomain.com/api/v1/health/db

# Redis Connection
curl https://api.yourdomain.com/api/v1/health/redis
```

### 2. Run Production Readiness Check

```bash
# SSH into Coolify deployment container
source .env.coolify.production
python scripts/production_readiness_check.py
```

**Expected Results:**
- ✅ **Environment Variables**: All production vars configured
- ✅ **Database**: PostgreSQL connection successful
- ✅ **Redis**: Cache connection successful  
- ✅ **Strict Baseline**: All requirements met
- ✅ **Monitoring**: Prometheus alerts configured

### 3. Run Smoke Tests

Update smoke test URLs and run:

```bash
export ADMIN_BASE_URL=https://admin.yourdomain.com
export RESELLER_BASE_URL=https://reseller.yourdomain.com
export TENANT_BASE_URL=https://acme.isp.yourdomain.com
export MGMT_API_URL=https://api.yourdomain.com
export TENANT_SLUG=acme

make smoke
```

## 📊 Monitoring & Alerts

### Prometheus Targets

Your Prometheus should scrape:
- ✅ **Management Platform**: `api.yourdomain.com:8001/metrics`
- ✅ **ISP Service**: `isp.yourdomain.com:8000/metrics`  
- ✅ **PostgreSQL**: Database metrics
- ✅ **Redis**: Cache metrics
- ✅ **System**: Node exporter metrics

### Critical Alerts Configured

- 🚨 **HighErrorRate5xx**: 5xx error rate > 5%
- 🚨 **ServiceDown**: Service availability monitoring
- 🚨 **ManagementAPIDown**: Core API health
- 🚨 **TenantProvisioningLatencyHigh**: p95 > 60s
- 🚨 **LoginSuccessRateLow**: Success rate < 98%
- 🚨 **HighMemoryUsage**: > 90% memory usage
- 🚨 **DatabaseDown**: PostgreSQL connectivity

## 🔒 Security Checklist

### Pre-Production Security
- [ ] **Replace all example secrets** with secure, randomly-generated values
- [ ] **Configure OpenBao/Vault** with proper authentication
- [ ] **Set up TLS certificates** for all domains
- [ ] **Configure firewall rules** and security groups
- [ ] **Enable audit logging** for all security events

### Row-Level Security Validation
```bash
# Verify RLS is applied
psql $DATABASE_URL -c "SELECT current_tenant_id();"

# Check tenant isolation
curl -H "X-Tenant: acme" https://api.yourdomain.com/api/v1/customers
```

## 🚦 Deployment Flow

### Automatic CI/CD
1. **Code Push** → GitHub repository
2. **CI Pipeline** → Build image, run tests
3. **Image Push** → GitHub Container Registry
4. **Webhook** → Notify Coolify
5. **Deploy** → Coolify updates services
6. **Validation** → Health checks pass

### Manual Deployment
```bash
# Build production image
docker build -f Dockerfile.production -t ghcr.io/dotmac/dotmac-framework:latest .

# Push to registry
docker push ghcr.io/dotmac/dotmac-framework:latest

# Trigger Coolify deployment
curl -X POST "https://coolify.yourdomain.com/api/v1/webhooks/[webhook-id]"
```

## 🎯 DNS Configuration

Point your domains to Coolify server:

```bash
admin.yourdomain.com       A    [COOLIFY_SERVER_IP]
api.yourdomain.com         A    [COOLIFY_SERVER_IP] 
isp.yourdomain.com         A    [COOLIFY_SERVER_IP]
reseller.yourdomain.com    A    [COOLIFY_SERVER_IP]
```

## 📞 Production Support

### Monitoring Access
- **Prometheus**: `https://prometheus.yourdomain.com`
- **Alertmanager**: `https://alerts.yourdomain.com`
- **Application Logs**: Via Coolify dashboard

### Emergency Procedures
1. **Service Down**: Check Coolify service logs
2. **Database Issues**: Verify PostgreSQL service health
3. **Cache Issues**: Restart Redis service
4. **High Load**: Scale services in Coolify

---

**🚀 Your Coolify production deployment is ready!**

The DotMac Framework will run with:
- ✅ Production environment (`ENVIRONMENT=production`)
- ✅ Strict baseline validation (`STRICT_PROD_BASELINE=true`)
- ✅ PostgreSQL with Row-Level Security
- ✅ Redis caching layer
- ✅ OpenBao secrets management
- ✅ Comprehensive Prometheus monitoring
- ✅ Automated CI/CD deployment