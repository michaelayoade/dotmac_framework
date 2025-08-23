#!/bin/bash
# Test runner script for dotmac_platform SDKs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Resolve docker compose command (v2 'docker compose' or legacy 'docker-compose')
resolve_compose_cmd() {
    if docker compose version >/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        echo "docker-compose"
    else
        print_error "Docker Compose not found. Please install Docker Desktop (includes 'docker compose') or docker-compose."
        exit 1
    fi
}

DC_CMD=$(resolve_compose_cmd)

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Function to build test images
build_images() {
    print_status "Building test images..."
    $DC_CMD -f docker-compose.test.yml build
    print_success "Test images built successfully"
}

# Function to start services
start_services() {
    print_status "Starting test services..."
    $DC_CMD -f docker-compose.test.yml up -d redis postgres httpbin prism
    
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    for service in redis postgres httpbin prism; do
        if $DC_CMD -f docker-compose.test.yml ps $service | grep -q "Up (healthy)"; then
            print_success "$service is healthy"
        else
            print_warning "$service may not be fully ready"
        fi
    done
}

# Function to stop services
stop_services() {
    print_status "Stopping test services..."
    $DC_CMD -f docker-compose.test.yml down -v
    print_success "Test services stopped"
}

# Function to run specific test suite
run_test_suite() {
    local suite=$1
    local description=$2
    
    print_status "Running $description..."
    
    if $DC_CMD -f docker-compose.test.yml run --rm test-$suite; then
        print_success "$description completed successfully"
        return 0
    else
        print_error "$description failed"
        return 1
    fi
}

# Function to collect test reports
collect_reports() {
    print_status "Collecting test reports..."
    
    # Create reports directory if it doesn't exist
    mkdir -p reports
    
    # Copy reports from Docker volume
    docker run --rm -v dotmac_platform_test_reports:/source -v $(pwd)/reports:/dest alpine cp -r /source/. /dest/ 2>/dev/null || true
    
    if [ -d "reports" ] && [ "$(ls -A reports)" ]; then
        print_success "Test reports collected in ./reports/"
        echo "Available reports:"
        find reports -name "*.html" -o -name "*.xml" -o -name "*.json" | sort
    else
        print_warning "No test reports found"
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  unit              Run unit tests only"
    echo "  integration       Run integration tests only"
    echo "  smoke             Run smoke tests only"
    echo "  performance       Run performance tests only"
    echo "  lint              Run linting and formatting checks"
    echo "  contracts         Run contract conformance tests"
    echo "  all               Run all test suites"
    echo "  build             Build test Docker images"
    echo "  start             Start test services"
    echo "  stop              Stop test services"
    echo "  clean             Clean up test environment"
    echo "  reports           Collect test reports"
    echo ""
    echo "Options:"
    echo "  --no-build        Skip building Docker images"
    echo "  --keep-services   Keep services running after tests"
    echo "  --verbose         Enable verbose output"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit                    # Run unit tests"
    echo "  $0 all --no-build         # Run all tests without rebuilding"
    echo "  $0 integration --verbose  # Run integration tests with verbose output"
}

# Parse command line arguments
COMMAND=""
NO_BUILD=false
KEEP_SERVICES=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        unit|integration|smoke|performance|lint|contracts|all|build|start|stop|clean|reports)
            COMMAND=$1
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --keep-services)
            KEEP_SERVICES=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Set verbose mode
if [ "$VERBOSE" = true ]; then
    set -x
fi

# Main execution
main() {
    print_status "dotmac_platform Test Runner"
    print_status "============================"
    
    # Check Docker
    check_docker
    
    case $COMMAND in
        build)
            build_images
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        clean)
            print_status "Cleaning up test environment..."
            $DC_CMD -f docker-compose.test.yml down -v --remove-orphans
            docker system prune -f
            print_success "Test environment cleaned"
            ;;
        reports)
            collect_reports
            ;;
        unit)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            run_test_suite "unit" "Unit Tests"
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            ;;
        integration)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            run_test_suite "integration" "Integration Tests"
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            ;;
        smoke)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            run_test_suite "smoke" "Smoke Tests"
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            ;;
        performance)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            run_test_suite "performance" "Performance Tests"
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            ;;
        lint)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            run_test_suite "lint" "Linting and Formatting Checks"
            collect_reports
            ;;
        contracts)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            run_test_suite "contracts" "Contract Conformance Tests"
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            ;;
        all)
            if [ "$NO_BUILD" = false ]; then
                build_images
            fi
            start_services
            
            # Run all test suites
            FAILED_SUITES=()
            
            if ! run_test_suite "lint" "Linting and Formatting Checks"; then
                FAILED_SUITES+=("lint")
            fi
            
            if ! run_test_suite "unit" "Unit Tests"; then
                FAILED_SUITES+=("unit")
            fi
            
            if ! run_test_suite "integration" "Integration Tests"; then
                FAILED_SUITES+=("integration")
            fi
            
            if ! run_test_suite "contracts" "Contract Conformance Tests"; then
                FAILED_SUITES+=("contracts")
            fi
            
            if ! run_test_suite "smoke" "Smoke Tests"; then
                FAILED_SUITES+=("smoke")
            fi
            
            if ! run_test_suite "performance" "Performance Tests"; then
                FAILED_SUITES+=("performance")
            fi
            
            if [ "$KEEP_SERVICES" = false ]; then
                stop_services
            fi
            collect_reports
            
            # Report results
            if [ ${#FAILED_SUITES[@]} -eq 0 ]; then
                print_success "All test suites passed!"
                exit 0
            else
                print_error "Failed test suites: ${FAILED_SUITES[*]}"
                exit 1
            fi
            ;;
        "")
            print_error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            print_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Trap to ensure cleanup on exit
trap 'if [ "$KEEP_SERVICES" = false ]; then stop_services; fi' EXIT

# Run main function
main
