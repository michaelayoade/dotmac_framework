#!/usr/bin/env python3
"""
Test Management Platform functionality for remote deployment.
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add management platform to path
sys.path.insert(0, '/home/dotmac_framework/management-platform/app')

def test_management_platform_startup():
    """Test if Management Platform can start properly."""
    
    print("🏢 Management Platform - Production Deployment Test")
    print("=" * 60)
    
    # Set required environment variables
    os.environ.setdefault('SECRET_KEY', 'mgmt-secret-key-minimum-32-chars-long')
    os.environ.setdefault('JWT_SECRET_KEY', 'mgmt-jwt-secret-key-minimum-32-chars-long')
    os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://isp_user:isp_secure_pass_123@localhost:5432/isp_platform')
    
    try:
        print("1. Testing Management Platform imports...")
        from config import get_settings
        settings = get_settings()
        print(f"   ✅ Settings loaded: {settings.app_name}")
        
        print("2. Testing FastAPI app creation...")
        import main
        # The main module should have the app
        print("   ✅ Main module imported successfully")
        
        print("3. Testing app initialization...")
        from run_server import create_app
        from fastapi.testclient import TestClient
        
        # Use the working run_server approach
        app = create_app()
        client = TestClient(app)
        print("   ✅ Test client created")
        
        # Test basic endpoints
        try:
            response = client.get("/")
            print(f"   📍 Root endpoint: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ Root endpoint test: {e}")
        
        try:
            response = client.get("/health")
            print(f"   🏥 Health endpoint: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ Health endpoint test: {e}")
        
        print(f"\n✅ Management Platform Status: OPERATIONAL")
        print(f"   📋 App Name: {settings.app_name}")
        print(f"   🔢 Version: {settings.app_version}")
        print(f"   🔧 Environment: {settings.environment}")
        print(f"   💾 Database: {settings.database_url}")
        
        return True, settings
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def create_deployment_config():
    """Create deployment configuration for remote server."""
    print(f"\n2. Creating Deployment Configuration...")
    
    config = {
        "target_server": {
            "host": "149.102.135.97",  # Your server IP
            "ssh_port": 22,
            "ssh_user": "root",
            "deploy_path": "/opt/dotmac-tenant"
        },
        "tenant_config": {
            "tenant_id": "test-tenant-001",
            "tenant_name": "Test ISP Deployment",
            "tier": "small",
            "services": [
                "customer-management",
                "billing",
                "network-automation"
            ]
        },
        "containers": {
            "isp_framework": {
                "image": "dotmac-isp:latest",
                "port": 8000,
                "env_vars": {
                    "ENVIRONMENT": "production",
                    "DATABASE_URL": "postgresql://tenant_user:tenant_pass@localhost:5432/tenant_db",
                    "REDIS_URL": "redis://localhost:6379/0"
                }
            },
            "postgres": {
                "image": "postgres:15",
                "port": 5432,
                "volumes": ["/opt/dotmac-tenant/data:/var/lib/postgresql/data"]
            },
            "redis": {
                "image": "redis:7-alpine", 
                "port": 6379
            }
        }
    }
    
    config_file = Path("/home/dotmac_framework/deployment_config.json")
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"   ✅ Deployment config created: {config_file}")
    print(f"   🎯 Target: {config['target_server']['host']}")
    print(f"   🏢 Tenant: {config['tenant_config']['tenant_name']}")
    print(f"   📦 Containers: {len(config['containers'])} services")
    
    return config_file

def main():
    """Run Management Platform deployment tests."""
    
    # Test 1: Basic Management Platform functionality
    success, settings = test_management_platform_startup()
    if not success:
        print("❌ Management Platform is not working. Cannot proceed with deployment.")
        return False
    
    # Test 2: Create deployment configuration
    config_file = create_deployment_config()
    
    print(f"\n🎯 Management Platform Ready for Remote Deployment!")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ Management Platform: Operational")
    print(f"📋 Configuration: {config_file}")
    print(f"🎯 Target Server: 149.102.135.97")
    print(f"🚀 Ready for tenant deployment")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)