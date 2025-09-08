#!/usr/bin/env python3
"""
Comprehensive validation test for DotMac framework implementation.
Tests all major components implemented in the gap resolution.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

async def test_sql_injection_fix():
    """Test that SQL injection vulnerability is fixed."""
    print("🔒 Testing SQL injection fix...")
    
    try:
        from dotmac_shared.security.tenant_middleware import TenantContextManager
        from sqlalchemy import text
        
        # Check that the file uses parameterized queries
        with open("src/dotmac_shared/security/tenant_middleware.py", "r") as f:
            content = f.read()
            
        # Should not find f-string SQL queries
        if "f\"SELECT set_config" in content:
            print("❌ SQL injection vulnerability still present")
            return False
            
        # Should find parameterized queries
        if "text(\"SELECT set_config" in content and ":tenant_id" in content:
            print("✅ SQL injection vulnerability fixed")
            return True
        else:
            print("❌ Parameterized queries not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing SQL injection fix: {e}")
        return False


def test_secrets_removal():
    """Test that hardcoded secrets are removed."""
    print("🔐 Testing secrets removal...")
    
    try:
        with open(".env", "r") as f:
            content = f.read()
        
        # Should not find hardcoded secrets
        if "staging-postgres-pass-2024" in content:
            print("❌ Hardcoded secrets still present")
            return False
            
        # Should find secret placeholders
        if "${SECRET:" in content:
            print("✅ Hardcoded secrets removed and replaced with placeholders")
            return True
        else:
            print("❌ Secret placeholders not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing secrets removal: {e}")
        return False


def test_input_validation():
    """Test that input validation schemas exist."""
    print("🛡️ Testing input validation...")
    
    try:
        from dotmac_shared.validation.input_schemas import TenantCreateRequest
        
        # Test schema validation
        try:
            # This should fail validation
            TenantCreateRequest(name="", domain="invalid", contact_email="invalid")
            print("❌ Input validation not working")
            return False
        except Exception:
            print("✅ Input validation working correctly")
            return True
            
    except ImportError as e:
        print(f"❌ Validation schemas not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing input validation: {e}")
        return False


def test_repository_standardization():
    """Test that BaseRepository exists and is properly structured."""
    print("🗄️ Testing repository standardization...")
    
    try:
        from dotmac_shared.repositories.base_repository import BaseRepository
        
        # Check that BaseRepository has key methods
        required_methods = ['create', 'get', 'get_multi', 'update', 'delete', 'count', 'exists']
        
        for method in required_methods:
            if not hasattr(BaseRepository, method):
                print(f"❌ BaseRepository missing method: {method}")
                return False
        
        print("✅ BaseRepository properly structured")
        return True
        
    except ImportError as e:
        print(f"❌ BaseRepository not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing repository: {e}")
        return False


def test_service_standardization():
    """Test that BaseService exists and is properly structured.""" 
    print("⚙️ Testing service standardization...")
    
    try:
        from dotmac_shared.services.base_service import BaseService, TenantAwareService
        
        # Check that BaseService has key methods
        required_methods = ['create', 'get', 'get_multi', 'count', 'exists', 'error_handling']
        
        for method in required_methods:
            if not hasattr(BaseService, method):
                print(f"❌ BaseService missing method: {method}")
                return False
        
        print("✅ BaseService properly structured")
        return True
        
    except ImportError as e:
        print(f"❌ BaseService not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        return False


async def test_health_monitoring():
    """Test that health monitoring service works."""
    print("🏥 Testing health monitoring...")
    
    try:
        from dotmac_shared.monitoring.health_service import (
            HealthMonitoringService, 
            HealthCheckConfig, 
            HealthStatus
        )
        
        # Create health service
        service = HealthMonitoringService()
        
        # Create a simple test check
        async def test_check():
            return True
            
        config = HealthCheckConfig(
            name="test",
            check_function=test_check,
            timeout_seconds=1
        )
        
        service.register_check(config)
        
        # Run the check
        result = await service.run_check("test")
        
        if result.status == HealthStatus.HEALTHY:
            print("✅ Health monitoring working correctly")
            return True
        else:
            print(f"❌ Health check failed: {result.message}")
            return False
            
    except ImportError as e:
        print(f"❌ Health monitoring not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing health monitoring: {e}")
        return False


def test_exceptions_framework():
    """Test that exception framework exists."""
    print("⚠️ Testing exception framework...")
    
    try:
        from dotmac_shared.core.exceptions import (
            RepositoryError,
            EntityNotFoundError,
            DuplicateEntityError,
            ServiceError
        )
        
        # Test exception creation
        repo_error = RepositoryError("test error")
        if repo_error.message == "test error":
            print("✅ Exception framework working correctly")
            return True
        else:
            print("❌ Exception framework not working")
            return False
            
    except ImportError as e:
        print(f"❌ Exception framework not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing exceptions: {e}")
        return False


async def run_validation():
    """Run all validation tests."""
    print("🚀 Starting DotMac Framework Implementation Validation")
    print("=" * 60)
    
    tests = [
        test_sql_injection_fix,
        test_secrets_removal,
        test_input_validation,
        test_repository_standardization,
        test_service_standardization,
        test_health_monitoring,
        test_exceptions_framework,
    ]
    
    results = []
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    # Summary
    print("=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Implementation is working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - Review implementation")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)