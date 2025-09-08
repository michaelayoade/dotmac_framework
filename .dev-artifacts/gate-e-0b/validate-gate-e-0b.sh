#!/bin/bash
set -euo pipefail

# Gate E-0b Database/Cache Validation Script
# Tests that PostgreSQL and Redis are healthy and can connect to OpenBao

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
if [[ -f .env.gate-e-0b ]]; then
    source .env.gate-e-0b
    log_info "Loaded Gate E-0b environment configuration"
else
    log_error "Missing .env.gate-e-0b file"
    exit 1
fi

test_postgres() {
    log_info "Testing PostgreSQL connection..."
    if PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5436 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "PostgreSQL is accessible and accepting connections"
        
        # Test basic query
        local result
        result=$(PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -p 5436 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM health_check;" 2>/dev/null | xargs || echo "0")
        log_info "Health check table has $result records"
        return 0
    else
        log_error "PostgreSQL connection failed"
        return 1
    fi
}

test_redis() {
    log_info "Testing Redis connection..."
    if redis-cli -h localhost -p 6381 -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        log_success "Redis is accessible and responding to PING"
        
        # Test basic operations
        redis-cli -h localhost -p 6381 -a "$REDIS_PASSWORD" set test_key "gate-e0b" >/dev/null 2>&1
        local value
        value=$(redis-cli -h localhost -p 6381 -a "$REDIS_PASSWORD" get test_key 2>/dev/null)
        if [[ "$value" == "gate-e0b" ]]; then
            log_success "Redis SET/GET operations working"
            redis-cli -h localhost -p 6381 -a "$REDIS_PASSWORD" del test_key >/dev/null 2>&1
        else
            log_warning "Redis SET/GET test failed"
        fi
        return 0
    else
        log_error "Redis connection failed"
        return 1
    fi
}

test_openbao_connectivity() {
    log_info "Testing connectivity to OpenBao from E-0b services..."
    # Check if OpenBao (from E-0a) is accessible
    if curl -f -s "$OPENBAO_URL/v1/sys/health" >/dev/null 2>&1; then
        log_success "OpenBao is accessible from E-0b network"
        return 0
    else
        log_error "OpenBao connectivity test failed"
        return 1
    fi
}

# Main validation flow
main() {
    log_info "Starting Gate E-0b Database/Cache Validation"
    log_info "==========================================="
    
    local failed_tests=0
    
    # Check if E-0a (OpenBao) is running
    log_info "Verifying Gate E-0a (OpenBao) is running..."
    if ! curl -f -s "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
        log_error "Gate E-0a (OpenBao) is not accessible. Please ensure E-0a is running first."
        exit 1
    fi
    log_success "Gate E-0a (OpenBao) is accessible"
    
    # Check if services are running
    log_info "Checking if Gate E-0b services are running..."
    if ! docker-compose -f docker-compose.gate-e-0b.yml ps | grep -q "Up"; then
        log_error "Gate E-0b services are not running. Please start them first with:"
        log_error "  docker-compose -f docker-compose.gate-e-0b.yml up -d"
        exit 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for database and cache services to become ready..."
    sleep 15
    
    # Run all tests
    test_openbao_connectivity || ((failed_tests++))
    test_postgres || ((failed_tests++))
    test_redis || ((failed_tests++))
    
    # Summary
    echo
    log_info "Gate E-0b Validation Summary"
    log_info "============================"
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "🎉 Gate E-0b (Database/Cache) is healthy and ready!"
        log_success "Ready to proceed to Gate E-0c (Observability)"
        echo
        log_info "Available services:"
        log_info "  - PostgreSQL: localhost:5436"
        log_info "  - Redis: localhost:6381"
        log_info "  - OpenBao connectivity: ✓"
        exit 0
    else
        log_error "❌ $failed_tests test(s) failed"
        log_error "Please fix the issues before proceeding to Gate E-0c"
        exit 1
    fi
}

# Run main function
main "$@"