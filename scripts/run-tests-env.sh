#!/bin/bash
# Environment-specific test runner for DotMac Framework

set -e

# Default values
ENVIRONMENT="local"
TEST_TYPE="all"
VERBOSE=false
REPORT_ONLY=false

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

show_help() {
    cat << EOF
DotMac Framework Environment-Specific Test Runner

Usage: $0 [OPTIONS]

Options:
    -e, --env ENVIRONMENT       Test environment: local, ci, staging, production (default: local)
    -t, --type TEST_TYPE       Test type: unit, integration, e2e, all, smoke (default: all)
    -v, --verbose              Enable verbose output
    -r, --report-only          Generate reports only (skip test execution)
    -h, --help                 Show this help message

Environments:
    local       Local development environment with Docker containers
    ci          CI/CD optimized environment for automated testing  
    staging     Staging environment testing with real services
    production  Production smoke tests (read-only, minimal)

Examples:
    $0 --env local --type unit
    $0 --env ci --type integration --verbose
    $0 --env staging --type e2e
    $0 --env production --type smoke
    $0 --report-only

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -r|--report-only)
            REPORT_ONLY=true
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
done

# Validate environment
case $ENVIRONMENT in
    local|ci|staging|production)
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        log_info "Valid environments: local, ci, staging, production"
        exit 1
        ;;
esac

# Load environment-specific configuration
ENV_FILE="configs/test/${ENVIRONMENT}.env"
if [ ! -f "$ENV_FILE" ]; then
    log_error "Environment configuration file not found: $ENV_FILE"
    exit 1
fi

log_info "Loading configuration for environment: $ENVIRONMENT"
set -a  # Automatically export variables
source "$ENV_FILE"
set +a

# Create test reports directory
mkdir -p test-reports

# Generate reports only if requested
if [ "$REPORT_ONLY" = true ]; then
    log_info "Generating test reports only..."
    if [ -x "scripts/generate-test-report.sh" ]; then
        ./scripts/generate-test-report.sh
    else
        log_error "Test report generation script not found or not executable"
        exit 1
    fi
    exit 0
fi

# Environment-specific pre-test setup
case $ENVIRONMENT in
    local)
        log_info "Setting up local test environment..."
        if [ -x "src/dotmac_shared/scripts/test-docker.sh" ]; then
            # Use the Docker-based testing for local environment
            ./src/dotmac_shared/scripts/test-docker.sh "$TEST_TYPE"
            exit $?
        else
            log_error "Docker test script not found"
            exit 1
        fi
        ;;
    ci)
        log_info "Running tests in CI environment..."
        # CI tests run in containerized environment
        export CI=true
        ;;
    staging|production)
        log_info "Running tests against $ENVIRONMENT environment..."
        # Validate required environment variables for external testing
        if [ -z "$ISP_SERVICE_URL" ] || [ -z "$MANAGEMENT_SERVICE_URL" ]; then
            log_error "Required service URLs not configured for $ENVIRONMENT environment"
            exit 1
        fi
        ;;
esac

# Set pytest arguments based on environment and test type
PYTEST_ARGS=()

# Add markers based on test type
case $TEST_TYPE in
    unit)
        PYTEST_ARGS+=("-m" "unit")
        ;;
    integration)
        PYTEST_ARGS+=("-m" "integration")
        ;;
    e2e)
        PYTEST_ARGS+=("-m" "e2e")
        ;;
    smoke)
        PYTEST_ARGS+=("-m" "smoke")
        ;;
    all)
        # No marker filter for all tests
        ;;
    *)
        log_error "Invalid test type: $TEST_TYPE"
        exit 1
        ;;
esac

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS+=("-v" "-s")
fi

# Add environment-specific arguments
case $ENVIRONMENT in
    production)
        # Extra safety for production
        PYTEST_ARGS+=("--tb=no" "--quiet")
        ;;
    ci)
        # CI optimizations
        PYTEST_ARGS+=("--tb=short" "--maxfail=5")
        ;;
esac

# Run the tests
log_info "Starting $TEST_TYPE tests in $ENVIRONMENT environment..."
log_info "Test command: pytest ${PYTEST_ARGS[*]}"

export PYTHONPATH="src:$PYTHONPATH"

if /root/.local/share/pypoetry/venv/bin/poetry run pytest "${PYTEST_ARGS[@]}"; then
    log_success "Tests completed successfully!"
    
    # Generate reports for non-production environments
    if [ "$ENVIRONMENT" != "production" ] && [ -x "scripts/generate-test-report.sh" ]; then
        log_info "Generating test reports..."
        ./scripts/generate-test-report.sh
    fi
    
    exit 0
else
    TEST_EXIT_CODE=$?
    log_error "Tests failed with exit code $TEST_EXIT_CODE"
    
    # Send alerts for production failures
    if [ "$ENVIRONMENT" = "production" ] && [ "$ALERT_ON_FAILURE" = "true" ]; then
        log_warn "Production tests failed - sending alerts..."
        # Alert logic would go here
    fi
    
    exit $TEST_EXIT_CODE
fi