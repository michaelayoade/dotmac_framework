"""Additional tests to improve API router coverage."""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import FastAPI, APIRouter

from dotmac_isp.api.routers import _register_module_routers, _register_portal_routers


class TestSuccessfulRouterRegistration:
    """Test successful router registration to cover missing lines."""
    
    def test_register_module_router_success_path(self):
        """Test the successful registration path for module routers."""
        app = FastAPI()
        mock_router = APIRouter()
        
        # Create a mock module that has the router
        mock_module = MagicMock()
        mock_module.identity_router = mock_router
        
        # Mock successful import and router finding
        with patch('builtins.__import__', return_value=mock_module), \
             patch('dotmac_isp.api.routers.getattr', return_value=mock_router), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_module_routers(app)
            
            # Should log successful registration
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list if call[0]]
            success_logs = [call for call in info_calls if "Registered router:" in call]
            assert len(success_logs) > 0, "Should log successful router registrations"
    
    def test_register_portal_router_success_path(self):
        """Test the successful registration path for portal routers."""
        app = FastAPI()
        mock_router = APIRouter()
        
        # Create a mock module that has the router
        mock_module = MagicMock()
        mock_module.admin_router = mock_router
        
        # Mock successful import and router finding
        with patch('builtins.__import__', return_value=mock_module), \
             patch('dotmac_isp.api.routers.getattr', return_value=mock_router), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_portal_routers(app)
            
            # Should log successful registration
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list if call[0]]
            success_logs = [call for call in info_calls if "Registered portal router:" in call]
            assert len(success_logs) > 0, "Should log successful portal router registrations"
    
    def test_module_router_error_logging(self):
        """Test error logging path for module routers."""
        app = FastAPI()
        
        # Mock import to raise a general exception
        with patch('builtins.__import__', side_effect=RuntimeError("Test error")), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_module_routers(app)
            
            # Should log error messages
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list if call[0]]
            error_logs = [call for call in error_calls if "Error registering router" in call]
            assert len(error_logs) > 0, "Should log router registration errors"
    
    def test_portal_router_error_logging(self):
        """Test error logging path for portal routers."""
        app = FastAPI()
        
        # Mock import to raise a general exception
        with patch('builtins.__import__', side_effect=RuntimeError("Test error")), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_portal_routers(app)
            
            # Should log error messages
            error_calls = [call[0][0] for call in mock_logger.error.call_args_list if call[0]]
            error_logs = [call for call in error_calls if "Error registering portal router" in call]
            assert len(error_logs) > 0, "Should log portal router registration errors"


class TestRouterRegistrationEdgeCases:
    """Test edge cases and specific scenarios."""
    
    def test_module_router_with_mixed_results(self):
        """Test module registration with some successes and some failures."""
        app = FastAPI()
        mock_router = APIRouter()
        
        call_count = 0
        
        def mock_import_side_effect(name, fromlist=None, **kwargs):
            """Mock Import Side Effect operation."""
            nonlocal call_count
            call_count += 1
            
            if "identity" in name:
                # First call succeeds
                mock_module = MagicMock()
                mock_module.identity_router = mock_router
                return mock_module
            elif call_count == 2:
                # Second call fails with ImportError
                raise ImportError("Module not found")
            else:
                # Third call fails with general exception
                raise RuntimeError("General error")
        
        def mock_getattr_side_effect(obj, name, default=None):
            """Mock Getattr Side Effect operation."""
            if hasattr(obj, name):
                return getattr(obj, name)
            return default
        
        with patch('builtins.__import__', side_effect=mock_import_side_effect), \
             patch('dotmac_isp.api.routers.getattr', side_effect=mock_getattr_side_effect), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_module_routers(app)
            
            # Should have logged at least one success
            all_calls = [call[0][0] for call in mock_logger.info.call_args_list if call[0]]
            all_calls.extend([call[0][0] for call in mock_logger.debug.call_args_list if call[0]])
            all_calls.extend([call[0][0] for call in mock_logger.error.call_args_list if call[0]])
            
            # Should have various types of log messages
            assert len(all_calls) > 0, "Should have logged various registration attempts"
    
    def test_portal_router_with_mixed_results(self):
        """Test portal registration with some successes and some failures."""
        app = FastAPI()
        mock_router = APIRouter()
        
        call_count = 0
        
        def mock_import_side_effect(name, fromlist=None, **kwargs):
            """Mock Import Side Effect operation."""
            nonlocal call_count
            call_count += 1
            
            if "admin" in name:
                # First call succeeds
                mock_module = MagicMock()
                mock_module.admin_router = mock_router
                return mock_module
            elif call_count == 2:
                # Second call fails with ImportError
                raise ImportError("Portal module not found")
            else:
                # Other calls fail with general exception
                raise RuntimeError("General error")
        
        def mock_getattr_side_effect(obj, name, default=None):
            """Mock Getattr Side Effect operation."""
            if hasattr(obj, name):
                return getattr(obj, name)
            return default
        
        with patch('builtins.__import__', side_effect=mock_import_side_effect), \
             patch('dotmac_isp.api.routers.getattr', side_effect=mock_getattr_side_effect), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_portal_routers(app)
            
            # Should have logged various attempts
            all_calls = [call[0][0] for call in mock_logger.info.call_args_list if call[0]]
            all_calls.extend([call[0][0] for call in mock_logger.debug.call_args_list if call[0]])
            all_calls.extend([call[0][0] for call in mock_logger.error.call_args_list if call[0]])
            
            # Should have various types of log messages
            assert len(all_calls) > 0, "Should have logged various registration attempts"


class TestSpecificErrorPaths:
    """Test specific error paths to increase coverage."""
    
    def test_module_registration_import_then_getattr_none(self):
        """Test import success but getattr returns None."""
        app = FastAPI()
        
        # Mock successful import but no router attribute
        mock_module = MagicMock()
        
        with patch('builtins.__import__', return_value=mock_module), \
             patch('dotmac_isp.api.routers.getattr', return_value=None), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_module_routers(app)
            
            # Should have warning logs about missing routers
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list if call[0]]
            missing_router_logs = [call for call in warning_calls if "not found in" in call]
            assert len(missing_router_logs) > 0, "Should warn about missing router attributes"
    
    def test_portal_registration_import_then_getattr_none(self):
        """Test import success but getattr returns None for portals."""
        app = FastAPI()
        
        # Mock successful import but no router attribute
        mock_module = MagicMock()
        
        with patch('builtins.__import__', return_value=mock_module), \
             patch('dotmac_isp.api.routers.getattr', return_value=None), \
             patch('dotmac_isp.api.routers.logger') as mock_logger:
            
            _register_portal_routers(app)
            
            # Should have warning logs about missing portal routers
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list if call[0]]
            missing_router_logs = [call for call in warning_calls if "Portal router" in call and "not found in" in call]
            assert len(missing_router_logs) > 0, "Should warn about missing portal router attributes"
    
    def test_all_router_paths_coverage(self):
        """Test comprehensive path coverage for router registration."""
        app = FastAPI()
        mock_router = APIRouter()
        
        # Test all major code paths in sequence
        scenarios = [
            # Success scenario
            (lambda name, **kw: mock_module_with_router(name, mock_router), lambda obj, name, default=None: mock_router if name.endswith('_router') else default),
            # ImportError scenario  
            (lambda name, **kw: import_error_side_effect(name), None),
            # General exception scenario
            (lambda name, **kw: general_error_side_effect(name), None),
            # Missing router scenario
            (lambda name, **kw: mock_module_without_router(name), lambda obj, name, default=None: default)
        ]
        
        for import_effect, getattr_effect in scenarios:
            with patch('builtins.__import__', side_effect=import_effect), \
                 patch('dotmac_isp.api.routers.getattr', side_effect=getattr_effect) if getattr_effect else patch('dotmac_isp.api.routers.getattr', return_value=None), \
                 patch('dotmac_isp.api.routers.logger'):
                
                # Should not raise exceptions
                _register_module_routers(app)
                _register_portal_routers(app)


def mock_module_with_router(name, router):
    """Create a mock module with the expected router."""
    mock_module = MagicMock()
    if "identity" in name:
        mock_module.identity_router = router
    elif "admin" in name:
        mock_module.admin_router = router
    return mock_module


def mock_module_without_router(name):
    """Create a mock module without the expected router."""
    return MagicMock()


def import_error_side_effect(name):
    """Simulate ImportError for all imports."""
    raise ImportError(f"No module named '{name}'")


def general_error_side_effect(name):
    """Simulate general exception for all imports."""
    raise RuntimeError(f"General error importing '{name}'")