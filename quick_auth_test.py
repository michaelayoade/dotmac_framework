#!/usr/bin/env python3
"""Quick authentication test to get a token and test endpoints."""

import requests
import json
import sys

BASE_URL = "http://149.102.135.97:8000"

def test_login():
    """Test login and get auth token."""
    login_data = {
        "email": "admin@test.com",
        "password": "TestPassword123!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Login Status: {response.status_code}")
        print(f"Login Response: {response.text}")
        
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
        
    except Exception as e:
        print(f"Login Error: {e}")
        return None

def test_endpoints_with_auth(token):
    """Test protected endpoints with auth token."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    endpoints_to_test = [
        ("GET", "/api/v1/auth/me", "Get current user"),
        ("GET", "/api/v1/tenants/", "List tenants"),
        ("GET", "/api/v1/billing/plans", "List billing plans"),
        ("GET", "/api/v1/deployment/templates", "List deployment templates")
    ]
    
    for method, endpoint, description in endpoints_to_test:
        try:
            response = requests.request(
                method,
                f"{BASE_URL}{endpoint}",
                headers=headers,
                timeout=30
            )
            status_emoji = "✅" if response.status_code < 400 else "❌"
            print(f"{status_emoji} {method} {endpoint} - {response.status_code} - {description}")
            
            if response.status_code < 400 and response.content:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   📊 Returned {len(data)} items")
                    elif isinstance(data, dict):
                        print(f"   📋 Keys: {list(data.keys())}")
                except:
                    print(f"   📄 Response length: {len(response.text)} chars")
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")

def test_public_endpoints():
    """Test public endpoints that don't require auth."""
    public_endpoints = [
        ("GET", "/health", "Health check"),
        ("GET", "/api/v1/health", "API health"),
        ("GET", "/api/v1/health/database", "Database health"),
        ("GET", "/openapi.json", "OpenAPI schema"),
    ]
    
    print("🌍 Testing Public Endpoints:")
    for method, endpoint, description in public_endpoints:
        try:
            response = requests.request(
                method,
                f"{BASE_URL}{endpoint}",
                timeout=30
            )
            status_emoji = "✅" if response.status_code == 200 else "❌"
            print(f"{status_emoji} {method} {endpoint} - {response.status_code} - {description}")
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {e}")

def main():
    print("🚀 Quick Authentication & Endpoint Test")
    print(f"🎯 Target: {BASE_URL}")
    print("="*60)
    
    # Test public endpoints first
    test_public_endpoints()
    print("")
    
    # Try to login and get token
    print("🔐 Testing Authentication:")
    token = test_login()
    
    if token:
        print(f"✅ Login successful! Token: {token[:20]}...")
        print("")
        print("🔒 Testing Protected Endpoints:")
        test_endpoints_with_auth(token)
    else:
        print("❌ Login failed - testing protected endpoints without auth:")
        test_endpoints_with_auth(None)
    
    print("\n" + "="*60)
    print("✅ Quick test completed!")

if __name__ == "__main__":
    main()