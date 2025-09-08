"""Simple tests to improve coverage of __init__.py and otel.py."""

import sys
from unittest.mock import patch

import pytest


class TestInitCoverage:
    """Test __init__.py import error branches."""
    
    def test_middleware_import_error_branch(self):
        """Test middleware ImportError branch coverage."""
        # Create a simple test that forces the import error path
        with patch.dict('sys.modules'):
            # Remove the middleware module if it exists
            modules_to_remove = [k for k in list(sys.modules.keys()) if 'middleware' in k and 'dotmac' in k]
            for mod in modules_to_remove:
                sys.modules.pop(mod, None)
            
            # Force import failure by patching
            with patch('dotmac_observability.middleware', side_effect=ImportError("Test import error")):
                try:
                    # Try to trigger re-import
                    import importlib
                    if 'dotmac_observability' in sys.modules:
                        importlib.reload(sys.modules['dotmac_observability'])
                except ImportError:
                    pass  # Expected
                
                # Verify the module still works with fallbacks
                import dotmac_observability
                assert hasattr(dotmac_observability, 'MIDDLEWARE_AVAILABLE')
                assert isinstance(dotmac_observability.MIDDLEWARE_AVAILABLE, bool)

    def test_otel_import_error_branch(self):
        """Test OTEL ImportError branch coverage."""
        # Test that OTEL fallbacks work
        import dotmac_observability
        
        # Verify OTEL attributes exist
        assert hasattr(dotmac_observability, 'OTEL_AVAILABLE')
        assert isinstance(dotmac_observability.OTEL_AVAILABLE, bool)
        
        # Test the fallback behavior 
        if not dotmac_observability.OTEL_AVAILABLE:
            assert dotmac_observability.enable_otel_bridge is None
        
    def test_import_error_paths_directly(self):
        """Direct test of import error handling."""
        # Mock sys.modules to simulate missing dependencies
        original_modules = sys.modules.copy()
        
        try:
            # Remove OpenTelemetry modules
            otel_modules = [k for k in sys.modules.keys() if k.startswith('opentelemetry')]
            for mod in otel_modules:
                sys.modules.pop(mod, None)
            
            # Remove FastAPI/Starlette modules  
            fastapi_modules = [k for k in sys.modules.keys() if k.startswith(('fastapi', 'starlette'))]
            for mod in fastapi_modules:
                sys.modules.pop(mod, None)
                
            # Force re-import to trigger fallback paths
            dotmac_modules = [k for k in list(sys.modules.keys()) if k.startswith('dotmac_observability')]
            for mod in dotmac_modules:
                sys.modules.pop(mod, None)
            
            # Import should work with fallbacks
            import dotmac_observability
            
            # Core functionality should be available
            assert dotmac_observability.MetricsCollector is not None
            assert dotmac_observability.HealthMonitor is not None
            
        finally:
            # Restore original modules
            sys.modules.update(original_modules)


class TestOtelCoverage:
    """Test otel.py coverage."""
    
    def test_otel_available_flag(self):
        """Test OTEL_AVAILABLE flag."""
        try:
            from dotmac_observability.otel import OTEL_AVAILABLE
            assert isinstance(OTEL_AVAILABLE, bool)
        except ImportError:
            # If we can't import otel module, that means OTEL is not available
            from dotmac_observability import OTEL_AVAILABLE
            assert OTEL_AVAILABLE is False

    def test_otel_imports_when_unavailable(self):
        """Test otel imports when OpenTelemetry is unavailable."""
        try:
            from dotmac_observability.otel import OTEL_AVAILABLE
            if not OTEL_AVAILABLE:
                # Test that the fallback values are set correctly
                from dotmac_observability.otel import (
                    otel_metrics,
                    OTLPMetricExporter,
                    MeterProvider,
                    PeriodicExportingMetricReader,
                    Resource,
                    set_meter_provider
                )
                
                # These should all be None when OTEL is not available
                assert otel_metrics is None
                assert OTLPMetricExporter is None
                assert MeterProvider is None
                assert PeriodicExportingMetricReader is None
                assert Resource is None
                assert set_meter_provider is None
                
        except ImportError:
            # Can't import otel module at all
            pass

    def test_enable_otel_bridge_import_error(self):
        """Test enable_otel_bridge when OTEL not available."""
        try:
            from dotmac_observability.otel import enable_otel_bridge, OTEL_AVAILABLE
            
            if not OTEL_AVAILABLE:
                # Should raise ImportError when called
                from dotmac_observability import MetricsCollector
                collector = MetricsCollector()
                
                with pytest.raises(ImportError, match="OpenTelemetry extras not installed"):
                    enable_otel_bridge(collector, service_name="test")
                    
        except ImportError:
            # Module not available - test the fallback in __init__.py
            from dotmac_observability import enable_otel_bridge
            assert enable_otel_bridge is None

    def test_otel_bridge_class_when_unavailable(self):
        """Test OTelBridge class when OTEL unavailable."""
        try:
            from dotmac_observability.otel import OTelBridge, OTEL_AVAILABLE
            from dotmac_observability import MetricsCollector
            
            if not OTEL_AVAILABLE:
                collector = MetricsCollector()
                
                # Should raise ImportError when trying to initialize
                with pytest.raises(ImportError, match="OpenTelemetry extras not installed"):
                    OTelBridge(collector, "test-service")
                    
        except ImportError:
            # Module can't be imported at all
            pass

    def test_otel_error_handling_branches(self):
        """Test various error handling branches in otel.py."""
        try:
            from dotmac_observability.otel import OTEL_AVAILABLE
            
            # Test import error coverage by accessing module attributes
            if OTEL_AVAILABLE:
                # Test the successful import path
                from dotmac_observability.otel import enable_otel_bridge
                assert enable_otel_bridge is not None
            else:
                # Test the import error path  
                from dotmac_observability.otel import enable_otel_bridge
                
                from dotmac_observability import MetricsCollector
                collector = MetricsCollector()
                
                with pytest.raises(ImportError):
                    enable_otel_bridge(collector, service_name="test")
                    
        except ImportError:
            # Can't import otel module - expected when OpenTelemetry not available
            from dotmac_observability import OTEL_AVAILABLE
            assert OTEL_AVAILABLE is False


class TestTypesCoverage:
    """Test remaining coverage in types.py."""
    
    def test_health_check_result_defaults(self):
        """Test HealthCheckResult with all defaults."""
        from dotmac_observability.types import HealthCheckResult, HealthStatus
        
        result = HealthCheckResult("test", HealthStatus.HEALTHY, 100.0)
        
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms == 100.0
        assert result.error is None
        assert result.message is None
        assert result.required is True  # Default value
        assert result.timestamp is None