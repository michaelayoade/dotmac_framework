"""
Integration tests for dotmac-database package.
"""

import uuid
from datetime import datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from dotmac.database import (
    BaseModel,
    SoftDeleteMixin,
    TenantAwareMixin,
    create_async_engine,
    DatabaseManager,
)


class IntegrationTestModel(BaseModel, SoftDeleteMixin, TenantAwareMixin):
    """Test model for integration testing."""
    __tablename__ = "integration_test_model"
    
    name: Mapped[str] = mapped_column(sa.String(100))
    description: Mapped[str] = mapped_column(sa.Text, nullable=True)


class TestDatabaseIntegration:
    """Integration tests for database functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_model_lifecycle(self, db_session, sample_tenant_id):
        """Test complete model lifecycle with all mixins."""
        # Create model
        model = IntegrationTestModel(
            name="Integration Test",
            description="Test model for integration testing",
            tenant_id=sample_tenant_id
        )
        
        # Verify initial state
        assert isinstance(model.id, uuid.UUID)
        assert model.is_active is True
        assert model.deleted_at is None
        assert model.tenant_id == sample_tenant_id
        
        # Save to database
        db_session.add(model)
        await db_session.commit()
        
        # Verify timestamps were set
        assert model.created_at is not None
        assert model.updated_at is not None
        assert isinstance(model.created_at, datetime)
        
        original_id = model.id
        original_created = model.created_at
        
        # Update model
        model.description = "Updated description"
        await db_session.commit()
        await db_session.refresh(model)
        
        # Verify update behavior
        assert model.id == original_id  # ID shouldn't change
        assert model.created_at == original_created  # created_at shouldn't change
        assert model.updated_at > original_created  # updated_at should change
        assert model.description == "Updated description"
        
        # Test soft delete
        model.soft_delete()
        await db_session.commit()
        await db_session.refresh(model)
        
        assert model.is_active is False
        assert model.deleted_at is not None
        
        # Test restore
        model.restore()
        await db_session.commit()
        await db_session.refresh(model)
        
        assert model.is_active is True
        assert model.deleted_at is None
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_queries(self, db_session):
        """Test queries with tenant-aware models."""
        tenant1 = f"tenant_{uuid.uuid4().hex[:8]}"
        tenant2 = f"tenant_{uuid.uuid4().hex[:8]}"
        
        # Create models for different tenants
        model1 = IntegrationTestModel(
            name="Tenant 1 Model",
            tenant_id=tenant1
        )
        model2 = IntegrationTestModel(
            name="Tenant 2 Model", 
            tenant_id=tenant2
        )
        
        db_session.add_all([model1, model2])
        await db_session.commit()
        
        # Query for tenant 1 only
        result = await db_session.execute(
            sa.select(IntegrationTestModel)
            .where(IntegrationTestModel.tenant_id == tenant1)
        )
        tenant1_models = result.scalars().all()
        
        assert len(tenant1_models) == 1
        assert tenant1_models[0].name == "Tenant 1 Model"
        assert tenant1_models[0].tenant_id == tenant1
        
        # Query for tenant 2 only
        result = await db_session.execute(
            sa.select(IntegrationTestModel)
            .where(IntegrationTestModel.tenant_id == tenant2)
        )
        tenant2_models = result.scalars().all()
        
        assert len(tenant2_models) == 1
        assert tenant2_models[0].name == "Tenant 2 Model"
        assert tenant2_models[0].tenant_id == tenant2
    
    @pytest.mark.asyncio
    async def test_soft_delete_queries(self, db_session, sample_tenant_id):
        """Test queries with soft-deleted models."""
        # Create multiple models
        models = []
        for i in range(3):
            model = IntegrationTestModel(
                name=f"Model {i}",
                tenant_id=sample_tenant_id
            )
            models.append(model)
            db_session.add(model)
        
        await db_session.commit()
        
        # Soft delete one model
        models[1].soft_delete()
        await db_session.commit()
        
        # Query all models (including deleted)
        result = await db_session.execute(
            sa.select(IntegrationTestModel)
            .where(IntegrationTestModel.tenant_id == sample_tenant_id)
        )
        all_models = result.scalars().all()
        assert len(all_models) == 3
        
        # Query only active models
        result = await db_session.execute(
            sa.select(IntegrationTestModel)
            .where(
                sa.and_(
                    IntegrationTestModel.tenant_id == sample_tenant_id,
                    IntegrationTestModel.is_active == True
                )
            )
        )
        active_models = result.scalars().all()
        assert len(active_models) == 2
        
        # Verify correct models are active
        active_names = {model.name for model in active_models}
        assert "Model 0" in active_names
        assert "Model 2" in active_names
        assert "Model 1" not in active_names
    
    @pytest.mark.asyncio
    async def test_database_manager_integration(self, test_engine):
        """Test DatabaseManager with real database operations."""
        manager = DatabaseManager(
            read_engine=test_engine,
            write_engine=test_engine
        )
        
        try:
            # Test write operations
            async with manager.get_write_session() as session:
                model = IntegrationTestModel(
                    name="Manager Test",
                    tenant_id="test_tenant"
                )
                session.add(model)
                await session.commit()
                
                model_id = model.id
            
            # Test read operations
            async with manager.get_read_session() as session:
                result = await session.execute(
                    sa.select(IntegrationTestModel)
                    .where(IntegrationTestModel.id == model_id)
                )
                retrieved_model = result.scalar_one_or_none()
                
                assert retrieved_model is not None
                assert retrieved_model.name == "Manager Test"
                assert retrieved_model.tenant_id == "test_tenant"
        
        finally:
            await manager.close()
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, db_session, sample_tenant_id):
        """Test transaction rollback behavior."""
        # Create model in transaction
        model = IntegrationTestModel(
            name="Rollback Test",
            tenant_id=sample_tenant_id
        )
        db_session.add(model)
        
        # Rollback before commit
        await db_session.rollback()
        
        # Verify model was not persisted
        result = await db_session.execute(
            sa.select(IntegrationTestModel)
            .where(IntegrationTestModel.name == "Rollback Test")
        )
        retrieved_model = result.scalar_one_or_none()
        
        assert retrieved_model is None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_engine, sample_tenant_id):
        """Test concurrent database operations."""
        import asyncio
        
        async def create_model(session_num: int):
            manager = DatabaseManager(
                read_engine=test_engine,
                write_engine=test_engine
            )
            
            try:
                async with manager.get_write_session() as session:
                    model = IntegrationTestModel(
                        name=f"Concurrent Model {session_num}",
                        tenant_id=sample_tenant_id
                    )
                    session.add(model)
                    await session.commit()
                    return model.id
            finally:
                await manager.close()
        
        # Create multiple models concurrently
        tasks = [create_model(i) for i in range(3)]
        model_ids = await asyncio.gather(*tasks)
        
        # Verify all models were created
        assert len(model_ids) == 3
        assert all(isinstance(model_id, uuid.UUID) for model_id in model_ids)
        assert len(set(model_ids)) == 3  # All IDs should be unique
        
        # Verify models exist in database
        manager = DatabaseManager(
            read_engine=test_engine,
            write_engine=test_engine
        )
        
        try:
            async with manager.get_read_session() as session:
                result = await session.execute(
                    sa.select(IntegrationTestModel)
                    .where(IntegrationTestModel.id.in_(model_ids))
                )
                models = result.scalars().all()
                
                assert len(models) == 3
                model_names = {model.name for model in models}
                
                for i in range(3):
                    assert f"Concurrent Model {i}" in model_names
        
        finally:
            await manager.close()