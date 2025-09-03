"""
Unit tests for base classes and models.
"""

import uuid
from datetime import datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from dotmac.database import BaseModel
from dotmac.database.base import Base


class TestUser(BaseModel):
    """Test model using BaseModel."""
    __tablename__ = "test_users"
    
    email: Mapped[str] = mapped_column(sa.String(255), unique=True)
    name: Mapped[str] = mapped_column(sa.String(100))


class TestBase:
    """Test Base declarative base."""
    
    def test_base_is_declarative_base(self):
        """Test that Base is a proper declarative base."""
        assert hasattr(Base, 'registry')
        assert hasattr(Base, 'metadata')
    
    def test_base_can_create_models(self):
        """Test that Base can be used to create model classes."""
        class SimpleModel(Base):
            __tablename__ = "simple"
            id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
        
        assert hasattr(SimpleModel, '__table__')
        assert SimpleModel.__table__.name == "simple"


class TestBaseModel:
    """Test BaseModel abstract class."""
    
    def test_base_model_has_required_fields(self):
        """Test that BaseModel has id, created_at, updated_at fields."""
        user = TestUser(email="test@example.com", name="Test User")
        
        # Should have id field
        assert hasattr(user, 'id')
        assert isinstance(user.id, uuid.UUID)
        
        # Should have timestamp fields
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
    
    def test_base_model_generates_uuid_id(self):
        """Test that BaseModel auto-generates UUID for id field."""
        user1 = TestUser(email="test1@example.com", name="User 1")
        user2 = TestUser(email="test2@example.com", name="User 2")
        
        # IDs should be different UUIDs
        assert isinstance(user1.id, uuid.UUID)
        assert isinstance(user2.id, uuid.UUID)
        assert user1.id != user2.id
    
    def test_base_model_repr(self):
        """Test BaseModel string representation."""
        user = TestUser(email="test@example.com", name="Test User")
        repr_str = repr(user)
        
        assert "TestUser" in repr_str
        assert str(user.id) in repr_str
    
    @pytest.mark.asyncio
    async def test_base_model_database_operations(self, db_session):
        """Test basic database operations with BaseModel."""
        # Create user
        user = TestUser(email="test@example.com", name="Test User")
        db_session.add(user)
        await db_session.commit()
        
        # Verify timestamps are set
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        # Update user
        original_created = user.created_at
        original_updated = user.updated_at
        
        user.name = "Updated Name"
        await db_session.commit()
        await db_session.refresh(user)
        
        # created_at should not change, updated_at should
        assert user.created_at == original_created
        assert user.updated_at > original_updated
    
    @pytest.mark.asyncio 
    async def test_base_model_query_operations(self, db_session):
        """Test querying BaseModel instances."""
        # Create test data
        users = [
            TestUser(email=f"user{i}@example.com", name=f"User {i}")
            for i in range(3)
        ]
        
        for user in users:
            db_session.add(user)
        await db_session.commit()
        
        # Test basic query
        result = await db_session.execute(
            sa.select(TestUser).where(TestUser.name == "User 1")
        )
        user = result.scalar_one_or_none()
        
        assert user is not None
        assert user.name == "User 1"
        assert user.email == "user1@example.com"
        
        # Test count
        result = await db_session.execute(
            sa.select(sa.func.count(TestUser.id))
        )
        count = result.scalar()
        assert count == 3
    
    def test_base_model_table_configuration(self):
        """Test that BaseModel creates proper table structure."""
        table = TestUser.__table__
        
        # Check primary key
        assert table.primary_key is not None
        pk_columns = [col.name for col in table.primary_key.columns]
        assert 'id' in pk_columns
        
        # Check required columns exist
        column_names = [col.name for col in table.columns]
        assert 'id' in column_names
        assert 'created_at' in column_names  
        assert 'updated_at' in column_names
        assert 'email' in column_names
        assert 'name' in column_names
        
        # Check id column is UUID type
        id_column = table.columns['id']
        assert str(id_column.type).upper() in ['UUID', 'GUID', 'CHAR(32)']
    
    def test_base_model_inheritance(self):
        """Test that BaseModel can be inherited properly."""
        class ExtendedUser(TestUser):
            __tablename__ = "extended_users"
            
            age: Mapped[int] = mapped_column(sa.Integer, nullable=True)
        
        # Should inherit all BaseModel fields
        user = ExtendedUser(email="test@example.com", name="Test", age=25)
        
        assert hasattr(user, 'id')
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert hasattr(user, 'email')
        assert hasattr(user, 'name')
        assert hasattr(user, 'age')
        assert user.age == 25