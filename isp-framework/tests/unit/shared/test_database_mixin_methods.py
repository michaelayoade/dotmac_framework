"""Tests for database mixin method implementations."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from dotmac_isp.shared.database.base import SoftDeleteMixin, StatusMixin


class TestSoftDeleteMixinMethods:
    """Test SoftDeleteMixin method implementations."""
    
    def test_soft_delete_method_implementation(self):
        """Test soft_delete method actually executes the missing lines."""
        # Create a concrete class with the mixin
        class TestModel(SoftDeleteMixin):
            def __init__(self):
                self.is_deleted = False
                self.deleted_at = None
        
        instance = TestModel()
        
        # Mock datetime.utcnow to control the timestamp
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call the method - this should execute lines 60-61
            instance.soft_delete()
            
            # Verify the method executed correctly
            assert instance.is_deleted is True
            assert instance.deleted_at == mock_now
            mock_datetime.utcnow.assert_called_once()
    
    def test_restore_method_implementation(self):
        """Test restore method actually executes the missing lines."""
        # Create a concrete class with the mixin
        class TestModel(SoftDeleteMixin):
            def __init__(self):
                self.is_deleted = True
                self.deleted_at = datetime(2023, 12, 15, 10, 30, 45)
        
        instance = TestModel()
        
        # Call the method - this should execute lines 65-66
        instance.restore()
        
        # Verify the method executed correctly
        assert instance.is_deleted is False
        assert instance.deleted_at is None
    
    def test_soft_delete_method_multiple_calls(self):
        """Test soft_delete method can be called multiple times."""
        class TestModel(SoftDeleteMixin):
            def __init__(self):
                self.is_deleted = False
                self.deleted_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            first_time = datetime(2023, 12, 15, 10, 30, 45)
            second_time = datetime(2023, 12, 15, 11, 30, 45)
            mock_datetime.utcnow.side_effect = [first_time, second_time]
            
            # First call
            instance.soft_delete()
            assert instance.is_deleted is True
            assert instance.deleted_at == first_time
            
            # Second call - should update the timestamp
            instance.soft_delete()
            assert instance.is_deleted is True
            assert instance.deleted_at == second_time


class TestStatusMixinMethods:
    """Test StatusMixin method implementations."""
    
    def test_change_status_method_with_reason(self):
        """Test change_status method with reason parameter."""
        # Create a concrete class with the mixin
        class TestModel(StatusMixin):
            def __init__(self):
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
        
        instance = TestModel()
        
        # Mock datetime.utcnow to control the timestamp
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call the method - this should execute lines 105-107
            instance.change_status("inactive", "System maintenance")
            
            # Verify the method executed correctly
            assert instance.status == "inactive"
            assert instance.status_reason == "System maintenance"
            assert instance.status_changed_at == mock_now
            mock_datetime.utcnow.assert_called_once()
    
    def test_change_status_method_without_reason(self):
        """Test change_status method without reason parameter."""
        class TestModel(StatusMixin):
            def __init__(self):
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call the method with None reason - this should execute lines 105-107
            instance.change_status("disabled")
            
            # Verify the method executed correctly
            assert instance.status == "disabled"
            assert instance.status_reason is None
            assert instance.status_changed_at == mock_now
            mock_datetime.utcnow.assert_called_once()
    
    def test_change_status_method_multiple_changes(self):
        """Test change_status method with multiple status changes."""
        class TestModel(StatusMixin):
            def __init__(self):
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            first_time = datetime(2023, 12, 15, 10, 30, 45)
            second_time = datetime(2023, 12, 15, 11, 30, 45)
            third_time = datetime(2023, 12, 15, 12, 30, 45)
            mock_datetime.utcnow.side_effect = [first_time, second_time, third_time]
            
            # First change
            instance.change_status("inactive", "User requested")
            assert instance.status == "inactive"
            assert instance.status_reason == "User requested"
            assert instance.status_changed_at == first_time
            
            # Second change
            instance.change_status("suspended", "Payment overdue")
            assert instance.status == "suspended"
            assert instance.status_reason == "Payment overdue"
            assert instance.status_changed_at == second_time
            
            # Third change without reason
            instance.change_status("active")
            assert instance.status == "active"
            assert instance.status_reason is None
            assert instance.status_changed_at == third_time
    
    def test_change_status_with_empty_string_reason(self):
        """Test change_status method with empty string as reason."""
        class TestModel(StatusMixin):
            def __init__(self):
                self.status = "active"
                self.status_reason = "Initial reason"
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call with empty string reason
            instance.change_status("maintenance", "")
            
            # Verify the method executed correctly
            assert instance.status == "maintenance"
            assert instance.status_reason == ""
            assert instance.status_changed_at == mock_now


class TestMixinMethodsIntegration:
    """Test integration of mixin methods."""
    
    def test_combined_mixin_methods(self):
        """Test that both mixins work together correctly."""
        class TestModel(SoftDeleteMixin, StatusMixin):
            def __init__(self):
                # SoftDeleteMixin attributes
                self.is_deleted = False
                self.deleted_at = None
                
                # StatusMixin attributes
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            first_time = datetime(2023, 12, 15, 10, 30, 45)
            second_time = datetime(2023, 12, 15, 11, 30, 45)
            mock_datetime.utcnow.side_effect = [first_time, second_time]
            
            # Change status first
            instance.change_status("inactive", "Preparing for maintenance")
            assert instance.status == "inactive"
            assert instance.status_reason == "Preparing for maintenance"
            assert instance.status_changed_at == first_time
            
            # Then soft delete
            instance.soft_delete()
            assert instance.is_deleted is True
            assert instance.deleted_at == second_time
            
            # Status should remain unchanged by soft delete
            assert instance.status == "inactive"
            assert instance.status_reason == "Preparing for maintenance"
    
    def test_method_execution_coverage(self):
        """Test to ensure all method lines are executed for coverage."""
        # Test SoftDeleteMixin methods
        class SoftDeleteModel(SoftDeleteMixin):
            def __init__(self):
                self.is_deleted = False
                self.deleted_at = None
        
        soft_model = SoftDeleteModel()
        
        # Execute soft_delete (lines 60-61)
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.now()
            soft_model.soft_delete()
            assert soft_model.is_deleted is True
            assert soft_model.deleted_at is not None
        
        # Execute restore (lines 65-66)
        soft_model.restore()
        assert soft_model.is_deleted is False
        assert soft_model.deleted_at is None
        
        # Test StatusMixin methods
        class StatusModel(StatusMixin):
            def __init__(self):
                self.status = "initial"
                self.status_reason = None
                self.status_changed_at = None
        
        status_model = StatusModel()
        
        # Execute change_status (lines 105-107)
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.now()
            status_model.change_status("updated", "Test reason")
            assert status_model.status == "updated"
            assert status_model.status_reason == "Test reason"
            assert status_model.status_changed_at is not None