#!/bin/bash
# Standardized Docker-based testing for DotMac Framework
# This script provides a consistent interface for running tests using Docker

set -e

# Track whether we should auto-cleanup
AUTO_CLEANUP=${AUTO_CLEANUP:-true}
CLEANUP_ON_SUCCESS=${CLEANUP_ON_SUCCESS:-true}
CLEANUP_ON_FAILURE=${CLEANUP_ON_FAILURE:-true}

# Function to handle cleanup on exit
cleanup_on_exit() {
    local exit_code=$?
    
    if [ "$AUTO_CLEANUP" = "true" ]; then
        if [ $exit_code -eq 0 ] && [ "$CLEANUP_ON_SUCCESS" = "true" ]; then
            log_info "Tests completed successfully, cleaning up..."
            clean_tests
        elif [ $exit_code -ne 0 ] && [ "$CLEANUP_ON_FAILURE" = "true" ]; then
            log_warn "Tests failed (exit code: $exit_code), cleaning up..."
            clean_tests
        fi
    fi
}

# Set trap to cleanup on exit
trap cleanup_on_exit EXIT INT TERM

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
    --no-auto-cleanup  Disable automatic cleanup on exit
    --no-cleanup-success  Skip cleanup on successful tests
    --no-cleanup-failure  Skip cleanup on failed tests

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

    # Check for Docker Compose (v2 or v1)
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
        log_info "Using Docker Compose v2"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
        log_info "Using Docker Compose v1"
    else
        log_error "Docker Compose is required but not installed"
        exit 1
    fi
}

# Clean up test environment
clean_tests() {
    log_info "Cleaning up test environment..."
    $COMPOSE_CMD -f docker-compose.test.yml down -v --remove-orphans
    docker system prune -f --filter label=com.docker.compose.project=dotmac_framework
    
    # Clean up any conflicting networks
    docker network ls --filter name=dotmac-test --format "{{.Name}}" | xargs -r docker network rm 2>/dev/null || true
    
    # In CI environments, be more aggressive with cleanup
    if [ "${CI:-false}" = "true" ]; then
        log_info "CI environment detected, performing aggressive cleanup..."
        docker container prune -f --filter label=com.docker.compose.project=dotmac_framework
        docker volume prune -f --filter label=com.docker.compose.project=dotmac_framework
        docker network prune -f
    fi
    
    log_success "Test environment cleaned"
}

# Check for port conflicts and suggest alternatives
check_port_conflicts() {
    local ports=("5434" "6380" "5673" "15673" "8201")
    local conflicts=()
    
    for port in "${ports[@]}"; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            conflicts+=("$port")
        fi
    done
    
    if [ ${#conflicts[@]} -gt 0 ]; then
        log_warn "Port conflicts detected on: ${conflicts[*]}"
        log_info "Consider stopping conflicting services or using --rebuild to force cleanup"
        return 1
    fi
    return 0
}

# Build test infrastructure
build_tests() {
    local no_cache_flag=""
    if [[ "$*" == *"--no-cache"* ]]; then
        no_cache_flag="--no-cache"
    fi

    log_info "Building test infrastructure..."
    $COMPOSE_CMD -f docker-compose.test.yml build $no_cache_flag
    log_success "Test infrastructure built"
}

# Start infrastructure services
start_infrastructure() {
    log_info "Checking for port conflicts..."
    if ! check_port_conflicts; then
        log_info "Attempting to resolve conflicts by cleaning up..."
        clean_tests
    fi
    
    log_info "Starting infrastructure services..."
    $COMPOSE_CMD -f docker-compose.test.yml up -d postgres-test redis-test rabbitmq-test openbao-test

    # Wait for services to be healthy
    log_info "Waiting for services to be ready..."
    local timeout=180
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if $COMPOSE_CMD -f docker-compose.test.yml ps | grep -q "healthy"; then
            log_success "Infrastructure services are ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done

    log_error "Infrastructure services failed to start within ${timeout}s"
    $COMPOSE_CMD -f docker-compose.test.yml logs
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
            $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
                pytest -m "unit" $verbose_flag --tb=short
            ;;
        "integration")
            start_infrastructure
            log_info "Running integration tests..."
            $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
                pytest -m "integration" $verbose_flag --tb=short
            ;;
        "smoke")
            start_infrastructure
            log_info "Running smoke tests..."
            $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
                pytest -m "smoke" $verbose_flag --tb=short --maxfail=1
            ;;
        "all")
            start_infrastructure
            log_info "Running all tests..."
            $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
                pytest $verbose_flag --tb=short
            ;;
        "lint")
            log_info "Running code quality checks..."
            $COMPOSE_CMD -f docker-compose.test.yml run --rm test-runner \
                python -m ruff check src/ && python -m mypy src/
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

    # Parse cleanup options
    if [[ "$*" == *"--no-auto-cleanup"* ]]; then
        AUTO_CLEANUP=false
    fi
    if [[ "$*" == *"--no-cleanup-success"* ]]; then
        CLEANUP_ON_SUCCESS=false
    fi
    if [[ "$*" == *"--no-cleanup-failure"* ]]; then
        CLEANUP_ON_FAILURE=false
    fi

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
