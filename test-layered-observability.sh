#!/bin/bash
# Test Script: Validate Layered Observability Integration
# Purpose: Comprehensive testing of the fixed observability in layered CI/CD

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

# Test configuration availability
test_configuration_fixes() {
    log "INFO" "Testing critical configuration fixes..."
    
    # Test the core fixes from the conversation summary:
    # 1. create_default_config availability
    # 2. ExporterConfig/ExporterType classes
    # 3. Fixed imports
    
    local temp_test_script="/tmp/test_observability_config.py"
    
    cat > "$temp_test_script" << 'EOF'
#!/usr/bin/env python3
import sys
import os

# Add platform services to path
project_root = "/home/dotmac_framework"  # Fixed absolute path
sys.path.insert(0, os.path.join(project_root, "packages/dotmac-platform-services/src"))

try:
    # Test the critical imports that were previously failing
    from dotmac.platform.observability import create_default_config, ExporterConfig, ExporterType
    
    # Test config creation
    config = create_default_config(
        service_name='test-layered-service',
        environment='development',
        tracing_exporters=['console'],
        metrics_exporters=['console']
    )
    
    print("SUCCESS: create_default_config working")
    print(f"SUCCESS: Config created with service_name: {config.service_name}")
    print(f"SUCCESS: Environment: {config.environment}")
    print(f"SUCCESS: Tracing exporters: {len(config.tracing_exporters)}")
    print(f"SUCCESS: Metrics exporters: {len(config.metrics_exporters)}")
    
    # Test ExporterType enum
    prometheus_type = ExporterType.PROMETHEUS
    console_type = ExporterType.CONSOLE
    otlp_type = ExporterType.OTLP_GRPC
    
    print("SUCCESS: ExporterType enum working")
    
    # Test ExporterConfig creation
    test_exporter = ExporterConfig(
        type=ExporterType.CONSOLE,
        timeout=30000
    )
    
    print("SUCCESS: ExporterConfig class working")
    
    sys.exit(0)
    
except Exception as e:
    print(f"ERROR: Configuration test failed: {e}")
    sys.exit(1)
EOF

    if python3 "$temp_test_script"; then
        log "SUCCESS" "Configuration fixes validated"
        rm -f "$temp_test_script"
        return 0
    else
        log "ERROR" "Configuration fixes validation failed"
        rm -f "$temp_test_script"
        return 1
    fi
}

# Test Docker layer structure
test_docker_layers() {
    log "INFO" "Testing Docker layer structure..."
    
    local layers=("docker-compose.e-0a.yml" "docker-compose.e-0b.yml" "docker-compose.e-0c.yml")
    
    for layer in "${layers[@]}"; do
        if [ -f "$layer" ]; then
            log "SUCCESS" "$layer exists"
            
            # Validate layer syntax
            if docker compose -f "$layer" config >/dev/null 2>&1; then
                log "SUCCESS" "$layer syntax valid"
            else
                log "ERROR" "$layer has syntax errors"
                return 1
            fi
        else
            log "ERROR" "$layer missing"
            return 1
        fi
    done
    
    return 0
}

# Test environment requirements
test_environment() {
    log "INFO" "Testing environment requirements..."
    
    local required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "CLICKHOUSE_PASSWORD" "VAULT_TOKEN")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        else
            log "SUCCESS" "$var is set"
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log "ERROR" "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    return 0
}

# Test observability endpoints
test_observability_endpoints() {
    log "INFO" "Testing observability endpoints..."
    
    # Define endpoints with their expected behavior
    declare -A endpoints=(
        ["ClickHouse HTTP"]="localhost:8123:/ping"
        ["SignOz Collector Metrics"]="localhost:8889:/metrics"
        ["SignOz Query Health"]="localhost:8080:/api/v1/health"
        ["SignOz Frontend"]="localhost:3301:/"
    )
    
    local failed_endpoints=()
    
    for name in "${!endpoints[@]}"; do
        local endpoint="${endpoints[$name]}"
        local host_port="${endpoint%:*}"
        local path="${endpoint##*:}"
        local url="http://$host_port$path"
        
        log "INFO" "Testing $name endpoint: $url"
        
        if timeout 10 curl -sf "$url" >/dev/null 2>&1; then
            log "SUCCESS" "$name endpoint accessible"
        else
            log "WARNING" "$name endpoint not accessible (may not be started yet)"
            failed_endpoints+=("$name")
        fi
    done
    
    # For testing purposes, we allow some endpoints to be down
    if [ ${#failed_endpoints[@]} -eq ${#endpoints[@]} ]; then
        log "ERROR" "All observability endpoints are down"
        return 1
    fi
    
    return 0
}

# Test application startup simulation
test_application_startup() {
    log "INFO" "Testing application startup simulation..."
    
    # Create a simple test script that simulates application startup with observability
    local test_app_script="/tmp/test_app_startup.py"
    
    cat > "$test_app_script" << 'EOF'
#!/usr/bin/env python3
import sys
import os
import asyncio
import logging

# Set up environment
os.environ['ENVIRONMENT'] = 'development'
os.environ['DEBUG'] = 'true'

# Add paths
project_root = "/home/dotmac_framework"  # Fixed absolute path
sys.path.insert(0, os.path.join(project_root, "packages/dotmac-platform-services/src"))
sys.path.insert(0, os.path.join(project_root, "packages/dotmac-core/src"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_observability_startup():
    """Test that observability can be initialized without errors"""
    
    try:
        # Test observability initialization
        from dotmac.platform.observability import initialize_observability_service
        
        config = {
            'service_name': 'test-layered-app',
            'environment': 'test',
            'log_level': 'INFO'
        }
        
        # This should not throw the previous "NoneType not callable" errors
        initialize_observability_service(config)
        
        logger.info("SUCCESS: Observability service initialized without errors")
        return True
        
    except Exception as e:
        logger.error(f"ERROR: Observability startup failed: {e}")
        return False

async def main():
    logger.info("Testing application startup with observability...")
    
    success = await test_observability_startup()
    
    if success:
        logger.info("SUCCESS: Application startup simulation passed")
        sys.exit(0)
    else:
        logger.error("ERROR: Application startup simulation failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
EOF

    if python3 "$test_app_script"; then
        log "SUCCESS" "Application startup simulation passed"
        rm -f "$test_app_script"
        return 0
    else
        log "ERROR" "Application startup simulation failed"
        rm -f "$test_app_script"
        return 1
    fi
}

# Test layer dependencies
test_layer_dependencies() {
    log "INFO" "Testing layer dependency structure..."
    
    # E-0a should not depend on external networks
    if grep -q "external: true" "docker-compose.e-0a.yml"; then
        log "ERROR" "E-0a should not depend on external networks"
        return 1
    else
        log "SUCCESS" "E-0a is self-contained"
    fi
    
    # E-0b should use the network from E-0a
    if grep -q "external: true" "docker-compose.e-0b.yml"; then
        log "SUCCESS" "E-0b correctly references external network from E-0a"
    else
        log "ERROR" "E-0b should reference external network from E-0a"
        return 1
    fi
    
    # E-0c should use the network from E-0a
    if grep -q "external: true" "docker-compose.e-0c.yml"; then
        log "SUCCESS" "E-0c correctly references external network from E-0a"
    else
        log "ERROR" "E-0c should reference external network from E-0a"
        return 1
    fi
    
    return 0
}

# Main test function
main() {
    echo "🧪 Layered Observability Integration Test Suite"
    echo "=============================================="
    echo ""
    
    local test_results=()
    local failed_tests=()
    
    # Run test suite
    echo "Phase 1: Configuration and Structure Tests"
    echo "==========================================="
    
    if test_configuration_fixes; then
        test_results+=("✅ Configuration Fixes")
    else
        test_results+=("❌ Configuration Fixes")
        failed_tests+=("Configuration Fixes")
    fi
    
    if test_docker_layers; then
        test_results+=("✅ Docker Layer Structure")
    else
        test_results+=("❌ Docker Layer Structure")
        failed_tests+=("Docker Layer Structure")
    fi
    
    if test_layer_dependencies; then
        test_results+=("✅ Layer Dependencies")
    else
        test_results+=("❌ Layer Dependencies")
        failed_tests+=("Layer Dependencies")
    fi
    
    echo ""
    echo "Phase 2: Environment and Runtime Tests"
    echo "======================================"
    
    if test_environment; then
        test_results+=("✅ Environment Variables")
    else
        test_results+=("❌ Environment Variables")
        failed_tests+=("Environment Variables")
    fi
    
    if test_application_startup; then
        test_results+=("✅ Application Startup Simulation")
    else
        test_results+=("❌ Application Startup Simulation")
        failed_tests+=("Application Startup Simulation")
    fi
    
    echo ""
    echo "Phase 3: Observability Infrastructure Tests"
    echo "==========================================="
    
    if test_observability_endpoints; then
        test_results+=("✅ Observability Endpoints")
    else
        test_results+=("⚠️  Observability Endpoints (services may be down)")
        # Don't count this as a critical failure for now
    fi
    
    # Display results
    echo ""
    echo "📊 Test Results Summary"
    echo "======================"
    for result in "${test_results[@]}"; do
        echo "$result"
    done
    
    echo ""
    
    if [ ${#failed_tests[@]} -eq 0 ]; then
        log "SUCCESS" "All critical tests passed! 🎉"
        echo ""
        echo "✅ Ready for layered deployment with:"
        echo "   ./deploy-layered-observability.sh deploy"
        echo ""
        return 0
    else
        log "ERROR" "${#failed_tests[@]} critical test(s) failed"
        echo ""
        echo "❌ Failed tests that need attention:"
        for test in "${failed_tests[@]}"; do
            echo "   - $test"
        done
        echo ""
        echo "🔧 Please address the failed tests before deployment"
        return 1
    fi
}

# Handle script interruption
trap 'log "WARNING" "Testing interrupted by user"; exit 1' INT TERM

# Execute main function
main "$@"