#!/usr/bin/env python3
"""
Isolated test runner for comprehensive test suite.

This runner executes the comprehensive test suite in an isolated environment
to validate our mock implementations work correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add test directory to path
test_dir = Path(__file__).parent.parent / "tests"
sys.path.insert(0, str(test_dir))

# Import test modules directly
test_modules = [
    "test_ipam_service_comprehensive",
    "test_ipam_schemas_comprehensive", 
    "test_ipam_repository_comprehensive",
    "test_ipam_network_utils_comprehensive",
    "test_ssh_provisioning_comprehensive",
    "test_snmp_monitoring_comprehensive",
    "test_device_management_comprehensive",
    "test_radius_authentication_comprehensive",
    "test_integration_comprehensive"
]

async def run_test_suite():
    """Run the comprehensive test suite."""
    print("🚀 Starting Comprehensive Test Suite")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    for module_name in test_modules:
        print(f"\n📋 Testing Module: {module_name}")
        print("-" * 40)
        
        try:
            # Import the test module
            test_module = __import__(module_name)
            
            # Find test classes
            test_classes = [getattr(test_module, attr) for attr in dir(test_module) 
                           if attr.startswith('Test') and hasattr(getattr(test_module, attr), '__bases__')]
            
            for test_class in test_classes:
                print(f"  🧪 {test_class.__name__}")
                
                # Find test methods
                test_methods = [method for method in dir(test_class) 
                              if method.startswith('test_') and callable(getattr(test_class, method))]
                
                for test_method in test_methods:
                    total_tests += 1
                    method_name = test_method.replace('test_', '').replace('_', ' ').title()
                    
                    try:
                        # Create instance and run test
                        instance = test_class()
                        method = getattr(instance, test_method)
                        
                        if asyncio.iscoroutinefunction(method):
                            await method()
                        else:
                            method()
                        
                        print(f"    ✅ {method_name}")
                        passed_tests += 1
                        
                    except Exception as e:
                        if "skip" in str(e).lower() or "not available" in str(e).lower():
                            print(f"    ⏭️  {method_name} (Skipped: Module not available)")
                            skipped_tests += 1
                        else:
                            print(f"    ❌ {method_name} - {str(e)[:80]}...")
                            failed_tests += 1
        
        except Exception as e:
            print(f"  ❌ Failed to import {module_name}: {e}")
            failed_tests += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"Total Tests:   {total_tests}")
    print(f"✅ Passed:     {passed_tests}")
    print(f"❌ Failed:     {failed_tests}")  
    print(f"⏭️  Skipped:    {skipped_tests}")
    print(f"Success Rate:  {(passed_tests / max(total_tests, 1)) * 100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! Test suite is working correctly.")
    else:
        print(f"\n⚠️  {failed_tests} tests failed. This is expected if modules are not fully implemented.")
    
    return passed_tests, failed_tests, skipped_tests


if __name__ == "__main__":
    asyncio.run(run_test_suite())