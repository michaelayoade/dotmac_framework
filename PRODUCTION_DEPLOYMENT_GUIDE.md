# DotMac Platform - Production Deployment Guide

## 🎯 Overview

This guide provides complete instructions for deploying the DotMac Platform in a production environment. The platform consists of two main components:
- **Management Platform**: SaaS orchestration and ISP management
- **ISP Framework**: Multi-tenant ISP operations system

## 📋 Prerequisites

### System Requirements

#### Minimum Requirements (Small Deployment)
- **CPU**: 4 cores (8 threads)
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 1 Gbps connection
- **OS**: Ubuntu 20.04 LTS or newer, CentOS 8+, RHEL 8+

#### Recommended Requirements (Production)
- **CPU**: 8 cores (16 threads)
- **RAM**: 16 GB
- **Storage**: 100 GB NVMe SSD
- **Network**: 10 Gbps connection
- **OS**: Ubuntu 22.04 LTS (recommended)

#### Enterprise Requirements (High Availability)
- **CPU**: 16+ cores (32+ threads)
- **RAM**: 32+ GB
- **Storage**: 500+ GB NVMe SSD with RAID 10
- **Network**: 10+ Gbps with redundancy
- **Load Balancer**: External load balancer recommended

### Software Dependencies

```bash
# Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Docker Compose (if not included with Docker)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Additional tools
sudo apt update
sudo apt install -y curl wget git openssl htop iotop netstat-nat
```

### Network Configuration

#### Required Ports
| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| HTTP | 80 | TCP | HTTP traffic (redirects to HTTPS) |
| HTTPS | 443 | TCP | HTTPS traffic |
| SSH | 22 | TCP | Server administration |

#### Internal Ports (Docker Network)
| Service | Port | Description |
|---------|------|-------------|
| Management Platform | 8000 | Internal API |
| ISP Framework | 8001 | Internal API |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache/Queue |
| OpenBao | 8200 | Secrets Management |
| ClickHouse | 9000, 8123 | Analytics Database |
| SignOz Collector | 4317, 4318 | Observability |
| SignOz Query | 8080 | Query Service |
| SignOz Frontend | 3301 | Monitoring UI |

### Domain Configuration

You'll need the following domains/subdomains:
- `admin.yourdomain.com` - Management Platform
- `*.yourdomain.com` - ISP Framework (wildcard for multi-tenant)
- `monitoring.yourdomain.com` - Observability Dashboard

## 🚀 Installation Steps

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Create dotmac user (optional but recommended)
sudo useradd -m -s /bin/bash dotmac
sudo usermod -aG docker dotmac
sudo usermod -aG sudo dotmac

# Create directories
sudo mkdir -p /opt/dotmac
sudo chown dotmac:dotmac /opt/dotmac
sudo mkdir -p /var/log/dotmac
sudo chown dotmac:dotmac /var/log/dotmac
sudo mkdir -p /backup/dotmac
sudo chown dotmac:dotmac /backup/dotmac

# Switch to dotmac user
sudo su - dotmac
cd /opt/dotmac
```

### Step 2: Download and Setup

```bash
# Clone the repository (or extract from release package)
git clone https://github.com/yourdomain/dotmac-platform.git
cd dotmac-platform

# Or extract from release package
# tar -xzf dotmac-platform-v1.0.0.tar.gz
# cd dotmac-platform-v1.0.0

# Verify integrity
ls -la
```

### Step 3: Generate Secure Environment

```bash
# Generate production environment configuration
./scripts/generate-secure-env.sh

# Select option 2 for production
# The script will create .env.production with secure secrets

# Important: Customize the generated .env.production file
nano .env.production
```

#### Required Customizations in `.env.production`:

```bash
# Update these values for your domain
CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com,https://portal.yourdomain.com
ALLOWED_HOSTS=yourdomain.com,admin.yourdomain.com,portal.yourdomain.com

# External service configuration
STRIPE_SECRET_KEY=sk_live_your_actual_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_actual_stripe_key
SENDGRID_API_KEY=your_sendgrid_api_key

# SMTP Configuration (if not using SendGrid)
SMTP_SERVER=your.smtp.server
SMTP_USERNAME=your_smtp_user
SMTP_PASSWORD=your_smtp_password
FROM_EMAIL=noreply@yourdomain.com

# MinIO Configuration (for file storage)
MINIO_ENDPOINT=s3.yourdomain.com:9000
```

### Step 4: SSL Certificate Setup

#### Option A: Self-Signed Certificates (Development/Testing)
```bash
# Generate self-signed certificates
./scripts/generate-ssl-certs.sh

# Add domains to /etc/hosts for testing
echo "127.0.0.1 admin.dotmac.local portal.dotmac.local monitoring.dotmac.local" | sudo tee -a /etc/hosts
```

#### Option B: Let's Encrypt Certificates (Recommended for Production)
```bash
# Install certbot
sudo apt install snapd
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot

# Create SSL directory
mkdir -p ssl/certs

# Generate certificates for your domains
sudo certbot certonly --standalone --preferred-challenges http \
  -d yourdomain.com \
  -d admin.yourdomain.com \
  -d monitoring.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email

# Copy certificates to SSL directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/certs/yourdomain.com.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/certs/yourdomain.com.key
sudo cp /etc/letsencrypt/live/admin.yourdomain.com/fullchain.pem ssl/certs/admin.yourdomain.com.crt
sudo cp /etc/letsencrypt/live/admin.yourdomain.com/privkey.pem ssl/certs/admin.yourdomain.com.key

# Set proper permissions
sudo chown -R dotmac:dotmac ssl/
chmod 600 ssl/certs/*.key
chmod 644 ssl/certs/*.crt

# Setup auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### Option C: Commercial SSL Certificates
```bash
# Create SSL directory
mkdir -p ssl/certs

# Copy your commercial certificates
cp your-domain.crt ssl/certs/yourdomain.com.crt
cp your-domain.key ssl/certs/yourdomain.com.key
cp your-admin-domain.crt ssl/certs/admin.yourdomain.com.crt
cp your-admin-domain.key ssl/certs/admin.yourdomain.com.key

# Set proper permissions
chmod 600 ssl/certs/*.key
chmod 644 ssl/certs/*.crt
```

### Step 5: Update Nginx Configuration

```bash
# Update nginx configuration with your actual domains
sed -i 's/admin.dotmac.local/admin.yourdomain.com/g' nginx/conf.d/dotmac-platform.conf
sed -i 's/portal.dotmac.local/portal.yourdomain.com/g' nginx/conf.d/dotmac-platform.conf
sed -i 's/monitoring.dotmac.local/monitoring.yourdomain.com/g' nginx/conf.d/dotmac-platform.conf
sed -i 's/yourdomain.com/youractualddomain.com/g' nginx/conf.d/dotmac-platform.conf

# Update SSL certificate paths
sed -i 's|/etc/nginx/ssl/admin.dotmac.local|/etc/nginx/ssl/admin.yourdomain.com|g' nginx/conf.d/dotmac-platform.conf
sed -i 's|/etc/nginx/ssl/dotmac.local|/etc/nginx/ssl/yourdomain.com|g' nginx/conf.d/dotmac-platform.conf
```

### Step 6: Deploy the Platform

```bash
# Run security validation
./scripts/security-validation.sh

# Deploy to production
./scripts/deploy-production.sh

# The script will:
# 1. Check prerequisites
# 2. Validate environment configuration
# 3. Create backup (if existing deployment)
# 4. Build Docker images
# 5. Deploy services in correct order
# 6. Run database migrations
# 7. Validate deployment
# 8. Show deployment summary
```

### Step 7: Post-Deployment Configuration

#### Initial Admin User Creation
```bash
# Create first admin user for Management Platform
docker exec -it dotmac-management-platform python -m scripts.create_admin_user \
  --email admin@yourdomain.com \
  --password "SecurePassword123!" \
  --first-name "Admin" \
  --last-name "User"

# Create first admin user for ISP Framework
docker exec -it dotmac-isp-framework python -m scripts.create_admin \
  --email admin@yourdomain.com \
  --password "SecurePassword123!" \
  --tenant-id "default"
```

#### DNS Configuration
```bash
# Configure DNS records (example with your DNS provider)
# A record: yourdomain.com -> YOUR_SERVER_IP
# A record: admin.yourdomain.com -> YOUR_SERVER_IP
# A record: *.yourdomain.com -> YOUR_SERVER_IP (wildcard for tenant subdomains)
# A record: monitoring.yourdomain.com -> YOUR_SERVER_IP
```

## ✅ Verification and Testing

### Step 8: Health Check

```bash
# Run comprehensive health check
./scripts/health-check.sh

# Check individual services
curl -k https://admin.yourdomain.com/health
curl -k https://portal.yourdomain.com/health

# Check monitoring
curl -k https://monitoring.yourdomain.com
```

### Step 9: Smoke Testing

#### Management Platform Testing
```bash
# Test registration endpoint
curl -X POST https://admin.yourdomain.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123!","first_name":"Test","last_name":"User"}'

# Test login endpoint
curl -X POST https://admin.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"SecurePassword123!"}'
```

#### ISP Framework Testing
```bash
# Test health endpoint
curl -k https://portal.yourdomain.com/health

# Test tenant-specific endpoint
curl -k https://tenant1.yourdomain.com/health
```

### Step 10: Performance Testing

```bash
# Install Apache Bench for basic load testing
sudo apt install apache2-utils

# Test Management Platform performance
ab -n 100 -c 10 https://admin.yourdomain.com/health

# Test ISP Framework performance  
ab -n 100 -c 10 https://portal.yourdomain.com/health

# Monitor resource usage during test
htop
iostat -x 1
```

## 📊 Monitoring and Logging

### Built-in Monitoring

The platform includes SignOz for observability:
- **Metrics**: Application and infrastructure metrics
- **Traces**: Distributed tracing across services
- **Logs**: Centralized logging with search
- **Alerts**: Configurable alerting rules

Access monitoring at: https://monitoring.yourdomain.com
- Username: `admin`
- Password: `dotmac123` (change in nginx/.htpasswd)

### Log Files Location

```bash
# Application logs
/var/log/dotmac/deployment.log    # Deployment logs
/var/log/dotmac/health-check.log  # Health check logs

# Container logs
docker-compose -f docker-compose.production.yml logs -f [service_name]

# System logs
/var/log/nginx/                   # Nginx access and error logs
/var/log/postgresql/              # PostgreSQL logs
/var/log/redis/                   # Redis logs
```

### Setting Up External Monitoring

#### Prometheus + Grafana (Optional)
```bash
# Add external monitoring stack
curl -LO https://raw.githubusercontent.com/prometheus/prometheus/main/documentation/examples/prometheus.yml

# Configure monitoring endpoints
# Add to your monitoring system:
# - http://your-server:8889/metrics (SignOz collector)
# - http://your-server:8000/metrics (Management Platform)
# - http://your-server:8001/metrics (ISP Framework)
```

## 🔒 Security Hardening

### System Security

```bash
# Enable firewall
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https

# Disable root SSH login
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Setup fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Application Security

```bash
# Verify security settings
./scripts/security-validation.sh

# Check for secrets in environment
grep -r "REPLACE_WITH" .env.production && echo "❌ Unconfigured secrets found" || echo "✅ All secrets configured"

# Verify SSL configuration
openssl s_client -connect admin.yourdomain.com:443 -servername admin.yourdomain.com < /dev/null
```

## 💾 Backup and Recovery

### Automated Backup Setup

```bash
# Create backup script
cat > /opt/dotmac/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/dotmac/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Database backup
docker exec dotmac-postgres-shared pg_dumpall -U $POSTGRES_USER | gzip > "$BACKUP_DIR/database-backup.sql.gz"

# Volume backups
docker run --rm -v dotmac-postgres-shared-data-prod:/data -v "$BACKUP_DIR:/backup" alpine tar czf /backup/postgres-data.tar.gz -C /data .
docker run --rm -v dotmac-redis-shared-data-prod:/data -v "$BACKUP_DIR:/backup" alpine tar czf /backup/redis-data.tar.gz -C /data .

# Configuration backup
cp .env.production "$BACKUP_DIR/"
tar czf "$BACKUP_DIR/ssl-certs.tar.gz" ssl/

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x /opt/dotmac/scripts/backup.sh

# Setup cron job for daily backups
crontab -e
# Add: 0 2 * * * /opt/dotmac/scripts/backup.sh >> /var/log/dotmac/backup.log 2>&1
```

### Recovery Procedure

```bash
# Stop services
docker-compose -f docker-compose.production.yml down

# Restore database
zcat /backup/dotmac/BACKUP_DATE/database-backup.sql.gz | docker exec -i dotmac-postgres-shared psql -U $POSTGRES_USER

# Restore volumes
docker run --rm -v dotmac-postgres-shared-data-prod:/data -v "/backup/dotmac/BACKUP_DATE:/backup" alpine tar xzf /backup/postgres-data.tar.gz -C /data

# Restart services
docker-compose -f docker-compose.production.yml up -d

# Verify recovery
./scripts/health-check.sh
```

## 🔄 Updates and Maintenance

### Regular Updates

```bash
# Update the platform (with backup)
./scripts/deploy-production.sh --update

# Update just the images
docker-compose -f docker-compose.production.yml pull
docker-compose -f docker-compose.production.yml up -d

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### Maintenance Windows

```bash
# Schedule maintenance
# 1. Notify users
# 2. Create backup
./scripts/backup.sh

# 3. Apply updates
./scripts/deploy-production.sh --update

# 4. Run health checks
./scripts/health-check.sh

# 5. Monitor for issues
docker-compose -f docker-compose.production.yml logs -f
```

## 🆘 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check service logs
docker-compose -f docker-compose.production.yml logs [service_name]

# Check container status
docker ps -a

# Check resource usage
docker stats

# Check disk space
df -h
docker system df
```

#### SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in ssl/certs/yourdomain.com.crt -text -noout

# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Regenerate certificates if needed
./scripts/generate-ssl-certs.sh
```

#### Database Connection Issues
```bash
# Check PostgreSQL logs
docker logs dotmac-postgres-shared

# Test database connection
docker exec dotmac-postgres-shared psql -U $POSTGRES_USER -d dotmac_isp -c "SELECT version();"

# Check database disk usage
docker exec dotmac-postgres-shared du -sh /var/lib/postgresql/data
```

#### Performance Issues
```bash
# Check resource usage
htop
iotop
docker stats

# Check network connectivity
netstat -tuln
ss -tuln

# Analyze slow queries
docker exec dotmac-postgres-shared psql -U $POSTGRES_USER -d dotmac_isp -c "SELECT query, total_time, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

### Getting Help

- **Documentation**: Check the project documentation
- **Logs**: Always include relevant log files when reporting issues
- **Health Check**: Run `./scripts/health-check.sh` before reporting issues
- **Community**: Join the community support channels
- **Enterprise Support**: Contact support for enterprise customers

## 📞 Production Support

### Monitoring Checklist
- [ ] All services running and healthy
- [ ] SSL certificates valid (>30 days until expiry)  
- [ ] Database backups completing successfully
- [ ] Disk usage <80%
- [ ] Memory usage <80%
- [ ] No critical errors in logs
- [ ] External service integrations working
- [ ] Health checks passing

### Emergency Contacts
- **System Administrator**: [Your Contact Info]
- **Database Administrator**: [Your Contact Info]  
- **Security Team**: [Your Contact Info]
- **On-Call Engineer**: [Your Contact Info]

---

## 🎉 Deployment Complete!

Your DotMac Platform is now ready for production use. The deployment includes:

✅ **Secure multi-tenant architecture**  
✅ **SSL/TLS encryption**  
✅ **Comprehensive monitoring**  
✅ **Automated backups**  
✅ **Health monitoring**  
✅ **Production-ready configuration**  
✅ **Scalable infrastructure**  

**Next Steps:**
1. Configure your first ISP tenant
2. Set up external integrations (Stripe, email, etc.)
3. Create user accounts and permissions
4. Configure monitoring alerts
5. Plan regular maintenance windows

**Useful URLs:**
- Management Platform: https://admin.yourdomain.com
- ISP Framework: https://portal.yourdomain.com  
- Monitoring Dashboard: https://monitoring.yourdomain.com

---

**Document Version**: 1.0  
**Last Updated**: August 23, 2025  
**Next Review**: September 23, 2025  
**Contact**: engineering@dotmac.app