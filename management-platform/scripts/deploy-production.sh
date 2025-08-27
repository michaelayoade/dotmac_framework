#!/bin/bash
# =============================================================================
# DotMac Management Platform - Production Deployment Script
# =============================================================================
# Enterprise-grade deployment automation with comprehensive validation
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/dotmac-deployment.log"
DEPLOYMENT_ID="deploy-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

# =============================================================================
# Pre-deployment Validation
# =============================================================================

validate_prerequisites() {
    log "🔍 Phase 1.1: Validating deployment prerequisites..."
    
    # Check if running as root/sudo
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root for security reasons"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "curl" "jq" "openssl" "envsubst")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    log_success "All required commands are available"
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        exit 1
    fi
    log_success "Docker daemon is accessible"
    
    # Check Docker Compose version
    local compose_version=$(docker-compose --version | grep -oP '\\d+\\.\\d+\\.\\d+' | head -1)
    if [[ $(echo "$compose_version" | cut -d. -f1) -lt 2 ]]; then
        log_warn "Docker Compose version is $compose_version. Version 2.0+ recommended"
    fi
    
    # Check available disk space (minimum 20GB)
    local available_space=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
    local min_space=$((20 * 1024 * 1024))  # 20GB in KB
    if [[ $available_space -lt $min_space ]]; then
        log_error "Insufficient disk space. Need at least 20GB, have $(($available_space / 1024 / 1024))GB"
        exit 1
    fi
    log_success "Sufficient disk space available"
    
    # Check system resources
    local total_memory=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_memory -lt 8192 ]]; then
        log_warn "System has ${total_memory}MB RAM. 8GB+ recommended for production"
    fi
    
    log_success "Prerequisites validation completed"
}

validate_environment_config() {
    log "🔍 Phase 1.2: Validating environment configuration..."
    
    local env_file="$PROJECT_ROOT/.env.production"
    
    # Check if production environment file exists
    if [[ ! -f "$env_file" ]]; then
        log_error "Production environment file not found: $env_file"
        log_error "Copy env.production.template to .env.production and configure it"
        exit 1
    fi
    
    # Source the environment file
    source "$env_file"
    
    # Validate required environment variables
    local required_vars=(
        "ENVIRONMENT"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
        "REDIS_PASSWORD"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Validate secret key security
    if [[ ${#SECRET_KEY} -lt 64 ]]; then
        log_error "SECRET_KEY must be at least 64 characters long"
        exit 1
    fi
    
    if [[ ${#JWT_SECRET_KEY} -lt 64 ]]; then
        log_error "JWT_SECRET_KEY must be at least 64 characters long"
        exit 1
    fi
    
    # Check for insecure patterns
    local insecure_patterns=("password" "secret" "change" "replace" "example")
    for pattern in "${insecure_patterns[@]}"; do
        if echo "$SECRET_KEY" | grep -qi "$pattern"; then
            log_error "SECRET_KEY contains insecure pattern: $pattern"
            exit 1
        fi
    done
    
    # Validate environment is set to production
    if [[ "$ENVIRONMENT" != "production" ]]; then
        log_error "ENVIRONMENT must be set to 'production'"
        exit 1
    fi
    
    log_success "Environment configuration is valid"
}

validate_security_configuration() {
    log "🔍 Phase 1.3: Validating security configuration..."
    
    # Check SSL certificate configuration
    local ssl_cert_path="${SSL_CERT_PATH:-/etc/nginx/ssl/fullchain.pem}"
    local ssl_key_path="${SSL_KEY_PATH:-/etc/nginx/ssl/privkey.pem}"
    
    if [[ "$SSL_ENABLED" == "true" ]]; then
        if [[ ! -f "$ssl_cert_path" ]] || [[ ! -f "$ssl_key_path" ]]; then
            log_warn "SSL enabled but certificates not found. Will generate self-signed certificates"
        else
            # Validate certificate expiration
            local cert_expiry=$(openssl x509 -enddate -noout -in "$ssl_cert_path" | cut -d= -f2)
            local cert_expiry_timestamp=$(date -d "$cert_expiry" +%s)
            local current_timestamp=$(date +%s)
            local days_until_expiry=$(( (cert_expiry_timestamp - current_timestamp) / 86400 ))
            
            if [[ $days_until_expiry -lt 30 ]]; then
                log_warn "SSL certificate expires in $days_until_expiry days"
            else
                log_success "SSL certificate is valid for $days_until_expiry days"
            fi
        fi
    fi
    
    # Validate CORS origins
    if [[ -n "${CORS_ORIGINS:-}" ]]; then
        if echo "$CORS_ORIGINS" | grep -q "localhost"; then
            log_error "CORS_ORIGINS contains localhost in production"
            exit 1
        fi
    fi
    
    log_success "Security configuration validated"
}

# =============================================================================
# Infrastructure Setup
# =============================================================================

setup_directories() {
    log "🏗️ Phase 1.4: Setting up directory structure..."
    
    local directories=(
        "/var/log/dotmac"
        "/opt/dotmac/config"
        "/opt/dotmac/ssl"
        "/opt/dotmac/backups"
        "/opt/dotmac/uploads"
        "$PROJECT_ROOT/deployment/production/nginx"
        "$PROJECT_ROOT/deployment/production/postgres"
        "$PROJECT_ROOT/deployment/production/redis"
        "$PROJECT_ROOT/deployment/production/monitoring"
        "$PROJECT_ROOT/deployment/production/backup"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log_info "Creating directory: $dir"
            sudo mkdir -p "$dir"
            sudo chown -R $(whoami):$(whoami) "$dir" 2>/dev/null || true
        fi
    done
    
    log_success "Directory structure created"
}

generate_ssl_certificates() {
    log "🔒 Phase 1.5: Setting up SSL certificates..."
    
    local ssl_dir="$PROJECT_ROOT/deployment/production/ssl"
    local cert_file="$ssl_dir/fullchain.pem"
    local key_file="$ssl_dir/privkey.pem"
    
    if [[ ! -f "$cert_file" ]] || [[ ! -f "$key_file" ]]; then
        log_info "Generating self-signed SSL certificate for development/testing"
        
        # Generate private key
        openssl genrsa -out "$key_file" 2048
        
        # Generate certificate
        openssl req -new -x509 -key "$key_file" -out "$cert_file" -days 365 -subj "/CN=${MAIN_DOMAIN:-localhost}"
        
        # Set proper permissions
        chmod 600 "$key_file"
        chmod 644 "$cert_file"
        
        log_warn "Using self-signed certificate. Replace with CA-signed certificate for production"
    else
        log_success "SSL certificates found"
    fi
}

create_nginx_config() {
    log "🌐 Phase 1.6: Creating Nginx configuration..."
    
    local nginx_config="$PROJECT_ROOT/deployment/production/nginx/nginx.conf"
    
    cat > "$nginx_config" << 'EOF'
# DotMac Management Platform - Production Nginx Configuration
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    
    # Logging Configuration
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for" '
                   'rt=$request_time uct="$upstream_connect_time" '
                   'uht="$upstream_header_time" urt="$upstream_response_time"';
    
    access_log /var/log/nginx/access.log main;
    
    # Performance Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # Upstream Servers
    upstream mgmt_api {
        least_conn;
        server mgmt-api:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
    
    upstream frontend_apps {
        least_conn;
        server frontend-apps:3000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }
    
    # HTTP to HTTPS Redirect
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }
    
    # Main HTTPS Server
    server {
        listen 443 ssl http2;
        server_name ${MAIN_DOMAIN} ${API_DOMAIN} ${ADMIN_DOMAIN};
        
        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:50m;
        ssl_session_timeout 1d;
        ssl_session_tickets off;
        
        # HSTS
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        
        # API Routes
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://mgmt_api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # Timeouts
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
        
        # Authentication Routes (Rate Limited)
        location ~ ^/api/v1/auth/(login|register) {
            limit_req zone=login burst=5 nodelay;
            
            proxy_pass http://mgmt_api;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health Check
        location /health {
            proxy_pass http://mgmt_api/health;
            access_log off;
        }
        
        # Frontend Applications
        location / {
            proxy_pass http://frontend_apps;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
        
        # Static Assets Caching
        location ~* \\.(css|js|jpg|jpeg|png|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
            add_header X-Content-Type-Options nosniff;
        }
    }
}
EOF
    
    log_success "Nginx configuration created"
}

# =============================================================================
# Database Setup
# =============================================================================

setup_database_config() {
    log "🗄️ Phase 1.7: Setting up database configuration..."
    
    local postgres_dir="$PROJECT_ROOT/deployment/production/postgres"
    
    # PostgreSQL Configuration
    cat > "$postgres_dir/postgresql.conf" << 'EOF'
# DotMac Management Platform - PostgreSQL Production Configuration

# Connection Settings
listen_addresses = '*'
port = 5432
max_connections = 200
superuser_reserved_connections = 3

# Memory Settings
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200

# Checkpoints and WAL
checkpoint_timeout = 10min
max_wal_size = 1GB
min_wal_size = 80MB
wal_level = replica
max_wal_senders = 10
wal_keep_segments = 32

# Query Planner
random_page_cost = 1.1
seq_page_cost = 1
cpu_tuple_cost = 0.01
cpu_index_tuple_cost = 0.005
cpu_operator_cost = 0.0025

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_error_verbosity = default

# Security
ssl = on
password_encryption = scram-sha-256

# Autovacuum
autovacuum = on
log_autovacuum_min_duration = 0
autovacuum_max_workers = 3
autovacuum_naptime = 20s
autovacuum_vacuum_threshold = 50
autovacuum_analyze_threshold = 50
autovacuum_vacuum_scale_factor = 0.02
autovacuum_analyze_scale_factor = 0.01
autovacuum_freeze_max_age = 200000000
autovacuum_multixact_freeze_max_age = 400000000
autovacuum_vacuum_cost_delay = 2ms
autovacuum_vacuum_cost_limit = 400

# Lock Management
deadlock_timeout = 1s
max_locks_per_transaction = 64
max_pred_locks_per_transaction = 64
EOF
    
    # pg_hba.conf for authentication
    cat > "$postgres_dir/pg_hba.conf" << 'EOF'
# DotMac Management Platform - PostgreSQL Authentication Configuration

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            scram-sha-256
# IPv6 local connections:
host    all             all             ::1/128                 scram-sha-256
# Allow Docker network connections
host    all             all             172.0.0.0/8             scram-sha-256
# Allow replication connections
host    replication     all             172.0.0.0/8             scram-sha-256
EOF
    
    # Database initialization script
    cat > "$postgres_dir/init-databases.sql" << 'EOF'
-- DotMac Management Platform - Database Initialization Script

-- Create additional databases for multi-tenant architecture
SELECT 'CREATE DATABASE tenants' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tenants');
SELECT 'CREATE DATABASE billing' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'billing');
SELECT 'CREATE DATABASE analytics' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'analytics');
SELECT 'CREATE DATABASE support' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'support');
SELECT 'CREATE DATABASE audit' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'audit');

-- Create read-only user for monitoring
CREATE USER IF NOT EXISTS dotmac_monitor WITH PASSWORD 'monitor_password';
GRANT CONNECT ON DATABASE dotmac_production TO dotmac_monitor;
GRANT USAGE ON SCHEMA public TO dotmac_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dotmac_monitor;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dotmac_monitor;

-- Create backup user
CREATE USER IF NOT EXISTS dotmac_backup WITH REPLICATION PASSWORD 'backup_password';
EOF
    
    log_success "Database configuration files created"
}

# =============================================================================
# Deployment Execution
# =============================================================================

build_images() {
    log "🏗️ Phase 1.8: Building Docker images..."
    
    cd "$PROJECT_ROOT"
    
    # Build production images
    log_info "Building management platform image..."
    docker build -f Dockerfile --target production -t dotmac/management-platform:${IMAGE_TAG:-latest} .
    
    log_info "Building frontend applications image..."
    if [[ -f "../frontend/Dockerfile.production" ]]; then
        docker build -f ../frontend/Dockerfile.production -t dotmac/frontend-apps:${IMAGE_TAG:-latest} ../frontend/
    else
        log_warn "Frontend Dockerfile.production not found, skipping frontend build"
    fi
    
    log_success "Docker images built successfully"
}

deploy_infrastructure() {
    log "🚀 Phase 1.9: Deploying infrastructure services..."
    
    cd "$PROJECT_ROOT"
    
    # Create networks first
    docker network create --driver bridge dotmac-frontend || true
    docker network create --driver bridge dotmac-backend || true
    docker network create --driver bridge dotmac-monitoring || true
    
    # Deploy core infrastructure services first
    log_info "Starting core infrastructure services..."
    docker-compose -f docker-compose.production.yml up -d postgres-primary redis-master openbao
    
    # Wait for services to be ready
    log_info "Waiting for database to be ready..."
    timeout 60 bash -c 'until docker-compose -f docker-compose.production.yml exec postgres-primary pg_isready -U $POSTGRES_USER; do sleep 2; done'
    
    log_info "Waiting for Redis to be ready..."
    timeout 30 bash -c 'until docker-compose -f docker-compose.production.yml exec redis-master redis-cli ping; do sleep 2; done'
    
    log_success "Core infrastructure services are running"
    
    # Deploy application services
    log_info "Starting application services..."
    docker-compose -f docker-compose.production.yml up -d mgmt-api celery-worker celery-beat
    
    # Wait for API to be ready
    log_info "Waiting for API to be ready..."
    timeout 120 bash -c 'until curl -f http://localhost:8000/health; do sleep 5; done'
    
    log_success "Application services are running"
    
    # Deploy frontend and reverse proxy
    log_info "Starting frontend and reverse proxy..."
    docker-compose -f docker-compose.production.yml up -d frontend-apps nginx
    
    log_success "All services deployed successfully"
}

run_database_migrations() {
    log "📊 Phase 1.10: Running database migrations..."
    
    # Run Alembic migrations
    docker-compose -f docker-compose.production.yml exec mgmt-api alembic upgrade head
    
    log_success "Database migrations completed"
}

# =============================================================================
# Post-deployment Validation
# =============================================================================

validate_deployment() {
    log "✅ Phase 1.11: Validating deployment..."
    
    local services=("postgres-primary" "redis-master" "mgmt-api" "celery-worker" "nginx")
    
    for service in "${services[@]}"; do
        if docker-compose -f docker-compose.production.yml ps "$service" | grep -q "Up"; then
            log_success "Service $service is running"
        else
            log_error "Service $service is not running"
            exit 1
        fi
    done
    
    # Test API endpoints
    log_info "Testing API health endpoint..."
    local api_health=$(curl -s http://localhost/health | jq -r '.status' 2>/dev/null || echo "failed")
    if [[ "$api_health" == "healthy" ]]; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        exit 1
    fi
    
    # Test database connectivity
    log_info "Testing database connectivity..."
    if docker-compose -f docker-compose.production.yml exec postgres-primary psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" &>/dev/null; then
        log_success "Database connectivity confirmed"
    else
        log_error "Database connectivity failed"
        exit 1
    fi
    
    # Test Redis connectivity
    log_info "Testing Redis connectivity..."
    if docker-compose -f docker-compose.production.yml exec redis-master redis-cli ping | grep -q "PONG"; then
        log_success "Redis connectivity confirmed"
    else
        log_error "Redis connectivity failed"
        exit 1
    fi
    
    log_success "Deployment validation completed successfully"
}

generate_deployment_report() {
    log "📋 Phase 1.12: Generating deployment report..."
    
    local report_file="/tmp/dotmac-deployment-report-$DEPLOYMENT_ID.json"
    
    cat > "$report_file" << EOF
{
  "deployment_id": "$DEPLOYMENT_ID",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "environment": "$ENVIRONMENT",
  "status": "success",
  "services": {
    "postgres": "$(docker-compose -f docker-compose.production.yml ps postgres-primary --format json | jq -r '.State')",
    "redis": "$(docker-compose -f docker-compose.production.yml ps redis-master --format json | jq -r '.State')",
    "api": "$(docker-compose -f docker-compose.production.yml ps mgmt-api --format json | jq -r '.State')",
    "worker": "$(docker-compose -f docker-compose.production.yml ps celery-worker --format json | jq -r '.State')",
    "nginx": "$(docker-compose -f docker-compose.production.yml ps nginx --format json | jq -r '.State')"
  },
  "endpoints": {
    "health": "http://localhost/health",
    "api": "http://localhost/api/v1",
    "admin": "http://localhost/admin",
    "monitoring": "http://localhost:3001"
  },
  "next_steps": [
    "Configure monitoring and alerting",
    "Set up backup automation", 
    "Configure SSL certificates",
    "Run security hardening",
    "Set up disaster recovery"
  ]
}
EOF
    
    log_success "Deployment report generated: $report_file"
    cat "$report_file"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    log "🚀 Starting DotMac Management Platform Production Deployment"
    log "Deployment ID: $DEPLOYMENT_ID"
    log "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo ""
    
    # Phase 1: Infrastructure Foundation
    validate_prerequisites
    validate_environment_config
    validate_security_configuration
    setup_directories
    generate_ssl_certificates
    create_nginx_config
    setup_database_config
    build_images
    deploy_infrastructure
    run_database_migrations
    validate_deployment
    generate_deployment_report
    
    echo ""
    log_success "🎉 PHASE 1 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    log_success "Infrastructure foundation is ready for Phase 2 (Monitoring & Observability)"
    echo ""
    log_info "Next steps:"
    log_info "1. Run Phase 2: ./scripts/setup-monitoring.sh"
    log_info "2. Configure backup automation"
    log_info "3. Set up SSL certificates from CA"
    log_info "4. Run security hardening"
    echo ""
    log_info "Access points:"
    log_info "• API: http://localhost/api/v1"
    log_info "• Health: http://localhost/health"
    log_info "• Admin: http://localhost/admin"
    echo ""
}

# Trap signals for cleanup
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Execute main function
main "$@"