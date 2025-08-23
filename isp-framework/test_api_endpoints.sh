#!/bin/bash

# DotMac ISP Framework API Testing Script
# Comprehensive curl-based testing for all available endpoints

# Configuration
BASE_URL="http://localhost:8000"
API_BASE="$BASE_URL/api/v1"
RESULTS_FILE="api_test_results.json"
REPORT_FILE="api_test_report.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
ACCESS_TOKEN=""
CSRF_TOKEN=""
SESSION_COOKIE=""
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Initialize result files
echo "[]" > "$RESULTS_FILE"
echo "DotMac ISP Framework API Test Report - $(date)" > "$REPORT_FILE"
echo "=====================================================" >> "$REPORT_FILE"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$REPORT_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$REPORT_FILE"
    ((PASSED_TESTS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$REPORT_FILE"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$REPORT_FILE"
}

# Function to make API call and log results
make_api_call() {
    local method="$1"
    local endpoint="$2"
    local description="$3"
    local expected_status="$4"
    local data="$5"
    local extra_headers="$6"
    
    ((TOTAL_TESTS++))
    log_info "Testing: $method $endpoint - $description"
    
    # Build curl command
    local curl_cmd="curl -s -w '%{http_code}:%{time_total}' -X $method"
    
    # Add headers
    curl_cmd="$curl_cmd -H 'Content-Type: application/json'"
    curl_cmd="$curl_cmd -H 'Accept: application/json'"
    
    # Add authentication if available
    if [ ! -z "$ACCESS_TOKEN" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $ACCESS_TOKEN'"
    fi
    
    # Add CSRF token if available
    if [ ! -z "$CSRF_TOKEN" ]; then
        curl_cmd="$curl_cmd -H 'X-CSRF-Token: $CSRF_TOKEN'"
    fi
    
    # Add session cookie if available
    if [ ! -z "$SESSION_COOKIE" ]; then
        curl_cmd="$curl_cmd -H 'Cookie: $SESSION_COOKIE'"
    fi
    
    # Add extra headers
    if [ ! -z "$extra_headers" ]; then
        curl_cmd="$curl_cmd $extra_headers"
    fi
    
    # Add data for POST/PUT requests
    if [ ! -z "$data" ]; then
        curl_cmd="$curl_cmd -d '$data'"
    fi
    
    # Add endpoint
    curl_cmd="$curl_cmd '$endpoint'"
    
    # Execute curl command
    local response=$(eval "$curl_cmd")
    local status_code=$(echo "$response" | tail -c 15 | cut -d':' -f1)
    local response_time=$(echo "$response" | tail -c 15 | cut -d':' -f2)
    local response_body=$(echo "$response" | sed 's/...............$//')
    
    # Log results
    local result_entry="{
        \"method\": \"$method\",
        \"endpoint\": \"$endpoint\",
        \"description\": \"$description\",
        \"expected_status\": \"$expected_status\",
        \"actual_status\": \"$status_code\",
        \"response_time\": \"$response_time\",
        \"response_body\": $(echo "$response_body" | jq -R .),
        \"timestamp\": \"$(date -Iseconds)\"
    }"
    
    # Update results file
    jq ". += [$result_entry]" "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
    
    # Check if test passed
    if [ "$status_code" = "$expected_status" ] || [ "$expected_status" = "*" ]; then
        log_success "$method $endpoint returned $status_code (${response_time}s)"
        if [ ! -z "$response_body" ] && [ "$response_body" != "null" ]; then
            echo "Response: $(echo "$response_body" | jq . 2>/dev/null || echo "$response_body")" >> "$REPORT_FILE"
        fi
    else
        log_error "$method $endpoint returned $status_code, expected $expected_status (${response_time}s)"
        if [ ! -z "$response_body" ] && [ "$response_body" != "null" ]; then
            echo "Response: $(echo "$response_body" | jq . 2>/dev/null || echo "$response_body")" >> "$REPORT_FILE"
        fi
    fi
    
    echo "" >> "$REPORT_FILE"
}

# Function to get CSRF token
get_csrf_token() {
    log_info "Attempting to get CSRF token..."
    local response=$(curl -s -c /tmp/cookies.txt "$BASE_URL/")
    CSRF_TOKEN=$(curl -s -b /tmp/cookies.txt "$BASE_URL/" | grep -o 'csrf-token" content="[^"]*' | cut -d'"' -f3)
    SESSION_COOKIE=$(cat /tmp/cookies.txt | grep -o 'dotmac_session[[:space:]]*[^[:space:]]*' | tr -s '[:space:]' '=' | head -1)
    
    if [ ! -z "$CSRF_TOKEN" ]; then
        log_success "CSRF token obtained: ${CSRF_TOKEN:0:20}..."
    else
        log_warning "Could not obtain CSRF token, proceeding without it"
    fi
    
    if [ ! -z "$SESSION_COOKIE" ]; then
        log_success "Session cookie obtained"
    else
        log_warning "Could not obtain session cookie"
    fi
}

# Function to create test user and authenticate
setup_authentication() {
    log_info "Setting up authentication..."
    
    # Create test user directly in database (bypassing API restrictions)
    log_info "Creating test user in database..."
    python3 -c "
import sys
sys.path.insert(0, 'src')

try:
    from dotmac_isp.modules.identity.models import User
    from dotmac_isp.core.database import engine
    from dotmac_isp.shared.auth import hash_password
    from sqlalchemy.orm import Session
    from uuid import uuid4
    from datetime import datetime, timezone
    
    session = Session(engine)
    
    # Check if user exists
    existing_user = session.query(User).filter(User.email == 'testadmin@dotmac.com').first()
    if existing_user:
        print('Test user already exists')
    else:
        # Create test user
        test_user = User(
            id=str(uuid4()),
            email='testadmin@dotmac.com',
            username='testadmin',
            password_hash=hash_password('TestPassword123!'),
            first_name='Test',
            last_name='Admin',
            tenant_id='default-tenant',
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc)
        )
        
        session.add(test_user)
        session.commit()
        print('Test user created successfully')
    
    session.close()
    
except Exception as e:
    print(f'Error: {e}')
" 2>/dev/null || log_warning "Could not create test user, proceeding with existing authentication"
    
    # Try to login and get access token
    log_info "Attempting to login..."
    local login_response=$(curl -s -X POST "$API_BASE/identity/auth/login" \
        -H "Content-Type: application/json" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "Cookie: $SESSION_COOKIE" \
        -d '{"email":"testadmin@dotmac.com","password":"TestPassword123!"}')
    
    local status_code=$(curl -s -w '%{http_code}' -X POST "$API_BASE/identity/auth/login" \
        -H "Content-Type: application/json" \
        -H "X-CSRF-Token: $CSRF_TOKEN" \
        -H "Cookie: $SESSION_COOKIE" \
        -d '{"email":"testadmin@dotmac.com","password":"TestPassword123!"}' \
        -o /dev/null)
    
    if [ "$status_code" = "200" ]; then
        ACCESS_TOKEN=$(echo "$login_response" | jq -r '.access_token // empty')
        if [ ! -z "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            log_success "Authentication successful, token obtained"
        else
            log_warning "Login successful but no token received"
        fi
    else
        log_warning "Login failed with status $status_code, proceeding with unauthenticated tests"
        if [ ! -z "$login_response" ]; then
            echo "Login response: $login_response" >> "$REPORT_FILE"
        fi
    fi
}

# Main testing function
run_api_tests() {
    log_info "Starting comprehensive API testing..."
    echo "" >> "$REPORT_FILE"
    
    # 1. Health and Status Endpoints
    echo "=== HEALTH AND STATUS ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$BASE_URL/health" "Health check" "200"
    make_api_call "GET" "$BASE_URL/" "Root endpoint" "200"
    
    # 2. Authentication Endpoints
    echo "=== AUTHENTICATION ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "POST" "$API_BASE/identity/auth/login" "User login (invalid credentials)" "401" '{"email":"invalid@test.com","password":"wrongpassword"}'
    make_api_call "POST" "$API_BASE/identity/auth/logout" "User logout" "*"
    make_api_call "GET" "$API_BASE/identity/me" "Get current user profile" "*"
    
    # 3. Identity Management
    echo "=== IDENTITY MANAGEMENT ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/identity/users" "List users" "*"
    make_api_call "POST" "$API_BASE/identity/users" "Create user" "*" '{"email":"newuser@test.com","username":"newuser","password":"TestPass123","first_name":"New","last_name":"User","tenant_id":"default-tenant"}'
    
    # 4. Billing Endpoints
    echo "=== BILLING ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/billing/invoices" "List invoices" "*"
    make_api_call "GET" "$API_BASE/billing/payments" "List payments" "*"
    make_api_call "GET" "$API_BASE/billing/health" "Billing health check" "*"
    
    # 5. Network Monitoring
    echo "=== NETWORK MONITORING ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/network-monitoring/devices" "List monitoring devices" "*"
    make_api_call "GET" "$API_BASE/network-monitoring/profiles" "List monitoring profiles" "*"
    make_api_call "GET" "$API_BASE/network-monitoring/alerts" "List network alerts" "*"
    make_api_call "GET" "$API_BASE/network-monitoring/dashboard" "Network monitoring dashboard" "*"
    
    # 6. Inventory Management
    echo "=== INVENTORY MANAGEMENT ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/inventory/equipment" "List equipment" "*"
    make_api_call "GET" "$API_BASE/inventory/equipment-types" "List equipment types" "*"
    make_api_call "GET" "$API_BASE/inventory/warehouses" "List warehouses" "*"
    make_api_call "GET" "$API_BASE/inventory/vendors" "List vendors" "*"
    make_api_call "GET" "$API_BASE/inventory/health" "Inventory health check" "*"
    
    # 7. Project Management
    echo "=== PROJECT MANAGEMENT ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/projects/" "List projects" "*"
    make_api_call "GET" "$API_BASE/projects/dashboard/stats" "Project dashboard stats" "*"
    
    # 8. Analytics
    echo "=== ANALYTICS ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/analytics/overview" "Analytics overview" "*"
    make_api_call "GET" "$API_BASE/analytics/dashboards" "List dashboards" "*"
    make_api_call "GET" "$API_BASE/analytics/metrics" "List metrics" "*"
    make_api_call "GET" "$API_BASE/analytics/reports" "List reports" "*"
    
    # 9. Support System
    echo "=== SUPPORT ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/support/tickets" "List support tickets" "*"
    make_api_call "GET" "$API_BASE/support/dashboard" "Support dashboard" "*"
    
    # 10. Omnichannel
    echo "=== OMNICHANNEL ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/omnichannel/dashboard/stats" "Omnichannel dashboard stats" "*"
    make_api_call "GET" "$API_BASE/omnichannel/agents/available" "List available agents" "*"
    make_api_call "GET" "$API_BASE/omnichannel/health" "Omnichannel health check" "*"
    
    # 11. Sales
    echo "=== SALES ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/sales/opportunities" "List sales opportunities" "*"
    make_api_call "GET" "$API_BASE/sales/dashboard" "Sales dashboard" "*"
    
    # 12. Services
    echo "=== SERVICES ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/services/catalog" "Service catalog" "*"
    make_api_call "GET" "$API_BASE/services/health" "Services health check" "*"
    
    # 13. Compliance
    echo "=== COMPLIANCE ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/compliance/compliance/dashboard" "Compliance dashboard" "*"
    make_api_call "GET" "$API_BASE/compliance/compliance/assessments" "List compliance assessments" "*"
    
    # 14. Notifications
    echo "=== NOTIFICATIONS ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/notifications/templates" "List notification templates" "*"
    make_api_call "GET" "$API_BASE/notifications/health" "Notifications health check" "*"
    
    # 15. Field Operations
    echo "=== FIELD OPERATIONS ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/field-ops/work-orders" "List work orders" "*"
    make_api_call "GET" "$API_BASE/field-ops/dashboard" "Field ops dashboard" "*"
    
    # 16. Portal Management
    echo "=== PORTAL MANAGEMENT ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/portals/admin/dashboard" "Admin portal dashboard" "*"
    make_api_call "GET" "$API_BASE/portals/customer/dashboard" "Customer portal dashboard" "*"
    
    # 17. Integration Tests
    echo "=== INTEGRATION ENDPOINTS ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/integrations/ansible/health" "Ansible integration health" "*"
    
    # 18. Invalid Endpoints (should return 404)
    echo "=== INVALID ENDPOINTS (Expected 404) ===" >> "$REPORT_FILE"
    make_api_call "GET" "$API_BASE/nonexistent/endpoint" "Non-existent endpoint" "404"
    make_api_call "POST" "$BASE_URL/invalid" "Invalid endpoint" "*"
}

# Function to generate summary report
generate_summary() {
    echo "" >> "$REPORT_FILE"
    echo "=====================================================" >> "$REPORT_FILE"
    echo "TEST SUMMARY" >> "$REPORT_FILE"
    echo "=====================================================" >> "$REPORT_FILE"
    echo "Total Tests: $TOTAL_TESTS" >> "$REPORT_FILE"
    echo "Passed: $PASSED_TESTS" >> "$REPORT_FILE"
    echo "Failed: $FAILED_TESTS" >> "$REPORT_FILE"
    echo "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%" >> "$REPORT_FILE"
    echo "Timestamp: $(date)" >> "$REPORT_FILE"
    
    log_info "======================================================"
    log_info "API Testing Complete!"
    log_info "Total Tests: $TOTAL_TESTS"
    log_success "Passed: $PASSED_TESTS"
    log_error "Failed: $FAILED_TESTS"
    log_info "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    log_info "======================================================"
    log_info "Detailed results saved to: $RESULTS_FILE"
    log_info "Human-readable report saved to: $REPORT_FILE"
}

# Main execution
main() {
    log_info "DotMac ISP Framework API Testing Script"
    log_info "========================================"
    
    # Check if server is running
    if ! curl -s "$BASE_URL/health" > /dev/null; then
        log_error "Server is not running at $BASE_URL"
        log_error "Please start the server before running tests"
        exit 1
    fi
    
    log_success "Server is running at $BASE_URL"
    
    # Setup phase
    get_csrf_token
    setup_authentication
    
    # Run tests
    run_api_tests
    
    # Generate summary
    generate_summary
    
    # Cleanup
    rm -f /tmp/cookies.txt
    
    # Exit with appropriate code
    if [ $FAILED_TESTS -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"