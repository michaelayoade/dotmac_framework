#!/usr/bin/env python3
"""
Comprehensive test suite for DotMac Management Platform endpoints.
Tests all API endpoints, authentication, and portal integrations.
"""

import asyncio
import json
import requests
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

# Configuration
BASE_URL = "http://149.102.135.97:8000"
API_BASE = f"{BASE_URL}/api/v1"

class EndpointTester:
    """Test management platform endpoints systematically."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        self.test_data = {}
        
    def log_test(self, endpoint: str, method: str, status: int, success: bool, details: str = ""):
        """Log test results."""
        result = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if success else "❌"
        print(f"{status_emoji} {method} {endpoint} - {status} - {details}")
    
    def test_endpoint(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     auth_required: bool = False, expected_status: int = 200) -> Dict[str, Any]:
        """Test a single endpoint."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth_required and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            success = response.status_code == expected_status
            details = f"Response: {response.text[:100]}..." if response.text else "No content"
            
            self.log_test(endpoint, method.upper(), response.status_code, success, details)
            
            return {
                "success": success,
                "status_code": response.status_code,
                "response": response.json() if response.content else None,
                "headers": dict(response.headers)
            }
            
        except Exception as e:
            self.log_test(endpoint, method.upper(), 0, False, f"Error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def test_health_endpoints(self):
        """Test health and status endpoints."""
        print("\n🏥 Testing Health & Status Endpoints")
        
        # Basic health check
        self.test_endpoint("GET", "/health")
        
        # API health checks
        self.test_endpoint("GET", "/api/v1/health")
        self.test_endpoint("GET", "/api/v1/health/database")
        
        # OpenAPI documentation
        self.test_endpoint("GET", "/openapi.json")
        self.test_endpoint("GET", "/docs", expected_status=200)
        
        # Root endpoint
        self.test_endpoint("GET", "/")
    
    def test_authentication_endpoints(self):
        """Test authentication endpoints."""
        print("\n🔐 Testing Authentication Endpoints")
        
        # Test registration (without actual user creation for now)
        register_data = {
            "email": f"test-{uuid4().hex[:8]}@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "role": "admin"
        }
        
        # Test register endpoint (expect 422 or auth failure)
        result = self.test_endpoint("POST", "/api/v1/auth/register", 
                                  data=register_data, expected_status=422)
        
        # Test login endpoint (expect 422 for invalid credentials)
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }
        self.test_endpoint("POST", "/api/v1/auth/login", 
                          data=login_data, expected_status=422)
        
        # Test refresh token (expect 422 without token)
        self.test_endpoint("POST", "/api/v1/auth/refresh", 
                          data={"refresh_token": "invalid"}, expected_status=422)
        
        # Test protected endpoints without auth (expect 403/401)
        self.test_endpoint("GET", "/api/v1/auth/me", 
                          auth_required=True, expected_status=401)
    
    def test_tenant_endpoints(self):
        """Test tenant management endpoints."""
        print("\n🏢 Testing Tenant Management Endpoints")
        
        # Test list tenants (without auth - should get 401)
        self.test_endpoint("GET", "/api/v1/tenants/", expected_status=401)
        
        # Test create tenant (without auth - should get 401)
        tenant_data = {
            "name": "Test ISP Company",
            "slug": f"test-isp-{uuid4().hex[:6]}",
            "description": "Test ISP for endpoint validation",
            "contact_email": "admin@test-isp.com",
            "contact_name": "Test Admin"
        }
        self.test_endpoint("POST", "/api/v1/tenants/", 
                          data=tenant_data, expected_status=401)
        
        # Test get specific tenant (using our known tenant)
        test_tenant_id = "12345678-1234-1234-1234-123456789012"
        self.test_endpoint("GET", f"/api/v1/tenants/{test_tenant_id}", 
                          expected_status=401)
        
        # Test tenant status update
        status_data = {
            "status": "active",
            "reason": "Test status update"
        }
        self.test_endpoint("PUT", f"/api/v1/tenants/{test_tenant_id}/status", 
                          data=status_data, expected_status=401)
    
    def test_billing_endpoints(self):
        """Test billing and subscription endpoints."""
        print("\n💰 Testing Billing & Subscription Endpoints")
        
        # Test billing plans
        self.test_endpoint("GET", "/api/v1/billing/plans", expected_status=401)
        
        plan_data = {
            "name": "Test Plan",
            "description": "Test billing plan",
            "price_per_month": 29.99,
            "features": ["basic_support", "monitoring"]
        }
        self.test_endpoint("POST", "/api/v1/billing/plans", 
                          data=plan_data, expected_status=401)
        
        # Test subscriptions
        self.test_endpoint("GET", "/api/v1/billing/subscriptions", expected_status=401)
        
        # Test invoices
        self.test_endpoint("GET", "/api/v1/billing/invoices", expected_status=401)
        
        # Test payments
        self.test_endpoint("GET", "/api/v1/billing/payments", expected_status=401)
        
        # Test usage records
        self.test_endpoint("GET", "/api/v1/billing/usage", expected_status=401)
        
        # Test analytics (expect validation error for missing dates)
        self.test_endpoint("GET", "/api/v1/billing/analytics", expected_status=422)
    
    def test_deployment_endpoints(self):
        """Test deployment and infrastructure endpoints."""
        print("\n🚀 Testing Deployment & Infrastructure Endpoints")
        
        # Test deployment templates
        self.test_endpoint("GET", "/api/v1/deployment/templates", expected_status=401)
        
        template_data = {
            "name": "Test Template",
            "description": "Test deployment template",
            "cloud_provider": "aws",
            "resource_tier": "small"
        }
        self.test_endpoint("POST", "/api/v1/deployment/templates", 
                          data=template_data, expected_status=401)
    
    def test_portal_endpoints(self):
        """Test portal-specific endpoints."""
        print("\n🌐 Testing Portal Integration Endpoints")
        
        # These might be additional routes for portal integration
        portal_endpoints = [
            "/portals/admin",
            "/portals/customer", 
            "/portals/reseller"
        ]
        
        for endpoint in portal_endpoints:
            # These might return 404 if not implemented yet
            result = self.test_endpoint("GET", endpoint, expected_status=404)
    
    def test_advanced_workflows(self):
        """Test complex workflows and edge cases."""
        print("\n⚙️ Testing Advanced Workflows")
        
        # Test pagination parameters
        self.test_endpoint("GET", "/api/v1/tenants/?page=1&size=10", expected_status=401)
        
        # Test search functionality
        self.test_endpoint("GET", "/api/v1/tenants/?search=demo", expected_status=401)
        
        # Test invalid UUIDs
        self.test_endpoint("GET", "/api/v1/tenants/invalid-uuid", expected_status=422)
        
        # Test OPTIONS requests (CORS)
        try:
            response = requests.options(f"{BASE_URL}/api/v1/tenants/")
            success = response.status_code in [200, 204]
            self.log_test("/api/v1/tenants/", "OPTIONS", response.status_code, success, 
                         f"CORS headers: {dict(response.headers)}")
        except Exception as e:
            self.log_test("/api/v1/tenants/", "OPTIONS", 0, False, f"Error: {e}")
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("📊 MANAGEMENT PLATFORM ENDPOINT TEST REPORT")
        print("="*60)
        
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - successful_tests
        
        print(f"📈 Total Endpoints Tested: {total_tests}")
        print(f"✅ Successful Tests: {successful_tests}")
        print(f"❌ Failed Tests: {failed_tests}")
        print(f"📊 Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests Details:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['method']} {result['endpoint']} - {result['details']}")
        
        # Group by endpoint category
        categories = {}
        for result in self.test_results:
            endpoint = result['endpoint']
            if '/health' in endpoint:
                category = 'Health & Status'
            elif '/auth' in endpoint:
                category = 'Authentication'
            elif '/tenants' in endpoint:
                category = 'Tenant Management'
            elif '/billing' in endpoint:
                category = 'Billing & Subscriptions'
            elif '/deployment' in endpoint:
                category = 'Deployment & Infrastructure'
            elif '/portals' in endpoint:
                category = 'Portal Integration'
            else:
                category = 'Other'
            
            if category not in categories:
                categories[category] = {'total': 0, 'success': 0}
            categories[category]['total'] += 1
            if result['success']:
                categories[category]['success'] += 1
        
        print(f"\n📋 Results by Category:")
        for category, stats in categories.items():
            success_rate = (stats['success']/stats['total'])*100
            print(f"  {category}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        return {
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'failed_tests': failed_tests,
            'success_rate': (successful_tests/total_tests)*100,
            'categories': categories,
            'detailed_results': self.test_results
        }
    
    def run_all_tests(self):
        """Run all endpoint tests."""
        print("🚀 Starting Comprehensive Management Platform Endpoint Testing")
        print(f"🎯 Target: {self.base_url}")
        
        self.test_health_endpoints()
        self.test_authentication_endpoints()
        self.test_tenant_endpoints()
        self.test_billing_endpoints()
        self.test_deployment_endpoints()
        self.test_portal_endpoints()
        self.test_advanced_workflows()
        
        return self.generate_report()

def main():
    """Run the endpoint testing suite."""
    tester = EndpointTester(BASE_URL)
    report = tester.run_all_tests()
    
    # Save detailed results
    with open('/home/dotmac_framework/endpoint_test_results.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: /home/dotmac_framework/endpoint_test_results.json")
    
    # Return appropriate exit code
    return 0 if report['failed_tests'] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())