#!/bin/bash

# Fixed Authentication Test Script
BASE_URL="http://localhost:8000"

echo "🔐 Testing Authentication System"
echo "=================================="

# Test 1: Health Check
echo "1. Testing health endpoint..."
health_response=$(curl -s "$BASE_URL/health")
echo "   Health: $health_response"

# Test 2: Root endpoint  
echo "2. Testing root endpoint..."
root_response=$(curl -s "$BASE_URL/")
echo "   Root: $root_response"

# Test 3: Login attempt
echo "3. Testing login endpoint..."

# Create JSON payload
login_payload='{"email": "admin@test.com", "password": "TestPassword123!"}'

# Try login
echo "   Attempting login with: $login_payload"
login_response=$(curl -s -X POST "$BASE_URL/api/v1/identity/auth/login" \
  -H "Content-Type: application/json" \
  --data-raw "$login_payload")

echo "   Login response: $login_response"

# Check if we got a token
access_token=$(echo "$login_response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ ! -z "$access_token" ]; then
    echo "   ✅ Authentication successful!"
    echo "   🎫 Access token: ${access_token:0:50}..."
    
    # Test 4: Test protected endpoint
    echo "4. Testing protected endpoint with token..."
    protected_response=$(curl -s "$BASE_URL/api/v1/identity/me" \
      -H "Authorization: Bearer $access_token")
    echo "   Profile response: $protected_response"
    
    # Test 5: Test analytics with token
    echo "5. Testing analytics endpoint with token..."
    analytics_response=$(curl -s "$BASE_URL/api/v1/analytics/overview" \
      -H "Authorization: Bearer $access_token")
    echo "   Analytics response: $analytics_response"
    
else
    echo "   ❌ Authentication failed"
    echo "   Response: $login_response"
fi

echo ""
echo "🎯 Test Summary"
echo "==============="
echo "All endpoints tested with authentication flow"