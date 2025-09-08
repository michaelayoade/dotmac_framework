#!/bin/bash
# Gate E-0a Validation: Core Infrastructure Layer
# Purpose: Validate data persistence and secrets management are healthy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.e-0a.yml"

echo "🔍 Gate E-0a Validation: Core Infrastructure Layer"
echo "================================================"

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ ERROR: $COMPOSE_FILE not found"
    exit 1
fi

# Function to check service health
check_service_health() {
    local service_name="$1"
    local max_attempts=30
    local attempt=0
    
    echo "🔄 Checking $service_name health..."
    
    while [ $attempt -lt $max_attempts ]; do
        if docker compose -f "$COMPOSE_FILE" ps "$service_name" | grep -q "healthy"; then
            echo "✅ $service_name is healthy"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "   Attempt $attempt/$max_attempts - waiting for $service_name..."
        sleep 5
    done
    
    echo "❌ $service_name failed to become healthy after $((max_attempts * 5)) seconds"
    return 1
}

# Function to test connectivity
test_connectivity() {
    local service="$1"
    local host="$2" 
    local port="$3"
    local type="${4:-tcp}"
    
    echo "🔗 Testing $service connectivity ($type $host:$port)..."
    
    if [ "$type" = "tcp" ]; then
        if timeout 10 bash -c "</dev/tcp/$host/$port"; then
            echo "✅ $service is accessible"
            return 0
        fi
    elif [ "$type" = "http" ]; then
        if timeout 10 curl -sf "http://$host:$port/ping" >/dev/null; then
            echo "✅ $service HTTP endpoint is accessible"
            return 0
        fi
    fi
    
    echo "❌ $service is not accessible"
    return 1
}

# Start services
echo "🚀 Starting Gate E-0a services..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check service health
check_service_health "postgres-shared" || exit 1
check_service_health "redis-shared" || exit 1  
check_service_health "openbao-shared" || exit 1

# Test connectivity
test_connectivity "PostgreSQL" "localhost" "5434" "tcp" || exit 1
test_connectivity "Redis" "localhost" "6378" "tcp" || exit 1
test_connectivity "OpenBao" "localhost" "8200" "http" || exit 1

# Additional validation tests
echo "🧪 Running additional validation tests..."

# Test PostgreSQL databases
echo "📊 Testing PostgreSQL database creation..."
docker compose -f "$COMPOSE_FILE" exec -T postgres-shared psql -U dotmac_admin -d dotmac_isp -c "SELECT 1;" >/dev/null 2>&1 && echo "✅ dotmac_isp database accessible" || exit 1
docker compose -f "$COMPOSE_FILE" exec -T postgres-shared psql -U dotmac_admin -d mgmt_platform -c "SELECT 1;" >/dev/null 2>&1 && echo "✅ mgmt_platform database accessible" || exit 1

# Test Redis authentication
echo "🔐 Testing Redis authentication..."
docker compose -f "$COMPOSE_FILE" exec -T redis-shared redis-cli -a "${REDIS_PASSWORD:-default_password}" ping >/dev/null 2>&1 && echo "✅ Redis authentication working" || exit 1

# Test OpenBao readiness
echo "🛡️  Testing OpenBao readiness..."
timeout 10 curl -sf "http://localhost:8200/v1/sys/health" | grep -q "initialized" && echo "✅ OpenBao is initialized" || exit 1

echo ""
echo "🎉 Gate E-0a PASSED: Core Infrastructure Layer is healthy"
echo "✅ PostgreSQL: Multiple databases ready"
echo "✅ Redis: Authenticated and ready"  
echo "✅ OpenBao: Initialized and ready"
echo ""
echo "Ready to proceed to Gate E-0b (Observability Infrastructure)"