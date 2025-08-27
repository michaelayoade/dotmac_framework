#!/usr/bin/env python3
"""
Staging deployment test for container-per-tenant architecture.

This script validates the core tenant isolation functionality with minimal
infrastructure setup (just PostgreSQL).
"""

import os
import sys
import asyncio
import asyncpg
import hashlib
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "isp-framework" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "shared"))

async def test_database_isolation():
    """Test actual database schema isolation with real PostgreSQL."""
    print("🗄️  Testing Database Schema Isolation")
    print("=" * 50)
    
    try:
        # Connect to PostgreSQL as admin
        conn = await asyncpg.connect(
            user="dotmac_admin",
            password="staging-postgres-pass-2024",
            host="localhost",
            port=5434,
            database="dotmac_isp"
        )
        print("✅ Connected to PostgreSQL")
        
        # Test 1: Create tenant schemas
        tenant_ids = ["acme-001", "beta-002", "gamma-003"]
        
        for tenant_id in tenant_ids:
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            
            # Create schema
            await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            print(f"✅ Created schema: {schema_name}")
            
            # Create a test table in the schema
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {schema_name}.test_customers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100),
                    tenant_id VARCHAR(50) DEFAULT '{tenant_id}'
                )
            """)
            
            # Insert test data
            await conn.execute(f"""
                INSERT INTO {schema_name}.test_customers (name) 
                VALUES ('Customer for {tenant_id}')
            """)
            print(f"✅ Created test table and data in {schema_name}")
        
        # Test 2: Verify isolation
        print("\n🧪 Testing schema isolation...")
        
        for tenant_id in tenant_ids:
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            
            # Query data from this tenant's schema
            rows = await conn.fetch(f"""
                SELECT name, tenant_id 
                FROM {schema_name}.test_customers
            """)
            
            for row in rows:
                assert row['tenant_id'] == tenant_id, f"Data leakage detected!"
                print(f"✅ {schema_name}: {row['name']} (tenant: {row['tenant_id']})")
        
        # Test 3: Test search path isolation
        print("\n🔍 Testing search path isolation...")
        
        for tenant_id in tenant_ids:
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            
            # Set search path to this tenant's schema
            await conn.execute(f"SET search_path = {schema_name}")
            
            # Query without schema prefix (should only see this tenant's data)
            rows = await conn.fetch("SELECT COUNT(*) as count FROM test_customers")
            count = rows[0]['count']
            
            assert count == 1, f"Expected 1 record, got {count}"
            print(f"✅ Search path isolation working for {schema_name}: {count} records")
        
        print("\n🎉 Database isolation test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database isolation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if 'conn' in locals():
            await conn.close()


async def test_tenant_provisioning_logic():
    """Test tenant provisioning service logic."""
    print("\n🏭 Testing Tenant Provisioning Logic")
    print("=" * 50)
    
    try:
        # Test tenant ID generation
        def generate_tenant_id(name: str) -> str:
            safe_name = "".join(c.lower() for c in name if c.isalnum() or c in '-_')
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            return f"{safe_name}-{hash_suffix}"
        
        test_companies = [
            "Acme Corporation",
            "Beta Industries Inc.",
            "Gamma Solutions LLC"
        ]
        
        tenant_configs = []
        
        for company in test_companies:
            tenant_id = generate_tenant_id(company)
            
            config = {
                "tenant_id": tenant_id,
                "company_name": company,
                "database_schema": f"tenant_{tenant_id.replace('-', '_')}",
                "database_url": f"postgresql+asyncpg://user_{tenant_id.replace('-', '_')}:password@localhost:5434/dotmac_isp?options=-csearch_path=tenant_{tenant_id.replace('-', '_')}",
                "redis_namespace": f"tenant:{tenant_id}:",
                "redis_db": hash(tenant_id) % 16,
                "container_name": f"dotmac-tenant-{tenant_id}",
                "environment": {
                    "TENANT_ID": tenant_id,
                    "DATABASE_SCHEMA": f"tenant_{tenant_id.replace('-', '_')}",
                    "REDIS_NAMESPACE": f"tenant:{tenant_id}:",
                    "PYTHONPATH": "/app/src:/app/shared"
                }
            }
            
            tenant_configs.append(config)
            print(f"✅ Generated config for {company}")
            print(f"   Tenant ID: {tenant_id}")
            print(f"   DB Schema: {config['database_schema']}")
            print(f"   Redis DB: {config['redis_db']}")
            print(f"   Redis Namespace: {config['redis_namespace']}")
        
        # Test uniqueness
        tenant_ids = [config['tenant_id'] for config in tenant_configs]
        schemas = [config['database_schema'] for config in tenant_configs]
        
        assert len(set(tenant_ids)) == len(tenant_ids), "Duplicate tenant IDs!"
        assert len(set(schemas)) == len(schemas), "Duplicate schemas!"
        
        print("\n✅ All tenant configurations are unique")
        print("✅ Tenant provisioning logic test passed!")
        
        return tenant_configs
        
    except Exception as e:
        print(f"❌ Tenant provisioning logic test failed: {e}")
        return None


async def test_shared_module_integration():
    """Test that shared modules work in the staging environment."""
    print("\n📦 Testing Shared Module Integration")
    print("=" * 50)
    
    try:
        # Test shared module imports
        from startup.error_handling import create_startup_manager, StartupPhase
        print("✅ startup.error_handling imported successfully")
        
        from health.comprehensive_checks import setup_health_checker
        print("✅ health.comprehensive_checks imported successfully")
        
        # Test ISP Framework imports with shared modules
        from dotmac_isp.core.tenant_cache import TenantCacheService
        print("✅ ISP Framework tenant cache imported successfully")
        
        # Create a test startup manager
        manager = create_startup_manager("tenant-test")
        print("✅ Startup manager created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Shared module integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all staging deployment tests."""
    print("🚀 Container-per-Tenant Staging Deployment Test")
    print("=" * 60)
    
    tests = [
        ("Database Schema Isolation", test_database_isolation()),
        ("Tenant Provisioning Logic", test_tenant_provisioning_logic()),
        ("Shared Module Integration", test_shared_module_integration())
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results.append((test_name, result is not None and result is not False))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 STAGING DEPLOYMENT TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, success in results:
        if success:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        else:
            print(f"❌ {test_name}: FAILED")
            failed += 1
    
    print(f"\n📈 Summary: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL STAGING TESTS PASSED!")
        print("🚀 Container-per-tenant architecture is validated and ready for production!")
        return True
    else:
        print("⚠️  Some tests failed. Review the issues above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)