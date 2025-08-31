# 🚀 DotMac Platform Comprehensive Deployment Guide

Complete deployment and operations guide for the DotMac ISP Management Platform.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Production Deployment](#production-deployment)
- [Container Management](#container-management)
- [Monitoring & Observability](#monitoring--observability)
- [Backup & Disaster Recovery](#backup--disaster-recovery)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements

**Production Environment:**
- **CPU**: 16+ cores (32+ recommended)
- **RAM**: 64GB minimum (128GB recommended)
- **Storage**: 1TB SSD minimum (NVMe preferred)
- **Network**: 10Gbps minimum bandwidth
- **OS**: Ubuntu 22.04 LTS or RHEL 9+

**Development Environment:**
- **CPU**: 8+ cores
- **RAM**: 16GB minimum (32GB recommended)  
- **Storage**: 500GB SSD
- **Network**: 1Gbps bandwidth
- **OS**: Ubuntu 22.04 LTS, macOS 13+, or Windows 11 with WSL2

### Required Software

```bash
# Core dependencies
sudo apt update && sudo apt install -y \
  docker.io docker-compose-v2 \
  nginx postgresql-client redis-tools \
  git curl wget jq \
  python3 python3-pip python3-venv \
  nodejs npm pnpm \
  helm kubectl

# Optional but recommended
sudo apt install -y \
  htop tmux vim \
  prometheus-node-exporter \
  fail2ban ufw
```

### Platform Dependencies

```bash
# Install Kubernetes (if not using managed service)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# Install Helm 3
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🌐 Environment Setup

### 1. Environment Configuration

```bash
# Clone the repository
git clone https://github.com/dotmac/platform.git
cd dotmac-platform

# Create environment files
cp .env.example .env.production
cp .env.example .env.staging
cp .env.example .env.development

# Configure production environment
vim .env.production
```

**Essential Environment Variables:**

```bash
# Core Configuration
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/dotmac_prod
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET_KEY=jwt-secret-key-here
ENCRYPTION_KEY=32-byte-encryption-key

# External Services
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=notifications@yourdomain.com
SMTP_PASSWORD=smtp-password

# Payment Processing
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...

# Monitoring
SIGNOZ_ENDPOINT=http://signoz:4318
PROMETHEUS_ENDPOINT=http://prometheus:9090

# Domain Configuration
DOMAIN=api.dotmac.platform
FRONTEND_DOMAIN=app.dotmac.platform
```

### 2. SSL Certificate Setup

```bash
# Using Let's Encrypt (recommended)
sudo certbot certonly --nginx -d api.dotmac.platform -d app.dotmac.platform

# Or use your own certificates
sudo mkdir -p /etc/ssl/dotmac
sudo cp your-cert.pem /etc/ssl/dotmac/cert.pem
sudo cp your-key.pem /etc/ssl/dotmac/key.pem
sudo chmod 600 /etc/ssl/dotmac/key.pem
```

### 3. Database Setup

```bash
# Create production database
sudo -u postgres createdb dotmac_prod
sudo -u postgres createuser dotmac_user
sudo -u postgres psql -c "ALTER USER dotmac_user CREATEDB;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dotmac_prod TO dotmac_user;"

# Run migrations
PYTHONPATH=src python -m alembic upgrade head

# 🤖 CRITICAL: Validate deployment readiness before proceeding
make -f Makefile.readiness deployment-ready
# This ensures 100% startup success and schema integrity
```

## 🐳 Production Deployment

### Option 1: Docker Compose (Single Server)

```bash
# Production deployment with Docker Compose
cp docker-compose.prod.yml docker-compose.override.yml
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify services
docker-compose ps
docker-compose logs -f
```

### Option 2: Kubernetes (Recommended)

```bash
# Create namespace
kubectl create namespace dotmac-production

# Install using Helm
helm install dotmac-platform ./helm/dotmac-platform \
  --namespace dotmac-production \
  --values values.production.yaml \
  --wait --timeout=600s

# Verify deployment
kubectl get pods -n dotmac-production
kubectl get services -n dotmac-production
kubectl get ingress -n dotmac-production
```

**Example Kubernetes Values (values.production.yaml):**

```yaml
replicaCount: 3

image:
  repository: dotmac/platform
  tag: "latest"
  pullPolicy: Always

service:
  type: LoadBalancer
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: api.dotmac.platform
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: dotmac-tls
      hosts:
        - api.dotmac.platform

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

postgresql:
  enabled: true
  auth:
    postgresPassword: "secure-postgres-password"
    database: "dotmac_prod"
  primary:
    persistence:
      enabled: true
      size: 500Gi
      storageClass: "fast-ssd"

redis:
  enabled: true
  auth:
    enabled: true
    password: "secure-redis-password"
  master:
    persistence:
      enabled: true
      size: 100Gi

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
  prometheusRule:
    enabled: true
```

### Option 3: Complete ISP Platform Deployment

```bash
# Deploy complete integrated ISP framework
helm install dotmac-isp-complete \
  ./src/dotmac_shared/deployments/helm/dotmac-isp-complete \
  --namespace dotmac-production \
  --create-namespace \
  --values values.isp-complete.yaml \
  --wait --timeout=1200s

# This deploys:
# - ISP Framework (management API)
# - FreeRADIUS server
# - Ansible engine  
# - VOLTHA stack (GPON management)
# - Complete infrastructure
```

## 📊 Container Management

### Health Check Endpoints

The platform provides comprehensive health monitoring:

```bash
# Health check endpoints
curl https://api.dotmac.platform/health          # Legacy compatibility
curl https://api.dotmac.platform/health/live     # Liveness probe
curl https://api.dotmac.platform/health/ready    # Readiness probe  
curl https://api.dotmac.platform/health/startup  # Startup probe
```

### Container Lifecycle

**Graceful Shutdown:**
```bash
# Send SIGTERM for graceful shutdown
docker kill --signal=SIGTERM container_name

# Or use docker-compose
docker-compose stop

# Force stop after timeout
docker-compose down --timeout 30
```

**Container Scaling:**
```bash
# Scale with Docker Compose
docker-compose up -d --scale api=3 --scale worker=5

# Scale with Kubernetes
kubectl scale deployment dotmac-api --replicas=5 -n dotmac-production
```

### Multi-Tenant Container Management

**ISP Container Provisioning:**
```bash
# Create new ISP tenant container
curl -X POST https://management.dotmac.platform/api/v1/tenants \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Regional ISP Co",
    "plan": "professional", 
    "max_customers": 5000,
    "features": ["billing", "support", "field_ops"]
  }'

# Monitor container provisioning
kubectl logs -f deployment/tenant-provisioner -n dotmac-management
```

## 📈 Monitoring & Observability

### Metrics Collection

**Prometheus Configuration:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'dotmac-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'dotmac-containers'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names: ['dotmac-production']
```

**Grafana Dashboards:**
```bash
# Import pre-built dashboards
curl -X POST http://grafana:3000/api/dashboards/import \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dotmac-overview.json
```

### Log Management

**Centralized Logging with SignOz:**
```bash
# Configure log forwarding
docker run -d \
  --name signoz-collector \
  -v /var/log:/var/log:ro \
  -v /var/lib/docker/containers:/var/lib/docker/containers:ro \
  signoz/signoz-otel-collector:latest
```

### Alerting Rules

```yaml
groups:
  - name: dotmac-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: ContainerDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.instance }} is down"

      - alert: HighMemoryUsage
        expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage in {{ $labels.container_name }}"
```

## 💾 Backup & Disaster Recovery

### Automated Backup Setup

```bash
# Setup automated backups
sudo bash deployment/scripts/setup_backups.sh

# Manual backup
bash scripts/backup_system.sh --full --encrypt

# Verify backups
bash scripts/verify_backups.sh
```

**Backup Schedule:**
```bash
# Add to crontab
0 2 * * * /opt/dotmac/scripts/backup_system.sh --daily
0 3 * * 0 /opt/dotmac/scripts/backup_system.sh --weekly  
0 4 1 * * /opt/dotmac/scripts/backup_system.sh --monthly
```

### Disaster Recovery Procedure

**Complete System Restore:**
```bash
# 1. Restore from backup
bash scripts/restore_system.sh --backup-id=20240101-020000 --verify

# 2. Verify data integrity
bash scripts/verify_data_integrity.sh

# 3. Restart services
docker-compose up -d
kubectl rollout restart deployment -n dotmac-production

# 4. Run health checks
bash scripts/health_check.sh --comprehensive
```

## 🔒 Security Configuration

### Production Security Hardening

```bash
# Apply security hardening
python3 scripts/apply_security_hardening.py --force

# Enable fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Configure firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Secret Management

**Using OpenBao (HashiCorp Vault):**
```bash
# Initialize vault
openbao operator init -key-shares=5 -key-threshold=3

# Store secrets
openbao kv put secret/dotmac/db password="secure-db-password"
openbao kv put secret/dotmac/jwt key="jwt-secret-key"
```

### SSL/TLS Configuration

**Nginx SSL Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name api.dotmac.platform;

    ssl_certificate /etc/ssl/dotmac/cert.pem;
    ssl_certificate_key /etc/ssl/dotmac/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🚀 Performance Optimization

### Application Tuning

```bash
# Apply performance optimizations
python3 scripts/optimize_performance.py

# Database optimization
sudo -u postgres psql -d dotmac_prod -f scripts/database_optimization.sql

# Redis optimization  
sudo echo "maxmemory 8gb" >> /etc/redis/redis.conf
sudo echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
sudo systemctl restart redis
```

### Load Balancing

**HAProxy Configuration:**
```
global
    daemon
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend dotmac_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/dotmac/combined.pem
    redirect scheme https if !{ ssl_fc }
    default_backend dotmac_backend

backend dotmac_backend
    balance roundrobin
    option httpchk GET /health/ready
    server app1 10.0.1.10:8000 check
    server app2 10.0.1.11:8000 check
    server app3 10.0.1.12:8000 check
```

## 🔧 Troubleshooting

### Common Issues

**1. Container Won't Start**
```bash
# Check logs
docker-compose logs api
kubectl logs deployment/dotmac-api -n dotmac-production

# Check resource usage
docker stats
kubectl top pods -n dotmac-production

# Check health endpoints
curl http://localhost:8000/health/startup
```

**2. Database Connection Issues**
```bash
# Test database connectivity
pg_isready -h localhost -p 5432 -U dotmac_user

# Check database logs
tail -f /var/log/postgresql/postgresql-*.log

# Verify environment variables
env | grep DATABASE
```

**3. High Memory Usage**
```bash
# Check memory usage by container
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Identify memory leaks
kubectl top pods -n dotmac-production --sort-by=memory
```

### Debug Mode

```bash
# Enable debug mode (development only)
export DEBUG=true
export LOG_LEVEL=debug

# Restart with debug logging
docker-compose restart api
```

### Log Analysis

```bash
# Follow application logs
tail -f logs/application.log

# Search for errors
grep -i error logs/application.log | tail -20

# Monitor real-time metrics
watch -n 1 'curl -s http://localhost:8000/metrics | grep http_requests_total'
```

## 📞 Support & Maintenance

### Regular Maintenance Tasks

**Daily:**
- Check system health dashboards
- Review error logs
- Verify backup completion

**Weekly:**
- Update security patches
- Review performance metrics
- Test disaster recovery procedures

**Monthly:**
- Security vulnerability scan
- Performance optimization review
- Capacity planning assessment

### Getting Help

**Documentation:**
- [API Reference](https://docs.dotmac.platform/api/)
- [Operations Guide](https://docs.dotmac.platform/ops/)
- [Troubleshooting Guide](https://docs.dotmac.platform/troubleshooting/)

**Support Channels:**
- **Emergency**: support@dotmac.platform
- **General**: help@dotmac.platform
- **Documentation**: docs@dotmac.platform

---

**Last Updated**: 2024-12-31
**Version**: 1.0.0