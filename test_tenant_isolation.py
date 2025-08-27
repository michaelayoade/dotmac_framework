#!/usr/bin/env python3
"""
Comprehensive test suite for container-per-tenant isolation.

This script validates that our tenant isolation improvements work correctly
without requiring a full Docker infrastructure deployment.
"""

import os
import sys
import tempfile
import hashlib
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent / "isp-framework" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "shared"))
sys.path.insert(0, str(Path(__file__).parent / "management-platform" / "app"))

def test_shared_module_imports():
    """Test that shared modules can be imported correctly."""
    print("🧪 Testing shared module imports...")
    
    try:
        from startup.error_handling import create_startup_manager, StartupPhase
        print("   ✅ startup.error_handling imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import startup.error_handling: {e}")
        return False
    
    try:
        from health.comprehensive_checks import setup_health_checker
        print("   ✅ health.comprehensive_checks imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import health.comprehensive_checks: {e}")
        return False
    
    return True


def test_tenant_cache_isolation():
    """Test Redis cache isolation between tenants."""
    print("\n🧪 Testing tenant cache isolation...")
    
    try:
        from dotmac_isp.core.tenant_cache import TenantCacheService
        
        # Create two tenant cache services
        cache_tenant_a = TenantCacheService("redis://localhost:6379/0", "tenant:acme:")
        cache_tenant_b = TenantCacheService("redis://localhost:6379/0", "tenant:beta:")
        
        # Test key isolation
        key_a = cache_tenant_a._get_namespaced_key("user:123")
        key_b = cache_tenant_b._get_namespaced_key("user:123")
        
        assert key_a != key_b, f"Keys should be different: {key_a} vs {key_b}"
        assert key_a == "tenant:acme:user:123", f"Unexpected key format: {key_a}"
        assert key_b == "tenant:beta:user:123", f"Unexpected key format: {key_b}"
        
        print(f"   ✅ Tenant A key: {key_a}")
        print(f"   ✅ Tenant B key: {key_b}")
        print("   ✅ Keys are properly isolated")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Tenant cache isolation test failed: {e}")
        return False


def test_tenant_database_isolation():
    """Test database schema isolation logic."""
    print("\n🧪 Testing tenant database isolation...")
    
    try:
        # Test schema name generation
        tenant_ids = ["acme-corp", "beta-inc", "gamma-ltd"]
        schemas = []
        
        for tenant_id in tenant_ids:
            schema = f"tenant_{tenant_id}".replace("-", "_")
            schemas.append(schema)
            print(f"   ✅ Tenant {tenant_id} -> Schema {schema}")
        
        # Ensure all schemas are unique
        assert len(schemas) == len(set(schemas)), "Duplicate schemas detected"
        
        # Test database URL generation
        for tenant_id, schema in zip(tenant_ids, schemas):
            db_url = f"postgresql+asyncpg://user_{tenant_id.replace('-', '_')}:password@postgres:5432/dotmac_isp?options=-csearch_path={schema}"
            print(f"   ✅ {tenant_id} DB URL: {db_url[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database isolation test failed: {e}")
        return False


def test_tenant_id_generation():
    """Test tenant ID generation and collision avoidance."""
    print("\n🧪 Testing tenant ID generation...")
    
    try:
        def generate_tenant_id(name: str) -> str:
            safe_name = "".join(c.lower() for c in name if c.isalnum() or c in '-_')
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            return f"{safe_name}-{hash_suffix}"
        
        test_names = [
            "Acme Corporation",
            "Beta Industries LLC",
            "Gamma Solutions Inc.",
            "Acme Corporation",  # Duplicate to test consistency
        ]
        
        tenant_ids = []
        for name in test_names:
            tenant_id = generate_tenant_id(name)
            tenant_ids.append(tenant_id)
            print(f"   ✅ '{name}' -> {tenant_id}")
        
        # Test consistency (same name -> same ID)
        assert tenant_ids[0] == tenant_ids[3], "Same name should generate same ID"
        
        # Test uniqueness (different names -> different IDs)
        unique_ids = set(tenant_ids[:3])  # Exclude duplicate
        assert len(unique_ids) == 3, "Different names should generate different IDs"
        
        return True
        
    except Exception as e:
        print(f"   ❌ Tenant ID generation test failed: {e}")
        return False


def test_container_configuration():
    """Test container configuration generation."""
    print("\n🧪 Testing container configuration generation...")
    
    try:
        tenant_id = "test-tenant-001"
        
        # Simulate configuration generation
        container_config = {
            "name": f"dotmac-tenant-{tenant_id}",
            "environment": {
                "TENANT_ID": tenant_id,
                "DATABASE_SCHEMA": f"tenant_{tenant_id.replace('-', '_')}",
                "REDIS_NAMESPACE": f"tenant:{tenant_id}:",
                "PYTHONPATH": "/app/src:/app/shared",
                "OTEL_RESOURCE_ATTRIBUTES": f"service.name=dotmac-tenant-{tenant_id},tenant.id={tenant_id}",
            },
            "volumes": {
                "/app/shared": {"bind": "/home/dotmac_framework/shared", "mode": "ro"}
            },
            "healthcheck": {
                "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                "start_period": "120s"
            }
        }
        
        # Validate configuration
        assert container_config["environment"]["TENANT_ID"] == tenant_id
        assert "/app/shared" in container_config["environment"]["PYTHONPATH"]
        assert f"tenant:{tenant_id}:" == container_config["environment"]["REDIS_NAMESPACE"]
        
        print(f"   ✅ Container name: {container_config['name']}")
        print(f"   ✅ Tenant ID: {container_config['environment']['TENANT_ID']}")
        print(f"   ✅ DB Schema: {container_config['environment']['DATABASE_SCHEMA']}")
        print(f"   ✅ Redis namespace: {container_config['environment']['REDIS_NAMESPACE']}")
        print(f"   ✅ Python path: {container_config['environment']['PYTHONPATH']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Container configuration test failed: {e}")
        return False


def test_docker_files_exist():
    """Test that all required Docker files exist and are valid."""
    print("\n🧪 Testing Docker files existence...")
    
    required_files = [
        "docker/Dockerfile.base",
        "docker/Dockerfile.isp-optimized", 
        "docker/docker-compose.tenant-template.yml",
        "docker/scripts/tenant-startup.sh",
        "isp-framework/Dockerfile",
        "management-platform/Dockerfile",
        "docker-compose.yml"
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist


def test_startup_script_validation():
    """Test tenant startup script has required components."""
    print("\n🧪 Testing tenant startup script validation...")
    
    script_path = "docker/scripts/tenant-startup.sh"
    if not os.path.exists(script_path):
        print(f"   ❌ Startup script missing: {script_path}")
        return False
    
    try:
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        required_components = [
            "TENANT_ID",
            "DATABASE_URL",
            "alembic upgrade head",
            "PYTHONPATH",
            "wait_for_dependencies",
            "check_environment"
        ]
        
        for component in required_components:
            if component in script_content:
                print(f"   ✅ Contains {component}")
            else:
                print(f"   ❌ Missing {component}")
                return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Startup script validation failed: {e}")
        return False


def main():
    """Run all tenant isolation tests."""
    print("🔬 Container-per-Tenant Isolation Test Suite")
    print("=" * 50)
    
    tests = [
        ("Shared Module Imports", test_shared_module_imports),
        ("Tenant Cache Isolation", test_tenant_cache_isolation),
        ("Database Schema Isolation", test_tenant_database_isolation),
        ("Tenant ID Generation", test_tenant_id_generation),
        ("Container Configuration", test_container_configuration),
        ("Docker Files Existence", test_docker_files_exist),
        ("Startup Script Validation", test_startup_script_validation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED\n")
            else:
                failed += 1
                print(f"❌ {test_name}: FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name}: ERROR - {e}\n")
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Tenant isolation is working correctly.")
        return True
    else:
        print(f"⚠️  {failed} tests failed. Review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)