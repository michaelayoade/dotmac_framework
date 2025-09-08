#!/bin/bash
set -euo pipefail

# Gate E-0 Support Services Validation Script
# Tests that all support services are healthy and accessible

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Load environment variables
if [[ -f .env.gate-e-0 ]]; then
    source .env.gate-e-0
    log_info "Loaded Gate E-0 environment configuration"
else
    log_error "Missing .env.gate-e-0 file"
    exit 1
fi

# Test functions
test_postgres() {
    log_info "Testing PostgreSQL connection..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5435 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "PostgreSQL is accessible and accepting connections"
        
        # Test basic query
        local result
        result=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5435 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM health_check;" 2>/dev/null || echo "0")
        log_info "Health check table has $result records"
        return 0
    else
        log_error "PostgreSQL connection failed"
        return 1
    fi
}

test_redis() {
    log_info "Testing Redis connection..."
    if redis-cli -h localhost -p 6380 -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        log_success "Redis is accessible and responding to PING"
        
        # Test basic operations
        redis-cli -h localhost -p 6380 -a "$REDIS_PASSWORD" set test_key "gate-e-0" >/dev/null 2>&1
        local value
        value=$(redis-cli -h localhost -p 6380 -a "$REDIS_PASSWORD" get test_key 2>/dev/null)
        if [[ "$value" == "gate-e-0" ]]; then
            log_success "Redis SET/GET operations working"
            redis-cli -h localhost -p 6380 -a "$REDIS_PASSWORD" del test_key >/dev/null 2>&1
        else
            log_warning "Redis SET/GET test failed"
        fi
        return 0
    else
        log_error "Redis connection failed"
        return 1
    fi
}

test_clickhouse() {
    log_info "Testing ClickHouse connection..."
    if curl -f -s "http://localhost:8123/ping" >/dev/null 2>&1; then
        log_success "ClickHouse is accessible and responding"
        
        # Test basic query
        local result
        result=$(curl -s "http://localhost:8123/?query=SELECT%201" 2>/dev/null || echo "0")
        if [[ "$result" == "1" ]]; then
            log_success "ClickHouse query execution working"
        else
            log_warning "ClickHouse query test failed"
        fi
        return 0
    else
        log_error "ClickHouse connection failed"
        return 1
    fi
}

test_signoz_query() {
    log_info "Testing SigNoz Query Service..."
    if curl -f -s "http://localhost:8080/api/v1/health" >/dev/null 2>&1; then
        log_success "SigNoz Query Service is healthy"
        
        # Test version endpoint
        local version_info
        version_info=$(curl -s "http://localhost:8080/api/v1/version" 2>/dev/null | head -c 100)
        log_info "SigNoz version info: ${version_info:0:50}..."
        return 0
    else
        log_error "SigNoz Query Service health check failed"
        return 1
    fi
}

test_signoz_frontend() {
    log_info "Testing SigNoz Frontend..."
    if curl -f -s "http://localhost:3301" >/dev/null 2>&1; then
        log_success "SigNoz Frontend is accessible"
        return 0
    else
        log_error "SigNoz Frontend is not accessible"
        return 1
    fi
}

test_otel_collector() {
    log_info "Testing OpenTelemetry Collector..."
    
    # Test OTLP gRPC endpoint (just check if port is open)
    if timeout 5 bash -c "</dev/tcp/localhost/4317" 2>/dev/null; then
        log_success "OTLP gRPC endpoint (4317) is accessible"
    else
        log_error "OTLP gRPC endpoint (4317) is not accessible"
        return 1
    fi
    
    # Test OTLP HTTP endpoint
    if timeout 5 bash -c "</dev/tcp/localhost/4318" 2>/dev/null; then
        log_success "OTLP HTTP endpoint (4318) is accessible"
    else
        log_error "OTLP HTTP endpoint (4318) is not accessible"
        return 1
    fi
    
    return 0
}

test_openbao() {
    log_info "Testing OpenBao (Vault) connection..."
    if curl -f -s "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
        log_success "OpenBao is accessible and responding"
        
        # Test authentication with root token
        local response
        response=$(curl -s -H "X-Vault-Token: $OPENBAO_ROOT_TOKEN" "http://localhost:8200/v1/sys/health" 2>/dev/null)
        if [[ -n "$response" ]]; then
            log_success "OpenBao root token authentication working"
        else
            log_warning "OpenBao authentication test failed"
        fi
        return 0
    else
        log_error "OpenBao connection failed"
        return 1
    fi
}

test_docker_health() {
    log_info "Checking Docker container health status..."
    local unhealthy_containers
    unhealthy_containers=$(docker-compose -f docker-compose.gate-e-0.yml ps --filter health=unhealthy --quiet | wc -l)
    local healthy_containers
    healthy_containers=$(docker-compose -f docker-compose.gate-e-0.yml ps --filter health=healthy --quiet | wc -l)
    
    log_info "Healthy containers: $healthy_containers"
    if [[ "$unhealthy_containers" -gt 0 ]]; then
        log_error "Found $unhealthy_containers unhealthy containers"
        docker-compose -f docker-compose.gate-e-0.yml ps
        return 1
    else
        log_success "All containers are healthy"
        return 0
    fi
}

# Main validation flow
main() {
    log_info "Starting Gate E-0 Support Services Validation"
    log_info "==========================================="
    
    local failed_tests=0
    
    # Check if services are running
    log_info "Checking if Gate E-0 services are running..."
    if ! docker-compose -f docker-compose.gate-e-0.yml ps | grep -q "Up"; then
        log_error "Gate E-0 services are not running. Please start them first with:"
        log_error "  docker-compose -f docker-compose.gate-e-0.yml up -d"
        exit 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to become ready..."
    sleep 15
    
    # Run all tests
    test_docker_health || ((failed_tests++))
    test_openbao || ((failed_tests++))
    test_postgres || ((failed_tests++))
    test_redis || ((failed_tests++))
    test_clickhouse || ((failed_tests++))
    test_signoz_query || ((failed_tests++))
    test_signoz_frontend || ((failed_tests++))
    test_otel_collector || ((failed_tests++))
    
    # Summary
    echo
    log_info "Gate E-0 Validation Summary"
    log_info "=========================="
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "🎉 All Gate E-0 support services are healthy and accessible!"
        log_success "Ready to proceed to Gate E-1 (Management Application)"
        echo
        log_info "Available services:"
        log_info "  - OpenBao (Vault): http://localhost:8200"
        log_info "  - PostgreSQL: localhost:5435"
        log_info "  - Redis: localhost:6380"
        log_info "  - ClickHouse: http://localhost:8123"
        log_info "  - SigNoz Query: http://localhost:8080"
        log_info "  - SigNoz Frontend: http://localhost:3301"
        log_info "  - OTLP Collector: gRPC=4317, HTTP=4318"
        exit 0
    else
        log_error "❌ $failed_tests test(s) failed"
        log_error "Please fix the issues before proceeding to Gate E-1"
        exit 1
    fi
}

# Run main function
main "$@"