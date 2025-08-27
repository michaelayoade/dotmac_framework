#!/usr/bin/env python3
"""
Comprehensive API Security Validation Script
Tests all security components independently and provides detailed security assessment
"""

import asyncio
import logging
import sys
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def validate_request_validation():
    """Test request validation security features"""
    print("🛡️  Testing Request Validation Security...")
    try:
        from request_validation import SecurityValidators, BaseSecureModel, SecureStringField
        
        results = {"passed": [], "failed": []}
        
        # Test SQL injection detection
        try:
            SecurityValidators.validate_no_sql_injection("'; DROP TABLE users; --")
            results["failed"].append("SQL injection detection failed")
        except Exception:
            results["passed"].append("SQL injection detection working")
        
        # Test XSS detection
        try:
            SecurityValidators.validate_no_xss("<script>alert('xss')</script>")
            results["failed"].append("XSS detection failed")
        except Exception:
            results["passed"].append("XSS detection working")
        
        # Test path traversal detection
        try:
            SecurityValidators.validate_no_path_traversal("../../../etc/passwd")
            results["failed"].append("Path traversal detection failed")
        except Exception:
            results["passed"].append("Path traversal detection working")
        
        # Test secure string field
        try:
            field = SecureStringField(value="normal text")
            results["passed"].append("Secure string field validation working")
        except Exception as e:
            results["failed"].append(f"Secure string field failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def validate_rate_limiting():
    """Test rate limiting functionality"""
    print("⚡ Testing Rate Limiting...")
    try:
        from api_rate_limiter import RedisRateLimiter, TenantQuota
        
        results = {"passed": [], "failed": []}
        
        # Test quota configuration
        try:
            rate_limiter = RedisRateLimiter()
            if hasattr(rate_limiter, 'tenant_quotas') and rate_limiter.tenant_quotas:
                results["passed"].append("Tenant quotas configured")
            else:
                results["failed"].append("Tenant quotas not configured")
        except Exception as e:
            results["failed"].append(f"Rate limiter initialization failed: {e}")
        
        # Test quota types
        try:
            basic_quota = TenantQuota(daily_requests=10000, hourly_requests=1000, minute_requests=50)
            if basic_quota.daily_requests == 10000:
                results["passed"].append("Quota types working")
            else:
                results["failed"].append("Quota types not working")
        except Exception as e:
            results["failed"].append(f"Quota types failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def validate_authentication():
    """Test authentication middleware"""
    print("🔐 Testing Authentication & Authorization...")
    try:
        from api_auth_middleware import JWTTokenValidator, RoleBasedAccessControl, UserRole, AuthUser
        
        results = {"passed": [], "failed": []}
        
        # Test JWT validator
        try:
            jwt_validator = JWTTokenValidator(secret_key="test-key-that-is-at-least-32-characters-long")
            results["passed"].append("JWT validator initialization working")
        except Exception as e:
            results["failed"].append(f"JWT validator failed: {e}")
        
        # Test RBAC
        try:
            rbac = RoleBasedAccessControl()
            if rbac.role_hierarchy and rbac.role_permissions:
                results["passed"].append("RBAC configuration working")
            else:
                results["failed"].append("RBAC not properly configured")
        except Exception as e:
            results["failed"].append(f"RBAC failed: {e}")
        
        # Test user roles
        try:
            test_user = AuthUser(
                user_id="test-123",
                email="test@example.com",
                tenant_id="tenant-123",
                roles=[UserRole.TENANT_ADMIN.value],
                permissions=["tenant.admin"],
                is_active=True,
                is_verified=True
            )
            
            rbac = RoleBasedAccessControl()
            if rbac.has_permission(test_user, "tenant.admin"):
                results["passed"].append("Permission checking working")
            else:
                results["failed"].append("Permission checking failed")
        except Exception as e:
            results["failed"].append(f"User role testing failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def validate_threat_detection():
    """Test threat detection system"""
    print("🚨 Testing Threat Detection...")
    try:
        from api_threat_detector import APIThreatDetector, ThreatType, ThreatLevel
        
        results = {"passed": [], "failed": []}
        
        # Test threat detector initialization
        try:
            # Use in-memory testing (no Redis dependency)
            threat_detector = APIThreatDetector()
            if threat_detector.threat_patterns:
                results["passed"].append("Threat detector initialization working")
            else:
                results["failed"].append("Threat patterns not configured")
        except Exception as e:
            results["failed"].append(f"Threat detector initialization failed: {e}")
        
        # Test malicious pattern detection
        try:
            threat_detector = APIThreatDetector()
            patterns = threat_detector._detect_malicious_patterns(
                url="/api/users?id='; DROP TABLE users; --",
                headers={"User-Agent": "sqlmap/1.0"},
                user_agent="sqlmap/1.0"
            )
            
            if patterns:
                results["passed"].append("Malicious pattern detection working")
            else:
                results["failed"].append("Malicious pattern detection not working")
        except Exception as e:
            results["failed"].append(f"Pattern detection failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def validate_security_headers():
    """Test security headers configuration"""
    print("🛡️  Testing Security Headers...")
    try:
        from api_security_headers import SecurityHeaders, CORSPolicyManager
        
        results = {"passed": [], "failed": []}
        
        # Test default security headers
        try:
            headers = SecurityHeaders.DEFAULT_SECURITY_HEADERS
            required_headers = ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"]
            
            if all(header in headers for header in required_headers):
                results["passed"].append("Default security headers configured")
            else:
                results["failed"].append("Missing required security headers")
        except Exception as e:
            results["failed"].append(f"Security headers test failed: {e}")
        
        # Test CSP generation
        try:
            csp = SecurityHeaders.get_content_security_policy(strict_mode=True)
            if "default-src 'none'" in csp:
                results["passed"].append("CSP generation working")
            else:
                results["failed"].append("CSP generation not working properly")
        except Exception as e:
            results["failed"].append(f"CSP generation failed: {e}")
        
        # Test CORS configuration
        try:
            cors_manager = CORSPolicyManager("development")
            config = cors_manager.get_cors_configuration()
            
            if config.get("allow_credentials") is not None:
                results["passed"].append("CORS configuration working")
            else:
                results["failed"].append("CORS configuration incomplete")
        except Exception as e:
            results["failed"].append(f"CORS configuration failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def validate_integration():
    """Test security suite integration"""
    print("🔗 Testing Security Suite Integration...")
    try:
        from api_security_integration import APISecuritySuite
        
        results = {"passed": [], "failed": []}
        
        # Test security suite initialization
        try:
            security_suite = APISecuritySuite(
                environment="development",
                jwt_secret_key="test-key-that-is-at-least-32-characters-long",
                redis_url="redis://localhost:6379"
            )
            results["passed"].append("Security suite initialization working")
        except Exception as e:
            results["failed"].append(f"Security suite initialization failed: {e}")
        
        # Test configuration generation
        try:
            security_suite = APISecuritySuite(environment="production")
            config = security_suite._get_security_config()
            
            if config.get("rate_limiting", {}).get("enabled"):
                results["passed"].append("Security configuration generation working")
            else:
                results["failed"].append("Security configuration incomplete")
        except Exception as e:
            results["failed"].append(f"Configuration generation failed: {e}")
        
        return results
        
    except Exception as e:
        return {"passed": [], "failed": [f"Module import failed: {e}"]}

async def run_comprehensive_validation():
    """Run all security validation tests"""
    print("🔍 Starting Comprehensive API Security Validation")
    print("=" * 60)
    
    all_results = {}
    total_passed = 0
    total_failed = 0
    
    # Run all validation tests
    validation_tests = [
        ("Request Validation", validate_request_validation),
        ("Rate Limiting", validate_rate_limiting), 
        ("Authentication & Authorization", validate_authentication),
        ("Threat Detection", validate_threat_detection),
        ("Security Headers", validate_security_headers),
        ("Integration Suite", validate_integration)
    ]
    
    for test_name, test_func in validation_tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            results = await test_func()
            all_results[test_name] = results
            
            passed = len(results.get("passed", []))
            failed = len(results.get("failed", []))
            
            total_passed += passed
            total_failed += failed
            
            # Display results
            for pass_msg in results.get("passed", []):
                print(f"  ✅ {pass_msg}")
            
            for fail_msg in results.get("failed", []):
                print(f"  ❌ {fail_msg}")
            
            # Summary for this test
            print(f"  📊 Results: {passed} passed, {failed} failed")
            
        except Exception as e:
            print(f"  💥 Test execution failed: {e}")
            total_failed += 1
    
    # Overall summary
    print(f"\n🎯 Overall Security Validation Results")
    print("=" * 60)
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    
    # Calculate security score
    total_tests = total_passed + total_failed
    security_score = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"📈 Security Score: {security_score:.1f}%")
    
    # Determine overall status
    if security_score >= 90 and total_failed <= 2:
        status = "EXCELLENT"
        emoji = "🏆"
    elif security_score >= 75 and total_failed <= 5:
        status = "GOOD"
        emoji = "👍"
    elif security_score >= 60:
        status = "NEEDS_IMPROVEMENT"
        emoji = "⚠️"
    else:
        status = "CRITICAL"
        emoji = "🚨"
    
    print(f"{emoji} Overall Status: {status}")
    
    # Recommendations
    if total_failed > 0:
        print(f"\n🔧 Recommendations:")
        if total_failed > 10:
            print("  • Address critical security component failures immediately")
        if security_score < 80:
            print("  • Review and strengthen security configurations")
        print("  • Run tests with Redis connection for full rate limiting validation")
        print("  • Test with actual FastAPI application for complete integration")
    
    print(f"\n⏰ Validation completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        "overall_status": status,
        "security_score": security_score,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "detailed_results": all_results
    }

if __name__ == "__main__":
    # Run the validation
    results = asyncio.run(run_comprehensive_validation())
    
    # Exit with appropriate code
    exit_code = 0 if results["total_failed"] == 0 else 1
    sys.exit(exit_code)