#!/bin/bash
# Gate E-0b Validation: Observability Infrastructure Layer
# Purpose: Validate fixed observability stack (ClickHouse + SignOz) is operational

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.e-0b.yml"

echo "🔍 Gate E-0b Validation: Observability Infrastructure Layer"
echo "========================================================="

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ ERROR: $COMPOSE_FILE not found"
    exit 1
fi

# Check prerequisite: Gate E-0a services must be running
echo "📋 Checking prerequisites (Gate E-0a)..."
if ! docker ps | grep -q "dotmac-postgres-shared.*healthy"; then
    echo "❌ ERROR: Gate E-0a not validated - postgres-shared must be healthy"
    exit 1
fi

if ! docker ps | grep -q "dotmac-redis-shared.*healthy"; then
    echo "❌ ERROR: Gate E-0a not validated - redis-shared must be healthy"
    exit 1
fi

if ! docker ps | grep -q "dotmac-openbao-shared.*healthy"; then
    echo "❌ ERROR: Gate E-0a not validated - openbao-shared must be healthy"
    exit 1
fi

echo "✅ Gate E-0a prerequisites satisfied"

# Function to check service health with better error reporting
check_service_health() {
    local service_name="$1"
    local max_attempts=40  # Extended for observability services
    local attempt=0
    
    echo "🔄 Checking $service_name health..."
    
    while [ $attempt -lt $max_attempts ]; do
        local status=$(docker compose -f "$COMPOSE_FILE" ps --format "table {{.Service}} {{.Status}}" | grep "$service_name" | awk '{print $2}' || echo "unknown")
        
        if echo "$status" | grep -q "healthy"; then
            echo "✅ $service_name is healthy"
            return 0
        elif echo "$status" | grep -q "unhealthy"; then
            echo "⚠️  $service_name is unhealthy - checking logs..."
            docker compose -f "$COMPOSE_FILE" logs --tail=20 "$service_name" || true
            sleep 10
        fi
        
        attempt=$((attempt + 1))
        echo "   Attempt $attempt/$max_attempts - waiting for $service_name... (status: $status)"
        sleep 8
    done
    
    echo "❌ $service_name failed to become healthy after $((max_attempts * 8)) seconds"
    echo "Last logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=50 "$service_name" || true
    return 1
}

# Function to test observability endpoints
test_observability_endpoint() {
    local service="$1"
    local url="$2"
    local expected_response="${3:-}"
    
    echo "🌐 Testing $service endpoint: $url"
    
    if response=$(timeout 15 curl -sf "$url" 2>/dev/null); then
        if [ -n "$expected_response" ]; then
            if echo "$response" | grep -q "$expected_response"; then
                echo "✅ $service endpoint is healthy and responding correctly"
                return 0
            else
                echo "⚠️  $service endpoint responded but content unexpected"
                echo "Response: $response"
                return 1
            fi
        else
            echo "✅ $service endpoint is accessible"
            return 0
        fi
    else
        echo "❌ $service endpoint is not accessible"
        return 1
    fi
}

# Start observability services
echo "🚀 Starting Gate E-0b services..."
docker compose -f "$COMPOSE_FILE" up -d

# Wait for initial startup
echo "⏳ Waiting for observability services to initialize..."
sleep 20

# Check individual service health in dependency order
echo "📊 Validating ClickHouse..."
check_service_health "clickhouse" || exit 1

echo "📡 Validating SignOz Collector..."
check_service_health "signoz-collector" || exit 1

echo "🔍 Validating SignOz Query Service..."  
check_service_health "signoz-query" || exit 1

echo "🖥️  Validating SignOz Frontend..."
check_service_health "signoz-frontend" || exit 1

# Test observability endpoints
echo "🧪 Testing observability endpoints..."

# Test ClickHouse
test_observability_endpoint "ClickHouse HTTP" "http://localhost:8123/ping" "Ok" || exit 1

# Test SignOz collector metrics endpoint
test_observability_endpoint "SignOz Collector" "http://localhost:8889/metrics" "otelcol_process_uptime" || exit 1

# Test SignOz query health
test_observability_endpoint "SignOz Query" "http://localhost:8080/api/v1/health" || exit 1

# Test SignOz frontend
test_observability_endpoint "SignOz Frontend" "http://localhost:3301/" || exit 1

# Test OTLP endpoints (key for application integration)
echo "🔌 Testing OTLP endpoints..."
if timeout 5 bash -c '</dev/tcp/localhost/4317' 2>/dev/null; then
    echo "✅ OTLP gRPC endpoint (4317) is accessible"
else
    echo "❌ OTLP gRPC endpoint (4317) is not accessible"
    exit 1
fi

if timeout 5 bash -c '</dev/tcp/localhost/4318' 2>/dev/null; then
    echo "✅ OTLP HTTP endpoint (4318) is accessible"  
else
    echo "❌ OTLP HTTP endpoint (4318) is not accessible"
    exit 1
fi

# Validate ClickHouse database structure for SignOz
echo "🗄️  Validating ClickHouse SignOz schema..."
if docker compose -f "$COMPOSE_FILE" exec -T clickhouse clickhouse-client --query "SHOW DATABASES" | grep -q "signoz"; then
    echo "✅ SignOz ClickHouse database exists"
else
    echo "⚠️  SignOz database not found - may be created on first metrics"
fi

# Test configuration integration
echo "⚙️  Testing observability configuration integration..."
if docker compose -f "$COMPOSE_FILE" exec -T signoz-collector cat /etc/otel-collector-config.yaml | grep -q "clickhouse"; then
    echo "✅ SignOz collector configuration is properly mounted"
else
    echo "❌ SignOz collector configuration issue"
    exit 1
fi

echo ""
echo "🎉 Gate E-0b PASSED: Observability Infrastructure is operational"
echo "✅ ClickHouse: Ready for metrics storage"
echo "✅ SignOz Collector: Ready for OTLP ingestion (ports 4317, 4318)"
echo "✅ SignOz Query: Ready for metrics queries"
echo "✅ SignOz Frontend: Ready for dashboards (http://localhost:3301)"
echo "✅ Fixed observability configuration validated"
echo ""
echo "Ready to proceed to Gate E-0c (Applications with Observability)"