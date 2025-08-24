#!/bin/bash
# DotMac Platform - Production Deployment Script
# Automates the complete production deployment process

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
BACKUP_DIR="/backup/dotmac"
LOG_FILE="/var/log/dotmac/deployment.log"

echo -e "${BLUE}🚀 DotMac Platform - Production Deployment${NC}"
echo "=============================================="
echo ""

# Function to log messages
log_message() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    log_message "${BLUE}📋 Checking prerequisites...${NC}"
    
    # Check Docker and Docker Compose
    if ! command -v docker &> /dev/null; then
        log_message "${RED}❌ Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        log_message "${RED}❌ Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check if running as root or with Docker permissions
    if ! docker info &> /dev/null; then
        log_message "${RED}❌ Cannot connect to Docker daemon${NC}"
        exit 1
    fi
    
    # Check environment file
    if [[ ! -f "$PROJECT_ROOT/$ENV_FILE" ]]; then
        log_message "${RED}❌ Production environment file not found: $ENV_FILE${NC}"
        log_message "${YELLOW}💡 Run './scripts/generate-secure-env.sh' and select production${NC}"
        exit 1
    fi
    
    # Check SSL certificates
    if [[ ! -d "$PROJECT_ROOT/ssl/certs" ]] || [[ -z "$(ls -A "$PROJECT_ROOT/ssl/certs" 2>/dev/null)" ]]; then
        log_message "${YELLOW}⚠️  SSL certificates not found. Using self-signed certificates.${NC}"
        ./scripts/generate-ssl-certs.sh
    fi
    
    log_message "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function to validate environment configuration
validate_environment() {
    log_message "${BLUE}🔍 Validating environment configuration...${NC}"
    
    # Load environment variables
    source "$PROJECT_ROOT/$ENV_FILE"
    
    # Check required variables
    REQUIRED_VARS=(
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "REDIS_PASSWORD"
        "JWT_SECRET_KEY"
        "MGMT_SECRET_KEY"
        "MGMT_JWT_SECRET_KEY"
        "VAULT_TOKEN"
        "CLICKHOUSE_PASSWORD"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
        "CORS_ORIGINS"
        "ALLOWED_HOSTS"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_message "${RED}❌ Required environment variable not set: $var${NC}"
            exit 1
        fi
    done
    
    # Validate security requirements
    if [[ "${ENVIRONMENT:-}" != "production" ]]; then
        log_message "${RED}❌ ENVIRONMENT must be set to 'production'${NC}"
        exit 1
    fi
    
    if [[ "${DEBUG:-false}" == "true" ]]; then
        log_message "${RED}❌ DEBUG must be set to 'false' in production${NC}"
        exit 1
    fi
    
    if [[ "${SSL_ENABLED:-false}" != "true" ]]; then
        log_message "${YELLOW}⚠️  SSL_ENABLED should be 'true' in production${NC}"
    fi
    
    log_message "${GREEN}✅ Environment validation passed${NC}"
}

# Function to create backup
create_backup() {
    if [[ "$1" == "--skip-backup" ]]; then
        log_message "${YELLOW}⚠️  Skipping backup as requested${NC}"
        return
    fi
    
    log_message "${BLUE}💾 Creating backup...${NC}"
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
    BACKUP_PATH="$BACKUP_DIR/$(date +%Y%m%d-%H%M%S)"
    
    # Backup database
    if docker ps | grep -q dotmac-postgres-shared; then
        log_message "${BLUE}📄 Backing up database...${NC}"
        docker exec dotmac-postgres-shared pg_dumpall -U "${POSTGRES_USER}" | gzip > "$BACKUP_PATH/database-backup.sql.gz"
    fi
    
    # Backup volumes
    log_message "${BLUE}📁 Backing up volumes...${NC}"
    docker run --rm -v dotmac-postgres-shared-data-prod:/data -v "$BACKUP_PATH:/backup" alpine tar czf /backup/postgres-data.tar.gz -C /data .
    docker run --rm -v dotmac-redis-shared-data-prod:/data -v "$BACKUP_PATH:/backup" alpine tar czf /backup/redis-data.tar.gz -C /data .
    
    # Backup configuration
    cp -r "$PROJECT_ROOT/$ENV_FILE" "$BACKUP_PATH/"
    cp -r "$PROJECT_ROOT/ssl" "$BACKUP_PATH/" 2>/dev/null || true
    
    log_message "${GREEN}✅ Backup created: $BACKUP_PATH${NC}"
}

# Function to build images
build_images() {
    log_message "${BLUE}🔨 Building Docker images...${NC}"
    
    # Set build arguments
    BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    VERSION=${VERSION:-"1.0.0"}
    
    # Build ISP Framework
    log_message "${BLUE}📦 Building ISP Framework...${NC}"
    docker build \
        --file "$PROJECT_ROOT/isp-framework/Dockerfile.production" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        --tag "dotmac/isp-framework:$VERSION" \
        --tag "dotmac/isp-framework:latest" \
        "$PROJECT_ROOT/isp-framework"
    
    # Build Management Platform
    log_message "${BLUE}📦 Building Management Platform...${NC}"
    docker build \
        --file "$PROJECT_ROOT/management-platform/Dockerfile.production" \
        --build-arg BUILD_DATE="$BUILD_DATE" \
        --build-arg VCS_REF="$VCS_REF" \
        --build-arg VERSION="$VERSION" \
        --tag "dotmac/management-platform:$VERSION" \
        --tag "dotmac/management-platform:latest" \
        "$PROJECT_ROOT/management-platform"
    
    log_message "${GREEN}✅ Images built successfully${NC}"
}

# Function to deploy services
deploy_services() {
    log_message "${BLUE}🚀 Deploying services...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Pull external images
    log_message "${BLUE}⬇️  Pulling external images...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull postgres-shared redis-shared nginx-proxy clickhouse signoz-collector signoz-query signoz-frontend
    
    # Deploy infrastructure services first
    log_message "${BLUE}🏗️  Starting infrastructure services...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d postgres-shared redis-shared openbao-shared
    
    # Wait for infrastructure to be ready
    log_message "${BLUE}⏳ Waiting for infrastructure services...${NC}"
    sleep 30
    
    # Deploy observability services
    log_message "${BLUE}📊 Starting observability services...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d clickhouse signoz-collector signoz-query signoz-frontend
    
    # Wait for observability to be ready
    sleep 20
    
    # Deploy application services
    log_message "${BLUE}🎯 Starting application services...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d isp-framework isp-worker management-platform mgmt-celery-worker mgmt-celery-beat
    
    # Wait for applications to be ready
    sleep 30
    
    # Deploy reverse proxy last
    log_message "${BLUE}🌐 Starting reverse proxy...${NC}"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d nginx-proxy
    
    log_message "${GREEN}✅ All services deployed${NC}"
}

# Function to run database migrations
run_migrations() {
    log_message "${BLUE}🗄️  Running database migrations...${NC}"
    
    # ISP Framework migrations
    docker exec dotmac-isp-framework python -m alembic upgrade head || {
        log_message "${RED}❌ ISP Framework migrations failed${NC}"
        exit 1
    }
    
    # Management Platform migrations
    docker exec dotmac-management-platform python -m alembic upgrade head || {
        log_message "${RED}❌ Management Platform migrations failed${NC}"
        exit 1
    }
    
    log_message "${GREEN}✅ Database migrations completed${NC}"
}

# Function to validate deployment
validate_deployment() {
    log_message "${BLUE}🔍 Validating deployment...${NC}"
    
    # Check service health
    SERVICES=(
        "dotmac-postgres-shared:5432"
        "dotmac-redis-shared:6379"
        "dotmac-isp-framework:8000"
        "dotmac-management-platform:8000"
        "dotmac-nginx-proxy:80"
        "dotmac-nginx-proxy:443"
    )
    
    for service in "${SERVICES[@]}"; do
        container=$(echo "$service" | cut -d':' -f1)
        port=$(echo "$service" | cut -d':' -f2)
        
        if ! docker ps | grep -q "$container"; then
            log_message "${RED}❌ Container not running: $container${NC}"
            exit 1
        fi
        
        # Check if port is responding (with timeout)
        if ! timeout 10 bash -c "docker exec $container nc -z localhost $port" 2>/dev/null; then
            log_message "${YELLOW}⚠️  Port check failed for $container:$port (may be normal for some services)${NC}"
        fi
    done
    
    # Check HTTP health endpoints with retry
    HEALTH_ENDPOINTS=(
        "http://localhost:8000/health"
        "http://localhost:8001/health"
    )
    
    for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
        log_message "${BLUE}🏥 Checking health endpoint: $endpoint${NC}"
        
        for i in {1..5}; do
            if curl -sf "$endpoint" > /dev/null 2>&1; then
                log_message "${GREEN}✅ Health check passed: $endpoint${NC}"
                break
            else
                if [[ $i -eq 5 ]]; then
                    log_message "${RED}❌ Health check failed after 5 attempts: $endpoint${NC}"
                    exit 1
                else
                    log_message "${YELLOW}⏳ Health check attempt $i failed, retrying in 10s...${NC}"
                    sleep 10
                fi
            fi
        done
    done
    
    log_message "${GREEN}✅ Deployment validation passed${NC}"
}

# Function to show deployment summary
show_summary() {
    log_message ""
    log_message "${GREEN}🎉 Production deployment completed successfully!${NC}"
    log_message ""
    log_message "${BLUE}📋 Deployment Summary:${NC}"
    log_message "• Management Platform: https://admin.yourdomain.com"
    log_message "• ISP Framework: https://portal.yourdomain.com"
    log_message "• Monitoring: https://monitoring.yourdomain.com"
    log_message "• Deployment Time: $(date)"
    log_message ""
    log_message "${BLUE}📊 Service Status:${NC}"
    docker-compose -f "$PROJECT_ROOT/$COMPOSE_FILE" --env-file "$PROJECT_ROOT/$ENV_FILE" ps
    log_message ""
    log_message "${BLUE}📝 Next Steps:${NC}"
    log_message "1. Configure DNS to point to this server"
    log_message "2. Update SSL certificates if using real domains"
    log_message "3. Configure external services (Stripe, email, etc.)"
    log_message "4. Set up monitoring alerts"
    log_message "5. Run smoke tests"
    log_message ""
    log_message "${YELLOW}💡 Useful Commands:${NC}"
    log_message "• View logs: docker-compose -f $COMPOSE_FILE logs -f [service]"
    log_message "• Check status: docker-compose -f $COMPOSE_FILE ps"
    log_message "• Stop services: docker-compose -f $COMPOSE_FILE down"
    log_message "• Update services: ./scripts/deploy-production.sh --update"
    log_message ""
}

# Main deployment function
main() {
    # Parse command line arguments
    SKIP_BACKUP=false
    UPDATE_ONLY=false
    
    for arg in "$@"; do
        case $arg in
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --update)
                UPDATE_ONLY=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --skip-backup    Skip backup creation"
                echo "  --update        Update existing deployment"
                echo "  --help, -h      Show this help message"
                exit 0
                ;;
            *)
                log_message "${RED}Unknown option: $arg${NC}"
                exit 1
                ;;
        esac
    done
    
    # Create log directory
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Start deployment
    log_message "${BLUE}🚀 Starting production deployment at $(date)${NC}"
    
    if [[ "$UPDATE_ONLY" == "true" ]]; then
        log_message "${BLUE}🔄 Update mode: Skipping initial checks${NC}"
        build_images
        deploy_services
        run_migrations
        validate_deployment
    else
        check_prerequisites
        validate_environment
        
        if [[ "$SKIP_BACKUP" == "false" ]]; then
            create_backup
        else
            create_backup --skip-backup
        fi
        
        build_images
        deploy_services
        run_migrations
        validate_deployment
    fi
    
    show_summary
    
    log_message "${GREEN}✅ Production deployment completed successfully at $(date)${NC}"
}

# Run main function with all arguments
main "$@"