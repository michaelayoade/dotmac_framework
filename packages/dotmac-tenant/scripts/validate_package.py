#!/usr/bin/env python3
"""
Validation script for dotmac-tenant package.

Runs basic validation tests to ensure the package is correctly structured
and all core functionality is working.
"""

import sys
import traceback
from pathlib import Path

# Add package to path for testing
package_root = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(package_root))

def test_basic_imports():
    """Test that all core modules can be imported."""
    print("Testing basic imports...")
    
    try:
        # Test core package import
        import dotmac.tenant
        print("✅ Core package import successful")
        
        # Test individual module imports
        from dotmac.tenant import TenantContext, TenantMiddleware, TenantConfig
        print("✅ Main classes import successful")
        
        from dotmac.tenant.identity import TenantIdentityResolver, get_current_tenant
        print("✅ Identity module imports successful")
        
        from dotmac.tenant.middleware import TenantMiddleware, TenantSecurityMiddleware
        print("✅ Middleware imports successful")
        
        from dotmac.tenant.boundary import TenantSecurityEnforcer
        print("✅ Security boundary imports successful")
        
        from dotmac.tenant.db import TenantDatabaseManager, configure_tenant_database
        print("✅ Database helpers imports successful")
        
        from dotmac.tenant.exceptions import TenantError, TenantNotFoundError
        print("✅ Exception imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\nTesting basic functionality...")
    
    try:
        from dotmac.tenant import TenantContext, TenantConfig, TenantResolutionStrategy
        from dotmac.tenant.identity import TenantIdentityResolver
        
        # Test config creation
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HOST_BASED,
            host_tenant_mapping={"test.example.com": "test-tenant"}
        )
        print("✅ TenantConfig creation successful")
        
        # Test resolver creation
        resolver = TenantIdentityResolver(config)
        print("✅ TenantIdentityResolver creation successful")
        
        # Test context creation
        context = TenantContext(
            tenant_id="test-tenant",
            resolution_method="test",
            resolved_from="unit-test"
        )
        print("✅ TenantContext creation successful")
        
        # Test context properties
        assert context.tenant_id == "test-tenant"
        assert context.resolution_method == "test"
        assert context.resolved_from == "unit-test"
        print("✅ TenantContext properties validation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_middleware_creation():
    """Test middleware creation without FastAPI."""
    print("\nTesting middleware creation...")
    
    try:
        from dotmac.tenant import TenantConfig, TenantMiddleware
        from dotmac.tenant.boundary import TenantSecurityEnforcer
        from unittest.mock import Mock
        
        # Mock FastAPI app
        mock_app = Mock()
        
        # Test basic middleware
        config = TenantConfig()
        middleware = TenantMiddleware(mock_app, config=config)
        print("✅ TenantMiddleware creation successful")
        
        # Test security enforcer
        enforcer = TenantSecurityEnforcer(config)
        print("✅ TenantSecurityEnforcer creation successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Middleware test failed: {e}")
        traceback.print_exc()
        return False


def test_database_manager():
    """Test database manager creation."""
    print("\nTesting database manager...")
    
    try:
        from dotmac.tenant import TenantConfig
        from dotmac.tenant.db import TenantDatabaseManager
        
        config = TenantConfig(
            database_strategy="rls",
            enable_rls=True
        )
        
        # Test without engine (should work)
        db_manager = TenantDatabaseManager(config)
        print("✅ TenantDatabaseManager creation successful")
        
        # Test RLS table tracking
        rls_tables = db_manager.get_rls_enabled_tables()
        assert isinstance(rls_tables, dict)
        print("✅ RLS table tracking successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Database manager test failed: {e}")
        traceback.print_exc()
        return False


def test_pattern_extraction():
    """Test tenant pattern extraction logic."""
    print("\nTesting pattern extraction...")
    
    try:
        from dotmac.tenant import TenantConfig, TenantResolutionStrategy
        from dotmac.tenant.identity import TenantIdentityResolver
        
        config = TenantConfig(
            resolution_strategy=TenantResolutionStrategy.HOST_BASED,
            default_host_pattern="{tenant}.example.com"
        )
        
        resolver = TenantIdentityResolver(config)
        
        # Test pattern extraction
        tenant_id = resolver._extract_tenant_from_pattern(
            "client1.example.com",
            "{tenant}.example.com"
        )
        assert tenant_id == "client1"
        print("✅ Pattern extraction successful")
        
        # Test failed extraction
        tenant_id = resolver._extract_tenant_from_pattern(
            "client1.different.com",
            "{tenant}.example.com"
        )
        assert tenant_id is None
        print("✅ Pattern extraction failure handling successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Pattern extraction test failed: {e}")
        traceback.print_exc()
        return False


def test_exception_handling():
    """Test exception classes."""
    print("\nTesting exception handling...")
    
    try:
        from dotmac.tenant.exceptions import (
            TenantError, TenantNotFoundError, TenantResolutionError,
            TenantSecurityError, TenantContextError
        )
        
        # Test basic exception
        try:
            raise TenantError("Test error", {"key": "value"})
        except TenantError as e:
            assert str(e) == "Test error"
            assert e.details == {"key": "value"}
        print("✅ TenantError handling successful")
        
        # Test specific exception
        try:
            raise TenantNotFoundError("test-tenant", "host")
        except TenantNotFoundError as e:
            assert "test-tenant" in str(e)
            assert "host" in str(e)
        print("✅ TenantNotFoundError handling successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Exception test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests."""
    print("🚀 Starting dotmac-tenant package validation")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_basic_functionality,
        test_middleware_creation,
        test_database_manager,
        test_pattern_extraction,
        test_exception_handling,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Validation Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed}/{passed+failed} ({100*passed/(passed+failed):.1f}%)")
    
    if failed == 0:
        print("\n🎉 All tests passed! Package validation successful.")
        return 0
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())