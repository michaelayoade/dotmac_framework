#!/bin/bash

# Multi-Tier Database Testing Setup Script
# Handles SQLite, PostgreSQL, and Docker environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTEST_ARGS="${PYTEST_ARGS:--v --tb=short}"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

# Function to check if PostgreSQL is available
check_postgresql() {
    local host="${POSTGRES_TEST_HOST:-localhost}"
    local port="${POSTGRES_TEST_PORT:-5433}"
    local user="${POSTGRES_TEST_USER:-postgres}"
    
    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h "$host" -p "$port" -U "$user" >/dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to check if Docker is available and containers are running
check_docker_containers() {
    if ! command -v docker >/dev/null 2>&1; then
        return 1
    fi
    
    if ! docker ps --format "table {{.Names}}" | grep -q "dotmac-test-postgres"; then
        return 1
    fi
    
    if ! docker ps --format "table {{.Names}}" | grep -q "dotmac-test-redis"; then
        return 1
    fi
    
    return 0
}

# Function to start Docker test environment
start_docker_environment() {
    print_header "Starting Docker Test Environment"
    
    cd "$PROJECT_ROOT"
    
    print_status "Stopping any existing test containers..."
    docker-compose -f docker-compose.test.yml down --remove-orphans 2>/dev/null || true
    
    print_status "Starting test services..."
    docker-compose -f docker-compose.test.yml up -d postgres-test redis-test
    
    print_status "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f docker-compose.test.yml exec -T postgres-test pg_isready -U postgres -d dotmac_isp_test >/dev/null 2>&1; then
            print_success "PostgreSQL is ready"
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "PostgreSQL failed to start within timeout"
        return 1
    fi
    
    # Wait for Redis
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f docker-compose.test.yml exec -T redis-test redis-cli ping >/dev/null 2>&1; then
            print_success "Redis is ready"
            break
        fi
        sleep 1
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        print_error "Redis failed to start within timeout"
        return 1
    fi
    
    print_success "Docker test environment is ready"
    return 0
}

# Function to run Tier 1 tests (SQLite)
run_tier1_tests() {
    print_header "Tier 1: SQLite Database Tests"
    
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    print_status "Running unit tests with SQLite..."
    
    # Use the enhanced conftest for SQLite testing
    python -m pytest tests/unit/modules/billing/test_models_fixed.py \
        --confcutdir=tests \
        $PYTEST_ARGS \
        -m "not postgresql_required" || {
        print_error "Tier 1 SQLite tests failed"
        return 1
    }
    
    print_success "Tier 1 SQLite tests completed successfully"
    return 0
}

# Function to run Tier 3 tests (PostgreSQL)
run_tier3_tests() {
    print_header "Tier 3: PostgreSQL Database Tests"
    
    cd "$PROJECT_ROOT"
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    
    # Set PostgreSQL environment variables
    export POSTGRES_TEST_HOST="${POSTGRES_TEST_HOST:-localhost}"
    export POSTGRES_TEST_PORT="${POSTGRES_TEST_PORT:-5433}"
    export POSTGRES_TEST_USER="${POSTGRES_TEST_USER:-postgres}"
    export POSTGRES_TEST_PASSWORD="${POSTGRES_TEST_PASSWORD:-postgres}"
    export POSTGRES_TEST_DB="${POSTGRES_TEST_DB:-dotmac_isp_test}"
    
    print_status "Running tests with PostgreSQL..."
    print_status "Database: ${POSTGRES_TEST_HOST}:${POSTGRES_TEST_PORT}/${POSTGRES_TEST_DB}"
    
    # Use PostgreSQL-specific conftest
    python -m pytest tests/unit/modules/billing/test_models_fixed.py \
        --confcutdir=tests \
        --confcutdir=tests/conftest_postgresql.py \
        $PYTEST_ARGS || {
        print_error "Tier 3 PostgreSQL tests failed"
        return 1
    }
    
    print_success "Tier 3 PostgreSQL tests completed successfully"
    return 0
}

# Function to run Tier 4 tests (Docker)
run_tier4_tests() {
    print_header "Tier 4: Docker Integration Tests"
    
    cd "$PROJECT_ROOT"
    
    if ! check_docker_containers; then
        print_status "Starting Docker test environment..."
        start_docker_environment || {
            print_error "Failed to start Docker environment"
            return 1
        }
    fi
    
    print_status "Running integration tests in Docker..."
    
    # Run tests inside the test-runner container
    docker-compose -f docker-compose.test.yml run --rm test-runner \
        python -m pytest tests/unit/modules/billing/test_models_fixed.py \
        $PYTEST_ARGS || {
        print_error "Tier 4 Docker tests failed"
        return 1
    }
    
    print_success "Tier 4 Docker integration tests completed successfully"
    return 0
}

# Function to run comprehensive test suite
run_comprehensive_tests() {
    print_header "Multi-Tier Database Testing Suite"
    
    local failed_tiers=()
    
    # Tier 1: SQLite Tests (always available)
    print_status "Running Tier 1 (SQLite) tests..."
    if ! run_tier1_tests; then
        failed_tiers+=("Tier1-SQLite")
    fi
    
    # Tier 3: PostgreSQL Tests (if available)
    if check_postgresql; then
        print_status "PostgreSQL detected, running Tier 3 tests..."
        if ! run_tier3_tests; then
            failed_tiers+=("Tier3-PostgreSQL")
        fi
    else
        print_warning "PostgreSQL not available, skipping Tier 3 tests"
        print_status "To run PostgreSQL tests, ensure PostgreSQL is running on ${POSTGRES_TEST_HOST:-localhost}:${POSTGRES_TEST_PORT:-5433}"
    fi
    
    # Tier 4: Docker Tests (if Docker is available)
    if command -v docker >/dev/null 2>&1; then
        print_status "Docker detected, running Tier 4 tests..."
        if ! run_tier4_tests; then
            failed_tiers+=("Tier4-Docker")
        fi
    else
        print_warning "Docker not available, skipping Tier 4 tests"
    fi
    
    # Summary
    echo
    print_header "Test Results Summary"
    
    if [ ${#failed_tiers[@]} -eq 0 ]; then
        print_success "All available test tiers completed successfully!"
        return 0
    else
        print_error "Failed test tiers: ${failed_tiers[*]}"
        return 1
    fi
}

# Function to clean up test environment
cleanup_test_environment() {
    print_header "Cleaning Up Test Environment"
    
    cd "$PROJECT_ROOT"
    
    print_status "Stopping Docker test containers..."
    docker-compose -f docker-compose.test.yml down --remove-orphans 2>/dev/null || true
    
    print_status "Removing test database files..."
    rm -f test.db test_sync.db test_async.db 2>/dev/null || true
    
    print_status "Cleaning up Python cache..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    print_success "Test environment cleaned up"
}

# Function to generate test data factories
generate_test_factories() {
    print_header "Generating Test Data Factories"
    
    cd "$PROJECT_ROOT"
    
    print_status "Test factories have been created in tests/factories/"
    print_status "Available factories:"
    echo "  - InvoiceFactory (billing)"
    echo "  - PaymentFactory (billing)"
    echo "  - CustomerFactory (identity)"
    echo "  - ServiceInstanceFactory (services)"
    echo "  - NetworkDeviceFactory (network)"
    
    print_success "Test factories are ready to use"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  tier1           Run Tier 1 tests (SQLite)"
    echo "  tier3           Run Tier 3 tests (PostgreSQL)"
    echo "  tier4           Run Tier 4 tests (Docker)"
    echo "  all             Run all available test tiers"
    echo "  docker-start    Start Docker test environment"
    echo "  docker-stop     Stop Docker test environment"
    echo "  cleanup         Clean up test environment"
    echo "  factories       Show test data factories info"
    echo "  help            Show this help message"
    echo
    echo "Environment Variables:"
    echo "  POSTGRES_TEST_HOST     PostgreSQL host (default: localhost)"
    echo "  POSTGRES_TEST_PORT     PostgreSQL port (default: 5433)"
    echo "  POSTGRES_TEST_USER     PostgreSQL user (default: postgres)"
    echo "  POSTGRES_TEST_PASSWORD PostgreSQL password (default: postgres)"
    echo "  POSTGRES_TEST_DB       PostgreSQL database (default: dotmac_isp_test)"
    echo "  PYTEST_ARGS           Additional pytest arguments (default: -v --tb=short)"
    echo
    echo "Examples:"
    echo "  $0 all                 # Run all available test tiers"
    echo "  $0 tier1               # Run only SQLite tests"
    echo "  PYTEST_ARGS=\"-x -vs\" $0 tier3    # Run PostgreSQL tests with custom args"
}

# Main script logic
main() {
    case "${1:-all}" in
        "tier1")
            run_tier1_tests
            ;;
        "tier3")
            if check_postgresql; then
                run_tier3_tests
            else
                print_error "PostgreSQL not available. Please start PostgreSQL or use Docker."
                print_status "Run '$0 docker-start' to start test environment"
                exit 1
            fi
            ;;
        "tier4")
            run_tier4_tests
            ;;
        "all")
            run_comprehensive_tests
            ;;
        "docker-start")
            start_docker_environment
            ;;
        "docker-stop"|"cleanup")
            cleanup_test_environment
            ;;
        "factories")
            generate_test_factories
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"