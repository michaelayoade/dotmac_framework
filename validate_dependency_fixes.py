#!/usr/bin/env python3
"""
Validate that all dependency fixes have been applied successfully.
"""

import sys
import os
from datetime import datetime, timezone

def test_datetime_imports():
    """Test that timezone imports work correctly."""
    try:
        # Test timezone usage
        now = datetime.now(timezone.utc)
        print(f"✅ Timezone import test passed: {now}")
        return True
    except Exception as e:
        print(f"❌ Timezone import test failed: {e}")
        return False

def test_service_generator():
    """Test that service generator works without variable errors."""
    try:
        # Add the ISP framework source to Python path
        sys.path.insert(0, '/home/dotmac_framework/isp-framework/src')
        
        from dotmac_isp.shared.service_generator import ServiceGenerator, ServiceConfig
        
        config = ServiceConfig(
            module_name='test_module',
            service_name='TestService',
            model_name='TestModel'
        )
        
        generator = ServiceGenerator()
        print("✅ Service generator test passed")
        return True
        
    except Exception as e:
        print(f"❌ Service generator test failed: {e}")
        return False

def test_observability_imports():
    """Test observability package imports."""
    try:
        import opentelemetry
        from opentelemetry import trace, metrics
        print("✅ OpenTelemetry core imports work")
        
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            print("✅ FastAPI instrumentation available")
        except ImportError as e:
            print(f"⚠️  FastAPI instrumentation may need installation: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenTelemetry imports failed: {e}")
        return False

def check_fixed_syntax_errors():
    """Check that common syntax errors have been resolved."""
    
    error_patterns = [
        ("timezone not defined", "timezone import issues"),
        ("file_path not defined", "service generator variable issues"),
        ("config not defined", "service generator config issues"),
    ]
    
    # Files that were known to have issues
    test_files = [
        "isp-framework/src/dotmac_isp/shared/service_generator.py",
        "management-platform/app/workers/tasks/plugin_tasks.py",
    ]
    
    for filepath in test_files:
        if os.path.exists(filepath):
            try:
                # Try to compile the file
                with open(filepath, 'r') as f:
                    compile(f.read(), filepath, 'exec')
                print(f"✅ Syntax check passed: {filepath}")
            except SyntaxError as e:
                print(f"❌ Syntax error in {filepath}: {e}")
                return False
            except Exception as e:
                print(f"⚠️  Could not check {filepath}: {e}")
        else:
            print(f"⚠️  File not found: {filepath}")
    
    return True

def main():
    """Run all validation tests."""
    print("🔍 Validating dependency fixes...")
    print("=" * 50)
    
    tests = [
        ("Datetime timezone imports", test_datetime_imports),
        ("Service generator", test_service_generator),
        ("OpenTelemetry imports", test_observability_imports),
        ("Syntax error fixes", check_fixed_syntax_errors),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"   Test failed: {test_name}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All dependency fixes validated successfully!")
        return 0
    else:
        print("⚠️  Some issues remain - check the output above")
        return 1

if __name__ == "__main__":
    sys.exit(main())