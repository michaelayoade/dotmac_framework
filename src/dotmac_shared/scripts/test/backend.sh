#!/bin/bash
# Consolidated backend testing script for DotMac Framework
# Replaces multiple scripts with a single, optimized test runner

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_PROFILE="test"
COVERAGE_MIN=80

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Help message
show_help() {
    cat << EOF
DotMac Backend Test Runner

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    unit                Run unit tests only (fast, isolated)
    integration         Run integration tests (requires services)
    contract           Run API contract tests
    security           Run security-focused tests
    mutation           Run mutation testing (requires --mutation flag)
    all                Run unit + integration tests
    coverage           Generate coverage report
    clean              Clean test artifacts and containers

OPTIONS:
    -v, --verbose      Verbose output
    -f, --fast         Skip slow tests
    --fail-fast        Stop on first failure
    --mutation         Enable mutation testing
    --no-cov          Skip coverage collection
    --docker          Force Docker execution
    --local           Force local execution (no Docker)
    --services SERVICE Set specific services to test (comma-separated)

EXAMPLES:
    $0 unit                               # Fast unit tests
    $0 integration --services=identity    # Integration tests for identity service
    $0 contract --verbose                 # Contract tests with verbose output
    $0 all --docker                      # All tests in Docker
    $0 mutation --mutation               # Run mutation testing

ENVIRONMENT VARIABLES:
    TEST_ENV           Test environment (local, docker, ci)
    PYTEST_ARGS        Additional pytest arguments
    COVERAGE_MIN       Minimum coverage threshold (default: 80)
    TEST_TIMEOUT       Test timeout in seconds (default: 300)

EOF
}

# Check dependencies
check_dependencies() {
    local missing_deps=()

    if ! command -v pytest &> /dev/null; then
        missing_deps+=("pytest")
    fi

    if ! command -v docker &> /dev/null && [[ "$USE_DOCKER" == "true" ]]; then
        missing_deps+=("docker")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Install with: pip install pytest coverage pytest-cov pytest-asyncio"
        exit 1
    fi
}

# Optimized database container setup with Unix socket for speed
setup_test_database() {
    local db_container="dotmac-test-db-optimized"

    log_info "Setting up optimized test database..."

    # Check if container exists and is running
    if docker ps -q -f name="$db_container" | grep -q .; then
        log_info "Test database already running"
        return 0
    fi

    # Remove existing container if stopped
    docker rm -f "$db_container" 2>/dev/null || true

    # Start optimized PostgreSQL with Unix socket and tmpfs
    docker run -d \
        --name "$db_container" \
        -e POSTGRES_DB=dotmac_test \
        -e POSTGRES_USER=test \
        -e POSTGRES_PASSWORD=test \
        -e POSTGRES_INITDB_ARGS="--auth-host=trust" \
        --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=512m \
        --tmpfs /tmp:rw,noexec,nosuid,size=128m \
        -p 5433:5432 \
        --health-cmd="pg_isready -U test -d dotmac_test" \
        --health-interval=5s \
        --health-timeout=3s \
        --health-retries=5 \
        postgres:15-alpine \
        postgres -c fsync=off -c synchronous_commit=off -c checkpoint_segments=32 -c wal_buffers=16MB -c shared_buffers=256MB

    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    local timeout=30
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if docker exec "$db_container" pg_isready -U test -d dotmac_test > /dev/null 2>&1; then
            log_success "Test database ready"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
        echo -n "."
    done

    log_error "Database failed to start within ${timeout}s"
    docker logs "$db_container"
    return 1
}

# Optimized Redis setup with Unix socket
setup_test_redis() {
    local redis_container="dotmac-test-redis-optimized"

    log_info "Setting up optimized test Redis..."

    if docker ps -q -f name="$redis_container" | grep -q .; then
        log_info "Test Redis already running"
        return 0
    fi

    docker rm -f "$redis_container" 2>/dev/null || true

    docker run -d \
        --name "$redis_container" \
        -p 6380:6379 \
        --tmpfs /data:rw,noexec,nosuid,size=256m \
        --health-cmd="redis-cli ping" \
        --health-interval=5s \
        --health-timeout=3s \
        --health-retries=3 \
        redis:7-alpine \
        redis-server --save "" --appendonly no --protected-mode no

    # Wait for Redis to be ready
    local timeout=15
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if docker exec "$redis_container" redis-cli ping > /dev/null 2>&1; then
            log_success "Test Redis ready"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    log_error "Redis failed to start within ${timeout}s"
    return 1
}

# Clean test environment
clean_test_environment() {
    log_info "Cleaning test environment..."

    # Stop and remove test containers
    docker rm -f dotmac-test-db-optimized dotmac-test-redis-optimized 2>/dev/null || true

    # Clean pytest cache and coverage files
    find "$PROJECT_ROOT" -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name ".coverage*" -type f -delete 2>/dev/null || true
    find "$PROJECT_ROOT" -name "coverage.xml" -type f -delete 2>/dev/null || true

    log_success "Test environment cleaned"
}

# Build pytest command with optimizations
build_pytest_command() {
    local test_type="$1"
    local cmd="pytest"

    # Base arguments for performance and consistency
    cmd+=" --strict-markers --strict-config"
    cmd+=" --tb=short -ra"
    cmd+=" --durations=10"  # Show 10 slowest tests

    # Coverage settings (unless disabled)
    if [[ "$NO_COVERAGE" != "true" ]]; then
        cmd+=" --cov-config=pyproject.toml"
        cmd+=" --cov-report=term-missing"
        cmd+=" --cov-report=html:htmlcov"
        cmd+=" --cov-report=xml"
        cmd+=" --cov-fail-under=${COVERAGE_MIN}"
    fi

    # Test type specific markers and settings
    case "$test_type" in
        "unit")
            cmd+=" -m 'unit'"
            cmd+=" --maxfail=5"  # Fail fast for unit tests
            ;;
        "integration")
            cmd+=" -m 'integration'"
            cmd+=" --maxfail=3"
            ;;
        "contract")
            cmd+=" -m 'contracts'"
            cmd+=" --maxfail=1"  # Contract tests should never fail
            ;;
        "security")
            cmd+=" -m 'security'"
            cmd+=" --maxfail=1"  # Security tests are critical
            ;;
        "all")
            cmd+=" -m 'unit or integration'"
            ;;
    esac

    # Performance optimizations
    if [[ "$FAST_MODE" == "true" ]]; then
        cmd+=" -m 'not slow'"
        cmd+=" --disable-warnings"
    fi

    # Fail fast mode
    if [[ "$FAIL_FAST" == "true" ]]; then
        cmd+=" --maxfail=1"
    fi

    # Verbose mode
    if [[ "$VERBOSE" == "true" ]]; then
        cmd+=" -v"
    fi

    # Service filter
    if [[ -n "$TEST_SERVICES" ]]; then
        local service_filter=""
        IFS=',' read -ra SERVICES <<< "$TEST_SERVICES"
        for service in "${SERVICES[@]}"; do
            if [[ -n "$service_filter" ]]; then
                service_filter+=" or "
            fi
            service_filter+="$service"
        done
        cmd+=" -k '$service_filter'"
    fi

    # Additional pytest arguments
    if [[ -n "$PYTEST_ARGS" ]]; then
        cmd+=" $PYTEST_ARGS"
    fi

    echo "$cmd"
}

# Run mutation testing
run_mutation_testing() {
    log_info "Running mutation testing (this may take a while)..."

    if ! command -v mutmut &> /dev/null; then
        log_warn "Installing mutmut for mutation testing..."
        pip install mutmut
    fi

    # Configure mutmut
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # Run mutation testing on core modules
    local modules=(
        "backend/dotmac_sdk_core"
        "backend/dotmac_identity"
        "backend/dotmac_core_events"
    )

    for module in "${modules[@]}"; do
        if [[ -d "$PROJECT_ROOT/$module" ]]; then
            log_info "Running mutation testing on $module..."
            cd "$PROJECT_ROOT"

            # Run mutmut with timeout
            timeout 1800 mutmut run \
                --paths-to-mutate="$module" \
                --tests-dir="tests/" \
                --runner="python -m pytest -x" \
                || log_warn "Mutation testing timed out for $module"

            # Show results
            mutmut results || true
            mutmut junitxml > "mutation-results-$(basename "$module").xml" || true
        fi
    done

    log_success "Mutation testing completed"
}

# Generate coverage report
generate_coverage_report() {
    log_info "Generating detailed coverage report..."

    if command -v coverage &> /dev/null; then
        # Generate HTML report
        coverage html --directory=htmlcov --title="DotMac Framework Coverage"

        # Generate XML for CI
        coverage xml

        # Show terminal report
        coverage report --show-missing

        log_success "Coverage report generated in htmlcov/"
    else
        log_warn "Coverage tool not found, install with: pip install coverage"
    fi
}

# Run tests with proper setup
run_tests() {
    local test_type="$1"

    # Set test environment variables
    export DOTMAC_TEST_MODE=true
    export DOTMAC_DATABASE_URL="postgresql://test:test@localhost:5433/dotmac_test"
    export DOTMAC_REDIS_URL="redis://localhost:6380/0"
    export DOTMAC_LOG_LEVEL="WARNING"  # Reduce noise in tests

    # Setup infrastructure for integration tests
    if [[ "$test_type" == "integration" || "$test_type" == "contract" || "$test_type" == "all" ]]; then
        setup_test_database
        setup_test_redis
    fi

    # Build and run pytest command
    local pytest_cmd
    pytest_cmd=$(build_pytest_command "$test_type")

    log_info "Running $test_type tests..."
    log_info "Command: $pytest_cmd"

    cd "$PROJECT_ROOT"

    # Execute with timeout
    if timeout "${TEST_TIMEOUT:-300}" bash -c "$pytest_cmd"; then
        log_success "$test_type tests passed"

        # Generate coverage report if requested
        if [[ "$test_type" == "all" || "$test_type" == "coverage" ]]; then
            generate_coverage_report
        fi

        return 0
    else
        local exit_code=$?
        log_error "$test_type tests failed (exit code: $exit_code)"
        return $exit_code
    fi
}

# Parse command line arguments
parse_arguments() {
    COMMAND=""
    VERBOSE=false
    FAST_MODE=false
    FAIL_FAST=false
    USE_DOCKER=${USE_DOCKER:-auto}
    NO_COVERAGE=false
    MUTATION_TESTING=false
    TEST_SERVICES=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            unit|integration|contract|security|mutation|all|coverage|clean)
                COMMAND="$1"
                ;;
            -v|--verbose)
                VERBOSE=true
                ;;
            -f|--fast)
                FAST_MODE=true
                ;;
            --fail-fast)
                FAIL_FAST=true
                ;;
            --mutation)
                MUTATION_TESTING=true
                ;;
            --no-cov)
                NO_COVERAGE=true
                ;;
            --docker)
                USE_DOCKER=true
                ;;
            --local)
                USE_DOCKER=false
                ;;
            --services)
                TEST_SERVICES="$2"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done

    if [[ -z "$COMMAND" ]]; then
        log_error "No command specified"
        show_help
        exit 1
    fi
}

# Main execution
main() {
    parse_arguments "$@"
    check_dependencies

    cd "$PROJECT_ROOT"

    case "$COMMAND" in
        "unit"|"integration"|"contract"|"security"|"all")
            run_tests "$COMMAND"
            ;;
        "mutation")
            if [[ "$MUTATION_TESTING" == "true" ]]; then
                run_mutation_testing
            else
                log_error "Mutation testing requires --mutation flag"
                exit 1
            fi
            ;;
        "coverage")
            run_tests "all"
            ;;
        "clean")
            clean_test_environment
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# Execute main with all arguments
main "$@"
