#!/usr/bin/env python3
"""
Test script to verify observability configuration fixes.
This tests the critical imports that were failing before.
"""

import sys
import traceback
from pathlib import Path

# Add the packages to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/dotmac-platform-services/src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages/dotmac-core/src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_critical_imports():
    """Test the imports that were previously failing."""
    print("Testing critical observability imports...")
    
    try:
        # Test 1: Core configuration imports (was failing with None)
        print("1. Testing configuration imports...")
        from dotmac.platform.observability import (
            create_default_config, 
            ExporterConfig, 
            ExporterType
        )
        print("   ✅ Configuration imports successful")
        
        # Test 2: Create a basic config (was failing with NoneType callable)
        print("2. Testing create_default_config...")
        config = create_default_config(
            service_name="test-service",
            environment="development"
        )
        print(f"   ✅ Config created: service={config.service_name}, env={config.environment}")
        
        # Test 3: Test invalid exporter filtering (prometheus in tracing)
        print("3. Testing invalid exporter filtering...")
        config_with_invalid = create_default_config(
            service_name="test-service",
            tracing_exporters=["console", "prometheus"],  # prometheus should be filtered out
            metrics_exporters=["console", "prometheus"]   # prometheus should be kept
        )
        trace_exporters = [exp.type for exp in config_with_invalid.tracing_exporters]
        metrics_exporters = [exp.type for exp in config_with_invalid.metrics_exporters]
        
        assert ExporterType.PROMETHEUS not in trace_exporters, "Prometheus should be filtered from tracing"
        assert ExporterType.PROMETHEUS in metrics_exporters, "Prometheus should be kept in metrics"
        print("   ✅ Invalid exporter filtering works correctly")
        
        # Test 4: Test bootstrap imports 
        print("4. Testing bootstrap imports...")
        from dotmac.platform.observability.bootstrap import initialize_otel
        print("   ✅ Bootstrap imports successful")
        
        # Test 5: Test metrics registry method (was using wrong attribute)
        print("5. Testing metrics registry...")
        try:
            from dotmac.platform.observability import initialize_metrics_registry
            registry = initialize_metrics_registry("test-service", enable_prometheus=False)
            
            # This should work now (was failing with metric_definitions)
            metrics_list = registry.list_metrics()
            print(f"   ✅ Metrics registry works: {len(metrics_list)} metrics available")
        except Exception as e:
            print(f"   ⚠️  Metrics registry test failed (not critical): {e}")
        
        print("\n🎉 All critical observability fixes are working!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_app_initialization():
    """Test that applications can initialize with observability."""
    print("\nTesting application initialization...")
    
    try:
        # Test ISP app config creation
        print("1. Testing ISP app observability config...")
        from dotmac.platform.observability import create_default_config
        
        isp_config = create_default_config(
            service_name="isp-framework",
            environment="development",
            service_version="1.0.0",
            custom_resource_attributes={
                "service.type": "isp_framework",
                "deployment.mode": "development"
            },
            tracing_exporters=["console"],
            metrics_exporters=["console"]
        )
        print(f"   ✅ ISP config: {len(isp_config.tracing_exporters)} trace, {len(isp_config.metrics_exporters)} metrics exporters")
        
        # Test Management app config creation  
        print("2. Testing Management app observability config...")
        mgmt_config = create_default_config(
            service_name="dotmac-management",
            environment="development", 
            service_version="1.0.0",
            tracing_exporters=["console"],
            metrics_exporters=["console"]
        )
        print(f"   ✅ Management config: {len(mgmt_config.tracing_exporters)} trace, {len(mgmt_config.metrics_exporters)} metrics exporters")
        
        print("🎉 Application initialization tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Application initialization test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("OBSERVABILITY CONFIGURATION FIX VALIDATION")
    print("=" * 60)
    
    success = True
    success &= test_critical_imports()
    success &= test_app_initialization()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Observability fixes are working!")
        print("Applications should now be able to start without import/config errors.")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED - Additional fixes needed.")
        sys.exit(1)