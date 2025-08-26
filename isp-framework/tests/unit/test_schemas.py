"""Test Pydantic schemas."""

import pytest
from uuid import uuid4
from datetime import datetime
from pydantic import ValidationError

from dotmac_isp.shared.schemas import (
    BaseSchema,
    BaseModelSchema,
    TenantModelSchema,
    PaginationParams,
    PaginatedResponse,
, timezone)
from dotmac_isp.modules.identity.schemas import (
    UserCreate,
    UserResponse,
    CustomerCreate,
    LoginRequest,
    PasswordChangeRequest,
)


@pytest.mark.unit
class TestBaseSchemas:
    """Test base schema classes."""
    
    def test_base_schema_config(self):
        """Test base schema configuration."""
        schema = BaseSchema()
        config = schema.model_config
        assert config["from_attributes"] is True
        assert config["use_enum_values"] is True
        assert config["validate_assignment"] is True
        assert config["str_strip_whitespace"] is True
    
    def test_base_model_schema(self):
        """Test base model schema structure."""
        data = {
            "id": uuid4(),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_deleted": False,
        }
        schema = BaseModelSchema(**data)
        assert schema.id == data["id"]
        assert schema.created_at == data["created_at"]
        assert schema.updated_at == data["updated_at"]
        assert schema.is_deleted is False
        assert schema.deleted_at is None
    
    def test_tenant_model_schema(self):
        """Test tenant model schema structure."""
        data = {
            "id": uuid4(),
            "tenant_id": uuid4(),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "is_deleted": False,
        }
        schema = TenantModelSchema(**data)
        assert schema.tenant_id == data["tenant_id"]


@pytest.mark.unit
class TestPaginationSchemas:
    """Test pagination schemas."""
    
    def test_pagination_params_defaults(self):
        """Test pagination parameters default values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0
    
    def test_pagination_params_custom(self):
        """Test pagination parameters with custom values."""
        params = PaginationParams(page=3, size=10)
        assert params.page == 3
        assert params.size == 10
        assert params.offset == 20  # (3-1) * 10
    
    def test_pagination_params_validation(self):
        """Test pagination parameters validation."""
        # Test minimum values
        with pytest.raises(ValidationError):
            PaginationParams(page=0)
        
        with pytest.raises(ValidationError):
            PaginationParams(size=0)
        
        # Test maximum size
        with pytest.raises(ValidationError):
            PaginationParams(size=101)
    
    def test_paginated_response_creation(self):
        """Test paginated response creation."""
        items = ["item1", "item2", "item3"]
        response = PaginatedResponse.create(
            items=items,
            total=23,
            page=2,
            size=10
        )
        
        assert response.items == items
        assert response.total == 23
        assert response.page == 2
        assert response.size == 10
        assert response.pages == 3  # ceil(23/10)


@pytest.mark.unit
class TestIdentitySchemas:
    """Test identity module schemas."""
    
    def test_user_create_valid(self):
        """Test valid user creation schema."""
        data = {
            "username": "testuser",
            "email": "test@example.com", 
            "first_name": "Test",
            "last_name": "User",
            "password": "securepassword123",
        }
        schema = UserCreate(**data)
        assert schema.username == "testuser"
        assert schema.email == "test@example.com"
        assert schema.first_name == "Test"
        assert schema.last_name == "User"
        assert schema.password == "securepassword123"
        assert schema.timezone == "UTC"
        assert schema.language == "en"
    
    def test_user_create_validation(self):
        """Test user creation schema validation."""
        # Test short username
        with pytest.raises(ValidationError):
            UserCreate(
                username="ab",  # Too short
                email="test@example.com",
                first_name="Test",
                last_name="User", 
                password="securepassword123"
            )
        
        # Test invalid email
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="invalid-email",  # Invalid format
                first_name="Test",
                last_name="User",
                password="securepassword123"
            )
        
        # Test short password
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="short"  # Too short
            )
    
    def test_login_request_schema(self):
        """Test login request schema."""
        data = {
            "username": "testuser",
            "password": "password123",
            "remember_me": True
        }
        schema = LoginRequest(**data)
        assert schema.username == "testuser"
        assert schema.password == "password123" 
        assert schema.remember_me is True
        
        # Test with defaults
        schema = LoginRequest(username="test", password="pass")
        assert schema.remember_me is False
    
    def test_password_change_request(self):
        """Test password change request schema."""
        data = {
            "current_password": "oldpassword",
            "new_password": "newpassword123"
        }
        schema = PasswordChangeRequest(**data)
        assert schema.current_password == "oldpassword"
        assert schema.new_password == "newpassword123"
        
        # Test short new password
        with pytest.raises(ValidationError):
            PasswordChangeRequest(
                current_password="old",
                new_password="short"  # Too short
            )
    
    def test_customer_create_schema(self):
        """Test customer creation schema."""
        data = {
            "customer_number": "CUST001",
            "first_name": "John",
            "last_name": "Doe",
            "email_primary": "john@example.com",
            "customer_type": "residential"
        }
        schema = CustomerCreate(**data)
        assert schema.customer_number == "CUST001"
        assert schema.first_name == "John"
        assert schema.last_name == "Doe"
        assert schema.email_primary == "john@example.com"
        assert schema.marketing_opt_in is False  # Default value