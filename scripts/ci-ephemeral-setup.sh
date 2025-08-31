#!/bin/bash
# CI Ephemeral Tenant Environment Setup Script
# Creates and manages isolated tenant stacks for E2E testing

set -e

# Configuration
export CI_JOB_ID="${GITHUB_RUN_ID:-local}_${GITHUB_RUN_ATTEMPT:-1}"
export TEST_STAGE="${TEST_STAGE:-smoke}"
export GITHUB_SHA="${GITHUB_SHA:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Port allocation function
allocate_port() {
    python3 -c "
import socket
import sys
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port
print(find_free_port())
"
}

# Environment validation
validate_environment() {
    log "Validating environment..."
    
    # Check required tools
    for tool in docker docker-compose curl python3; do
        if ! command -v $tool &> /dev/null; then
            error "$tool is required but not installed"
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
    fi
    
    # Check disk space (minimum 5GB)
    available_space=$(df . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 5000000 ]; then
        warn "Less than 5GB disk space available: ${available_space}KB"
    fi
    
    success "Environment validation completed"
}

# Port allocation
allocate_ports() {
    log "Allocating dynamic ports..."
    
    export BACKEND_PORT=$(allocate_port)
    export ADMIN_PORT=$(allocate_port)
    export CUSTOMER_PORT=$(allocate_port)
    export RESELLER_PORT=$(allocate_port)
    export POSTGRES_PORT=$(allocate_port)
    export REDIS_PORT=$(allocate_port)
    export RABBITMQ_PORT=$(allocate_port)
    export RABBITMQ_MGMT_PORT=$(allocate_port)
    
    # Optional service ports
    export STRIPE_MOCK_PORT=$(allocate_port)
    export MINIO_PORT=$(allocate_port)
    export MINIO_CONSOLE_PORT=$(allocate_port)
    export MAILHOG_SMTP_PORT=$(allocate_port)
    export MAILHOG_UI_PORT=$(allocate_port)
    export JAEGER_UI_PORT=$(allocate_port)
    export JAEGER_COLLECTOR_PORT=$(allocate_port)
    
    log "Port allocation completed:"
    echo "  Backend: $BACKEND_PORT"
    echo "  Admin: $ADMIN_PORT"
    echo "  Customer: $CUSTOMER_PORT"
    echo "  Reseller: $RESELLER_PORT"
    echo "  PostgreSQL: $POSTGRES_PORT"
    echo "  Redis: $REDIS_PORT"
    
    # Save port configuration for other scripts
    cat > ".env.e2e-ports-${CI_JOB_ID}" << EOF
BACKEND_PORT=$BACKEND_PORT
ADMIN_PORT=$ADMIN_PORT
CUSTOMER_PORT=$CUSTOMER_PORT
RESELLER_PORT=$RESELLER_PORT
POSTGRES_PORT=$POSTGRES_PORT
REDIS_PORT=$REDIS_PORT
RABBITMQ_PORT=$RABBITMQ_PORT
RABBITMQ_MGMT_PORT=$RABBITMQ_MGMT_PORT
STRIPE_MOCK_PORT=$STRIPE_MOCK_PORT
MINIO_PORT=$MINIO_PORT
MINIO_CONSOLE_PORT=$MINIO_CONSOLE_PORT
MAILHOG_SMTP_PORT=$MAILHOG_SMTP_PORT
MAILHOG_UI_PORT=$MAILHOG_UI_PORT
JAEGER_UI_PORT=$JAEGER_UI_PORT
JAEGER_COLLECTOR_PORT=$JAEGER_COLLECTOR_PORT
EOF
}

# Cleanup existing resources
cleanup_existing() {
    log "Cleaning up any existing resources for job ${CI_JOB_ID}..."
    
    # Stop and remove containers
    docker-compose -f docker/docker-compose.e2e-tenant.yml down -v --remove-orphans 2>/dev/null || true
    
    # Remove any orphaned containers
    docker ps -a --filter "label=com.docker.compose.project=docker" \
        --filter "name=*-${CI_JOB_ID}" -q | xargs -r docker rm -f 2>/dev/null || true
    
    # Clean up networks
    docker network ls --filter "name=*${CI_JOB_ID}*" -q | xargs -r docker network rm 2>/dev/null || true
    
    # Clean up volumes (only if CI_JOB_ID is set to avoid accidents)
    if [[ "$CI_JOB_ID" != "local" ]]; then
        docker volume ls --filter "name=*${CI_JOB_ID}*" -q | xargs -r docker volume rm 2>/dev/null || true
    fi
    
    success "Cleanup completed"
}

# Build or pull required images
prepare_images() {
    log "Preparing Docker images..."
    
    if [[ -n "$GITHUB_SHA" && "$GITHUB_SHA" != "latest" ]]; then
        # In CI, images should be pre-built and tagged with SHA
        log "Using pre-built images tagged with SHA: $GITHUB_SHA"
        
        # Verify images exist
        for image in dotmac-isp dotmac-frontend-admin dotmac-frontend-customer; do
            if ! docker image inspect "${image}:${GITHUB_SHA}" &>/dev/null; then
                warn "Image ${image}:${GITHUB_SHA} not found, falling back to latest"
                export GITHUB_SHA="latest"
                break
            fi
        done
    else
        # Local development - build images if needed
        log "Building images locally..."
        
        if [[ ! "$(docker images -q dotmac-isp:latest 2> /dev/null)" ]]; then
            log "Building dotmac-isp image..."
            docker build -t dotmac-isp:latest . || error "Failed to build dotmac-isp image"
        fi
        
        if [[ ! "$(docker images -q dotmac-frontend-admin:latest 2> /dev/null)" ]]; then
            log "Building dotmac-frontend-admin image..."
            docker build -f frontend/Dockerfile.admin -t dotmac-frontend-admin:latest frontend/ || \
                warn "Failed to build admin frontend - using nginx placeholder"
        fi
        
        if [[ ! "$(docker images -q dotmac-frontend-customer:latest 2> /dev/null)" ]]; then
            log "Building dotmac-frontend-customer image..."
            docker build -f frontend/Dockerfile.customer -t dotmac-frontend-customer:latest frontend/ || \
                warn "Failed to build customer frontend - using nginx placeholder"
        fi
    fi
    
    success "Image preparation completed"
}

# Prepare test data
prepare_test_data() {
    log "Preparing test data for stage: $TEST_STAGE..."
    
    # Ensure test data directory exists
    mkdir -p docker/test-data
    
    # Base initialization SQL
    cat > docker/test-data/init.sql << 'EOF'
-- Base test database initialization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create test user roles
CREATE ROLE test_admin WITH LOGIN PASSWORD 'admin_pass';
CREATE ROLE test_customer WITH LOGIN PASSWORD 'customer_pass';
CREATE ROLE test_reseller WITH LOGIN PASSWORD 'reseller_pass';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE dotmac_test TO test_admin;
EOF

    # Stage-specific seed data
    case "$TEST_STAGE" in
        smoke)
            cat > docker/test-data/seed-smoke.sql << 'EOF'
-- Minimal smoke test data
INSERT INTO tenants (id, name, subdomain, status) VALUES
    ('test-tenant-1', 'Test Tenant', 'test', 'active');

INSERT INTO users (id, email, password_hash, role, tenant_id) VALUES
    (uuid_generate_v4(), 'admin@test.com', '$2b$12$example_hash', 'admin', 'test-tenant-1'),
    (uuid_generate_v4(), 'customer@test.com', '$2b$12$example_hash', 'customer', 'test-tenant-1');
EOF
            ;;
        core-flows)
            cat > docker/test-data/seed-core-flows.sql << 'EOF'
-- Core business flow test data
INSERT INTO tenants (id, name, subdomain, status) VALUES
    ('test-tenant-1', 'Test ISP Corp', 'testisp', 'active');

INSERT INTO users (id, email, password_hash, role, tenant_id, created_at) VALUES
    (uuid_generate_v4(), 'admin@testisp.com', '$2b$12$example_hash', 'admin', 'test-tenant-1', NOW()),
    (uuid_generate_v4(), 'customer1@example.com', '$2b$12$example_hash', 'customer', 'test-tenant-1', NOW()),
    (uuid_generate_v4(), 'customer2@example.com', '$2b$12$example_hash', 'customer', 'test-tenant-1', NOW()),
    (uuid_generate_v4(), 'reseller@partner.com', '$2b$12$example_hash', 'reseller', 'test-tenant-1', NOW());

INSERT INTO service_plans (id, name, speed_mbps, price_monthly, tenant_id) VALUES
    (uuid_generate_v4(), 'Basic 100Mbps', 100, 49.99, 'test-tenant-1'),
    (uuid_generate_v4(), 'Premium 500Mbps', 500, 89.99, 'test-tenant-1'),
    (uuid_generate_v4(), 'Business 1Gbps', 1000, 149.99, 'test-tenant-1');

INSERT INTO workflows (id, name, description, status, tenant_id) VALUES
    (uuid_generate_v4(), 'Customer Onboarding', 'Standard customer onboarding process', 'active', 'test-tenant-1'),
    (uuid_generate_v4(), 'Service Provisioning', 'Automated service provisioning', 'active', 'test-tenant-1');
EOF
            ;;
        payments-files)
            cat > docker/test-data/seed-payments-files.sql << 'EOF'
-- Payments and file management test data
INSERT INTO tenants (id, name, subdomain, status, billing_enabled) VALUES
    ('test-tenant-1', 'Test ISP Corp', 'testisp', 'active', true);

INSERT INTO users (id, email, password_hash, role, tenant_id) VALUES
    (uuid_generate_v4(), 'admin@testisp.com', '$2b$12$example_hash', 'admin', 'test-tenant-1'),
    (uuid_generate_v4(), 'billing@testisp.com', '$2b$12$example_hash', 'billing_admin', 'test-tenant-1'),
    (uuid_generate_v4(), 'customer@example.com', '$2b$12$example_hash', 'customer', 'test-tenant-1');

INSERT INTO customers (id, email, stripe_customer_id, tenant_id) VALUES
    (uuid_generate_v4(), 'customer@example.com', 'cus_test_123', 'test-tenant-1');

INSERT INTO invoices (id, customer_id, amount, status, due_date, tenant_id) VALUES
    (uuid_generate_v4(), (SELECT id FROM customers LIMIT 1), 89.99, 'pending', NOW() + INTERVAL '30 days', 'test-tenant-1');

INSERT INTO file_categories (id, name, allowed_extensions, tenant_id) VALUES
    (uuid_generate_v4(), 'Customer Documents', 'pdf,doc,docx', 'test-tenant-1'),
    (uuid_generate_v4(), 'Service Agreements', 'pdf', 'test-tenant-1');
EOF
            ;;
        *)
            warn "Unknown test stage: $TEST_STAGE, using minimal data"
            cat > docker/test-data/seed-${TEST_STAGE}.sql << 'EOF'
-- Default minimal test data
INSERT INTO tenants (id, name, subdomain, status) VALUES
    ('test-tenant-1', 'Default Test Tenant', 'default', 'active');
EOF
            ;;
    esac
    
    success "Test data preparation completed for $TEST_STAGE"
}

# Start ephemeral environment
start_environment() {
    log "Starting ephemeral tenant environment..."
    
    # Determine which profiles to enable based on test stage
    profiles=""
    case "$TEST_STAGE" in
        payments-files)
            profiles="--profile payments --profile files"
            ;;
        core-flows)
            profiles="--profile utilities --profile observability"
            ;;
        upgrade-dr)
            profiles="--profile utilities --profile observability --profile email"
            ;;
    esac
    
    # Start the stack
    log "Starting Docker Compose stack with profiles: $profiles"
    docker-compose -f docker/docker-compose.e2e-tenant.yml up -d $profiles
    
    # Show container status
    log "Container status:"
    docker-compose -f docker/docker-compose.e2e-tenant.yml ps
}

# Wait for services to be healthy
wait_for_services() {
    log "Waiting for services to become healthy..."
    
    # Define service health checks with timeouts
    declare -A services=(
        ["postgres-e2e"]="120"
        ["redis-e2e"]="60" 
        ["rabbitmq-e2e"]="180"
        ["dotmac-isp-e2e"]="300"
        ["frontend-admin-e2e"]="120"
        ["frontend-customer-e2e"]="120"
    )
    
    for service in "${!services[@]}"; do
        timeout=${services[$service]}
        log "Waiting for $service (timeout: ${timeout}s)..."
        
        if timeout ${timeout}s bash -c "
            while [[ \$(docker-compose -f docker/docker-compose.e2e-tenant.yml ps $service | grep -c 'healthy\|Up') -eq 0 ]]; do
                echo '  Still waiting for $service...'
                sleep 5
            done
        "; then
            success "$service is ready"
        else
            error "$service failed to become healthy within ${timeout}s"
        fi
    done
    
    # Additional connectivity tests
    log "Testing service connectivity..."
    
    # Test backend health endpoint
    if curl -f -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
        success "Backend API is responding"
    else
        error "Backend API health check failed"
    fi
    
    # Test frontend accessibility
    if curl -f -s "http://localhost:$ADMIN_PORT" > /dev/null; then
        success "Admin frontend is accessible"
    else
        warn "Admin frontend may not be ready"
    fi
    
    if curl -f -s "http://localhost:$CUSTOMER_PORT" > /dev/null; then
        success "Customer frontend is accessible"  
    else
        warn "Customer frontend may not be ready"
    fi
}

# Setup test utilities and seed additional data
setup_test_utilities() {
    log "Setting up test utilities and seeding data..."
    
    if docker-compose -f docker/docker-compose.e2e-tenant.yml ps test-utilities | grep -q "Up"; then
        log "Running database migrations..."
        docker-compose -f docker/docker-compose.e2e-tenant.yml exec -T test-utilities \
            python /scripts/run-migrations.py || warn "Migration script not found"
        
        log "Seeding additional test data..."
        docker-compose -f docker/docker-compose.e2e-tenant.yml exec -T test-utilities \
            python /scripts/seed-${TEST_STAGE}-data.py || warn "Seed script not found"
    else
        log "Test utilities container not running, skipping additional setup"
    fi
}

# Create monitoring and artifact directories
setup_monitoring() {
    log "Setting up monitoring and artifact collection..."
    
    # Create directories for artifacts
    mkdir -p artifacts/{logs,screenshots,videos,database,network,performance}
    
    # Start log collection in background
    nohup bash -c "
        while true; do
            docker-compose -f docker/docker-compose.e2e-tenant.yml logs --no-color --tail=100 > artifacts/logs/docker-compose-live.log 2>&1
            sleep 10
        done
    " > /dev/null 2>&1 &
    
    echo $! > ".log-collector-pid-${CI_JOB_ID}"
}

# Display environment information
show_environment_info() {
    log "Ephemeral tenant environment is ready!"
    echo
    echo "==================== ENVIRONMENT INFO ===================="
    echo "Job ID: $CI_JOB_ID"
    echo "Test Stage: $TEST_STAGE"
    echo "Git SHA: $GITHUB_SHA"
    echo
    echo "Service URLs:"
    echo "  🔧 Backend API:       http://localhost:$BACKEND_PORT"
    echo "  📊 Admin Portal:      http://localhost:$ADMIN_PORT"
    echo "  👤 Customer Portal:   http://localhost:$CUSTOMER_PORT"
    echo "  💼 Reseller Portal:   http://localhost:$RESELLER_PORT (if enabled)"
    echo
    echo "Database Connections:"
    echo "  🐘 PostgreSQL:        localhost:$POSTGRES_PORT"
    echo "  📦 Redis:             localhost:$REDIS_PORT"
    echo "  🐰 RabbitMQ:          localhost:$RABBITMQ_PORT"
    echo "  🐰 RabbitMQ Mgmt:     http://localhost:$RABBITMQ_MGMT_PORT"
    echo
    if [[ "$TEST_STAGE" == "payments-files" ]]; then
        echo "External Services:"
        echo "  💳 Stripe Mock:       http://localhost:$STRIPE_MOCK_PORT"
        echo "  📁 MinIO:             http://localhost:$MINIO_PORT"
        echo "  📁 MinIO Console:     http://localhost:$MINIO_CONSOLE_PORT"
        echo
    fi
    echo "Test Utilities:"
    echo "  📧 MailHog UI:        http://localhost:$MAILHOG_UI_PORT (if enabled)"
    echo "  🔍 Jaeger UI:         http://localhost:$JAEGER_UI_PORT (if enabled)"
    echo
    echo "Credentials:"
    echo "  Database: test_user / test_pass"
    echo "  RabbitMQ: test_user / test_pass"
    echo "  MinIO: testuser / testpass123"
    echo
    echo "=========================================================="
}

# Main execution
main() {
    log "Starting ephemeral tenant environment setup..."
    log "Configuration: JOB_ID=$CI_JOB_ID, STAGE=$TEST_STAGE, SHA=$GITHUB_SHA"
    
    validate_environment
    cleanup_existing
    allocate_ports
    prepare_images
    prepare_test_data
    start_environment
    wait_for_services
    setup_test_utilities
    setup_monitoring
    show_environment_info
    
    success "Ephemeral environment setup completed successfully!"
}

# Handle script termination
cleanup_on_exit() {
    if [[ -f ".log-collector-pid-${CI_JOB_ID}" ]]; then
        log_pid=$(cat ".log-collector-pid-${CI_JOB_ID}")
        kill $log_pid 2>/dev/null || true
        rm ".log-collector-pid-${CI_JOB_ID}"
    fi
}

trap cleanup_on_exit EXIT

# Run main function
main "$@"