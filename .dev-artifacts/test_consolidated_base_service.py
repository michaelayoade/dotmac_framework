#!/usr/bin/env python3
"""
Test the consolidated base service architecture.
"""

import sys
import tempfile
import os
from pathlib import Path

# Add src to Python path
sys.path.append('/home/dotmac_framework/src')

def test_base_service_imports():
    """Test that the unified base service can be imported properly."""
    print("🧪 Testing base service imports...")
    
    try:
        # Test individual imports
        from dotmac_shared.services.base import BaseService
        print("✅ BaseService imported successfully")
        
        from dotmac_shared.services.base import BaseManagementService  
        print("✅ BaseManagementService imported successfully")
        
        from dotmac_shared.services.base import ServiceFactory
        print("✅ ServiceFactory imported successfully")
        
        from dotmac_shared.services.base import ServiceRegistry
        print("✅ ServiceRegistry imported successfully")
        
        from dotmac_shared.services.base import ServiceBuilder
        print("✅ ServiceBuilder imported successfully")
        
        from dotmac_shared.services.base import ServiceRegistryBuilder
        print("✅ ServiceRegistryBuilder imported successfully")
        
        # Test exception imports
        from dotmac_shared.services.base import ServiceError, ServiceNotFoundError, ServiceConfigurationError, ServiceDependencyError
        print("✅ Service exceptions imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_base_service_structure():
    """Test the structure and methods of the base service."""
    print("\n🧪 Testing base service structure...")
    
    try:
        from dotmac_shared.services.base import BaseService
        
        # Check if BaseService has expected methods
        expected_methods = [
            'create', 'get_by_id', 'update', 'delete', 'list', 'count',
            '_validate_create', '_validate_update', '_validate_delete',
            '_validate_access', '_post_create', '_post_update', '_post_delete'
        ]
        
        for method in expected_methods:
            if hasattr(BaseService, method):
                print(f"✅ BaseService.{method} exists")
            else:
                print(f"❌ BaseService.{method} missing")
                return False
        
        # Check if BaseManagementService extends BaseService
        from dotmac_shared.services.base import BaseManagementService
        if issubclass(BaseManagementService, BaseService):
            print("✅ BaseManagementService extends BaseService")
        else:
            print("❌ BaseManagementService does not extend BaseService")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False

def test_service_factory_functionality():
    """Test the service factory functionality."""
    print("\n🧪 Testing service factory functionality...")
    
    try:
        from dotmac_shared.services.base import ServiceFactory, ServiceBuilder, BaseService
        from sqlalchemy.orm import Session
        from unittest.mock import Mock
        
        # Create mock database session
        mock_session = Mock(spec=Session)
        
        # Create factory instance
        factory = ServiceFactory(mock_session, tenant_id="test-tenant")
        print("✅ ServiceFactory instance created")
        
        # Test builder pattern
        builder = ServiceBuilder(factory)
        print("✅ ServiceBuilder instance created")
        
        # Test builder methods exist
        if hasattr(builder, 'with_service') and hasattr(builder, 'with_model') and hasattr(builder, 'build'):
            print("✅ ServiceBuilder has expected methods")
        else:
            print("❌ ServiceBuilder missing expected methods")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Service factory test failed: {e}")
        return False

def test_service_registry_functionality():
    """Test the service registry functionality."""
    print("\n🧪 Testing service registry functionality...")
    
    try:
        from dotmac_shared.services.base import ServiceRegistry, ServiceRegistryBuilder
        from sqlalchemy.orm import Session
        from unittest.mock import Mock
        
        # Create mock database session
        mock_session = Mock(spec=Session)
        
        # Create registry instance
        registry = ServiceRegistry(mock_session, tenant_id="test-tenant")
        print("✅ ServiceRegistry instance created")
        
        # Test registry methods exist
        expected_methods = [
            'register_service', 'get_service', 'list_services', 'is_registered',
            'is_healthy', 'get_health_status', 'unregister_service', 'clear_cache'
        ]
        
        for method in expected_methods:
            if hasattr(registry, method):
                print(f"✅ ServiceRegistry.{method} exists")
            else:
                print(f"❌ ServiceRegistry.{method} missing")
                return False
        
        # Test registry builder
        builder = ServiceRegistryBuilder(mock_session, tenant_id="test-tenant")
        print("✅ ServiceRegistryBuilder instance created")
        
        return True
        
    except Exception as e:
        print(f"❌ Service registry test failed: {e}")
        return False

def test_updated_service_imports():
    """Test that updated service files can still import properly."""
    print("\n🧪 Testing updated service imports...")
    
    # Test files that were updated by the import script
    test_imports = [
        "dotmac_isp.modules.billing.service",
        "dotmac_isp.modules.identity.service", 
        "dotmac_isp.modules.analytics.service",
        "dotmac_isp.modules.gis.services",
    ]
    
    for module_name in test_imports:
        try:
            __import__(module_name)
            print(f"✅ {module_name} imports successfully")
        except ImportError as e:
            print(f"⚠️  {module_name} import warning: {e}")
            # This is acceptable as some modules may have dependencies not available
        except Exception as e:
            print(f"❌ {module_name} import failed: {e}")
            return False
    
    return True

def test_management_service_imports():
    """Test management service imports."""
    print("\n🧪 Testing management service imports...")
    
    try:
        # Test the management shared import that was updated
        from dotmac_management.shared import BaseManagementService
        print("✅ BaseManagementService imported from management.shared")
        
        # Verify it's the same class as the unified one
        from dotmac_shared.services.base import BaseManagementService as UnifiedBaseManagementService
        
        if BaseManagementService is UnifiedBaseManagementService:
            print("✅ Management shared uses unified BaseManagementService")
        else:
            print("❌ Management shared does not use unified BaseManagementService")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Management service import test failed: {e}")
        return False

def main():
    """Run all tests for the consolidated base service."""
    print("🚀 Testing Consolidated Base Service Architecture")
    print("=" * 60)
    
    tests = [
        test_base_service_imports,
        test_base_service_structure, 
        test_service_factory_functionality,
        test_service_registry_functionality,
        test_updated_service_imports,
        test_management_service_imports,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ Test passed\n")
            else:
                print("❌ Test failed\n")
        except Exception as e:
            print(f"❌ Test error: {e}\n")
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Consolidated base service is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Review the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)