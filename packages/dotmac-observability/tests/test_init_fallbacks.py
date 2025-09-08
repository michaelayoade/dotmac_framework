"""
Test import fallback paths in __init__.py.
"""

import sys
from unittest.mock import patch


class TestImportFallbacks:
    """Test import fallback behavior in __init__.py."""

    def test_middleware_import_fallback(self):
        """Test middleware import fallback when FastAPI not available."""
        # Remove middleware modules from sys.modules if they exist
        modules_to_remove = []
        for key in list(sys.modules.keys()):
            if key.startswith('dotmac_observability.middleware'):
                modules_to_remove.append(key)
        
        for key in modules_to_remove:
            sys.modules.pop(key, None)
        
        # Mock middleware import failure
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if name == 'dotmac_observability.middleware' or name.endswith('.middleware'):
                raise ImportError("Mocked middleware import failure")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # Force re-import of dotmac_observability to trigger fallback
            if 'dotmac_observability' in sys.modules:
                del sys.modules['dotmac_observability']
            
            import dotmac_observability
            
            # Check fallback values
            assert dotmac_observability.MIDDLEWARE_AVAILABLE is False
            assert dotmac_observability.create_audit_middleware is None
            assert dotmac_observability.timing_middleware is None

    def test_otel_import_fallback(self):
        """Test OTEL import fallback when OpenTelemetry not available."""
        # Remove otel modules from sys.modules if they exist
        modules_to_remove = []
        for key in list(sys.modules.keys()):
            if key.startswith('dotmac_observability.otel'):
                modules_to_remove.append(key)
        
        for key in modules_to_remove:
            sys.modules.pop(key, None)
        
        # Mock otel import failure
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if name == 'dotmac_observability.otel' or name.endswith('.otel'):
                raise ImportError("Mocked OTEL import failure")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # Force re-import of dotmac_observability to trigger fallback
            if 'dotmac_observability' in sys.modules:
                del sys.modules['dotmac_observability']
            
            import dotmac_observability
            
            # Check fallback values
            assert dotmac_observability.OTEL_AVAILABLE is False
            assert dotmac_observability.enable_otel_bridge is None