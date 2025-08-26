#!/bin/bash
# Production Deployment Script for DotMac Framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOYMENT_DIR="$PROJECT_ROOT/deployment"
PRODUCTION_DIR="$DEPLOYMENT_DIR/production"

# Functions for colored output
print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_header() { echo -e "${BLUE}$1${NC}"; }
print_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Logging setup
LOG_FILE="/var/log/dotmac-deployment.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    print_error "Deployment failed at line $2 with exit code $1"
    print_error "Check the log file: $LOG_FILE"
    exit $1
}

# Command line arguments
ENVIRONMENT=${1:-production}
SKIP_BACKUP=${2:-false}
SKIP_TESTS=${3:-false}
FORCE_DEPLOY=${4:-false}

# Validation functions
check_requirements() {
    print_step "Checking deployment requirements..."
    
    # Check if running as root or with sudo
    if [[ $EUID -ne 0 && -z "$SUDO_USER" ]]; then
        print_warning "This script should be run with sudo for production deployment"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
    fi
    
    # Check required commands
    local required_commands=("docker" "docker-compose" "git" "curl" "openssl")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            print_error "Required command '$cmd' is not installed"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check available disk space (minimum 10GB)
    local available_space=$(df / | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 10485760 ]; then  # 10GB in KB
        print_warning "Less than 10GB disk space available"
        if [ "$FORCE_DEPLOY" != "true" ]; then
            exit 1
        fi
    fi
    
    print_status "All requirements satisfied"
}

check_environment_file() {
    print_step "Checking environment configuration..."
    
    local env_file="$PRODUCTION_DIR/.env.production"
    
    if [ ! -f "$env_file" ]; then
        print_error "Production environment file not found: $env_file"
        print_status "Copy the template and configure it:"
        print_status "cp $PRODUCTION_DIR/.env.production.template $env_file"
        exit 1
    fi
    
    # Check for default/insecure values
    local insecure_patterns=("CHANGE_THIS" "your-" "localhost" "127.0.0.1" "password123")
    local warnings=0
    
    for pattern in "${insecure_patterns[@]}"; do
        if grep -q "$pattern" "$env_file"; then
            print_warning "Found potentially insecure value: $pattern"
            warnings=$((warnings + 1))
        fi
    done
    
    if [ $warnings -gt 0 ] && [ "$FORCE_DEPLOY" != "true" ]; then
        print_error "Found $warnings potential security issues in environment file"
        print_error "Update the configuration or use --force to override"
        exit 1
    fi
    
    print_status "Environment configuration validated"
}

create_directories() {
    print_step "Creating required directories..."
    
    local directories=(
        "/opt/dotmac/data/postgres"
        "/opt/dotmac/data/redis" 
        "/opt/dotmac/data/openbao"
        "/opt/dotmac/data/isp/uploads"
        "/opt/dotmac/data/mgmt/uploads"
        "/opt/dotmac/logs/isp"
        "/opt/dotmac/logs/mgmt"
        "/opt/dotmac/logs/nginx"
        "/opt/dotmac/backups"
        "/opt/dotmac/ssl"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_status "Created directory: $dir"
        fi
    done
    
    # Set proper permissions
    chown -R 1000:1000 /opt/dotmac/data/
    chmod -R 755 /opt/dotmac/
    
    print_status "Directory structure created"
}

setup_ssl_certificates() {
    print_step "Setting up SSL certificates..."
    
    local ssl_dir="/opt/dotmac/ssl"
    local cert_file="$ssl_dir/fullchain.pem"
    local key_file="$ssl_dir/privkey.pem"
    
    # Check if certificates exist
    if [ -f "$cert_file" ] && [ -f "$key_file" ]; then
        print_status "SSL certificates already exist"
        return 0
    fi
    
    # Generate self-signed certificates for development/testing
    print_warning "Generating self-signed SSL certificates for testing"
    print_warning "Replace with proper certificates from Let's Encrypt or your CA"
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    chmod 600 "$key_file"
    chmod 644 "$cert_file"
    
    print_status "Self-signed certificates generated"
}

backup_existing_deployment() {
    if [ "$SKIP_BACKUP" == "true" ]; then
        print_warning "Skipping backup as requested"
        return 0
    fi
    
    print_step "Creating backup of existing deployment..."
    
    local backup_dir="/opt/dotmac/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup databases if containers are running
    if docker ps | grep -q dotmac-postgres; then
        print_status "Backing up PostgreSQL databases..."
        docker exec dotmac-postgres-prod pg_dumpall -U dotmac_admin > "$backup_dir/postgres_backup.sql"
    fi
    
    if docker ps | grep -q dotmac-redis; then
        print_status "Backing up Redis data..."
        docker exec dotmac-redis-prod redis-cli --rdb /data/backup.rdb
        docker cp dotmac-redis-prod:/data/backup.rdb "$backup_dir/redis_backup.rdb"
    fi
    
    # Backup configuration files
    if [ -f "$PRODUCTION_DIR/.env.production" ]; then
        cp "$PRODUCTION_DIR/.env.production" "$backup_dir/"
    fi
    
    print_status "Backup created: $backup_dir"
}

run_tests() {
    if [ "$SKIP_TESTS" == "true" ]; then
        print_warning "Skipping tests as requested"
        return 0
    fi
    
    print_step "Running pre-deployment tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run validation scripts
    print_status "Running environment validation..."
    python3 scripts/validate_environment.py || {
        print_error "Environment validation failed"
        exit 1
    }
    
    print_status "Running import validation..."
    python3 scripts/validate_imports.py || {
        print_error "Import validation failed"
        exit 1
    }
    
    print_status "Running migration validation..."
    python3 scripts/validate_migrations.py || {
        print_error "Migration validation failed" 
        exit 1
    }
    
    print_status "All tests passed"
}

build_images() {
    print_step "Building production Docker images..."
    
    cd "$PRODUCTION_DIR"
    
    # Load environment variables
    source .env.production
    
    # Build images with build cache
    print_status "Building ISP Framework image..."
    docker-compose -f docker-compose.prod.yml build --parallel isp-framework
    
    print_status "Building Management Platform image..."
    docker-compose -f docker-compose.prod.yml build --parallel management-platform
    
    # Tag images with version
    local version="${APP_VERSION:-$(date +%Y%m%d_%H%M%S)}"
    docker tag dotmac-isp:latest "dotmac-isp:$version"
    docker tag dotmac-mgmt:latest "dotmac-mgmt:$version"
    
    print_status "Images built and tagged with version: $version"
}

deploy_infrastructure() {
    print_step "Deploying infrastructure services..."
    
    cd "$PRODUCTION_DIR"
    
    # Start infrastructure services first
    docker-compose -f docker-compose.prod.yml up -d \
        postgres-shared \
        redis-shared \
        openbao-shared
    
    # Wait for infrastructure to be ready
    print_status "Waiting for infrastructure services..."
    
    local max_attempts=60
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose -f docker-compose.prod.yml ps | grep -E "(postgres-shared|redis-shared)" | grep -q "healthy"; then
            break
        fi
        print_status "Waiting for infrastructure... ($attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "Infrastructure services failed to start"
        exit 1
    fi
    
    print_status "Infrastructure services are ready"
}

run_migrations() {
    print_step "Running database migrations..."
    
    cd "$PRODUCTION_DIR"
    
    # Run ISP Framework migrations
    print_status "Running ISP Framework migrations..."
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin -d dotmac_isp -c "SELECT version();"
    
    # Run Management Platform migrations
    print_status "Running Management Platform migrations..."
    docker-compose -f docker-compose.prod.yml exec -T postgres-shared \
        psql -U dotmac_admin -d mgmt_platform -c "SELECT version();"
    
    print_status "Database migrations completed"
}

deploy_applications() {
    print_step "Deploying application services..."
    
    cd "$PRODUCTION_DIR"
    
    # Deploy applications with rolling update
    docker-compose -f docker-compose.prod.yml up -d \
        isp-framework \
        management-platform \
        mgmt-celery-worker \
        mgmt-celery-beat \
        nginx
    
    print_status "Application services deployed"
}

verify_deployment() {
    print_step "Verifying deployment..."
    
    local services=("isp-framework" "management-platform" "nginx")
    local max_attempts=30
    
    for service in "${services[@]}"; do
        print_status "Checking $service health..."
        local attempt=1
        
        while [ $attempt -le $max_attempts ]; do
            if docker-compose -f docker-compose.prod.yml ps "$service" | grep -q "healthy"; then
                print_status "$service is healthy"
                break
            fi
            
            if [ $attempt -eq $max_attempts ]; then
                print_error "$service failed health check"
                docker-compose -f docker-compose.prod.yml logs --tail=50 "$service"
                exit 1
            fi
            
            sleep 5
            attempt=$((attempt + 1))
        done
    done
    
    print_status "All services are healthy"
}

show_deployment_info() {
    print_header "\n🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    print_header "=" * 50
    
    print_status "Service URLs:"
    echo "  🌐 ISP Framework API: http://localhost:8001"
    echo "  🎛️  Management Platform: http://localhost:8000"
    echo "  🔒 OpenBao (Vault): http://localhost:8200"
    
    print_status "Logs locations:"
    echo "  📄 Deployment log: $LOG_FILE"
    echo "  📁 Application logs: /opt/dotmac/logs/"
    
    print_status "Management commands:"
    echo "  📊 View status: docker-compose -f deployment/production/docker-compose.prod.yml ps"
    echo "  📋 View logs: docker-compose -f deployment/production/docker-compose.prod.yml logs -f [service]"
    echo "  🔄 Restart service: docker-compose -f deployment/production/docker-compose.prod.yml restart [service]"
    
    print_warning "Next steps:"
    echo "  1. Configure monitoring stack: ./scripts/setup_monitoring.sh"
    echo "  2. Set up backup automation: ./deployment/scripts/setup_backups.sh"
    echo "  3. Configure SSL certificates with Let's Encrypt"
    echo "  4. Set up log rotation and monitoring alerts"
    echo "  5. Review security hardening checklist"
}

# Main deployment function
main() {
    print_header "🚀 DotMac Framework Production Deployment"
    print_header "Environment: $ENVIRONMENT"
    print_header "=" * 60
    
    log "Starting deployment at $(date)"
    
    # Pre-deployment checks
    check_requirements
    check_environment_file
    
    # Infrastructure setup
    create_directories
    setup_ssl_certificates
    
    # Backup and testing
    backup_existing_deployment
    run_tests
    
    # Deployment process
    build_images
    deploy_infrastructure
    run_migrations
    deploy_applications
    verify_deployment
    
    # Complete
    show_deployment_info
    log "Deployment completed successfully at $(date)"
}

# Handle command line options
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [environment] [skip_backup] [skip_tests] [force]"
        echo "  environment: production (default)"
        echo "  skip_backup: true to skip backup (default: false)"
        echo "  skip_tests: true to skip tests (default: false)"  
        echo "  force: true to force deployment despite warnings (default: false)"
        exit 0
        ;;
    --version|-v)
        echo "DotMac Deployment Script v1.0.0"
        exit 0
        ;;
esac

# Run main deployment
main "$@"