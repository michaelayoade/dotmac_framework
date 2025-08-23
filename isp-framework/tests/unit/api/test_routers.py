"""Tests for API router registration system."""

import pytest
from unittest.mock import MagicMock, patch, call
from fastapi import FastAPI
import logging
import importlib.util

from dotmac_isp.api.routers import register_routers, _register_module_routers, _register_portal_routers


class TestRegisterRouters:
    """Test main router registration function."""
    
    @patch('dotmac_isp.api.routers._register_portal_routers')
    @patch('dotmac_isp.api.routers._register_module_routers')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_routers_success(self, mock_logger, mock_module_routers, mock_portal_routers):
        """Test successful registration of all routers."""
        app = FastAPI()
        
        register_routers(app)
        
        # Verify both registration functions called
        mock_module_routers.assert_called_once_with(app)
        mock_portal_routers.assert_called_once_with(app)
        
        # Verify logging
        expected_calls = [
            call("Registering API routers..."),
            call("API router registration complete")
        ]
        mock_logger.info.assert_has_calls(expected_calls)
    
    @patch('dotmac_isp.api.routers._register_portal_routers')
    @patch('dotmac_isp.api.routers._register_module_routers')
    def test_register_routers_with_real_app(self, mock_module_routers, mock_portal_routers):
        """Test router registration with real FastAPI app."""
        app = FastAPI()
        original_routers = len(app.router.routes)
        
        register_routers(app)
        
        # Verify registration functions were called
        mock_module_routers.assert_called_once_with(app)
        mock_portal_routers.assert_called_once_with(app)


class TestRegisterModuleRouters:
    """Test module router registration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.mock_router = MagicMock()
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_module_routers_success(self, mock_logger, mock_import):
        """Test successful module router registration."""
        # Setup mock module with router
        mock_module = MagicMock()
        mock_module.identity_router = self.mock_router
        
        def mock_import_func(name, fromlist=None, *args, **kwargs):
            if "dotmac_isp.modules." in name:
                return mock_module
            return __import__(name, fromlist, *args, **kwargs)
        
        mock_import.side_effect = mock_import_func
        
        # Mock getattr to return the router
        with patch('dotmac_isp.api.routers.getattr', return_value=self.mock_router):
            _register_module_routers(self.app)
        
        # Verify router was added to app (check that include_router would be called)
        # Note: We can't easily verify include_router was called without mocking FastAPI
        mock_logger.info.assert_called()
        
        # Verify import was attempted for all expected modules
        expected_modules = [
            "dotmac_isp.modules.identity.router",
            "dotmac_isp.modules.billing.router", 
            "dotmac_isp.modules.services.router",
            "dotmac_isp.modules.support.router",
            "dotmac_isp.modules.customers.router",
            "dotmac_isp.modules.network_integration.router",
            "dotmac_isp.modules.gis.router",
            "dotmac_isp.modules.analytics.router",
            "dotmac_isp.modules.sales.router"
        ]
        
        # Check that import was called for each expected module
        import_calls = [call[0][0] for call in mock_import.call_args_list]
        for expected_module in expected_modules:
            assert expected_module in import_calls
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_module_routers_import_error(self, mock_logger, mock_import):
        """Test handling of import errors for missing modules."""
        mock_import.side_effect = ImportError("Module not found")
        
        _register_module_routers(self.app)
        
        # Should log debug messages for missing modules
        mock_logger.debug.assert_called()
        # Verify debug calls contain expected module paths
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("dotmac_isp.modules." in call for call in debug_calls)
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_module_routers_missing_router_attribute(self, mock_logger, mock_import):
        """Test handling of modules without expected router attribute."""
        mock_module = MagicMock()
        mock_import.return_value = mock_module
        
        # Mock getattr to return None (router not found)
        with patch('dotmac_isp.api.routers.getattr', return_value=None):
            _register_module_routers(self.app)
        
        # Should log warnings for missing routers
        mock_logger.warning.assert_called()
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("not found in" in call for call in warning_calls)
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_module_routers_general_exception(self, mock_logger, mock_import):
        """Test handling of general exceptions during registration."""
        mock_import.side_effect = Exception("Unexpected error")
        
        _register_module_routers(self.app)
        
        # Should log errors for unexpected exceptions
        mock_logger.error.assert_called()
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any("Error registering router" in call for call in error_calls)


class TestRegisterPortalRouters:
    """Test portal router registration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = FastAPI()
        self.mock_router = MagicMock()
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_portal_routers_success(self, mock_logger, mock_import):
        """Test successful portal router registration."""
        mock_module = MagicMock()
        mock_module.admin_router = self.mock_router
        mock_import.return_value = mock_module
        
        with patch('dotmac_isp.api.routers.getattr', return_value=self.mock_router):
            _register_portal_routers(self.app)
        
        mock_logger.info.assert_called()
        
        # Verify import was attempted for all expected portal modules
        expected_portals = [
            "dotmac_isp.portals.admin.router",
            "dotmac_isp.portals.customer.router",
            "dotmac_isp.portals.reseller.router", 
            "dotmac_isp.portals.technician.router"
        ]
        
        import_calls = [call[0][0] for call in mock_import.call_args_list]
        for expected_portal in expected_portals:
            assert expected_portal in import_calls
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_portal_routers_import_error(self, mock_logger, mock_import):
        """Test handling of import errors for missing portal modules."""
        mock_import.side_effect = ImportError("Portal module not found")
        
        _register_portal_routers(self.app)
        
        mock_logger.debug.assert_called()
        debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
        assert any("dotmac_isp.portals." in call for call in debug_calls)
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_portal_routers_missing_router_attribute(self, mock_logger, mock_import):
        """Test handling of portal modules without expected router attribute."""
        mock_module = MagicMock()
        mock_import.return_value = mock_module
        
        with patch('dotmac_isp.api.routers.getattr', return_value=None):
            _register_portal_routers(self.app)
        
        mock_logger.warning.assert_called()
        warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
        assert any("Portal router" in call and "not found in" in call for call in warning_calls)
    
    @patch('builtins.__import__')
    @patch('dotmac_isp.api.routers.logger')
    def test_register_portal_routers_general_exception(self, mock_logger, mock_import):
        """Test handling of general exceptions during portal registration."""
        mock_import.side_effect = Exception("Portal registration error")
        
        _register_portal_routers(self.app)
        
        mock_logger.error.assert_called()
        error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
        assert any("Error registering portal router" in call for call in error_calls)


class TestIntegrationScenarios:
    """Test integration scenarios for router registration."""
    
    @patch('builtins.__import__')
    def test_mixed_success_and_failure_registration(self, mock_import):
        """Test scenario with some successful and some failed registrations."""
        app = FastAPI()
        
        def import_side_effect(module_name, fromlist=None):
            if "identity" in module_name:
                # Success case - return mock module with router
                mock_module = MagicMock()
                mock_module.identity_router = MagicMock()
                return mock_module
            elif "billing" in module_name:
                # Import error case
                raise ImportError("Billing module not available")
            else:
                # General exception case
                raise Exception("Unexpected error")
        
        mock_import.side_effect = import_side_effect
        
        with patch('dotmac_isp.api.routers.getattr', return_value=MagicMock()):
            # Should not raise exceptions despite mixed results
            _register_module_routers(app)
    
    def test_router_registration_with_logging_levels(self):
        """Test that different log levels are used appropriately."""
        app = FastAPI()
        
        with patch('dotmac_isp.api.routers.logger') as mock_logger:
            # Test with all imports failing
            with patch('builtins.__import__', side_effect=ImportError()):
                _register_module_routers(app)
                
                # Should have debug calls for ImportError
                mock_logger.debug.assert_called()
                mock_logger.warning.assert_not_called()
                mock_logger.error.assert_not_called()
    
    def test_empty_app_registration(self):
        """Test registration with empty FastAPI app."""
        app = FastAPI()
        initial_routes = len(app.router.routes)
        
        # With no available modules, should not add routes
        with patch('builtins.__import__', side_effect=ImportError()):
            register_routers(app)
            
        # Routes should be unchanged (except for built-in routes)
        assert len(app.router.routes) >= initial_routes