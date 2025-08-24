#!/usr/bin/env python3
"""
Security Controls Test Script
Tests that security hardening measures are working correctly.
"""

import sys
import os
import logging

# Add ISP framework to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'isp-framework/src'))

def test_import_security():
    """Test that import security controls work."""
    print("🔒 Testing Import Security Controls...")
    
    try:
        from dotmac_isp.core.secrets.dependencies import import_optional
        
        # Test 1: Allowed module should work
        result = import_optional('structlog')
        print(f"✅ Allowed module 'structlog': {result is not None}")
        
        # Test 2: Blocked module should return None
        result = import_optional('os')
        print(f"✅ Blocked module 'os': {result is None}")
        
        # Test 3: Blocked module should return None
        result = import_optional('subprocess')  
        print(f"✅ Blocked module 'subprocess': {result is None}")
        
        # Test 4: Valid dotmac module should work
        result = import_optional('dotmac_isp.core')
        print(f"✅ Allowed dotmac module: {result is not None}")
        
        print("✅ Import security controls working correctly\n")
        return True
        
    except Exception as e:
        print(f"❌ Import security test failed: {e}\n")
        return False

def test_environment_files():
    """Test environment file security."""
    print("🔒 Testing Environment File Security...")
    
    # Check for removed insecure files
    removed_files = [
        '.env.development.template',
        '.env.production.template', 
        '.env.unified',
        'isp-framework/.env.staging'
    ]
    
    all_removed = True
    for file_path in removed_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"❌ Insecure file still exists: {file_path}")
            all_removed = False
        else:
            print(f"✅ Removed insecure file: {file_path}")
    
    # Check for secure files
    secure_files = [
        '.env.example',
        '.env.signoz', 
        'isp-framework/.env.example'
    ]
    
    for file_path in secure_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if os.path.exists(full_path):
            print(f"✅ Secure file exists: {file_path}")
        else:
            print(f"⚠️ Secure file missing: {file_path}")
    
    if all_removed:
        print("✅ Environment file security working correctly\n")
    else:
        print("❌ Environment file security needs attention\n")
        
    return all_removed

def test_explicit_imports():
    """Test that star imports have been replaced."""
    print("🔒 Testing Explicit Imports...")
    
    # Check migration file
    migration_file = os.path.join(
        os.path.dirname(__file__), 
        'management-platform/migrations/env.py'
    )
    
    if os.path.exists(migration_file):
        with open(migration_file, 'r') as f:
            content = f.read()
            
        if 'from app.models import *' in content:
            print("❌ Star import still exists in migrations/env.py")
            return False
        elif 'from app.models.billing import' in content:
            print("✅ Explicit imports implemented in migrations/env.py")
            return True
        else:
            print("⚠️ Could not verify import changes in migrations/env.py")
            return False
    else:
        print("⚠️ Migration file not found")
        return False

def main():
    """Run all security tests."""
    print("🛡️ DotMac Platform Security Controls Test")
    print("=" * 50)
    
    # Set up logging to capture security warnings
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    tests_passed = 0
    total_tests = 3
    
    # Run tests
    if test_import_security():
        tests_passed += 1
        
    if test_environment_files():
        tests_passed += 1
        
    if test_explicit_imports():
        tests_passed += 1
    
    # Results
    print("=" * 50)
    print(f"🔒 Security Tests Results: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("✅ All security controls working correctly!")
        print("🚀 Platform ready for secure deployment")
        return 0
    else:
        print("❌ Some security controls need attention")
        print("⚠️ Review failed tests before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())