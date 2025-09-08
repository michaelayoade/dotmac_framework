#!/bin/bash
# Gate B: DB + Integration - Database migrations, Redis tasks, API integration
# Purpose: Validate database operations and integration components

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
    
    if eval "$test_command" >/tmp/gate_b_${test_name//[^a-zA-Z0-9]/_}.log 2>&1; then
        log "SUCCESS" "$test_name passed"
        PASSED_TESTS+=("$test_name")
        return 0
    else
        if [ "$required" = "true" ]; then
            log "ERROR" "$test_name failed (REQUIRED)"
            FAILED_TESTS+=("$test_name")
            echo "Last 10 lines of output:"
            tail -10 "/tmp/gate_b_${test_name//[^a-zA-Z0-9]/_}.log" | sed 's/^/  /'
        else
            log "WARNING" "$test_name failed (OPTIONAL)"
            WARNINGS+=("$test_name")
        fi
        return 1
    fi
}

# Function to start ephemeral test database
start_test_database() {
    log "INFO" "Starting ephemeral PostgreSQL for testing"
    
    # Use our layered approach for test database
    if [ -f "docker-compose.e-0a.yml" ]; then
        # Use minimal test environment
        export POSTGRES_PASSWORD=test_password_gate_b
        export REDIS_PASSWORD=test_password_gate_b
        export VAULT_TOKEN=test-token-gate-b
        
        run_test "start_test_db" \
            "docker compose -f docker-compose.e-0a.yml up -d postgres-shared redis-shared" \
            true
        
        # Wait for services to be healthy
        log "INFO" "Waiting for test database to be ready..."
        sleep 10
        
        run_test "test_db_health" \
            "docker compose -f docker-compose.e-0a.yml exec -T postgres-shared pg_isready -U dotmac_admin" \
            true
            
        run_test "test_redis_health" \
            "docker compose -f docker-compose.e-0a.yml exec -T redis-shared redis-cli ping" \
            true
    else
        # Fallback to direct Docker approach
        run_test "start_test_db_fallback" \
            "docker run -d --name test-postgres-gate-b -e POSTGRES_PASSWORD=test_password -e POSTGRES_DB=test_db -p 5433:5432 postgres:15-alpine" \
            true
            
        run_test "start_test_redis_fallback" \
            "docker run -d --name test-redis-gate-b -p 6380:6379 redis:7-alpine redis-server --requirepass test_password" \
            true
            
        sleep 5
    fi
}

# Function to test database migrations
test_database_migrations() {
    log "INFO" "Testing database migrations"
    
    # Set up test database connection
    export DATABASE_URL="postgresql://dotmac_admin:test_password_gate_b@localhost:5434/dotmac_isp"
    
    if [ -f "alembic.ini" ]; then
        # Test migration upgrade
        run_test "migration_upgrade" \
            "alembic upgrade head" \
            true
            
        # Test migration rollback and re-upgrade
        run_test "migration_rollback_upgrade" \
            "alembic downgrade -1 && alembic upgrade head" \
            true
            
        # Test migration history
        run_test "migration_history" \
            "alembic history --verbose" \
            false
    else
        log "WARNING" "No alembic.ini found - skipping migration tests"
        WARNINGS+=("no_alembic_config")
    fi
}

# Function to test API startup and health
test_api_startup() {
    log "INFO" "Testing API startup and health endpoints"
    
    # Test ISP Framework startup
    if [ -f "src/dotmac_isp/app.py" ]; then
        export DATABASE_URL="postgresql://dotmac_admin:test_password_gate_b@localhost:5434/dotmac_isp"
        export REDIS_URL="redis://:test_password_gate_b@localhost:6378/0"
        export ENVIRONMENT="testing"
        
        # Create simple API test
        cat > /tmp/test_isp_startup.py << 'EOF'
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_api_startup():
    try:
        from dotmac_isp.app import create_app
        
        # Create app in test mode
        app = await create_app()
        
        if app:
            print("SUCCESS: ISP API startup successful")
            return True
        else:
            print("ERROR: ISP API creation returned None")
            return False
            
    except Exception as e:
        print(f"ERROR: ISP API startup failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api_startup())
    sys.exit(0 if result else 1)
EOF

        run_test "isp_api_startup" \
            "python /tmp/test_isp_startup.py" \
            true
    fi
    
    # Test Management Platform startup
    if [ -f "src/dotmac_management/main.py" ]; then
        export DATABASE_URL="postgresql://dotmac_admin:test_password_gate_b@localhost:5434/mgmt_platform"
        export REDIS_URL="redis://:test_password_gate_b@localhost:6378/3"
        export ENVIRONMENT="testing"
        
        cat > /tmp/test_mgmt_startup.py << 'EOF'
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_api_startup():
    try:
        from dotmac_management.main import create_app
        
        # Create app in test mode
        app = await create_app()
        
        if app:
            print("SUCCESS: Management API startup successful")
            return True
        else:
            print("ERROR: Management API creation returned None")
            return False
            
    except Exception as e:
        print(f"ERROR: Management API startup failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api_startup())
    sys.exit(0 if result else 1)
EOF

        run_test "mgmt_api_startup" \
            "python /tmp/test_mgmt_startup.py" \
            true
    fi
}

# Function to test task queue integration
test_task_queue() {
    log "INFO" "Testing task queue integration with Redis"
    
    # Create simple task queue test
    cat > /tmp/test_task_queue.py << 'EOF'
import redis
import json
import time
import sys

def test_redis_task_queue():
    try:
        # Connect to test Redis
        r = redis.Redis(host='localhost', port=6378, password='test_password_gate_b', db=1, decode_responses=True)
        
        # Test basic connectivity
        if not r.ping():
            print("ERROR: Cannot connect to Redis")
            return False
        
        # Test task enqueue/dequeue simulation
        task_data = {
            'task_id': 'test_task_123',
            'task_type': 'test_task',
            'data': {'message': 'Hello from Gate B test'}
        }
        
        # Enqueue task
        r.lpush('test_queue', json.dumps(task_data))
        
        # Dequeue task
        result = r.brpop('test_queue', timeout=5)
        
        if result:
            queue_name, task_json = result
            dequeued_task = json.loads(task_json)
            
            if dequeued_task['task_id'] == task_data['task_id']:
                print("SUCCESS: Task queue enqueue/dequeue working")
                return True
            else:
                print("ERROR: Task data mismatch")
                return False
        else:
            print("ERROR: Task dequeue timeout")
            return False
            
    except Exception as e:
        print(f"ERROR: Task queue test failed: {e}")
        return False

if __name__ == "__main__":
    result = test_redis_task_queue()
    sys.exit(0 if result else 1)
EOF

    run_test "redis_task_queue" \
        "python /tmp/test_task_queue.py" \
        true
}

# Function to test platform services
test_platform_services() {
    log "INFO" "Testing platform services integration"
    
    # Test observability configuration (from our previous fixes)
    if [ -f "packages/dotmac-platform-services/src/dotmac/platform/observability/config.py" ]; then
        cat > /tmp/test_observability.py << 'EOF'
import sys
import os

# Add platform services to path
sys.path.insert(0, 'packages/dotmac-platform-services/src')

def test_observability_config():
    try:
        from dotmac.platform.observability import create_default_config, ExporterConfig, ExporterType
        
        # Test config creation (this was the P0 fix)
        config = create_default_config(
            service_name='gate-b-test',
            environment='development'
        )
        
        if config and config.service_name == 'gate-b-test':
            print("SUCCESS: Observability configuration working")
            return True
        else:
            print("ERROR: Observability config creation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Observability test failed: {e}")
        return False

if __name__ == "__main__":
    result = test_observability_config()
    sys.exit(0 if result else 1)
EOF

        run_test "observability_config" \
            "python /tmp/test_observability.py" \
            true
    fi
    
    # Test auth services if available
    if [ -f "packages/dotmac-platform-services/src/dotmac/platform/auth/jwt_service.py" ]; then
        cat > /tmp/test_auth_services.py << 'EOF'
import sys
import os

# Add platform services to path
sys.path.insert(0, 'packages/dotmac-platform-services/src')

def test_jwt_service():
    try:
        from dotmac.platform.auth.jwt_service import JWTService
        
        # Test JWT service initialization
        jwt_service = JWTService(
            secret_key="test-secret-key-gate-b",
            algorithm="HS256",
            access_token_expire_minutes=30
        )
        
        if jwt_service:
            # Test token creation and validation
            test_data = {"sub": "test_user", "test": True}
            token = jwt_service.create_access_token(data=test_data)
            
            if token:
                decoded = jwt_service.verify_token(token)
                if decoded and decoded.get("sub") == "test_user":
                    print("SUCCESS: JWT service working")
                    return True
        
        print("ERROR: JWT service test failed")
        return False
        
    except Exception as e:
        print(f"ERROR: Auth service test failed: {e}")
        return False

if __name__ == "__main__":
    result = test_jwt_service()
    sys.exit(0 if result else 1)
EOF

        run_test "auth_services" \
            "python /tmp/test_auth_services.py" \
            false
    fi
}

# Function to cleanup test resources
cleanup_test_resources() {
    log "INFO" "Cleaning up test resources"
    
    if [ -f "docker-compose.e-0a.yml" ]; then
        docker compose -f docker-compose.e-0a.yml down --remove-orphans 2>/dev/null || true
    fi
    
    # Cleanup fallback containers
    docker stop test-postgres-gate-b test-redis-gate-b 2>/dev/null || true
    docker rm test-postgres-gate-b test-redis-gate-b 2>/dev/null || true
    
    # Cleanup temp files
    rm -f /tmp/test_*.py
}

# Main execution
main() {
    echo "🔍 Gate B: DB + Integration Testing"
    echo "==================================="
    echo "Testing database migrations, Redis tasks, API integration"
    echo ""
    
    # Start test infrastructure
    start_test_database
    
    # Test database operations
    test_database_migrations
    
    # Test API startup
    test_api_startup
    
    # Test task queue
    test_task_queue
    
    # Test platform services
    test_platform_services
    
    # Generate summary
    echo ""
    echo "📊 Gate B Results Summary"
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
        log "ERROR" "Gate B FAILED - ${#FAILED_TESTS[@]} required tests failed"
        echo ""
        echo "🔧 Logs available in /tmp/gate_b_*.log"
        echo "🔧 Check database connectivity and migration scripts"
        
        cleanup_test_resources
        return 1
    else
        echo ""
        log "SUCCESS" "Gate B PASSED - All required tests passed"
        
        echo ""
        echo "🎉 Ready to proceed to Gate C (Frontend Quality)"
        
        cleanup_test_resources
        return 0
    fi
}

# Handle interruption
trap 'log "WARNING" "Gate B testing interrupted"; cleanup_test_resources; exit 1' INT TERM

# Execute
main "$@"