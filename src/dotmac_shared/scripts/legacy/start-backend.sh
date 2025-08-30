#!/bin/bash
# DotMac Framework - Backend Startup Script
# Orchestrates all backend services in Docker for development and production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${ENVIRONMENT:-development}
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"
PROJECT_NAME="dotmac-framework"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
DotMac Framework - Backend Startup Script

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    start           Start all backend services
    stop            Stop all backend services
    restart         Restart all backend services
    status          Show service status
    logs            Show service logs
    clean           Clean up containers and volumes
    build           Build all service images
    publish         Publish API contracts
    health          Check service health

OPTIONS:
    -e, --env       Environment (development|staging|production) [default: development]
    -p, --project   Project name [default: dotmac-framework]
    -f, --follow    Follow logs (use with logs command)
    -h, --help      Show this help

EXAMPLES:
    $0 start                           # Start all services
    $0 start --env production          # Start in production mode
    $0 logs --follow                   # Follow all service logs
    $0 publish                         # Publish API contracts
    $0 health                          # Check all service health

SERVICES:
    - PostgreSQL Database
    - Redis Cache
    - API Gateway (Port 8000)
    - Platform Service (Port 8001)
    - Core Events (Port 8002)
    - Core Ops (Port 8003)
    - Identity Service (Port 8004)
    - Billing Service (Port 8005)
    - Networking Service (Port 8006)
    - Analytics Service (Port 8007)
    - Services Management (Port 8008)
    - DevTools (Port 8009)

EOF
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi

    log_success "Dependencies check passed"
}

# Create comprehensive docker-compose file for backend services
create_backend_compose() {
    log_info "Creating backend services compose file..."

    cat > /home/dotmac_framework/docker-compose.backend.yml << 'EOF'
version: '3.8'

networks:
  dotmac-backend:
    driver: bridge
  dotmac-frontend:
    driver: bridge

volumes:
  postgres_data:
  redis_data:

services:
  # Core Infrastructure
  postgres:
    image: postgres:16-alpine
    container_name: dotmac-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: dotmac_platform
      POSTGRES_USER: dotmac
      POSTGRES_PASSWORD: dotmac_secure_password
      POSTGRES_MULTIPLE_DATABASES: "dotmac_platform,dotmac_events,dotmac_billing,dotmac_identity,dotmac_networking,dotmac_analytics,dotmac_services"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-multiple-databases.sh:/docker-entrypoint-initdb.d/init-multiple-databases.sh:ro
    networks:
      - dotmac-backend
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dotmac -d dotmac_platform"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: dotmac-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - dotmac-backend
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # API Gateway
  api-gateway:
    build:
      context: ./dotmac_api_gateway
      dockerfile: Dockerfile
    container_name: dotmac-api-gateway
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_platform
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    networks:
      - dotmac-backend
      - dotmac-frontend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Platform Service
  platform:
    build:
      context: ./dotmac_platform
      dockerfile: Dockerfile.prod
    container_name: dotmac-platform
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_platform
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
      - AUTH_SECRET_KEY=your-secret-key-change-in-production
    ports:
      - "8001:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Core Events Service
  core-events:
    build:
      context: ./dotmac_core_events
      dockerfile: Dockerfile
    container_name: dotmac-core-events
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_events
      - REDIS_URL=redis://redis:6379/1
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8002:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Core Ops Service
  core-ops:
    build:
      context: ./dotmac_core_ops
      dockerfile: Dockerfile
    container_name: dotmac-core-ops
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_platform
      - REDIS_URL=redis://redis:6379/2
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8003:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Identity Service
  identity:
    build:
      context: ./dotmac_identity
      dockerfile: Dockerfile
    container_name: dotmac-identity
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_identity
      - REDIS_URL=redis://redis:6379/3
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8004:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Billing Service
  billing:
    build:
      context: ./dotmac_billing
      dockerfile: Dockerfile
    container_name: dotmac-billing
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_billing
      - REDIS_URL=redis://redis:6379/4
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8005:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Networking Service
  networking:
    build:
      context: ./dotmac_networking
      dockerfile: Dockerfile
    container_name: dotmac-networking
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_networking
      - REDIS_URL=redis://redis:6379/5
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8006:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Analytics Service
  analytics:
    build:
      context: ./dotmac_analytics
      dockerfile: Dockerfile
    container_name: dotmac-analytics
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_analytics
      - REDIS_URL=redis://redis:6379/6
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8007:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Services Management
  services:
    build:
      context: ./dotmac_services
      dockerfile: Dockerfile
    container_name: dotmac-services
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_services
      - REDIS_URL=redis://redis:6379/7
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8008:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # DevTools Service
  devtools:
    build:
      context: ./dotmac_devtools
      dockerfile: Dockerfile
    container_name: dotmac-devtools
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgresql://dotmac:dotmac_secure_password@postgres:5432/dotmac_platform
      - REDIS_URL=redis://redis:6379/8
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    ports:
      - "8009:8000"
    networks:
      - dotmac-backend
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Contract Publishing Service (Prism Mock Server)
  contracts:
    image: stoplight/prism:latest
    container_name: dotmac-contracts
    command: mock -h 0.0.0.0 -p 4010 /contracts/openapi.yaml
    volumes:
      - ./dotmac_platform/tests/fixtures/openapi.yaml:/contracts/openapi.yaml:ro
    networks:
      - dotmac-frontend
    ports:
      - "4010:4010"
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:4010/health"]
      interval: 30s
      timeout: 5s
      retries: 3
EOF

    log_success "Backend compose file created"
}

# Create database initialization script
create_db_init() {
    log_info "Creating database initialization script..."

    mkdir -p /home/dotmac_framework/scripts

    cat > /home/dotmac_framework/scripts/init-multiple-databases.sh << 'EOF'
#!/bin/bash
set -e

function create_user_and_database() {
    local database=$1
    echo "Creating user and database '$database'"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE USER ${database}_user WITH ENCRYPTED PASSWORD '${database}_password';
        CREATE DATABASE $database;
        GRANT ALL PRIVILEGES ON DATABASE $database TO ${database}_user;
EOSQL
}

if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Multiple database creation requested: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        create_user_and_database $db
    done
    echo "Multiple databases created"
fi
EOF

    chmod +x /home/dotmac_framework/scripts/init-multiple-databases.sh
    log_success "Database initialization script created"
}

# Build all services
build_services() {
    log_info "Building all backend services..."

    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME build --parallel

    log_success "All services built successfully"
}

# Start all services
start_services() {
    log_info "Starting all backend services..."

    # Start infrastructure first
    log_info "Starting infrastructure services..."
    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME up -d postgres redis

    # Wait for infrastructure to be healthy
    log_info "Waiting for infrastructure services to be healthy..."
    sleep 10

    # Start application services
    log_info "Starting application services..."
    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME up -d

    log_success "All backend services started successfully"
}

# Stop all services
stop_services() {
    log_info "Stopping all backend services..."

    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME down

    log_success "All backend services stopped"
}

# Show service status
show_status() {
    log_info "Backend services status:"
    echo

    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME ps
}

# Show service logs
show_logs() {
    local follow_flag=""
    if [[ "$FOLLOW_LOGS" == "true" ]]; then
        follow_flag="-f"
    fi

    docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME logs $follow_flag
}

# Clean up services
clean_services() {
    log_warn "This will remove all containers and volumes. Are you sure? (y/N)"
    read -r response

    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "Cleaning up services..."
        docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME down -v --remove-orphans
        docker system prune -f
        log_success "Cleanup completed"
    else
        log_info "Cleanup cancelled"
    fi
}

# Check service health
check_health() {
    log_info "Checking service health..."

    services=(
        "http://localhost:8000/health:API Gateway"
        "http://localhost:8001/health:Platform Service"
        "http://localhost:4010/health:Contract Server"
    )

    for service in "${services[@]}"; do
        IFS=':' read -r url name <<< "$service"
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$name is healthy"
        else
            log_error "$name is not responding"
        fi
    done
}

# Publish API contracts
publish_contracts() {
    log_info "Publishing API contracts..."

    # Start contract server if not running
    if ! docker ps | grep -q dotmac-contracts; then
        log_info "Starting contract server..."
        docker-compose -f docker-compose.backend.yml -p $PROJECT_NAME up -d contracts
        sleep 5
    fi

    log_success "API contracts published at http://localhost:4010"
    log_info "Available endpoints:"
    echo "  - OpenAPI Docs: http://localhost:4010"
    echo "  - Health Check: http://localhost:4010/health"
    echo "  - API Gateway: http://localhost:8000"
    echo "  - Platform Service: http://localhost:8001"
}

# Parse command line arguments
COMMAND=""
FOLLOW_LOGS="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -p|--project)
            PROJECT_NAME="$2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW_LOGS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        start|stop|restart|status|logs|clean|build|publish|health)
            COMMAND="$1"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    cd /home/dotmac_framework

    check_dependencies
    create_backend_compose
    create_db_init

    case "$COMMAND" in
        start)
            build_services
            start_services
            check_health
            ;;
        stop)
            stop_services
            ;;
        restart)
            stop_services
            sleep 2
            start_services
            check_health
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        clean)
            clean_services
            ;;
        build)
            build_services
            ;;
        publish)
            publish_contracts
            ;;
        health)
            check_health
            ;;
        "")
            log_error "No command specified"
            show_help
            exit 1
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
EOF
