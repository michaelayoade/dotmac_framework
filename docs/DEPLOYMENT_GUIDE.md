# DotMac Platform Deployment & Operations Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Container Lifecycle & Health Probes](#container-lifecycle--health-probes)
3. [Infrastructure Setup](#infrastructure-setup)
4. [Database Configuration](#database-configuration)
5. [Application Deployment](#application-deployment)
6. [Security Configuration](#security-configuration)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance Procedures](#maintenance-procedures)

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 22.04 LTS or RHEL 8+
- **CPU**: Minimum 8 cores (16+ recommended for production)
- **RAM**: Minimum 16GB (32GB+ recommended)
- **Storage**: 100GB+ SSD for application, 500GB+ for database
- **Network**: 1Gbps connection minimum

### Software Dependencies

```bash
# Core dependencies
- Docker 24.0+
- Kubernetes 1.28+
- PostgreSQL 14+
- Redis 7.0+
- Nginx 1.24+
- Python 3.11+
- Node.js 20+
```

### Required Tools

```bash
# Install essential tools
sudo apt-get update
sudo apt-get install -y \
  git curl wget \
  build-essential \
  openssl \
  jq \
  htop \
  net-tools
```

## Container Lifecycle & Health Probes

### Kubernetes Health Endpoints

Both ISP Framework and Management Platform now include production-ready Kubernetes health probes:

```bash
# Test health endpoints
curl http://localhost:8000/health/live      # ISP Framework liveness
curl http://localhost:8000/health/ready     # ISP Framework readiness
curl http://localhost:8000/health/startup   # ISP Framework startup

curl http://localhost:8001/health/live      # Management Platform liveness
curl http://localhost:8001/health/ready     # Management Platform readiness
curl http://localhost:8001/health/startup   # Management Platform startup
```

### Graceful Shutdown

Services support proper container termination:

- **SIGTERM/SIGINT**: Graceful shutdown initiation
- **30-second timeout**: Connection draining period
- **Resource cleanup**: Database and cache connections closed
- **Health probe failure**: Services marked unhealthy during shutdown

### Container State Management

Services track startup/shutdown states:

- **Startup tracking**: Monitors initialization progress
- **Health dependencies**: Database, cache, observability checks
- **Readiness dependencies**: Service-specific validation
- **Container info**: Kubernetes environment detection

## Infrastructure Setup

### 1. Single Server Deployment

```bash
# Clone repository
git clone https://github.com/dotmac/platform.git
cd platform

# Set environment
export ENVIRONMENT=production
export DOMAIN=your-domain.com

# Run setup script
./scripts/setup_single_server.sh
```

### 2. Kubernetes Deployment

#### Install Kubernetes

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

#### Deploy Application

```bash
# Create namespace
kubectl create namespace dotmac

# Apply configurations
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmap.yaml
kubectl apply -f kubernetes/secrets.yaml

# Deploy services
kubectl apply -f kubernetes/redis-deployment.yaml
kubectl apply -f kubernetes/postgres-deployment.yaml
kubectl apply -f kubernetes/app-deployment.yaml
kubectl apply -f kubernetes/nginx-ingress.yaml

# Apply HPA and monitoring
kubectl apply -f kubernetes/hpa.yaml
kubectl apply -f kubernetes/monitoring/

# Verify health probes are working
kubectl get pods -n dotmac
kubectl port-forward -n dotmac svc/isp-framework 8000:8000 &
kubectl port-forward -n dotmac svc/management-platform 8001:8001 &

# Test health endpoints
curl http://localhost:8000/health/live      # Should return 200 when healthy
curl http://localhost:8000/health/ready     # Should return 200 when ready
curl http://localhost:8000/health/startup   # Should return 200 when started

curl http://localhost:8001/health/live      # Management platform health
curl http://localhost:8001/health/ready     # Management platform readiness
curl http://localhost:8001/health/startup   # Management platform startup
```

#### Health Probe Configuration

Example Kubernetes deployment with health probes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: isp-framework
  namespace: dotmac
spec:
  replicas: 2
  selector:
    matchLabels:
      app: isp-framework
  template:
    metadata:
      labels:
        app: isp-framework
    spec:
      containers:
      - name: isp-framework
        image: dotmac/isp-framework:latest
        ports:
        - containerPort: 8000

        # Kubernetes Health Probes
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2

        startupProbe:
          httpGet:
            path: /health/startup
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 30  # Allow up to 5 minutes for startup

        # Graceful shutdown
        terminationGracePeriodSeconds: 30

        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
```

### 3. Docker Compose Deployment

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose ps
docker-compose logs -f
```

## Database Configuration

### PostgreSQL Setup

#### 1. Initialize Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

-- Create database and user
CREATE DATABASE dotmac_production;
CREATE USER dotmac_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE dotmac_production TO dotmac_user;

-- Enable extensions
\c dotmac_production
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
```

#### 2. SSL Configuration

```bash
# Generate SSL certificates
cd /var/lib/postgresql/14/main
openssl req -new -x509 -days 365 -nodes -text \
  -out server.crt -keyout server.key -subj "/CN=postgres"
chmod 600 server.key
chown postgres:postgres server.key server.crt

# Update postgresql.conf
echo "ssl = on" >> postgresql.conf
echo "ssl_cert_file = 'server.crt'" >> postgresql.conf
echo "ssl_key_file = 'server.key'" >> postgresql.conf

# Restart PostgreSQL
sudo systemctl restart postgresql
```

#### 3. High Availability Setup

```bash
# Run replication setup script
./scripts/setup_pg_replication.sh primary

# On standby server
./scripts/setup_pg_replication.sh standby
```

### Redis Configuration

```bash
# Edit Redis configuration
sudo nano /etc/redis/redis.conf

# Production settings
maxmemory 4gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Enable password
requirepass your_redis_password

# Restart Redis
sudo systemctl restart redis
```

## Application Deployment

### 1. Environment Configuration

Create `.env.production`:

```bash
# Database
DATABASE_URL=postgresql://dotmac_user:password@localhost:5432/dotmac_production
DATABASE_SSL_MODE=require

# Redis
REDIS_URL=redis://:password@localhost:6379/0

# Security
SECRET_KEY=generate-strong-secret-key
JWT_SECRET=generate-jwt-secret
ENCRYPTION_KEY=generate-encryption-key

# API
API_BASE_URL=https://api.your-domain.com
FRONTEND_URL=https://your-domain.com

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-specific-password

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=your-sentry-dsn

# Features
ENABLE_MULTI_TENANT=true
ENABLE_RATE_LIMITING=true
ENABLE_AUDIT_LOG=true
```

### 2. Backend Deployment

```bash
# Navigate to backend
cd isp-framework

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start application
gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info \
  --access-logfile /var/log/dotmac/access.log \
  --error-logfile /var/log/dotmac/error.log \
  dotmac_isp.main:app
```

### 3. Frontend Deployment

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Serve with Nginx
sudo cp -r dist/* /var/www/dotmac/
```

### 4. Nginx Configuration

```nginx
# /etc/nginx/sites-available/dotmac
upstream backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Frontend
    location / {
        root /var/www/dotmac;
        try_files $uri $uri/ /index.html;
    }

    # API Proxy
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 90;
    }

    # WebSocket Support
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Security Configuration

### 1. SSL/TLS Setup

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

### 2. Firewall Configuration

```bash
# UFW setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5432/tcp  # PostgreSQL (restrict to specific IPs)
sudo ufw allow 6379/tcp  # Redis (restrict to specific IPs)
sudo ufw enable
```

### 3. Security Hardening

```bash
# Disable root SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Configure fail2ban
sudo apt-get install fail2ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Set up audit logging
sudo apt-get install auditd
sudo systemctl enable auditd
sudo systemctl start auditd
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'dotmac-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
```

### 2. Grafana Dashboards

```bash
# Install Grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
sudo apt-get update
sudo apt-get install grafana

# Configure datasource
cat <<EOF > /etc/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://localhost:9090
    isDefault: true
EOF

# Start Grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

### 3. Alert Rules

```yaml
# alerts.yml
groups:
  - name: dotmac_alerts
    rules:
      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        annotations:
          summary: "High CPU usage detected"

      - alert: DatabaseSlowQueries
        expr: db_slow_queries_total > 100
        for: 10m
        annotations:
          summary: "Too many slow queries"

      - alert: LowCacheHitRatio
        expr: db_cache_hit_ratio < 0.9
        for: 15m
        annotations:
          summary: "Database cache hit ratio is low"
```

### 4. Log Aggregation

```bash
# Install ELK Stack
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  elasticsearch:8.10.0

docker run -d \
  --name kibana \
  -p 5601:5601 \
  --link elasticsearch \
  kibana:8.10.0

# Configure Filebeat
cat <<EOF > /etc/filebeat/filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/dotmac/*.log
      - /var/log/nginx/*.log

output.elasticsearch:
  hosts: ["localhost:9200"]
EOF
```

## Backup & Recovery

### 1. Database Backup

```bash
# Automated backup script
cat <<'EOF' > /usr/local/bin/backup_database.sh
#!/bin/bash
BACKUP_DIR="/backup/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="dotmac_production"

# Create backup
pg_dump -U postgres -d $DB_NAME -f "$BACKUP_DIR/backup_$DATE.sql"

# Compress
gzip "$BACKUP_DIR/backup_$DATE.sql"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/backup_$DATE.sql.gz" s3://your-backup-bucket/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup_database.sh

# Schedule with cron
echo "0 2 * * * /usr/local/bin/backup_database.sh" | crontab -
```

### 2. Application Backup

```bash
# Backup application data
tar -czf /backup/app_$(date +%Y%m%d).tar.gz \
  /var/www/dotmac \
  /etc/nginx/sites-available \
  /home/dotmac/.env.production
```

### 3. Disaster Recovery

```bash
# Restore database
gunzip < backup_20240824_020000.sql.gz | psql -U postgres -d dotmac_production

# Restore application
tar -xzf app_20240824.tar.gz -C /

# Verify restoration
./scripts/health_check.sh
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

#### 2. High Memory Usage

```bash
# Check memory usage
free -h
htop

# Clear Redis cache
redis-cli FLUSHALL

# Restart services
sudo systemctl restart dotmac-app
```

#### 3. Slow Performance

```bash
# Check slow queries
psql -U postgres -d dotmac_production -c "
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"

# Check Nginx connections
nginx -t
nginx -s reload
```

#### 4. SSL Certificate Issues

```bash
# Renew certificate
sudo certbot renew --dry-run
sudo certbot renew

# Verify certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Start with verbose output
python -m dotmac_isp.main --debug

# Monitor logs
tail -f /var/log/dotmac/*.log | grep ERROR
```

## Maintenance Procedures

### Daily Tasks

- Monitor system health dashboard
- Check backup completion
- Review error logs
- Verify SSL certificates

### Weekly Tasks

- Database vacuum and analyze
- Clear old logs
- Update security patches
- Performance review

### Monthly Tasks

- Full system backup
- Security audit
- Capacity planning review
- Update documentation

### Maintenance Commands

```bash
# Database maintenance
sudo -u postgres psql -d dotmac_production -c "VACUUM ANALYZE;"
sudo -u postgres psql -d dotmac_production -c "REINDEX DATABASE dotmac_production;"

# Clear logs
find /var/log/dotmac -name "*.log" -mtime +30 -delete

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Restart services
sudo systemctl restart postgresql redis nginx dotmac-app
```

## Performance Tuning

### PostgreSQL Optimization

```sql
-- Update postgresql.conf
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
```

### Redis Optimization

```bash
# redis.conf
tcp-backlog 511
timeout 0
tcp-keepalive 300
databases 16
maxclients 10000
```

### Application Optimization

```python
# Gunicorn configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
```

## Health Checks

### Automated Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "=== DotMac Platform Health Check ==="

# Check services
for service in postgresql redis nginx dotmac-app; do
    if systemctl is-active --quiet $service; then
        echo "✓ $service is running"
    else
        echo "✗ $service is not running"
    fi
done

# Check database
if psql -U postgres -d dotmac_production -c "SELECT 1" > /dev/null 2>&1; then
    echo "✓ Database is accessible"
else
    echo "✗ Database is not accessible"
fi

# Check ISP Framework health endpoints
echo "Checking ISP Framework health endpoints..."
for endpoint in live ready startup; do
    if curl -f http://localhost:8000/health/$endpoint > /dev/null 2>&1; then
        echo "✓ ISP Framework /health/$endpoint is responding"
    else
        echo "✗ ISP Framework /health/$endpoint is not responding"
    fi
done

# Check Management Platform health endpoints
echo "Checking Management Platform health endpoints..."
for endpoint in live ready startup; do
    if curl -f http://localhost:8001/health/$endpoint > /dev/null 2>&1; then
        echo "✓ Management Platform /health/$endpoint is responding"
    else
        echo "✗ Management Platform /health/$endpoint is not responding"
    fi
done

# Check legacy health endpoint for backwards compatibility
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Legacy health endpoint is responding"
else
    echo "✗ Legacy health endpoint is not responding"
fi

# Check disk space
df -h | grep -E '^/dev/' | awk '{print $6 " " $5}' | while read output; do
    usage=$(echo $output | awk '{print $2}' | sed 's/%//')
    partition=$(echo $output | awk '{print $1}')
    if [ $usage -ge 80 ]; then
        echo "⚠ Disk usage high on $partition: $usage%"
    fi
done
```

## Support & Resources

### Documentation

- [Architecture Guide](/docs/ARCHITECTURE.md)
- [API Documentation](/docs/API_DOCUMENTATION.md)
- [Security Guide](/docs/SECURITY.md)

### Contact

- **Technical Support**: <support@dotmac.cloud>
- **Emergency Hotline**: +1-xxx-xxx-xxxx
- **Slack Channel**: #dotmac-ops

### Useful Commands Reference

```bash
# Service management
systemctl status/start/stop/restart dotmac-app

# Log viewing
journalctl -u dotmac-app -f
tail -f /var/log/dotmac/*.log

# Database console
psql -U postgres -d dotmac_production

# Redis console
redis-cli -a password

# Network diagnostics
netstat -tulpn
ss -tulpn
lsof -i :8000
```

---

*Last Updated: August 2024*
*Version: 1.0.0*
