#!/bin/bash
# DotMac ISP Framework - Production Setup Script
# This script configures the system for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOTMAC_USER="dotmac"
DOTMAC_HOME="/opt/dotmac-isp"
LOG_DIR="/var/log/dotmac-isp"
SERVICE_NAME="dotmac-isp"

echo -e "${BLUE}🚀 DotMac ISP Framework - Production Setup${NC}"
echo "======================================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Create dedicated user for the application
create_user() {
    echo "Creating application user..."
    if ! id "$DOTMAC_USER" &>/dev/null; then
        useradd --system --home-dir "$DOTMAC_HOME" --shell /bin/bash --create-home "$DOTMAC_USER"
        print_status "Created user: $DOTMAC_USER"
    else
        print_warning "User $DOTMAC_USER already exists"
    fi
}

# Create directory structure
create_directories() {
    echo "Creating directory structure..."
    
    directories=(
        "$DOTMAC_HOME"
        "$DOTMAC_HOME/app"
        "$DOTMAC_HOME/config"
        "$DOTMAC_HOME/secrets"
        "$DOTMAC_HOME/uploads"
        "$DOTMAC_HOME/backups"
        "$LOG_DIR"
        "/etc/dotmac-isp"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chown "$DOTMAC_USER:$DOTMAC_USER" "$dir"
        print_status "Created directory: $dir"
    done
    
    # Set restrictive permissions on secrets directory
    chmod 700 "$DOTMAC_HOME/secrets"
}

# Install system dependencies
install_dependencies() {
    echo "Installing system dependencies..."
    
    # Update package list
    apt-get update
    
    # Install required packages
    packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "postgresql-client"
        "redis-tools"
        "nginx"
        "supervisor"
        "certbot"
        "python3-certbot-nginx"
        "fail2ban"
        "ufw"
        "htop"
        "curl"
        "wget"
        "git"
    )
    
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            apt-get install -y "$package"
            print_status "Installed: $package"
        else
            print_warning "$package already installed"
        fi
    done
}

# Setup Python virtual environment
setup_python_env() {
    echo "Setting up Python virtual environment..."
    
    sudo -u "$DOTMAC_USER" python3 -m venv "$DOTMAC_HOME/venv"
    
    # Activate venv and install requirements
    sudo -u "$DOTMAC_USER" bash -c "
        source $DOTMAC_HOME/venv/bin/activate
        pip install --upgrade pip
        pip install wheel setuptools
    "
    
    print_status "Python virtual environment created"
}

# Configure firewall
configure_firewall() {
    echo "Configuring firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful!)
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow application port (if different from 80/443)
    ufw allow 8000/tcp
    
    # Enable firewall
    ufw --force enable
    
    print_status "Firewall configured"
}

# Configure Fail2Ban
configure_fail2ban() {
    echo "Configuring Fail2Ban..."
    
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
# Ban time: 1 hour
bantime = 3600
# Find time: 10 minutes  
findtime = 600
# Max retries: 5
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s

[nginx-http-auth]
enabled = true
port = http,https
logpath = %(nginx_error_log)s

[nginx-limit-req]
enabled = true
port = http,https
logpath = %(nginx_error_log)s
maxretry = 10

[dotmac-isp]
enabled = true
port = 8000
logpath = $LOG_DIR/app.log
maxretry = 5
bantime = 1800
EOF

    systemctl enable fail2ban
    systemctl restart fail2ban
    
    print_status "Fail2Ban configured"
}

# Generate SSL certificate
setup_ssl() {
    echo "Setting up SSL certificate..."
    
    read -p "Enter your domain name (e.g., api.yourdomain.com): " DOMAIN
    
    if [[ -z "$DOMAIN" ]]; then
        print_warning "No domain provided, skipping SSL setup"
        return
    fi
    
    # Get certificate
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"
    
    print_status "SSL certificate configured for $DOMAIN"
}

# Configure Nginx
configure_nginx() {
    echo "Configuring Nginx..."
    
    cat > /etc/nginx/sites-available/dotmac-isp << 'EOF'
# DotMac ISP Framework - Nginx Configuration

upstream dotmac_app {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;

server {
    listen 80;
    server_name _;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Hide Nginx version
    server_tokens off;
    
    # Client upload limit
    client_max_body_size 50M;
    
    # Static files
    location /static/ {
        alias /opt/dotmac-isp/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/dotmac-isp/uploads/;
        expires 1d;
    }
    
    # Health check (no rate limiting)
    location /health {
        proxy_pass http://dotmac_app;
        access_log off;
    }
    
    # Authentication endpoints (stricter rate limiting)
    location ~ ^/(auth|login|register|reset-password) {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://dotmac_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API endpoints (rate limited)
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://dotmac_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # All other requests
    location / {
        proxy_pass http://dotmac_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/dotmac-isp /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    nginx -t
    
    systemctl enable nginx
    systemctl restart nginx
    
    print_status "Nginx configured"
}

# Configure Supervisor
configure_supervisor() {
    echo "Configuring Supervisor..."
    
    cat > /etc/supervisor/conf.d/dotmac-isp.conf << EOF
[program:dotmac-isp-api]
command=$DOTMAC_HOME/venv/bin/python -m uvicorn dotmac_isp.app:app --host 0.0.0.0 --port 8000 --workers 4
directory=$DOTMAC_HOME/app
user=$DOTMAC_USER
group=$DOTMAC_USER
autostart=true
autorestart=true
stdout_logfile=$LOG_DIR/api.log
stderr_logfile=$LOG_DIR/api-error.log
stdout_logfile_maxbytes=50MB
stderr_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile_backups=10
environment=PYTHONPATH="$DOTMAC_HOME/app/src"

[program:dotmac-isp-worker]
command=$DOTMAC_HOME/venv/bin/python -m celery -A dotmac_isp.celery worker --loglevel=info --concurrency=4
directory=$DOTMAC_HOME/app
user=$DOTMAC_USER
group=$DOTMAC_USER
autostart=true
autorestart=true
stdout_logfile=$LOG_DIR/worker.log
stderr_logfile=$LOG_DIR/worker-error.log
stdout_logfile_maxbytes=50MB
stderr_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile_backups=10
environment=PYTHONPATH="$DOTMAC_HOME/app/src"

[program:dotmac-isp-scheduler]
command=$DOTMAC_HOME/venv/bin/python -m celery -A dotmac_isp.celery beat --loglevel=info
directory=$DOTMAC_HOME/app
user=$DOTMAC_USER
group=$DOTMAC_USER
autostart=true
autorestart=true
stdout_logfile=$LOG_DIR/scheduler.log
stderr_logfile=$LOG_DIR/scheduler-error.log
stdout_logfile_maxbytes=50MB
stderr_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile_backups=10
environment=PYTHONPATH="$DOTMAC_HOME/app/src"

[group:dotmac-isp]
programs=dotmac-isp-api,dotmac-isp-worker,dotmac-isp-scheduler
priority=999
EOF

    systemctl enable supervisor
    systemctl restart supervisor
    
    print_status "Supervisor configured"
}

# Setup log rotation
configure_logrotate() {
    echo "Configuring log rotation..."
    
    cat > /etc/logrotate.d/dotmac-isp << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
    su $DOTMAC_USER $DOTMAC_USER
}
EOF

    print_status "Log rotation configured"
}

# Setup monitoring
setup_monitoring() {
    echo "Setting up basic monitoring..."
    
    # Create monitoring script
    cat > /usr/local/bin/dotmac-health-check << 'EOF'
#!/bin/bash
# Health check script for DotMac ISP Framework

# Check API health
if ! curl -f -s http://localhost:8000/health > /dev/null; then
    echo "$(date): API health check failed" >> /var/log/dotmac-isp/health.log
    # Restart services if needed
    supervisorctl restart dotmac-isp:*
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "$(date): High disk usage: ${DISK_USAGE}%" >> /var/log/dotmac-isp/health.log
fi

# Check memory usage
MEM_USAGE=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
if (( $(echo "$MEM_USAGE > 90" | bc -l) )); then
    echo "$(date): High memory usage: ${MEM_USAGE}%" >> /var/log/dotmac-isp/health.log
fi
EOF

    chmod +x /usr/local/bin/dotmac-health-check
    
    # Add to crontab
    echo "*/5 * * * * /usr/local/bin/dotmac-health-check" | crontab -u root -
    
    print_status "Monitoring configured"
}

# Main setup function
main() {
    echo "Starting production setup..."
    
    create_user
    create_directories
    install_dependencies
    setup_python_env
    configure_firewall
    configure_fail2ban
    configure_nginx
    configure_supervisor
    configure_logrotate
    setup_monitoring
    
    echo ""
    echo -e "${GREEN}🎉 Production setup completed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Copy your application code to $DOTMAC_HOME/app/"
    echo "2. Install Python dependencies in the virtual environment"
    echo "3. Copy .env.production to $DOTMAC_HOME/config/.env"
    echo "4. Configure secrets: $DOTMAC_HOME/venv/bin/python -c 'from dotmac_isp.shared.secrets import setup_production_secrets; setup_production_secrets()'"
    echo "5. Run database migrations"
    echo "6. Start services: supervisorctl start dotmac-isp:*"
    echo "7. Setup SSL certificate if not done already"
    echo ""
    echo -e "${YELLOW}⚠️  Remember to:${NC}"
    echo "- Update .env.production with your actual configuration"
    echo "- Set up database and Redis servers"
    echo "- Configure DNS to point to this server"
    echo "- Set up database backups"
    echo "- Configure monitoring and alerting"
}

# Run main setup
main "$@"