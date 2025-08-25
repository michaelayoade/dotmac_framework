#!/usr/bin/env python3
"""
Minimal test to validate ISP Framework can import core components.
"""

import sys
import os

# Add the ISP framework to path
sys.path.insert(0, '/home/dotmac_framework/isp-framework/src')

def test_core_imports():
    """Test core imports step by step."""
    
    print("🧪 Testing ISP Framework Core Imports")
    print("=" * 50)
    
    try:
        print("1. Testing settings...")
        from dotmac_isp.core.settings import get_settings
        settings = get_settings()
        print(f"   ✅ Settings loaded: {settings.app_name}")
    except Exception as e:
        print(f"   ❌ Settings failed: {e}")
        return False
    
    try:
        print("2. Testing database...")
        from dotmac_isp.core.database import engine, async_engine
        print("   ✅ Database engines created")
    except Exception as e:
        print(f"   ❌ Database failed: {e}")
        return False
        
    try:
        print("3. Testing shared exceptions...")
        from dotmac_isp.shared.exceptions import DotMacISPError
        print("   ✅ Shared exceptions imported")
    except Exception as e:
        print(f"   ❌ Shared exceptions failed: {e}")
        return False
    
    try:
        print("4. Testing basic FastAPI app creation...")
        from fastapi import FastAPI
        app = FastAPI(title="Test ISP Framework")
        print("   ✅ FastAPI app created")
        return True
    except Exception as e:
        print(f"   ❌ FastAPI app failed: {e}")
        return False

def test_app_import():
    """Test if the main app can import without the problematic modules."""
    print("\n5. Testing main app import...")
    try:
        # Set environment to make sure we have config
        os.environ.setdefault('JWT_SECRET_KEY', 'dev-test-key-minimum-32-chars-long')
        os.environ.setdefault('SECRET_KEY', 'dev-test-secret-minimum-32-chars-long')
        
        import dotmac_isp.app
        print("   ✅ Main app imports successfully!")
        return True
    except Exception as e:
        print(f"   ❌ Main app import failed: {e}")
        print(f"   📝 Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("🚀 DotMac ISP Framework - Minimal Import Test")
    
    # Test core components first
    core_success = test_core_imports()
    
    if core_success:
        print(f"\n✅ Core components working!")
        # Try main app import
        app_success = test_app_import()
        
        if app_success:
            print(f"\n🎉 ISP Framework is ready!")
        else:
            print(f"\n⚠️ Core works, but full app has issues")
    else:
        print(f"\n❌ Core components have issues")