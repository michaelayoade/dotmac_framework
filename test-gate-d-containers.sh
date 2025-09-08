#!/bin/bash
# Gate D: Containers - Docker build + compose smoke tests with dependency approach
# Purpose: Validate Docker builds and dependency-based container startup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO") echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" ;;
        "WARNING") echo -e "${YELLOW}[WARNING]${NC} ${timestamp} - $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" ;;
    esac
}

# Track results
declare -a PASSED_TESTS=()
declare -a FAILED_TESTS=()
declare -a WARNINGS=()

# Function to run test and track results
run_test() {
    local test_name="$1"
    local test_command="$2"
    local required="${3:-true}"
    
    log "INFO" "Running $test_name..."
    
    if eval "$test_command" >/tmp/gate_d_${test_name//[^a-zA-Z0-9]/_}.log 2>&1; then
        log "SUCCESS" "$test_name passed"
        PASSED_TESTS+=("$test_name")
        return 0
    else
        if [ "$required" = "true" ]; then
            log "ERROR" "$test_name failed (REQUIRED)"
            FAILED_TESTS+=("$test_name")
            echo "Last 15 lines of output:"
            tail -15 "/tmp/gate_d_${test_name//[^a-zA-Z0-9]/_}.log" | sed 's/^/  /'
        else
            log "WARNING" "$test_name failed (OPTIONAL)"
            WARNINGS+=("$test_name")
        fi
        return 1
    fi
}

# Function to check Docker prerequisites
check_docker_prerequisites() {
    log "INFO" "Checking Docker prerequisites"
    
    run_test "docker_available" \
        "docker --version" \
        true
        
    run_test "docker_compose_available" \
        "docker compose version" \
        true
        
    run_test "docker_daemon_running" \
        "docker ps" \
        true
}

# Function to build Docker images
build_docker_images() {
    log "INFO" "Building Docker images"
    
    # Build ISP Framework image if Dockerfile exists
    if [ -f "Dockerfile.isp" ] || [ -f "isp-framework/Dockerfile" ]; then
        local dockerfile_path
        if [ -f "Dockerfile.isp" ]; then
            dockerfile_path="Dockerfile.isp"
        else
            dockerfile_path="isp-framework/Dockerfile"
        fi
        
        run_test "build_isp_image" \
            "docker build -f $dockerfile_path -t dotmac/isp:gate-d-test ." \
            true
    else
        log "WARNING" "No ISP Framework Dockerfile found"
        WARNINGS+=("no_isp_dockerfile")
    fi
    
    # Build Management Platform image if Dockerfile exists
    if [ -f "Dockerfile.management" ] || [ -f "management-platform/Dockerfile" ]; then
        local dockerfile_path
        if [ -f "Dockerfile.management" ]; then
            dockerfile_path="Dockerfile.management"
        else
            dockerfile_path="management-platform/Dockerfile"
        fi
        
        run_test "build_management_image" \
            "docker build -f $dockerfile_path -t dotmac/management:gate-d-test ." \
            true
    else
        log "WARNING" "No Management Platform Dockerfile found"
        WARNINGS+=("no_management_dockerfile")
    fi
}

# Function to setup test environment with OpenBao secrets
setup_test_environment() {
    log "INFO" "Setting up test environment with dependency-based approach"
    
    # Generate test environment secrets
    cat > /tmp/gate_d_test.env << EOF
POSTGRES_PASSWORD=gate_d_test_postgres_pass
REDIS_PASSWORD=gate_d_test_redis_pass
CLICKHOUSE_PASSWORD=gate_d_test_clickhouse_pass
VAULT_TOKEN=gate-d-test-token
MGMT_SECRET_KEY=gate_d_test_mgmt_secret
MGMT_JWT_SECRET_KEY=gate_d_test_jwt_secret
POSTGRES_USER=dotmac_admin
ENVIRONMENT=testing
APP_VERSION=gate-d-test
EOF

    # Load test environment
    export $(cat /tmp/gate_d_test.env | xargs)
}

# Function to test layered container startup (dependency approach)
test_layered_container_startup() {
    log "INFO" "Testing dependency-based container startup"
    
    # Test Gate E-0a (Core Infrastructure)
    log "INFO" "Testing Gate E-0a startup..."
    
    run_test "gate_e0a_startup" \
        "docker compose -f docker-compose.e-0a.yml up -d" \
        true
        
    if [ $? -eq 0 ]; then
        # Wait for services to initialize
        log "INFO" "Waiting for Gate E-0a services to initialize..."
        sleep 15
        
        # Test Gate E-0a health
        run_test "gate_e0a_postgres_health" \
            "docker compose -f docker-compose.e-0a.yml exec -T postgres-shared pg_isready -U dotmac_admin" \
            true
            
        run_test "gate_e0a_redis_health" \
            "docker compose -f docker-compose.e-0a.yml exec -T redis-shared redis-cli ping" \
            true
            
        # Test Gate E-0b (Observability Infrastructure)
        log "INFO" "Testing Gate E-0b startup..."
        
        run_test "gate_e0b_startup" \
            "docker compose -f docker-compose.e-0b.yml up -d" \
            true
            
        if [ $? -eq 0 ]; then
            # Wait for observability services
            log "INFO" "Waiting for Gate E-0b services to initialize..."
            sleep 30
            
            # Test observability health
            run_test "gate_e0b_clickhouse_health" \
                "timeout 30 bash -c 'until curl -f http://localhost:8123/ping; do sleep 2; done'" \
                true
                
            run_test "gate_e0b_collector_health" \
                "timeout 30 bash -c 'until curl -f http://localhost:8889/metrics; do sleep 2; done'" \
                false
        fi
        
        # Test Gate E-0c (Applications) if images were built
        if docker image inspect dotmac/isp:gate-d-test >/dev/null 2>&1 || docker image inspect dotmac/management:gate-d-test >/dev/null 2>&1; then
            log "INFO" "Testing Gate E-0c startup with built images..."
            
            # Temporarily update compose file to use test images
            if [ -f "docker-compose.e-0c.yml" ]; then
                # Create test version of E-0c compose
                sed 's/target: development/image: dotmac\/isp:gate-d-test/g' docker-compose.e-0c.yml > docker-compose.e-0c-test.yml 2>/dev/null || cp docker-compose.e-0c.yml docker-compose.e-0c-test.yml
                
                run_test "gate_e0c_startup" \
                    "timeout 120 docker compose -f docker-compose.e-0c-test.yml up -d --no-build" \
                    false
                    
                if [ $? -eq 0 ]; then
                    # Wait for applications
                    log "INFO" "Waiting for applications to initialize..."
                    sleep 45
                    
                    # Test application health endpoints
                    run_test "isp_health_endpoint" \
                        "timeout 30 bash -c 'until curl -f http://localhost:8001/health; do sleep 3; done'" \
                        false
                        
                    run_test "management_health_endpoint" \
                        "timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 3; done'" \
                        false
                fi
                
                rm -f docker-compose.e-0c-test.yml
            fi
        else
            log "INFO" "Skipping Gate E-0c tests - no built images available"
        fi
    fi
}

# Function to test basic API functionality
test_basic_api_functionality() {
    log "INFO" "Testing basic API functionality"
    
    # Test ISP Framework API
    if timeout 5 curl -sf http://localhost:8001/health >/dev/null 2>&1; then
        run_test "isp_api_docs" \
            "curl -f http://localhost:8001/docs" \
            false
            
        # Test basic API endpoint if available
        run_test "isp_basic_endpoint" \
            "curl -f -X GET http://localhost:8001/api/v1/health || curl -f http://localhost:8001/health" \
            false
    fi
    
    # Test Management Platform API
    if timeout 5 curl -sf http://localhost:8000/health >/dev/null 2>&1; then
        run_test "management_api_docs" \
            "curl -f http://localhost:8000/docs" \
            false
            
        run_test "management_basic_endpoint" \
            "curl -f -X GET http://localhost:8000/api/v1/health || curl -f http://localhost:8000/health" \
            false
    fi
}

# Function to test database migrations in containers
test_container_migrations() {
    log "INFO" "Testing database migrations in containers"
    
    # Test migrations in ISP container
    if docker ps | grep -q "dotmac-isp-framework"; then
        run_test "isp_container_migration" \
            "docker exec dotmac-isp-framework alembic current" \
            false
    fi
    
    # Test migrations in Management container
    if docker ps | grep -q "dotmac-management-platform"; then
        run_test "management_container_migration" \
            "docker exec dotmac-management-platform alembic current" \
            false
    fi
}

# Function to test observability integration
test_observability_integration() {
    log "INFO" "Testing observability integration in containers"
    
    # Test SignOz UI
    if timeout 5 curl -sf http://localhost:3301 >/dev/null 2>&1; then
        run_test "signoz_ui" \
            "curl -f http://localhost:3301" \
            false
    fi
    
    # Test metrics collection
    if timeout 5 curl -sf http://localhost:8889/metrics >/dev/null 2>&1; then
        run_test "metrics_collection" \
            "curl -s http://localhost:8889/metrics | grep -E '(otelcol_|dotmac_)'" \
            false
    fi
    
    # Test application metrics endpoints
    if timeout 5 curl -sf http://localhost:8001/metrics >/dev/null 2>&1; then
        run_test "isp_metrics_endpoint" \
            "curl -f http://localhost:8001/metrics" \
            false
    fi
    
    if timeout 5 curl -sf http://localhost:8000/metrics >/dev/null 2>&1; then
        run_test "management_metrics_endpoint" \
            "curl -f http://localhost:8000/metrics" \
            false
    fi
}

# Function to cleanup test resources
cleanup_test_resources() {
    log "INFO" "Cleaning up test resources"
    
    # Stop all layered services
    docker compose -f docker-compose.e-0c.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.e-0b.yml down --remove-orphans 2>/dev/null || true
    docker compose -f docker-compose.e-0a.yml down --remove-orphans 2>/dev/null || true
    
    # Remove test images
    docker rmi dotmac/isp:gate-d-test dotmac/management:gate-d-test 2>/dev/null || true
    
    # Cleanup temp files
    rm -f /tmp/gate_d_test.env docker-compose.e-0c-test.yml
    
    # Prune unused resources
    docker system prune -f >/dev/null 2>&1 || true
}

# Main execution
main() {
    echo "🔍 Gate D: Container Testing"
    echo "============================"
    echo "Testing Docker builds and dependency-based container startup"
    echo ""
    
    # Check prerequisites
    check_docker_prerequisites
    
    # Setup test environment
    setup_test_environment
    
    # Build images
    build_docker_images
    
    # Test layered container startup
    test_layered_container_startup
    
    # Test API functionality
    test_basic_api_functionality
    
    # Test database migrations
    test_container_migrations
    
    # Test observability integration
    test_observability_integration
    
    # Generate summary
    echo ""
    echo "📊 Gate D Results Summary"
    echo "========================="
    echo "✅ Passed Tests: ${#PASSED_TESTS[@]}"
    for test in "${PASSED_TESTS[@]}"; do
        echo "   - $test"
    done
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo ""
        echo "⚠️  Warnings: ${#WARNINGS[@]}"
        for warning in "${WARNINGS[@]}"; do
            echo "   - $warning"
        done
    fi
    
    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo ""
        echo "❌ Failed Tests: ${#FAILED_TESTS[@]}"
        for test in "${FAILED_TESTS[@]}"; do
            echo "   - $test"
        done
        
        echo ""
        log "ERROR" "Gate D FAILED - ${#FAILED_TESTS[@]} required tests failed"
        echo ""
        echo "🔧 Logs available in /tmp/gate_d_*.log"
        echo "🔧 Check Docker builds and container configurations"
        
        cleanup_test_resources
        return 1
    else
        echo ""
        log "SUCCESS" "Gate D PASSED - All required tests passed"
        
        if [ ${#WARNINGS[@]} -gt 0 ]; then
            echo ""
            echo "💡 Some optional tests failed - consider investigating for production readiness"
        fi
        
        echo ""
        echo "🎉 Ready to proceed to Gate E (Full E2E + Observability)"
        
        cleanup_test_resources
        return 0
    fi
}

# Handle interruption
trap 'log "WARNING" "Gate D testing interrupted"; cleanup_test_resources; exit 1' INT TERM

# Execute
main "$@"