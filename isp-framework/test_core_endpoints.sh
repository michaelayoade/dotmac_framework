#!/bin/bash

# Core Module API Testing Script
# Tests the basic endpoints that are currently working

set -e

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}DotMac ISP Framework - Core Module Testing${NC}"
echo -e "${BLUE}===============================================${NC}"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    
    echo -e "${BLUE}Testing: ${NC}$method $endpoint - $description"
    
    local response=$(curl -s -w "|%{http_code}|%{time_total}" -X "$method" "$BASE_URL$endpoint")
    local body="${response%|*|*}"
    local status="${response##*|}"
    local time="${response%|*}"
    time="${time##*|}"
    
    if [[ "$status" == "200" ]] || [[ "$status" == "204" ]]; then
        echo -e "  ${GREEN}✓ Status: $status (${time}s)${NC}"
    else
        echo -e "  ${RED}✗ Status: $status (${time}s)${NC}"
    fi
    
    # Pretty print JSON response if possible
    if echo "$body" | jq . >/dev/null 2>&1; then
        echo -e "  ${BLUE}Response:${NC}"
        echo "$body" | jq . | sed 's/^/    /'
    else
        echo -e "  ${BLUE}Response:${NC} $body"
    fi
    echo ""
}

# Test core application endpoints
echo -e "${BLUE}=== Core Application Endpoints ===${NC}"
test_endpoint "GET" "/" "Root API information"
test_endpoint "GET" "/health" "Health check"
test_endpoint "GET" "/favicon.ico" "Favicon (should return 204)"

# Test system status endpoints
echo -e "${BLUE}=== System Status Endpoints ===${NC}"
test_endpoint "GET" "/ssl-status" "SSL certificate status"
test_endpoint "GET" "/celery-status" "Celery task queue status"

# Test invalid endpoints to verify error handling
echo -e "${BLUE}=== Error Handling ===${NC}"
test_endpoint "GET" "/nonexistent" "Non-existent endpoint (should return 404)"
test_endpoint "GET" "/api/v1/invalid" "Invalid API endpoint (should return 404)"

echo -e "${GREEN}Core module testing complete!${NC}"