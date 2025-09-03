"""
Unit tests for database mixins.
"""

from datetime import datetime, timedelta
import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from dotmac.database import BaseModel
from dotmac.database.mixins import (
    SoftDeleteMixin,
    AuditMixin,
    TenantAwareMixin,
    SoftDeleteAuditMixin,
    TenantAwareSoftDeleteMixin,
    CompleteMixin,
)


class SoftDeleteModel(BaseModel, SoftDeleteMixin):
    __tablename__ = "soft_delete_test"
    name: Mapped[str] = mapped_column(sa.String(100))


class AuditModel(BaseModel, AuditMixin):
    __tablename__ = "audit_test"
    name: Mapped[str] = mapped_column(sa.String(100))


class TenantAwareModel(BaseModel, TenantAwareMixin):
    __tablename__ = "tenant_aware_test"
    name: Mapped[str] = mapped_column(sa.String(100))


class CompleteModel(BaseModel, CompleteMixin):
    __tablename__ = "complete_test"
    name: Mapped[str] = mapped_column(sa.String(100))


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin functionality."""
    
    def test_soft_delete_fields_exist(self):
        """Test that soft delete fields are added."""
        model = SoftDeleteModel(name="Test")
        
        assert hasattr(model, 'is_active')
        assert hasattr(model, 'deleted_at')
        assert model.is_active is True
        assert model.deleted_at is None
    
    def test_soft_delete_method(self):
        """Test soft delete method functionality."""
        model = SoftDeleteModel(name="Test")
        
        # Should be active initially
        assert model.is_active is True
        assert model.deleted_at is None
        
        # Soft delete
        model.soft_delete()
        
        assert model.is_active is False
        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)
    
    def test_soft_delete_with_timestamp(self):
        """Test soft delete with custom timestamp."""
        model = SoftDeleteModel(name="Test")
        custom_time = datetime.utcnow() - timedelta(hours=1)
        
        model.soft_delete(custom_time)
        
        assert model.is_active is False
        assert model.deleted_at == custom_time
    
    def test_restore_method(self):
        """Test restore functionality."""
        model = SoftDeleteModel(name="Test")
        
        # Soft delete first
        model.soft_delete()
        assert model.is_active is False
        
        # Restore
        model.restore()
        assert model.is_active is True
        assert model.deleted_at is None
    
    def test_active_scope_query(self):
        """Test active scope query method."""
        # This would need to be tested with actual database session
        # For now, just test that the method exists
        assert hasattr(SoftDeleteModel, 'active')
        assert callable(SoftDeleteModel.active)
    
    @pytest.mark.asyncio
    async def test_soft_delete_database_behavior(self, db_session):
        """Test soft delete with database operations."""
        # Create model
        model = SoftDeleteModel(name="Test Record")
        db_session.add(model)
        await db_session.commit()
        
        # Verify it's active
        assert model.is_active is True
        assert model.deleted_at is None
        
        # Soft delete
        model.soft_delete()
        await db_session.commit()
        
        # Verify soft delete
        await db_session.refresh(model)
        assert model.is_active is False
        assert model.deleted_at is not None
        
        # Restore
        model.restore()
        await db_session.commit()
        
        await db_session.refresh(model)
        assert model.is_active is True
        assert model.deleted_at is None


class TestAuditMixin:
    """Test AuditMixin functionality."""
    
    def test_audit_fields_exist(self):
        """Test that audit fields are added."""
        model = AuditModel(name="Test")
        
        assert hasattr(model, 'created_by_id')
        assert hasattr(model, 'updated_by_id')
        assert model.created_by_id is None
        assert model.updated_by_id is None
    
    def test_set_audit_fields(self):
        """Test setting audit fields."""
        model = AuditModel(name="Test")
        user_id = "user_123"
        
        model.created_by_id = user_id
        model.updated_by_id = user_id
        
        assert model.created_by_id == user_id
        assert model.updated_by_id == user_id
    
    @pytest.mark.asyncio
    async def test_audit_database_behavior(self, db_session):
        """Test audit fields with database operations."""
        user_id = "user_123"
        model = AuditModel(name="Test Record")
        model.created_by_id = user_id
        model.updated_by_id = user_id
        
        db_session.add(model)
        await db_session.commit()
        
        # Verify audit fields are persisted
        await db_session.refresh(model)
        assert model.created_by_id == user_id
        assert model.updated_by_id == user_id


class TestTenantAwareMixin:
    """Test TenantAwareMixin functionality."""
    
    def test_tenant_fields_exist(self):
        """Test that tenant field is added."""
        model = TenantAwareModel(name="Test")
        
        assert hasattr(model, 'tenant_id')
        assert model.tenant_id is None
    
    def test_set_tenant_id(self):
        """Test setting tenant ID."""
        model = TenantAwareModel(name="Test")
        tenant_id = "tenant_123"
        
        model.tenant_id = tenant_id
        assert model.tenant_id == tenant_id
    
    @pytest.mark.asyncio
    async def test_tenant_database_behavior(self, db_session, sample_tenant_id):
        """Test tenant awareness with database operations."""
        model = TenantAwareModel(name="Test Record")
        model.tenant_id = sample_tenant_id
        
        db_session.add(model)
        await db_session.commit()
        
        # Verify tenant ID is persisted
        await db_session.refresh(model)
        assert model.tenant_id == sample_tenant_id


class TestCombinationMixins:
    """Test combination mixins (SoftDeleteAuditMixin, etc.)."""
    
    def test_soft_delete_audit_mixin(self):
        """Test SoftDeleteAuditMixin combines both mixins."""
        class TestModel(BaseModel, SoftDeleteAuditMixin):
            __tablename__ = "test_soft_delete_audit"
            name: Mapped[str] = mapped_column(sa.String(100))
        
        model = TestModel(name="Test")
        
        # Should have soft delete fields
        assert hasattr(model, 'is_active')
        assert hasattr(model, 'deleted_at')
        
        # Should have audit fields
        assert hasattr(model, 'created_by_id')
        assert hasattr(model, 'updated_by_id')
        
        # Should have both behaviors
        model.soft_delete()
        assert model.is_active is False
        
        model.created_by_id = "user_123"
        assert model.created_by_id == "user_123"
    
    def test_tenant_aware_soft_delete_mixin(self):
        """Test TenantAwareSoftDeleteMixin combines mixins."""
        class TestModel(BaseModel, TenantAwareSoftDeleteMixin):
            __tablename__ = "test_tenant_soft_delete"
            name: Mapped[str] = mapped_column(sa.String(100))
        
        model = TestModel(name="Test")
        
        # Should have tenant field
        assert hasattr(model, 'tenant_id')
        
        # Should have soft delete fields
        assert hasattr(model, 'is_active')
        assert hasattr(model, 'deleted_at')
        
        # Should have both behaviors
        model.tenant_id = "tenant_123"
        model.soft_delete()
        
        assert model.tenant_id == "tenant_123"
        assert model.is_active is False


class TestCompleteMixin:
    """Test CompleteMixin with all features."""
    
    def test_complete_mixin_has_all_fields(self):
        """Test CompleteMixin includes all mixin fields."""
        model = CompleteModel(name="Test")
        
        # Soft delete fields
        assert hasattr(model, 'is_active')
        assert hasattr(model, 'deleted_at')
        
        # Audit fields
        assert hasattr(model, 'created_by_id')
        assert hasattr(model, 'updated_by_id')
        
        # Tenant field
        assert hasattr(model, 'tenant_id')
    
    def test_complete_mixin_all_behaviors(self):
        """Test CompleteMixin supports all behaviors."""
        model = CompleteModel(name="Test")
        
        # Set all fields
        model.tenant_id = "tenant_123"
        model.created_by_id = "user_456" 
        model.updated_by_id = "user_456"
        
        # Soft delete
        model.soft_delete()
        
        # Verify all work together
        assert model.tenant_id == "tenant_123"
        assert model.created_by_id == "user_456"
        assert model.is_active is False
        assert model.deleted_at is not None
        
        # Restore
        model.restore()
        assert model.is_active is True
        assert model.deleted_at is None
    
    @pytest.mark.asyncio
    async def test_complete_mixin_database_operations(self, db_session, sample_tenant_id, sample_user_id):
        """Test CompleteMixin with full database operations."""
        model = CompleteModel(name="Complete Test")
        model.tenant_id = sample_tenant_id
        model.created_by_id = sample_user_id
        model.updated_by_id = sample_user_id
        
        db_session.add(model)
        await db_session.commit()
        
        # Verify all fields persist
        await db_session.refresh(model)
        assert model.name == "Complete Test"
        assert model.tenant_id == sample_tenant_id
        assert model.created_by_id == sample_user_id
        assert model.is_active is True
        
        # Test soft delete
        model.soft_delete()
        await db_session.commit()
        
        await db_session.refresh(model)
        assert model.is_active is False
        assert model.deleted_at is not None
        
        # Test restore
        model.restore()
        model.updated_by_id = "different_user"
        await db_session.commit()
        
        await db_session.refresh(model)
        assert model.is_active is True
        assert model.deleted_at is None
        assert model.updated_by_id == "different_user"