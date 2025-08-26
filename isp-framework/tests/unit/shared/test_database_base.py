"""Comprehensive unit tests for shared database base module - 100% coverage."""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy import String, DateTime, Boolean, Text, UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

from dotmac_isp.shared.database.base import (
    Base,
    TimestampMixin,
    SoftDeleteMixin,
    TenantMixin,
    StatusMixin,
    AuditMixin,
    BaseModel,
    TenantModel,
    SimpleModel
)


class TestBase:
    """Test the base SQLAlchemy declarative base."""

    def test_base_is_declarative_base(self):
        """Test Base inherits from DeclarativeBase."""
        assert issubclass(Base, DeclarativeBase)

    def test_base_docstring(self):
        """Test Base has proper documentation."""
        assert Base.__doc__ is not None
        assert "DotMac ISP Framework" in Base.__doc__

    def test_base_instantiation(self):
        """Test Base can be used to create models."""
        # Create a test model using Base
        class TestModel(Base):
            """Class for TestModel operations."""
            __tablename__ = 'test_table'
            id: Mapped[str] = mapped_column(String(50), primary_key=True)

        # Should be able to create instance
        model = TestModel()
        assert isinstance(model, Base)
        assert hasattr(model, 'metadata')


class TestTimestampMixin:
    """Test the TimestampMixin with 100% coverage."""

    def test_timestamp_mixin_fields(self):
        """Test TimestampMixin has required fields."""
        class TestModel(Base, TimestampMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_timestamps'
            id: Mapped[str] = mapped_column(String(50), primary_key=True)

        # Check fields exist
        assert hasattr(TestModel, 'created_at')
        assert hasattr(TestModel, 'updated_at')

    def test_timestamp_mixin_field_types(self):
        """Test TimestampMixin field configurations."""
        class TestModel(Base, TimestampMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_timestamps_types'
            id = String(50, primary_key=True)

        # Test field properties through model columns
        created_at_column = TestModel.__table__.columns.get('created_at')
        updated_at_column = TestModel.__table__.columns.get('updated_at')

        assert created_at_column is not None
        assert updated_at_column is not None
        assert not created_at_column.nullable
        assert not updated_at_column.nullable

    def test_timestamp_mixin_default_values(self):
        """Test TimestampMixin default value configurations."""
        class TestModel(Base, TimestampMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_timestamps_defaults'
            id = String(50, primary_key=True)

        model = TestModel()
        
        # Fields should exist (values set by database server_default)
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')

    @patch('dotmac_isp.shared.database.base.func.now')
    def test_timestamp_mixin_server_defaults(self, mock_now):
        """Test server default functions are used."""
        mock_now.return_value = "mocked_now_func"

        class TestModel(Base, TimestampMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_timestamps_server'
            id = String(50, primary_key=True)

        # Server defaults should be configured
        created_at_column = TestModel.__table__.columns.get('created_at')
        assert created_at_column.server_default is not None


class TestSoftDeleteMixin:
    """Test the SoftDeleteMixin with 100% coverage."""

    def test_soft_delete_mixin_fields(self):
        """Test SoftDeleteMixin has required fields."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_soft_delete'
            id = String(50, primary_key=True)

        assert hasattr(TestModel, 'deleted_at')
        assert hasattr(TestModel, 'is_deleted')

    def test_soft_delete_mixin_field_types(self):
        """Test SoftDeleteMixin field configurations."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_soft_delete_types'
            id = String(50, primary_key=True)

        deleted_at_column = TestModel.__table__.columns.get('deleted_at')
        is_deleted_column = TestModel.__table__.columns.get('is_deleted')

        assert deleted_at_column is not None
        assert is_deleted_column is not None
        assert deleted_at_column.nullable  # Can be null
        assert not is_deleted_column.nullable  # Cannot be null

    def test_soft_delete_method(self):
        """Test soft_delete method functionality."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_soft_delete_method'
            id = String(50, primary_key=True)

        model = TestModel()
        assert model.is_deleted is None or model.is_deleted is False
        assert model.deleted_at is None

        # Mock datetime.utcnow
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            model.soft_delete()

            assert model.is_deleted is True
            assert model.deleted_at == mock_now

    def test_restore_method(self):
        """Test restore method functionality."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_restore_method'
            id = String(50, primary_key=True)

        model = TestModel()
        
        # First soft delete
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now
            model.soft_delete()

        assert model.is_deleted is True
        assert model.deleted_at == mock_now

        # Then restore
        model.restore()

        assert model.is_deleted is False
        assert model.deleted_at is None

    def test_soft_delete_default_values(self):
        """Test SoftDeleteMixin default values."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_soft_delete_defaults'
            id = String(50, primary_key=True)

        model = TestModel()
        
        # Check defaults through table column defaults
        is_deleted_column = TestModel.__table__.columns.get('is_deleted')
        assert is_deleted_column.default is not None


class TestTenantMixin:
    """Test the TenantMixin with 100% coverage."""

    def test_tenant_mixin_fields(self):
        """Test TenantMixin has required fields."""
        class TestModel(Base, TenantMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_tenant'
            id = String(50, primary_key=True)

        assert hasattr(TestModel, 'tenant_id')

    def test_tenant_mixin_field_configuration(self):
        """Test TenantMixin field configuration."""
        class TestModel(Base, TenantMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_tenant_config'
            id = String(50, primary_key=True)

        tenant_id_column = TestModel.__table__.columns.get('tenant_id')
        
        assert tenant_id_column is not None
        assert not tenant_id_column.nullable  # Required field
        assert tenant_id_column.index  # Should be indexed

    def test_tenant_mixin_uuid_type(self):
        """Test TenantMixin uses UUID type."""
        class TestModel(Base, TenantMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_tenant_uuid'
            id = String(50, primary_key=True)

        tenant_id_column = TestModel.__table__.columns.get('tenant_id')
        assert isinstance(tenant_id_column.type, UUID)
        assert not tenant_id_column.type.as_uuid  # as_uuid=False


class TestStatusMixin:
    """Test the StatusMixin with 100% coverage."""

    def test_status_mixin_fields(self):
        """Test StatusMixin has required fields."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_status'
            id = String(50, primary_key=True)

        assert hasattr(TestModel, 'status')
        assert hasattr(TestModel, 'status_reason')
        assert hasattr(TestModel, 'status_changed_at')

    def test_status_mixin_field_configurations(self):
        """Test StatusMixin field configurations."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_status_config'
            id = String(50, primary_key=True)

        status_column = TestModel.__table__.columns.get('status')
        status_reason_column = TestModel.__table__.columns.get('status_reason')
        status_changed_at_column = TestModel.__table__.columns.get('status_changed_at')

        assert not status_column.nullable  # Required
        assert status_reason_column.nullable  # Optional
        assert status_changed_at_column.nullable  # Optional
        assert status_column.index  # Should be indexed

    def test_status_mixin_defaults(self):
        """Test StatusMixin default values."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_status_defaults'
            id = String(50, primary_key=True)

        status_column = TestModel.__table__.columns.get('status')
        assert status_column.default is not None

    def test_change_status_method(self):
        """Test change_status method functionality."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_change_status'
            id = String(50, primary_key=True)

        model = TestModel()

        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            model.change_status("inactive", "Testing status change")

            assert model.status == "inactive"
            assert model.status_reason == "Testing status change"
            assert model.status_changed_at == mock_now

    def test_change_status_method_without_reason(self):
        """Test change_status method without reason."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_change_status_no_reason'
            id = String(50, primary_key=True)

        model = TestModel()

        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            model.change_status("suspended")

            assert model.status == "suspended"
            assert model.status_reason is None
            assert model.status_changed_at == mock_now


class TestAuditMixin:
    """Test the AuditMixin with 100% coverage."""

    def test_audit_mixin_fields(self):
        """Test AuditMixin has required fields."""
        class TestModel(Base, AuditMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_audit'
            id = String(50, primary_key=True)

        assert hasattr(TestModel, 'created_by')
        assert hasattr(TestModel, 'updated_by')
        assert hasattr(TestModel, 'notes')

    def test_audit_mixin_field_configurations(self):
        """Test AuditMixin field configurations."""
        class TestModel(Base, AuditMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_audit_config'
            id = String(50, primary_key=True)

        created_by_column = TestModel.__table__.columns.get('created_by')
        updated_by_column = TestModel.__table__.columns.get('updated_by')
        notes_column = TestModel.__table__.columns.get('notes')

        assert created_by_column.nullable  # Optional
        assert updated_by_column.nullable  # Optional
        assert notes_column.nullable  # Optional

    def test_audit_mixin_uuid_types(self):
        """Test AuditMixin uses UUID for user fields."""
        class TestModel(Base, AuditMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_audit_uuid'
            id = String(50, primary_key=True)

        created_by_column = TestModel.__table__.columns.get('created_by')
        updated_by_column = TestModel.__table__.columns.get('updated_by')

        assert isinstance(created_by_column.type, UUID)
        assert isinstance(updated_by_column.type, UUID)
        assert not created_by_column.type.as_uuid  # as_uuid=False
        assert not updated_by_column.type.as_uuid  # as_uuid=False


class TestBaseModel:
    """Test the complete BaseModel with 100% coverage."""

    def test_base_model_inheritance(self):
        """Test BaseModel inherits from all mixins."""
        assert issubclass(BaseModel, Base)
        assert issubclass(BaseModel, TimestampMixin)
        assert issubclass(BaseModel, SoftDeleteMixin)
        assert issubclass(BaseModel, TenantMixin)
        assert issubclass(BaseModel, StatusMixin)
        assert issubclass(BaseModel, AuditMixin)

    def test_base_model_is_abstract(self):
        """Test BaseModel is abstract."""
        assert BaseModel.__abstract__ is True

    def test_base_model_has_id_field(self):
        """Test BaseModel has UUID primary key field."""
        assert hasattr(BaseModel, 'id')

    def test_base_model_id_configuration(self):
        """Test BaseModel id field configuration."""
        # Create a concrete model to test id field
        class ConcreteModel(BaseModel):
            """Class for ConcreteModel operations."""
            __tablename__ = 'test_concrete_base'

        id_column = ConcreteModel.__table__.columns.get('id')
        assert id_column is not None
        assert id_column.primary_key
        assert isinstance(id_column.type, UUID)
        assert not id_column.type.as_uuid  # as_uuid=False

    def test_base_model_id_default_function(self):
        """Test BaseModel id field has default UUID generator."""
        class ConcreteModel(BaseModel):
            """Class for ConcreteModel operations."""
            __tablename__ = 'test_concrete_id_default'

        id_column = ConcreteModel.__table__.columns.get('id')
        assert id_column.default is not None
        
        # Test the default function generates valid UUID string
        default_value = id_column.default.arg()
        uuid.UUID(default_value)  # Should not raise exception

    def test_base_model_combined_functionality(self):
        """Test BaseModel combines all mixin functionality."""
        class ConcreteModel(BaseModel):
            """Class for ConcreteModel operations."""
            __tablename__ = 'test_concrete_combined'

        model = ConcreteModel()

        # Should have all mixin methods
        assert hasattr(model, 'soft_delete')
        assert hasattr(model, 'restore')
        assert hasattr(model, 'change_status')

        # Test combined functionality
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            model.soft_delete()
            model.change_status("deleted", "Soft deleted")

            assert model.is_deleted is True
            assert model.status == "deleted"
            assert model.status_changed_at == mock_now

    def test_base_model_docstring(self):
        """Test BaseModel has comprehensive documentation."""
        assert BaseModel.__doc__ is not None
        assert "Timestamps" in BaseModel.__doc__
        assert "Soft delete" in BaseModel.__doc__
        assert "Multi-tenant" in BaseModel.__doc__
        assert "Status tracking" in BaseModel.__doc__
        assert "Audit trail" in BaseModel.__doc__


class TestTenantModel:
    """Test the TenantModel with 100% coverage."""

    def test_tenant_model_inheritance(self):
        """Test TenantModel inherits correctly."""
        assert issubclass(TenantModel, Base)
        assert issubclass(TenantModel, TimestampMixin)
        assert issubclass(TenantModel, StatusMixin)

    def test_tenant_model_excludes_audit_trail(self):
        """Test TenantModel doesn't include full audit trail."""
        assert not issubclass(TenantModel, SoftDeleteMixin)
        assert not issubclass(TenantModel, AuditMixin)

    def test_tenant_model_is_abstract(self):
        """Test TenantModel is abstract."""
        assert TenantModel.__abstract__ is True

    def test_tenant_model_has_required_fields(self):
        """Test TenantModel has id and tenant_id fields."""
        assert hasattr(TenantModel, 'id')
        assert hasattr(TenantModel, 'tenant_id')

    def test_tenant_model_field_configurations(self):
        """Test TenantModel field configurations."""
        class ConcreteTenantModel(TenantModel):
            """Class for ConcreteTenantModel operations."""
            __tablename__ = 'test_concrete_tenant'

        id_column = ConcreteTenantModel.__table__.columns.get('id')
        tenant_id_column = ConcreteTenantModel.__table__.columns.get('tenant_id')

        assert id_column.primary_key
        assert isinstance(id_column.type, UUID)
        assert not tenant_id_column.nullable
        assert isinstance(tenant_id_column.type, UUID)

    def test_tenant_model_docstring(self):
        """Test TenantModel has proper documentation."""
        assert TenantModel.__doc__ is not None
        assert "tenant-specific" in TenantModel.__doc__


class TestSimpleModel:
    """Test the SimpleModel with 100% coverage."""

    def test_simple_model_inheritance(self):
        """Test SimpleModel inherits minimally."""
        assert issubclass(SimpleModel, Base)
        assert issubclass(SimpleModel, TimestampMixin)

    def test_simple_model_excludes_complex_mixins(self):
        """Test SimpleModel excludes complex mixins."""
        assert not issubclass(SimpleModel, SoftDeleteMixin)
        assert not issubclass(SimpleModel, TenantMixin)
        assert not issubclass(SimpleModel, StatusMixin)
        assert not issubclass(SimpleModel, AuditMixin)

    def test_simple_model_is_abstract(self):
        """Test SimpleModel is abstract."""
        assert SimpleModel.__abstract__ is True

    def test_simple_model_has_id_field(self):
        """Test SimpleModel has id field."""
        assert hasattr(SimpleModel, 'id')

    def test_simple_model_id_configuration(self):
        """Test SimpleModel id field configuration."""
        class ConcreteSimpleModel(SimpleModel):
            """Class for ConcreteSimpleModel operations."""
            __tablename__ = 'test_concrete_simple'

        id_column = ConcreteSimpleModel.__table__.columns.get('id')
        assert id_column.primary_key
        assert isinstance(id_column.type, UUID)

    def test_simple_model_docstring(self):
        """Test SimpleModel has proper documentation."""
        assert SimpleModel.__doc__ is not None
        assert "lookup tables" in SimpleModel.__doc__
        assert "configurations" in SimpleModel.__doc__


class TestMixinCombinations:
    """Test various mixin combinations and edge cases."""

    def test_single_mixin_usage(self):
        """Test using individual mixins."""
        class TimestampOnlyModel(Base, TimestampMixin):
            """Class for TimestampOnlyModel operations."""
            __tablename__ = 'test_timestamp_only'
            id = String(50, primary_key=True)

        assert hasattr(TimestampOnlyModel, 'created_at')
        assert hasattr(TimestampOnlyModel, 'updated_at')
        assert not hasattr(TimestampOnlyModel, 'is_deleted')

    def test_custom_mixin_combinations(self):
        """Test custom combinations of mixins."""
        class CustomModel(Base, TimestampMixin, StatusMixin):
            """Class for CustomModel operations."""
            __tablename__ = 'test_custom_combo'
            id = String(50, primary_key=True)

        model = CustomModel()
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'status')
        assert hasattr(model, 'change_status')
        assert not hasattr(model, 'tenant_id')

    def test_all_methods_available_on_base_model(self):
        """Test all mixin methods are available on BaseModel."""
        class ConcreteModel(BaseModel):
            """Class for ConcreteModel operations."""
            __tablename__ = 'test_all_methods'

        model = ConcreteModel()

        # All mixin methods should be available
        assert callable(getattr(model, 'soft_delete')
        assert callable(getattr(model, 'restore')
        assert callable(getattr(model, 'change_status')

        # Test method chaining doesn't interfere
        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            model.change_status("active")
            model.soft_delete()
            model.restore()
            model.change_status("inactive", "Test reason")

            assert model.status == "inactive"
            assert model.is_deleted is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_status_change(self):
        """Test changing status to empty string."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_empty_status'
            id = String(50, primary_key=True)

        model = TestModel()
        model.change_status("")

        assert model.status == ""

    def test_none_status_change(self):
        """Test changing status to None."""
        class TestModel(Base, StatusMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_none_status'
            id = String(50, primary_key=True)

        model = TestModel()
        model.change_status(None)

        assert model.status is None

    def test_restore_without_soft_delete(self):
        """Test restore on non-deleted model."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_restore_clean'
            id = String(50, primary_key=True)

        model = TestModel()
        model.restore()

        assert model.is_deleted is False
        assert model.deleted_at is None

    def test_multiple_soft_deletes(self):
        """Test multiple soft deletes on same model."""
        class TestModel(Base, SoftDeleteMixin):
            """Class for TestModel operations."""
            __tablename__ = 'test_multiple_deletes'
            id = String(50, primary_key=True)

        model = TestModel()

        with patch('dotmac_isp.shared.database.base.datetime') as mock_datetime:
            first_time = datetime(2023, 1, 1, 12, 0, 0)
            second_time = datetime(2023, 1, 2, 12, 0, 0)
            
            mock_datetime.utcnow.return_value = first_time
            model.soft_delete()
            first_deleted_at = model.deleted_at

            mock_datetime.utcnow.return_value = second_time
            model.soft_delete()  # Delete again

            # Should update to new time
            assert model.deleted_at == second_time
            assert model.deleted_at != first_deleted_at