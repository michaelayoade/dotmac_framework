#!/bin/bash
# Standardized Docker-based testing for DotMac Framework
# This script provides a consistent interface for running tests using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Help message
show_help() {
    cat << EOF
DotMac Framework - Docker Test Runner

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    unit                 Run unit tests only (fast)
    integration         Run integration tests 
    smoke              Run smoke tests
    all                Run all tests (unit + integration)
    clean              Clean up test containers and volumes
    build              Build test infrastructure
    lint               Run code quality checks
    
OPTIONS:
    -h, --help         Show this help message
    -v, --verbose      Verbose output
    -q, --quiet        Quiet output (errors only)
    --no-cache         Build without cache
    --rebuild          Force rebuild of containers
    
EXAMPLES:
    $0 unit                    # Run unit tests
    $0 integration --verbose  # Run integration tests with verbose output
    $0 all --rebuild          # Rebuild and run all tests
    $0 clean                  # Clean up test environment

DOCKER SERVICES:
    - test-postgres: PostgreSQL database for testing
    - test-redis: Redis cache for testing  
    - httpbin: HTTP service for webhook testing
    - dotmac-platform-tests: Main test runner

EOF
}

# Check if docker and docker-compose are available
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi
}

# Clean up test environment
clean_tests() {
    log_info "Cleaning up test environment..."
    docker-compose -f docker-compose.test.yml down -v --remove-orphans
    docker system prune -f --filter label=com.docker.compose.project=dotmac_framework
    log_success "Test environment cleaned"
}

# Build test infrastructure
build_tests() {
    local no_cache_flag=""
    if [[ "$*" == *"--no-cache"* ]]; then
        no_cache_flag="--no-cache"
    fi
    
    log_info "Building test infrastructure..."
    docker-compose -f docker-compose.test.yml build $no_cache_flag
    log_success "Test infrastructure built"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Starting infrastructure services..."
    docker-compose -f docker-compose.test.yml up -d test-postgres test-redis httpbin
    
    # Wait for services to be healthy
    log_info "Waiting for services to be ready..."
    local timeout=60
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if docker-compose -f docker-compose.test.yml ps | grep -q "healthy"; then
            log_success "Infrastructure services are ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    log_error "Infrastructure services failed to start within ${timeout}s"
    docker-compose -f docker-compose.test.yml logs
    return 1
}

# Run specific test type
run_tests() {
    local test_type=$1
    local verbose_flag=""
    
    if [[ "$*" == *"--verbose"* ]] || [[ "$*" == *"-v"* ]]; then
        verbose_flag="-v"
    elif [[ "$*" == *"--quiet"* ]] || [[ "$*" == *"-q"* ]]; then
        verbose_flag="-q"
    fi
    
    case $test_type in
        "unit")
            log_info "Running unit tests..."
            docker-compose -f docker-compose.test.yml run --rm dotmac-platform-tests \
                pytest -m "unit" $verbose_flag --tb=short
            ;;
        "integration")
            start_infrastructure
            log_info "Running integration tests..."
            docker-compose -f docker-compose.test.yml run --rm dotmac-platform-tests \
                pytest -m "integration" $verbose_flag --tb=short
            ;;
        "smoke")
            start_infrastructure
            log_info "Running smoke tests..."
            docker-compose -f docker-compose.test.yml run --rm dotmac-platform-tests \
                pytest -m "smoke" $verbose_flag --tb=short --maxfail=1
            ;;
        "all")
            start_infrastructure
            log_info "Running all tests..."
            docker-compose -f docker-compose.test.yml run --rm dotmac-platform-tests \
                pytest $verbose_flag --tb=short
            ;;
        "lint")
            log_info "Running code quality checks..."
            docker-compose -f docker-compose.test.yml run --rm lint-check
            ;;
        *)
            log_error "Unknown test type: $test_type"
            show_help
            exit 1
            ;;
    esac
}

# Main execution
main() {
    check_dependencies
    
    # Handle rebuild flag
    if [[ "$*" == *"--rebuild"* ]]; then
        clean_tests
        build_tests --no-cache
    fi
    
    # Parse command
    case "$1" in
        "unit"|"integration"|"smoke"|"all"|"lint")
            run_tests "$@"
            ;;
        "clean")
            clean_tests
            ;;
        "build")
            build_tests "$@"
            ;;
        "-h"|"--help"|"help"|"")
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"