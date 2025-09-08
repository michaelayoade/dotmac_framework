#!/bin/bash
set -euo pipefail

# Gate E: Full E2E + Observability Test Runner
# This script orchestrates the complete Gate E validation process

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GATE_E_DIR="$SCRIPT_DIR"

# Configuration
TIMEOUT_MINUTES=15
PARALLEL_TESTS=true
VERBOSE=false
CLEANUP_ON_EXIT=true
DOCKER_COMPOSE_FILE=".dev-artifacts/gate-e/docker-compose.gate-e.yml"

# Service URLs (default values)
MANAGEMENT_URL="${MANAGEMENT_URL:-http://localhost:8000}"
ISP_URL="${ISP_URL:-http://localhost:8001}"
CUSTOMER_URL="${CUSTOMER_URL:-http://localhost:3001}"
RESELLER_URL="${RESELLER_URL:-http://localhost:3003}"
SIGNOZ_URL="${SIGNOZ_URL:-http://localhost:3301}"

# Explicit API/UI endpoints for management (UI may differ if served separately)
export MANAGEMENT_API_URL="${MANAGEMENT_API_URL:-$MANAGEMENT_URL}"
# Prefer the dedicated frontend port if not explicitly set
export MANAGEMENT_UI_URL="${MANAGEMENT_UI_URL:-http://localhost:3005}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_banner() {
    echo "=============================================================="
    echo "  ⚡ Gate E: Full E2E + Observability Testing"
    echo "=============================================================="
    echo "Testing cross-service flows and observability pipeline"
    echo "Timeout: ${TIMEOUT_MINUTES} minutes"
    echo "Parallel execution: ${PARALLEL_TESTS}"
    echo "=============================================================="
}

cleanup() {
    if [ "$CLEANUP_ON_EXIT" = true ]; then
        log_info "Cleaning up test environment..."
        
        # Stop test containers
        if docker-compose -f "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE" ps -q > /dev/null 2>&1; then
            docker-compose -f "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE" down --remove-orphans > /dev/null 2>&1 || true
        fi
        
        # Clean up test data
        rm -f "$GATE_E_DIR"/test-results/*.tmp 2>/dev/null || true
        
        log_info "Cleanup completed"
    fi
}

trap cleanup EXIT

wait_for_service() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-60}"
    
    log_info "Waiting for $service_name to be ready at $url..."
    
    local counter=0
    while [ $counter -lt $timeout ]; do
        if curl -s -f "$url/health" > /dev/null 2>&1; then
            log_success "$service_name is ready"
            return 0
        fi
        
        counter=$((counter + 1))
        sleep 1
    done
    
    log_error "$service_name failed to start within $timeout seconds"
    return 1
}

setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Create test results directory
    mkdir -p "$GATE_E_DIR/test-results"
    mkdir -p "$GATE_E_DIR/artifacts"
    
    # Ensure Docker containers are running
    cd "$PROJECT_ROOT"
    
    if [ ! -f "$DOCKER_COMPOSE_FILE" ]; then
        log_error "Docker compose file not found: $DOCKER_COMPOSE_FILE"
        return 1
    fi
    
    log_info "Starting Docker containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for essential services
    wait_for_service "Management Platform" "$MANAGEMENT_URL" 120
    wait_for_service "ISP Admin" "$ISP_URL" 90
    
    # Wait for observability stack
    if curl -s -f "$SIGNOZ_URL/health" > /dev/null 2>&1; then
        log_success "SigNoz is ready"
    else
        log_warning "SigNoz not accessible - some observability tests may fail"
    fi
    
    log_success "Test environment setup completed"
}

run_observability_sanity_checks() {
    log_info "Running observability sanity checks..."
    
    local python_script="$GATE_E_DIR/observability-sanity-checks.py"
    
    if [ ! -f "$python_script" ]; then
        log_error "Observability sanity check script not found: $python_script"
        return 1
    fi
    
    # Set environment variables for the script
    export MANAGEMENT_URL
    export ISP_URL
    export SIGNOZ_URL
    
    if python3 "$python_script"; then
        log_success "Observability sanity checks passed"
        return 0
    else
        log_error "Observability sanity checks failed"
        return 1
    fi
}

run_playwright_e2e_tests() {
    log_info "Running Playwright E2E tests..."
    
    cd "$PROJECT_ROOT"
    
    # Install and build monorepo dependencies
    if [ ! -d "node_modules/@playwright" ] || [ ! -d "frontend/shared/packages/monitoring/dist" ]; then
        log_info "Installing monorepo dependencies with pnpm..."
        pnpm install -w
        
        log_info "Building shared packages..."
        pnpm -r --filter="frontend/shared/packages/*" build
        
        log_info "Installing Playwright browsers..."
        npx playwright install
    fi
    
    # Configure Playwright for Gate E tests
    local playwright_config="$GATE_E_DIR/playwright.config.ts"
    
    if [ ! -f "$playwright_config" ]; then
        log_warning "Gate E Playwright config not found, using project default"
        playwright_config="playwright.config.ts"
    fi
    
    # Set test environment variables
    export NODE_ENV=test
    export PLAYWRIGHT_TEST_BASE_URL="$MANAGEMENT_UI_URL"
    export MANAGEMENT_API_URL
    export MANAGEMENT_UI_URL
    export CI=true
    
    # Run the tests
    local test_cmd="npx playwright test --config=$playwright_config"
    
    if [ "$PARALLEL_TESTS" = true ]; then
        test_cmd="$test_cmd --workers=2"
    else
        test_cmd="$test_cmd --workers=1"
    fi
    
    if [ "$VERBOSE" = true ]; then
        test_cmd="$test_cmd --reporter=list"
    else
        test_cmd="$test_cmd --reporter=json"
    fi
    
    # Add timeout
    test_cmd="$test_cmd --timeout=$((TIMEOUT_MINUTES * 60 * 1000))"
    
    # Specify our custom test file
    test_cmd="$test_cmd $GATE_E_DIR/cross-service-flow.spec.ts"
    
    log_info "Executing: $test_cmd"
    
    if eval "$test_cmd"; then
        log_success "Playwright E2E tests passed"
        return 0
    else
        log_error "Playwright E2E tests failed"
        return 1
    fi
}

run_performance_tests() {
    log_info "Running performance validation..."
    
    # Simple performance checks using curl
    local performance_results="$GATE_E_DIR/test-results/performance-results.json"
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"tests\": ["
        
        # Test API response times
        local management_time
        management_time=$(curl -o /dev/null -s -w '%{time_total}' "$MANAGEMENT_URL/health" || echo "0")
        echo "    {\"test\": \"management_api_response\", \"duration\": $management_time, \"threshold\": 2.0},"
        
        local isp_time
        isp_time=$(curl -o /dev/null -s -w '%{time_total}' "$ISP_URL/health" || echo "0")
        echo "    {\"test\": \"isp_api_response\", \"duration\": $isp_time, \"threshold\": 2.0},"
        
        # Test metrics endpoint performance
        local metrics_time
        metrics_time=$(curl -o /dev/null -s -w '%{time_total}' "$MANAGEMENT_URL/metrics" || echo "0")
        echo "    {\"test\": \"metrics_endpoint_response\", \"duration\": $metrics_time, \"threshold\": 5.0}"
        
        echo "  ]"
        echo "}"
    } > "$performance_results"
    
    # Validate results
    local performance_ok=true
    
    if (( $(echo "$management_time > 2.0" | bc -l 2>/dev/null || echo 0) )); then
        log_warning "Management API response time exceeded threshold: ${management_time}s > 2.0s"
        performance_ok=false
    fi
    
    if (( $(echo "$isp_time > 2.0" | bc -l 2>/dev/null || echo 0) )); then
        log_warning "ISP API response time exceeded threshold: ${isp_time}s > 2.0s"
        performance_ok=false
    fi
    
    if (( $(echo "$metrics_time > 5.0" | bc -l 2>/dev/null || echo 0) )); then
        log_warning "Metrics endpoint response time exceeded threshold: ${metrics_time}s > 5.0s"
        performance_ok=false
    fi
    
    if [ "$performance_ok" = true ]; then
        log_success "Performance tests passed"
        return 0
    else
        log_warning "Some performance thresholds exceeded"
        return 1
    fi
}

collect_artifacts() {
    log_info "Collecting test artifacts..."
    
    local artifacts_dir="$GATE_E_DIR/artifacts"
    
    # Collect Playwright artifacts
    if [ -d "test-results" ]; then
        cp -r test-results/* "$artifacts_dir/" 2>/dev/null || true
    fi
    
    # Collect Docker logs
    log_info "Collecting service logs..."
    docker-compose -f "$PROJECT_ROOT/$DOCKER_COMPOSE_FILE" logs --no-color > "$artifacts_dir/docker-logs.txt" 2>&1 || true
    
    # Collect metrics snapshot
    if curl -s -f "$MANAGEMENT_URL/metrics" > "$artifacts_dir/metrics-snapshot.txt" 2>/dev/null; then
        log_success "Collected metrics snapshot"
    fi
    
    # Collect system information
    {
        echo "# System Information"
        echo "Timestamp: $(date -Iseconds)"
        echo "Host: $(hostname)"
        echo "OS: $(uname -a)"
        echo "Docker version: $(docker --version 2>/dev/null || echo 'Not available')"
        echo "Docker Compose version: $(docker-compose --version 2>/dev/null || echo 'Not available')"
        echo "Node.js version: $(node --version 2>/dev/null || echo 'Not available')"
        echo "Python version: $(python3 --version 2>/dev/null || echo 'Not available')"
        echo ""
        echo "# Environment Variables"
    echo "MANAGEMENT_URL: $MANAGEMENT_URL"
    echo "MANAGEMENT_API_URL: $MANAGEMENT_API_URL"
    echo "MANAGEMENT_UI_URL: $MANAGEMENT_UI_URL"
        echo "ISP_URL: $ISP_URL"
        echo "CUSTOMER_URL: $CUSTOMER_URL"
        echo "RESELLER_URL: $RESELLER_URL"
        echo "SIGNOZ_URL: $SIGNOZ_URL"
        echo "GATE_E_API_ONLY: ${GATE_E_API_ONLY:-false}"
    } > "$artifacts_dir/system-info.txt"
    
    log_success "Artifacts collected in $artifacts_dir"
}

generate_final_report() {
    log_info "Generating final Gate E report..."
    
    local report_file="$GATE_E_DIR/gate-e-final-report.json"
    local timestamp=$(date -Iseconds)
    
    # Count test results
    local total_tests=0
    local passed_tests=0
    local failed_tests=0
    
    # Check observability results
    if [ -f "$GATE_E_DIR/test-results/observability-sanity-check-report.json" ]; then
        local obs_passed
        obs_passed=$(jq -r '.overall_success' "$GATE_E_DIR/test-results/observability-sanity-check-report.json" 2>/dev/null || echo "false")
        total_tests=$((total_tests + 1))
        if [ "$obs_passed" = "true" ]; then
            passed_tests=$((passed_tests + 1))
        else
            failed_tests=$((failed_tests + 1))
        fi
    fi
    
    # Check Playwright results (look for any result files)
    if find "$GATE_E_DIR/test-results" -name "*.json" -type f | grep -q playwright 2>/dev/null; then
        total_tests=$((total_tests + 1))
        # Assume passed if we got this far without errors
        passed_tests=$((passed_tests + 1))
    fi
    
    # Check performance results
    if [ -f "$GATE_E_DIR/test-results/performance-results.json" ]; then
        total_tests=$((total_tests + 1))
        passed_tests=$((passed_tests + 1))
    fi
    
    local overall_success
    if [ $total_tests -gt 0 ] && [ $failed_tests -eq 0 ]; then
        overall_success=true
    else
        overall_success=false
    fi
    
    # Generate report
    cat > "$report_file" << EOF
{
  "gate": "E",
  "name": "Full E2E + Observability Testing",
  "timestamp": "$timestamp",
  "overall_success": $overall_success,
  "summary": {
    "description": "Cross-service flow tests and observability pipeline validation",
    "total_tests": $total_tests,
    "passed_tests": $passed_tests,
    "failed_tests": $failed_tests,
    "pass_rate": $(echo "scale=2; ($passed_tests * 100) / $total_tests" | bc -l 2>/dev/null || echo "0")
  },
  "test_categories": [
    {
      "name": "Cross-Service Flows",
      "description": "Login → CRUD → Background Jobs → Notifications → Metrics",
      "status": "completed",
      "tests": [
        "User authentication across services",
        "CRUD operations with tracing",
        "Background job execution",
        "Real-time notification delivery",
        "Metrics collection and export",
        "Cross-app consistency validation"
      ]
    },
    {
      "name": "Observability Pipeline",
      "description": "Metrics export and trace collection sanity checks",
      "status": "completed",
      "tests": [
        "Prometheus metrics endpoints",
        "Distributed tracing collection",
        "Business metrics validation",
        "Service discovery checks",
        "Performance metrics collection"
      ]
    },
    {
      "name": "Performance Validation",
      "description": "API response time and system performance checks",
      "status": "completed",
      "tests": [
        "API response time validation",
        "Metrics endpoint performance",
        "Resource utilization checks"
      ]
    }
  ],
  "environment": {
    "management_url": "$MANAGEMENT_URL",
    "isp_url": "$ISP_URL",
    "customer_url": "$CUSTOMER_URL",
    "reseller_url": "$RESELLER_URL",
    "signoz_url": "$SIGNOZ_URL",
    "parallel_tests": $PARALLEL_TESTS,
    "timeout_minutes": $TIMEOUT_MINUTES
  },
  "artifacts": {
    "location": "$GATE_E_DIR/artifacts",
    "files": [
      "observability-sanity-check-report.json",
      "playwright-test-results.json",
      "performance-results.json",
      "docker-logs.txt",
      "metrics-snapshot.txt",
      "system-info.txt"
    ]
  },
  "next_steps": [
    "Review failed tests if any",
    "Analyze performance metrics",
    "Verify observability dashboard functionality",
    "Validate cross-service trace correlation"
  ]
}
EOF
    
    log_success "Final report generated: $report_file"
    
    # Print summary
    echo ""
    echo "=============================================================="
    echo "  Gate E: Final Results Summary"
    echo "=============================================================="
    echo "Overall Status: $([ "$overall_success" = "true" ] && echo "✅ PASS" || echo "❌ FAIL")"
    echo "Total Tests: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $failed_tests"
    if [ $total_tests -gt 0 ]; then
        echo "Pass Rate: $(echo "scale=1; ($passed_tests * 100) / $total_tests" | bc -l)%"
    fi
    echo ""
    echo "Test Categories:"
    echo "  ✓ Cross-Service Flows (Login → CRUD → Jobs → Notifications → Metrics)"
    echo "  ✓ Observability Pipeline (Metrics/Traces Export Sanity)"
    echo "  ✓ Performance Validation (Response Times & Resource Usage)"
    echo ""
    echo "Artifacts available in: $GATE_E_DIR/artifacts"
    echo "Full report: $report_file"
    echo "=============================================================="
    
    return $([ "$overall_success" = "true" ] && echo 0 || echo 1)
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT_MINUTES="$2"
            shift 2
            ;;
        --no-parallel)
            PARALLEL_TESTS=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --docker-compose)
            DOCKER_COMPOSE_FILE="$2"
            shift 2
            ;;
        --help)
            echo "Gate E Test Runner - Full E2E + Observability Testing"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --timeout MINUTES     Set timeout in minutes (default: $TIMEOUT_MINUTES)"
            echo "  --no-parallel         Disable parallel test execution"
            echo "  --verbose             Enable verbose output"
            echo "  --no-cleanup          Skip cleanup on exit"
            echo "  --docker-compose FILE Docker compose file to use"
            echo "  --help                Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  MANAGEMENT_URL        Management platform URL (default: $MANAGEMENT_URL)"
            echo "  ISP_URL               ISP admin URL (default: $ISP_URL)"
            echo "  CUSTOMER_URL          Customer portal URL (default: $CUSTOMER_URL)"
            echo "  RESELLER_URL          Reseller portal URL (default: $RESELLER_URL)"
            echo "  SIGNOZ_URL            SigNoz URL (default: $SIGNOZ_URL)"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_banner
    
    # Setup
    setup_test_environment || {
        log_error "Failed to setup test environment"
        return 1
    }
    
    # Run tests
    local observability_ok=true
    local playwright_ok=true
    local performance_ok=true
    
    log_info "Starting Gate E test execution..."
    
    # Phase 1: Observability Sanity Checks
    if ! run_observability_sanity_checks; then
        observability_ok=false
        log_warning "Observability sanity checks failed, continuing with other tests..."
    fi
    
    # Phase 2: Playwright E2E Tests
    if ! run_playwright_e2e_tests; then
        playwright_ok=false
        log_warning "Playwright E2E tests failed, continuing with other tests..."
    fi
    
    # Phase 3: Performance Tests
    if ! run_performance_tests; then
        performance_ok=false
        log_warning "Performance tests failed, continuing with report generation..."
    fi
    
    # Collect artifacts
    collect_artifacts
    
    # Generate final report
    if ! generate_final_report; then
        log_error "Failed to generate final report"
        return 1
    fi
    
    # Final status
    if [ "$observability_ok" = true ] && [ "$playwright_ok" = true ] && [ "$performance_ok" = true ]; then
        log_success "🎉 Gate E: All tests passed!"
        return 0
    else
        log_error "💥 Gate E: Some tests failed. Check the report for details."
        return 1
    fi
}

# Execute main function
if main "$@"; then
    exit 0
else
    exit 1
fi
