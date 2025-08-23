#!/bin/bash
# User Data Script for DotMac ISP Instance Deployment
# This script runs on first boot to set up the DotMac platform

set -e
set -u

# Variables from OpenTofu template
TENANT_ID="${tenant_id}"
ENVIRONMENT="${environment}"
OPENBAO_ADDR="${openbao_addr}"
OPENBAO_TOKEN="${openbao_token}"
SIGNOZ_ENDPOINT="${signoz_endpoint}"
MANAGEMENT_API_URL="${management_api_url}"

# Logging
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "Starting DotMac ISP instance setup for tenant: $TENANT_ID"
echo "Environment: $ENVIRONMENT"
echo "Timestamp: $(date)"

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install essential packages
echo "Installing essential packages..."
apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    jq \
    htop \
    vim \
    nginx \
    postgresql-client \
    redis-tools \
    python3 \
    python3-pip \
    python3-venv \
    docker.io \
    docker-compose-plugin \
    awscli \
    fail2ban \
    ufw \
    certbot \
    python3-certbot-nginx

# Start and enable Docker
echo "Setting up Docker..."
systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu

# Install Docker Compose
echo "Installing Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
echo "Creating application directory..."
mkdir -p /opt/dotmac
cd /opt/dotmac

# Download and extract DotMac ISP Framework
echo "Downloading DotMac ISP Framework..."
# This will be replaced with actual download URL
curl -L "${MANAGEMENT_API_URL}/api/v1/tenants/${TENANT_ID}/package" -o dotmac-isp-framework.tar.gz
tar -xzf dotmac-isp-framework.tar.gz
rm dotmac-isp-framework.tar.gz

# Set up environment variables
echo "Setting up environment configuration..."
cat > /opt/dotmac/.env << EOF
# DotMac ISP Framework Configuration
TENANT_ID=$TENANT_ID
ENVIRONMENT=$ENVIRONMENT

# Database Configuration
DATABASE_URL=postgresql://dotmac_user:PLACEHOLDER_DB_PASSWORD@localhost:5432/dotmac_$TENANT_ID

# Redis Configuration  
REDIS_URL=redis://:PLACEHOLDER_REDIS_PASSWORD@localhost:6379/0

# OpenBao Integration
OPENBAO_ADDR=$OPENBAO_ADDR
OPENBAO_TOKEN=$OPENBAO_TOKEN
OPENBAO_MOUNT_POINT=secret/tenants/$TENANT_ID

# SignOz Observability
OTEL_EXPORTER_OTLP_ENDPOINT=$SIGNOZ_ENDPOINT
OTEL_SERVICE_NAME=dotmac-isp-$TENANT_ID
OTEL_SERVICE_VERSION=1.0.0
OTEL_RESOURCE_ATTRIBUTES="tenant.id=$TENANT_ID,deployment.environment=$ENVIRONMENT"

# Application Settings
SECRET_KEY=PLACEHOLDER_SECRET_KEY
JWT_SECRET_KEY=PLACEHOLDER_JWT_SECRET
LOG_LEVEL=info

# Feature Flags
ENABLE_BILLING=true
ENABLE_RESELLER_PORTAL=true
ENABLE_CUSTOMER_PORTAL=true
ENABLE_FIELD_OPS=true

# Management Platform Integration
MGMT_PLATFORM_URL=$MANAGEMENT_API_URL
MGMT_PLATFORM_TOKEN=PLACEHOLDER_MGMT_TOKEN
EOF

# Install OpenBao CLI
echo "Installing OpenBao CLI..."
curl -fsSL https://releases.hashicorp.com/vault/1.15.0/vault_1.15.0_linux_amd64.zip -o vault.zip
unzip vault.zip
mv vault /usr/local/bin/bao
rm vault.zip
chmod +x /usr/local/bin/bao

# Retrieve secrets from OpenBao
echo "Retrieving secrets from OpenBao..."
export VAULT_ADDR=$OPENBAO_ADDR
export VAULT_TOKEN=$OPENBAO_TOKEN

# Function to get secret from OpenBao
get_secret() {
    local path=$1
    local key=$2
    bao kv get -field=$key secret/tenants/$TENANT_ID/$path 2>/dev/null || echo "GENERATE_ME"
}

# Replace placeholders with actual secrets
DB_PASSWORD=$(get_secret "database" "password")
REDIS_PASSWORD=$(get_secret "cache" "password") 
SECRET_KEY=$(get_secret "app" "secret_key")
JWT_SECRET=$(get_secret "app" "jwt_secret")
MGMT_TOKEN=$(get_secret "management" "api_token")

sed -i "s/PLACEHOLDER_DB_PASSWORD/$DB_PASSWORD/g" /opt/dotmac/.env
sed -i "s/PLACEHOLDER_REDIS_PASSWORD/$REDIS_PASSWORD/g" /opt/dotmac/.env
sed -i "s/PLACEHOLDER_SECRET_KEY/$SECRET_KEY/g" /opt/dotmac/.env
sed -i "s/PLACEHOLDER_JWT_SECRET/$JWT_SECRET/g" /opt/dotmac/.env
sed -i "s/PLACEHOLDER_MGMT_TOKEN/$MGMT_TOKEN/g" /opt/dotmac/.env

# Set up PostgreSQL
echo "Setting up PostgreSQL..."
apt-get install -y postgresql postgresql-contrib
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres createdb dotmac_$TENANT_ID
sudo -u postgres psql -c "CREATE USER dotmac_user WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE dotmac_$TENANT_ID TO dotmac_user;"
sudo -u postgres psql -c "ALTER USER dotmac_user CREATEDB;"

# Set up Redis
echo "Setting up Redis..."
apt-get install -y redis-server
sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
systemctl restart redis-server
systemctl enable redis-server

# Set up firewall
echo "Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL from VPC
ufw allow from 10.0.0.0/8 to any port 6379  # Redis from VPC
ufw allow from 10.0.0.0/8 to any port 8000  # API from ALB

# Configure Nginx
echo "Configuring Nginx..."
cat > /etc/nginx/sites-available/dotmac << EOF
server {
    listen 80;
    server_name _;
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Proxy to DotMac application
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/dotmac /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
systemctl enable nginx

# Set up log rotation
echo "Setting up log rotation..."
cat > /etc/logrotate.d/dotmac << EOF
/opt/dotmac/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        systemctl reload nginx
    endscript
}
EOF

# Set up system monitoring
echo "Setting up system monitoring..."
cat > /opt/dotmac/monitor.sh << EOF
#!/bin/bash
# System monitoring script for DotMac instance

# Send heartbeat to management platform
curl -X POST "$MANAGEMENT_API_URL/api/v1/tenants/$TENANT_ID/heartbeat" \
    -H "Authorization: Bearer $MGMT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "status": "healthy",
        "metrics": {
            "cpu_usage": "'$(top -bn1 | grep load | awk '{printf "%.2f", $(NF-2)}')'",
            "memory_usage": "'$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')'",
            "disk_usage": "'$(df / | tail -1 | awk '{printf "%.2f", $5}' | sed 's/%//')'",
            "uptime": "'$(uptime -p)'"
        }
    }' || echo "Failed to send heartbeat"
EOF

chmod +x /opt/dotmac/monitor.sh

# Set up cron job for monitoring
echo "*/5 * * * * /opt/dotmac/monitor.sh" | crontab -u ubuntu -

# Set up DotMac application as systemd service
echo "Setting up DotMac service..."
cat > /etc/systemd/system/dotmac.service << EOF
[Unit]
Description=DotMac ISP Framework
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/dotmac
EnvironmentFile=/opt/dotmac/.env
ExecStart=/opt/dotmac/start.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create start script
cat > /opt/dotmac/start.sh << EOF
#!/bin/bash
cd /opt/dotmac
source .env
exec docker-compose up
EOF

chmod +x /opt/dotmac/start.sh
chown -R ubuntu:ubuntu /opt/dotmac

# Enable and start DotMac service
systemctl daemon-reload
systemctl enable dotmac
systemctl start dotmac

# Final status check
echo "Checking service status..."
systemctl status postgresql --no-pager
systemctl status redis-server --no-pager
systemctl status nginx --no-pager
systemctl status dotmac --no-pager

# Report deployment completion
echo "Reporting deployment completion to management platform..."
curl -X POST "$MANAGEMENT_API_URL/api/v1/tenants/$TENANT_ID/deployment/complete" \
    -H "Authorization: Bearer $MGMT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
        "status": "completed",
        "services": ["postgresql", "redis", "nginx", "dotmac"],
        "endpoints": {
            "web": "http://'$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)'",
            "api": "http://'$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)':8000"
        }
    }'

echo "DotMac ISP instance setup completed successfully for tenant: $TENANT_ID"
echo "Setup completed at: $(date)"