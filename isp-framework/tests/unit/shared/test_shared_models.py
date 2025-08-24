"""Tests for shared models module methods and properties."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from uuid import uuid4

from dotmac_isp.shared.models import (
    SoftDeleteMixin, StatusMixin, AddressMixin, ContactMixin
)


class TestSoftDeleteMixinMethods:
    """Test SoftDeleteMixin method implementations from shared.models."""
    
    def test_soft_delete_method(self):
        """Test soft_delete method - covers lines 28-29."""
        class TestModel(SoftDeleteMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.is_deleted = False
                self.deleted_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.models.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call the method - this executes lines 28-29
            instance.soft_delete()
            
            assert instance.is_deleted is True
            assert instance.deleted_at == mock_now
    
    def test_restore_method(self):
        """Test restore method - covers lines 33-34."""
        class TestModel(SoftDeleteMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.is_deleted = True
                self.deleted_at = datetime(2023, 12, 15, 10, 30, 45)
        
        instance = TestModel()
        
        # Call the method - this executes lines 33-34
        instance.restore()
        
        assert instance.is_deleted is False
        assert instance.deleted_at is None


class TestStatusMixinMethods:
    """Test StatusMixin method implementations from shared.models."""
    
    def test_change_status_method(self):
        """Test change_status method - covers lines 79-81."""
        class TestModel(StatusMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.models.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call the method - this executes lines 79-81
            instance.change_status("inactive", "System maintenance")
            
            assert instance.status == "inactive"
            assert instance.status_reason == "System maintenance"
            assert instance.status_changed_at == mock_now
    
    def test_change_status_method_with_none_reason(self):
        """Test change_status method with None reason."""
        class TestModel(StatusMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.status = "active"
                self.status_reason = "Previous reason"
                self.status_changed_at = None
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.models.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Call with None reason
            instance.change_status("suspended", None)
            
            assert instance.status == "suspended"
            assert instance.status_reason is None
            assert instance.status_changed_at == mock_now


class TestAddressMixinProperties:
    """Test AddressMixin property implementations."""
    
    def test_full_address_property_all_fields(self):
        """Test full_address property with all fields - covers lines 96-102."""
        class TestModel(AddressMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = "123 Main St"
                self.city = "New York"
                self.state_province = "NY"
                self.postal_code = "10001"
        
        instance = TestModel()
        
        # Call the property - this executes lines 96-102
        result = instance.full_address
        
        expected = "123 Main St, New York, NY, 10001"
        assert result == expected
    
    def test_full_address_property_partial_fields(self):
        """Test full_address property with some None fields."""
        class TestModel(AddressMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = "456 Oak Ave"
                self.city = None  # None value should be filtered out
                self.state_province = "CA"
                self.postal_code = "90210"
        
        instance = TestModel()
        
        result = instance.full_address
        
        expected = "456 Oak Ave, CA, 90210"
        assert result == expected
    
    def test_full_address_property_empty_fields(self):
        """Test full_address property with empty string fields."""
        class TestModel(AddressMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = "789 Pine St"
                self.city = ""  # Empty string should be filtered out
                self.state_province = "TX"
                self.postal_code = ""  # Empty string should be filtered out
        
        instance = TestModel()
        
        result = instance.full_address
        
        expected = "789 Pine St, TX"
        assert result == expected
    
    def test_full_address_property_all_none(self):
        """Test full_address property with all None fields."""
        class TestModel(AddressMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = None
                self.city = None
                self.state_province = None
                self.postal_code = None
        
        instance = TestModel()
        
        result = instance.full_address
        
        assert result == ""
    
    def test_full_address_property_mixed_none_and_empty(self):
        """Test full_address property with mix of None and empty strings."""
        class TestModel(AddressMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = "100 Broadway"
                self.city = ""
                self.state_province = None
                self.postal_code = "10005"
        
        instance = TestModel()
        
        result = instance.full_address
        
        expected = "100 Broadway, 10005"
        assert result == expected


class TestContactMixinProperties:
    """Test ContactMixin property implementations."""
    
    def test_primary_contact_property_with_email(self):
        """Test primary_contact property with email - covers line 117."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = "user@example.com"
                self.phone_primary = "555-1234"
        
        instance = TestModel()
        
        # Call the property - this executes line 117
        result = instance.primary_contact
        
        # Email should take precedence
        assert result == "user@example.com"
    
    def test_primary_contact_property_with_phone_only(self):
        """Test primary_contact property with phone only."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = None
                self.phone_primary = "555-5678"
        
        instance = TestModel()
        
        result = instance.primary_contact
        
        assert result == "555-5678"
    
    def test_primary_contact_property_with_empty_email(self):
        """Test primary_contact property with empty email."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = ""
                self.phone_primary = "555-9999"
        
        instance = TestModel()
        
        result = instance.primary_contact
        
        # Empty string is falsy, so phone should be used
        assert result == "555-9999"
    
    def test_primary_contact_property_no_contact_info(self):
        """Test primary_contact property with no contact info."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = None
                self.phone_primary = None
        
        instance = TestModel()
        
        result = instance.primary_contact
        
        assert result == "No contact info"
    
    def test_primary_contact_property_empty_strings(self):
        """Test primary_contact property with empty strings."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = ""
                self.phone_primary = ""
        
        instance = TestModel()
        
        result = instance.primary_contact
        
        assert result == "No contact info"
    
    def test_primary_contact_property_whitespace_strings(self):
        """Test primary_contact property with whitespace strings."""
        class TestModel(ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = "   "
                self.phone_primary = None
        
        instance = TestModel()
        
        result = instance.primary_contact
        
        # Whitespace string is truthy, so it should be returned
        assert result == "   "


class TestMixinIntegration:
    """Test integration of multiple mixins."""
    
    def test_multiple_mixin_methods(self):
        """Test using multiple mixins together."""
        class TestModel(SoftDeleteMixin, StatusMixin, AddressMixin, ContactMixin):
            """Class for TestModel operations."""
            def __init__(self):
                """  Init   operation."""
                # SoftDeleteMixin
                self.is_deleted = False
                self.deleted_at = None
                
                # StatusMixin
                self.status = "active"
                self.status_reason = None
                self.status_changed_at = None
                
                # AddressMixin
                self.street_address = "123 Test St"
                self.city = "Test City"
                self.state_province = "TS"
                self.postal_code = "12345"
                
                # ContactMixin
                self.email_primary = "test@example.com"
                self.phone_primary = "555-0123"
        
        instance = TestModel()
        
        with patch('dotmac_isp.shared.models.datetime') as mock_datetime:
            mock_now = datetime(2023, 12, 15, 10, 30, 45)
            mock_datetime.utcnow.return_value = mock_now
            
            # Test all methods work together
            instance.change_status("maintenance", "Scheduled maintenance")
            instance.soft_delete()
            
            # Check all properties work
            address = instance.full_address
            contact = instance.primary_contact
            
            # Verify all methods executed correctly
            assert instance.status == "maintenance"
            assert instance.status_reason == "Scheduled maintenance"
            assert instance.status_changed_at == mock_now
            
            assert instance.is_deleted is True
            assert instance.deleted_at == mock_now
            
            assert address == "123 Test St, Test City, TS, 12345"
            assert contact == "test@example.com"


class TestMethodCoverageCompleteness:
    """Ensure complete method coverage for missed lines."""
    
    def test_all_missed_lines_coverage(self):
        """Test all originally missed lines are covered."""
        
        # Lines 28-29: SoftDeleteMixin.soft_delete
        class SoftDeleteModel(SoftDeleteMixin):
            """Class for SoftDeleteModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.is_deleted = False
                self.deleted_at = None
        
        soft_instance = SoftDeleteModel()
        with patch('dotmac_isp.shared.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime.now()
            soft_instance.soft_delete()  # Lines 28-29
            assert soft_instance.is_deleted is True
        
        # Lines 33-34: SoftDeleteMixin.restore
        soft_instance.restore()  # Lines 33-34
        assert soft_instance.is_deleted is False
        
        # Lines 79-81: StatusMixin.change_status
        class StatusModel(StatusMixin):
            """Class for StatusModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.status = "initial"
                self.status_reason = None
                self.status_changed_at = None
        
        status_instance = StatusModel()
        with patch('dotmac_isp.shared.models.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime.now()
            status_instance.change_status("updated", "test")  # Lines 79-81
            assert status_instance.status == "updated"
        
        # Lines 96-102: AddressMixin.full_address property
        class AddressModel(AddressMixin):
            """Class for AddressModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.street_address = "123 Main"
                self.city = "City"
                self.state_province = "State"
                self.postal_code = "12345"
        
        address_instance = AddressModel()
        full_address = address_instance.full_address  # Lines 96-102
        assert "123 Main" in full_address
        
        # Line 117: ContactMixin.primary_contact property  
        class ContactModel(ContactMixin):
            """Class for ContactModel operations."""
            def __init__(self):
                """  Init   operation."""
                self.email_primary = "test@email.com"
                self.phone_primary = "555-1234"
        
        contact_instance = ContactModel()
        primary = contact_instance.primary_contact  # Line 117
        assert primary == "test@email.com"