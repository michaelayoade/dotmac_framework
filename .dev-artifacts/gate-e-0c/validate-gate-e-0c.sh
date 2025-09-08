#!/bin/bash
set -euo pipefail

# Gate E-0c Observability Validation Script
# Tests that observability stack is functional

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
if [[ -f .env.gate-e-0c ]]; then
    source .env.gate-e-0c
    log_info "Loaded Gate E-0c environment configuration"
else
    log_error "Missing .env.gate-e-0c file"
    exit 1
fi

test_clickhouse() {
    log_info "Testing ClickHouse connection..."
    if curl -f -s "http://localhost:8124/ping" >/dev/null 2>&1; then
        log_success "ClickHouse is accessible and responding"
        
        # Test basic query
        local result
        result=$(curl -s "http://localhost:8124/?query=SELECT%201" 2>/dev/null || echo "0")
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
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f -s "http://localhost:8081/api/v1/health" >/dev/null 2>&1; then
            log_success "SigNoz Query Service is healthy"
            
            # Test version endpoint
            local version_info
            version_info=$(curl -s "http://localhost:8081/api/v1/version" 2>/dev/null | head -c 100)
            log_info "SigNoz version info: ${version_info:0:50}..."
            return 0
        else
            ((attempt++))
            log_info "Attempt $attempt/$max_attempts: SigNoz Query Service not ready, waiting..."
            sleep 5
        fi
    done
    
    log_error "SigNoz Query Service health check failed after $max_attempts attempts"
    return 1
}

test_connectivity_to_previous_layers() {
    log_info "Testing connectivity to previous layers..."
    
    # Test E-0a (OpenBao)
    if curl -f -s "http://localhost:8200/v1/sys/health" >/dev/null 2>&1; then
        log_success "E-0a (OpenBao) connectivity: ✓"
    else
        log_error "E-0a (OpenBao) connectivity: ✗"
        return 1
    fi
    
    # Test E-0b (PostgreSQL)
    if PGPASSWORD="password123" psql -h localhost -p 5436 -U dotmac_admin -d dotmac_test -c "SELECT 1;" >/dev/null 2>&1; then
        log_success "E-0b (PostgreSQL) connectivity: ✓"
    else
        log_error "E-0b (PostgreSQL) connectivity: ✗"
        return 1
    fi
    
    # Test E-0b (Redis) 
    if redis-cli -h localhost -p 6381 -a "redis123" ping >/dev/null 2>&1; then
        log_success "E-0b (Redis) connectivity: ✓"
    else
        log_error "E-0b (Redis) connectivity: ✗"
        return 1
    fi
    
    return 0
}

# Main validation flow
main() {
    log_info "Starting Gate E-0c Observability Validation"
    log_info "=========================================="
    
    local failed_tests=0
    
    # Check if previous layers are running
    log_info "Verifying previous layers (E-0a, E-0b) are accessible..."
    test_connectivity_to_previous_layers || ((failed_tests++))
    
    # Check if E-0c services are running
    log_info "Checking if Gate E-0c services are running..."
    if ! docker-compose -f docker-compose.gate-e-0c.yml ps | grep -q "Up"; then
        log_error "Gate E-0c services are not running. Please start them first with:"
        log_error "  docker-compose -f docker-compose.gate-e-0c.yml up -d"
        exit 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for observability services to become ready..."
    sleep 10
    
    # Run core tests
    test_clickhouse || ((failed_tests++))
    test_signoz_query || ((failed_tests++))
    
    # Test OTEL endpoints (basic port connectivity)
    log_info "Testing OTLP endpoints accessibility..."
    if timeout 5 bash -c "</dev/tcp/localhost/4319" 2>/dev/null; then
        log_success "OTLP gRPC endpoint (4319) is accessible"
    else
        log_warning "OTLP gRPC endpoint (4319) is not accessible"
        ((failed_tests++))
    fi
    
    if timeout 5 bash -c "</dev/tcp/localhost/4320" 2>/dev/null; then
        log_success "OTLP HTTP endpoint (4320) is accessible"
    else
        log_warning "OTLP HTTP endpoint (4320) is not accessible"
        ((failed_tests++))
    fi
    
    # Summary
    echo
    log_info "Gate E-0c Validation Summary"
    log_info "============================"
    
    if [[ $failed_tests -eq 0 ]]; then
        log_success "🎉 Gate E-0c (Observability) is healthy and ready!"
        log_success "All Gate E-0 layers (E-0a, E-0b, E-0c) are operational!"
        log_success "Ready to proceed to Gate E-1 (Management Application)"
        echo
        log_info "Complete Gate E-0 Stack:"
        log_info "  ✓ E-0a: OpenBao (Vault) - http://localhost:8200"
        log_info "  ✓ E-0b: PostgreSQL - localhost:5436"
        log_info "  ✓ E-0b: Redis - localhost:6381"
        log_info "  ✓ E-0c: ClickHouse - http://localhost:8124"
        log_info "  ✓ E-0c: SigNoz Query - http://localhost:8081"
        log_info "  ✓ E-0c: OTLP Collector - gRPC=4319, HTTP=4320"
        exit 0
    else
        log_error "❌ $failed_tests test(s) failed"
        log_error "Please fix the issues before proceeding to Gate E-1"
        exit 1
    fi
}

# Run main function
main "$@"