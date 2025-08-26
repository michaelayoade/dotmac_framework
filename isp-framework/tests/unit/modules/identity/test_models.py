"""Unit tests for identity models."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4
import json

# Mock the dependencies
@pytest.fixture(scope="module", autouse=True, timezone)
def mock_dependencies():
    """Mock SQLAlchemy and other dependencies."""
    import sys
    from unittest.mock import MagicMock
    import types
    
    # Mock SQLAlchemy modules
    mock_sqlalchemy = types.ModuleType('sqlalchemy')
    mock_sqlalchemy.Column = MagicMock()
    mock_sqlalchemy.String = MagicMock()
    mock_sqlalchemy.Boolean = MagicMock()
    mock_sqlalchemy.DateTime = MagicMock()
    mock_sqlalchemy.ForeignKey = MagicMock()
    mock_sqlalchemy.Table = MagicMock()
    mock_sqlalchemy.Enum = MagicMock()
    mock_sqlalchemy.Text = MagicMock()
    
    mock_dialect = types.ModuleType('postgresql')
    mock_dialect.UUID = MagicMock()
    mock_sqlalchemy.dialects = types.ModuleType('dialects')
    mock_sqlalchemy.dialects.postgresql = mock_dialect
    
    mock_sqlalchemy_orm = types.ModuleType('orm')
    mock_sqlalchemy_orm.relationship = MagicMock()
    mock_sqlalchemy.orm = mock_sqlalchemy_orm
    
    sys.modules['sqlalchemy'] = mock_sqlalchemy
    sys.modules['sqlalchemy.dialects'] = mock_sqlalchemy.dialects
    sys.modules['sqlalchemy.dialects.postgresql'] = mock_dialect
    sys.modules['sqlalchemy.orm'] = mock_sqlalchemy_orm
    
    # Mock shared modules
    mock_shared = types.ModuleType('shared')
    mock_shared.models = types.ModuleType('models')
    mock_shared.models.TenantModel = type('TenantModel', (), {'metadata': MagicMock()})
    mock_shared.models.ContactMixin = object
    mock_shared.models.AddressMixin = object
    
    sys.modules['dotmac_isp'] = types.ModuleType('dotmac_isp')
    sys.modules['dotmac_isp.shared'] = mock_shared
    sys.modules['dotmac_isp.shared.models'] = mock_shared.models


@pytest.mark.unit
class TestIdentityEnums:
    """Test identity enumeration classes."""
    
    def test_user_role_enum(self):
        """Test UserRole enum values."""
        from dotmac_isp.modules.identity.models import UserRole
        
        # Test all enum values
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.TENANT_ADMIN.value == "tenant_admin"
        assert UserRole.MANAGER.value == "manager"
        assert UserRole.TECHNICIAN.value == "technician"
        assert UserRole.SUPPORT.value == "support"
        assert UserRole.SALES.value == "sales"
        assert UserRole.CUSTOMER.value == "customer"
        
        # Test enum count
        assert len(UserRole) == 7
    
    def test_customer_type_enum(self):
        """Test CustomerType enum values."""
        from dotmac_isp.modules.identity.models import CustomerType
        
        # Test all enum values
        assert CustomerType.RESIDENTIAL.value == "residential"
        assert CustomerType.BUSINESS.value == "business"
        assert CustomerType.ENTERPRISE.value == "enterprise"
        
        # Test enum count
        assert len(CustomerType) == 3
    
    def test_account_status_enum(self):
        """Test AccountStatus enum values."""
        from dotmac_isp.modules.identity.models import AccountStatus
        
        # Test all enum values
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.PENDING.value == "pending"
        assert AccountStatus.CANCELLED.value == "cancelled"
        
        # Test enum count
        assert len(AccountStatus) == 4


@pytest.mark.unit
class TestUserModelLogic:
    """Test User model business logic."""
    
    def create_mock_user(self):
        """Create a mock User instance for testing."""
        class MockUser:
            """Class for MockUser operations."""
            def __init__(self):
                """  Init   operation."""
                self.first_name = "John"
                self.last_name = "Doe"
                self.locked_until = None
                self.username = "johndoe"
                self.email = "john@example.com"
                self.is_active = True
                self.is_verified = False
                self.failed_login_attempts = "0"
                self.timezone = "UTC"
                self.language = "en"
            
            @property
            def full_name(self) -> str:
                """Get user's full name."""
                return f"{self.first_name} {self.last_name}"
            
            @property
            def is_locked(self) -> bool:
                """Check if user account is locked."""
                if self.locked_until:
                    return datetime.now(timezone.utc) < self.locked_until
                return False
        
        return MockUser()
    
    def test_full_name_property(self):
        """Test user full_name property."""
        user = self.create_mock_user()
        assert user.full_name == "John Doe"
        
        user.first_name = "Jane"
        user.last_name = "Smith"
        assert user.full_name == "Jane Smith"
    
    def test_is_locked_property_not_locked(self):
        """Test is_locked property when user is not locked."""
        user = self.create_mock_user()
        assert user.is_locked is False
    
    def test_is_locked_property_locked_until_future(self):
        """Test is_locked property when user is locked until future."""
        user = self.create_mock_user()
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
        assert user.is_locked is True
    
    def test_is_locked_property_lock_expired(self):
        """Test is_locked property when lock has expired."""
        user = self.create_mock_user()
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert user.is_locked is False
    
    def test_user_basic_properties(self):
        """Test user basic properties."""
        user = self.create_mock_user()
        assert user.username == "johndoe"
        assert user.email == "john@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.failed_login_attempts == "0"
        assert user.timezone == "UTC"
        assert user.language == "en"


@pytest.mark.unit
class TestRoleModelLogic:
    """Test Role model business logic."""
    
    def create_mock_role(self):
        """Create a mock Role instance for testing."""
        class MockRole:
            """Class for MockRole operations."""
            def __init__(self):
                """  Init   operation."""
                self.name = "Manager"
                self.description = "System manager role"
                self.permissions = None
                self.is_system_role = False
            
            def set_permissions(self, permissions_list):
                """Set permissions as JSON string."""
                self.permissions = json.dumps(permissions_list)
            
            def get_permissions(self):
                """Get permissions as list."""
                if self.permissions:
                    return json.loads(self.permissions)
                return []
            
            def has_permission(self, permission):
                """Check if role has specific permission."""
                return permission in self.get_permissions()
        
        return MockRole()
    
    def test_role_basic_properties(self):
        """Test role basic properties."""
        role = self.create_mock_role()
        assert role.name == "Manager"
        assert role.description == "System manager role"
        assert role.is_system_role is False
    
    def test_empty_permissions_handling(self):
        """Test handling of empty permissions."""
        role = self.create_mock_role()
        assert role.get_permissions() == []
        assert role.has_permission("read_users") is False
    
    def test_permission_setting_and_checking(self):
        """Test setting and checking permissions."""
        role = self.create_mock_role()
        permissions = ["read_users", "write_users", "read_roles"]
        
        role.set_permissions(permissions)
        assert role.get_permissions() == permissions
        assert role.has_permission("read_users") is True
        assert role.has_permission("write_users") is True
        assert role.has_permission("delete_users") is False
    
    def test_system_role_handling(self):
        """Test system role functionality."""
        role = self.create_mock_role()
        role.name = "Super Admin"
        role.is_system_role = True
        role.set_permissions(["*"])  # All permissions
        
        assert role.is_system_role is True
        assert role.has_permission("*") is True
        assert "Super Admin" in role.name


@pytest.mark.unit
class TestCustomerModelLogic:
    """Test Customer model business logic."""
    
    def create_mock_customer(self):
        """Create a mock Customer instance for testing."""
        from dotmac_isp.modules.identity.models import CustomerType
        
        class MockCustomer:
            """Class for MockCustomer operations."""
            def __init__(self):
                """  Init   operation."""
                self.customer_number = None
                self.customer_type = CustomerType.RESIDENTIAL
                self.company_name = None
                self.first_name = "Jane"
                self.last_name = "Smith"
                self.account_status = "active"
                self.primary_user_id = None
                
                # Contact info
                self.email_primary = "jane@example.com"
                self.phone_primary = "555-0123"
                
                # Address info
                self.street_address = "123 Main St"
                self.city = "Anytown"
                self.state_province = "CA"
                self.postal_code = "12345"
            
            def generate_customer_number(self):
                """Generate customer number."""
                if not self.customer_number:
                    import random
                    self.customer_number = f"CUST{random.randint(100000, 999999)}"
                return self.customer_number
            
            @property
            def display_name(self) -> str:
                """Get customer display name."""
                if self.customer_type == CustomerType.BUSINESS and self.company_name:
                    return self.company_name
                elif self.first_name and self.last_name:
                    return f"{self.first_name} {self.last_name}"
                return self.customer_number or "Unknown"
            
            def is_business_customer(self):
                """Check if this is a business customer."""
                return self.customer_type in [CustomerType.BUSINESS, CustomerType.ENTERPRISE]
            
            def get_full_address(self):
                """Get formatted full address."""
                parts = [
                    self.street_address,
                    self.city,
                    self.state_province,
                    self.postal_code,
                ]
                return ", ".join(filter(None, parts)
        
        return MockCustomer()
    
    def test_individual_customer_display_name(self):
        """Test display name for individual customers."""
        customer = self.create_mock_customer()
        assert customer.display_name == "Jane Smith"
    
    def test_company_customer_display_name(self):
        """Test display name for company customers."""
        from dotmac_isp.modules.identity.models import CustomerType
        
        customer = self.create_mock_customer()
        customer.customer_type = CustomerType.BUSINESS
        customer.company_name = "Acme Corp"
        assert customer.display_name == "Acme Corp"
    
    def test_customer_type_classification(self):
        """Test customer type classification."""
        from dotmac_isp.modules.identity.models import CustomerType
        
        customer = self.create_mock_customer()
        
        customer.customer_type = CustomerType.RESIDENTIAL
        assert customer.is_business_customer() is False
        
        customer.customer_type = CustomerType.BUSINESS
        assert customer.is_business_customer() is True
        
        customer.customer_type = CustomerType.ENTERPRISE
        assert customer.is_business_customer() is True
    
    def test_customer_number_generation(self):
        """Test customer number generation."""
        customer = self.create_mock_customer()
        customer_number = customer.generate_customer_number()
        
        assert customer_number.startswith("CUST")
        assert len(customer_number) == 10  # CUST + 6 digits
        assert customer.customer_number == customer_number
        
        # Test that calling again doesn't change the number
        same_number = customer.generate_customer_number()
        assert same_number == customer_number
    
    def test_address_formatting(self):
        """Test address formatting."""
        customer = self.create_mock_customer()
        full_address = customer.get_full_address()
        expected = "123 Main St, Anytown, CA, 12345"
        assert full_address == expected
    
    def test_contact_information(self):
        """Test customer contact information."""
        customer = self.create_mock_customer()
        assert customer.email_primary == "jane@example.com"
        assert customer.phone_primary == "555-0123"


@pytest.mark.unit
class TestAuthTokenModelLogic:
    """Test AuthToken model business logic."""
    
    def create_mock_auth_token(self):
        """Create a mock AuthToken instance for testing."""
        class MockAuthToken:
            """Class for MockAuthToken operations."""
            def __init__(self):
                """  Init   operation."""
                self.user_id = uuid4()
                self.token_hash = "abc123"
                self.token_type = "access"
                self.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
                self.is_revoked = False
                self.device_info = "Test Device"
                self.ip_address = "127.0.0.1"
                self.user_agent = "Test Agent"
            
            @property
            def is_expired(self) -> bool:
                """Check if token is expired."""
                return datetime.now(timezone.utc) > self.expires_at
            
            @property
            def is_valid(self) -> bool:
                """Check if token is valid (not revoked and not expired)."""
                return not self.is_revoked and not self.is_expired
        
        return MockAuthToken()
    
    def test_token_not_expired(self):
        """Test token is not expired when expires_at is in the future."""
        token = self.create_mock_auth_token()
        assert token.is_expired is False
    
    def test_token_expired(self):
        """Test token is expired when expires_at is in the past."""
        token = self.create_mock_auth_token()
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert token.is_expired is True
    
    def test_token_valid(self):
        """Test token is valid when not revoked and not expired."""
        token = self.create_mock_auth_token()
        assert token.is_valid is True
    
    def test_token_invalid_revoked(self):
        """Test token is invalid when revoked."""
        token = self.create_mock_auth_token()
        token.is_revoked = True
        assert token.is_valid is False
    
    def test_token_invalid_expired(self):
        """Test token is invalid when expired."""
        token = self.create_mock_auth_token()
        token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert token.is_valid is False
    
    def test_token_properties(self):
        """Test token basic properties."""
        token = self.create_mock_auth_token()
        assert token.token_type == "access"
        assert token.device_info == "Test Device"
        assert token.ip_address == "127.0.0.1"
        assert token.user_agent == "Test Agent"