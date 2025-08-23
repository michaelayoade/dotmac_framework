"""Basic tests to verify core functionality without database dependencies."""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from dotmac_isp.shared.schemas import (
    BaseSchema,
    BaseModelSchema,
    PaginationParams,
)
from dotmac_isp.modules.identity.schemas import (
    LoginRequest,
    UserCreate,
)
from uuid import uuid4
from datetime import datetime


@pytest.mark.unit
class TestSchemasFunctionality:
    """Test that schemas work correctly after fixes."""
    
    def test_base_schema_config(self):
        """Test base schema configuration."""
        schema = BaseSchema()
        config = schema.model_config
        assert config["from_attributes"] is True
        assert config["use_enum_values"] is True
        assert config["str_strip_whitespace"] is True
    
    def test_base_model_schema_fixed(self):
        """Test that BaseModelSchema works after MRO fix."""
        # This test verifies the critical schema inheritance fix
        data = {
            "id": uuid4(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_deleted": False,
        }
        schema = BaseModelSchema(**data)
        assert schema.id == data["id"]
        assert schema.is_deleted is False
        assert schema.deleted_at is None
    
    def test_pagination_params(self):
        """Test pagination parameters."""
        params = PaginationParams()
        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0
        
        params = PaginationParams(page=3, size=10)
        assert params.offset == 20  # (3-1) * 10
    
    def test_login_request_schema(self):
        """Test that LoginRequest works with BaseModel inheritance."""
        data = {
            "username": "testuser",
            "password": "password123",
            "remember_me": True
        }
        schema = LoginRequest(**data)
        assert schema.username == "testuser"
        assert schema.remember_me is True
    
    def test_user_create_schema(self):
        """Test UserCreate schema validation."""
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
        assert schema.timezone == "UTC"  # Default value
    
    def test_import_main_application(self):
        """Test that main application can be imported without errors."""
        # This test verifies the critical import fix
        from dotmac_isp.main import app
        assert app is not None
        assert hasattr(app, 'title')
        assert "DotMac ISP Framework" in app.title


@pytest.mark.unit 
class TestModelsBasicFunctionality:
    """Test basic model functionality without database."""
    
    def test_user_model_import(self):
        """Test that User model can be imported."""
        from dotmac_isp.modules.identity.models import User, UserRole, CustomerType
        
        # Test enum values
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert CustomerType.RESIDENTIAL.value == "residential"
    
    def test_billing_model_import(self):
        """Test that billing models can be imported."""
        from dotmac_isp.modules.billing.models import Invoice, InvoiceStatus
        
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.PAID.value == "paid"
    
    def test_base_model_mixins(self):
        """Test base model mixins functionality."""
        from dotmac_isp.shared.models import SoftDeleteMixin, StatusMixin
        
        # Test soft delete
        mixin = SoftDeleteMixin()
        mixin.soft_delete()
        assert mixin.is_deleted is True
        
        # Test status change
        status_mixin = StatusMixin()
        status_mixin.change_status("inactive", "Testing")
        assert status_mixin.status == "inactive"
        assert status_mixin.status_reason == "Testing"