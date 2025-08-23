"""
Tests for Base Repository Classes

TESTING IMPROVEMENT: Comprehensive unit tests for base repository classes
to ensure reliability of the foundation layer for all CRUD operations.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from dotmac_isp.shared.base_repository import BaseRepository, BaseTenantRepository, create_repository
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    DuplicateEntityError,
    ValidationError,
    DatabaseError
)
from dotmac_isp.shared.models import TenantMixin


# Isolated test models to avoid SQLAlchemy configuration conflicts
from sqlalchemy.ext.declarative import declarative_base

TestBase = declarative_base()

class TestModel(TestBase):
    __tablename__ = 'test_model'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TestTenantModel(TestBase, TenantMixin):
    __tablename__ = 'test_tenant_model'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))


class TestBaseRepository:
    """Test cases for BaseRepository class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = Mock(spec=Session)
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.rollback = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create repository instance."""
        return BaseRepository(mock_db, TestModel)
    
    @pytest.fixture
    def tenant_repository(self, mock_db):
        """Create tenant repository instance."""
        return BaseTenantRepository(mock_db, TestTenantModel, "tenant_123")
    
    def test_init(self, mock_db):
        """Test repository initialization."""
        repo = BaseRepository(mock_db, TestModel, "tenant_123")
        
        assert repo.db == mock_db
        assert repo.model_class == TestModel
        assert repo.tenant_id == "tenant_123"
    
    def test_create_success(self, repository, mock_db):
        """Test successful entity creation."""
        # Setup
        data = {"name": "Test Entity", "active": True}
        
        # Create a mock entity that matches our data
        mock_entity = Mock()
        mock_entity.id = uuid4()
        mock_entity.name = "Test Entity"
        mock_entity.active = True
        
        # Mock the model class to return our mock entity
        with patch.object(repository, 'model_class') as mock_model_class:
            mock_model_class.return_value = mock_entity
            mock_model_class.__name__ = 'TestModel'
            result = repository.create(data)
        
        # Assertions
        mock_model_class.assert_called_once_with(**data)
        mock_db.add.assert_called_once_with(mock_entity)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_entity)
        assert result == mock_entity
    
    def test_create_with_tenant_id(self, mock_db):
        """Test creation with tenant ID for tenant-aware models."""
        repo = BaseRepository(mock_db, TestTenantModel, "tenant_123")
        data = {"name": "Test Entity"}
        
        # Create a mock entity that matches our data
        mock_entity = Mock()
        mock_entity.id = uuid4()
        mock_entity.name = "Test Entity"
        mock_entity.tenant_id = "tenant_123"
        
        # Mock the model class constructor directly
        with patch.object(TestTenantModel, '__new__', return_value=mock_entity) as mock_constructor:
            result = repo.create(data)
        
        # Should add tenant_id to data before creating entity
        mock_db.add.assert_called_once_with(mock_entity)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_entity)
        assert result == mock_entity
    
    def test_create_duplicate_error(self, repository, mock_db):
        """Test creation with duplicate entity."""
        # Setup
        mock_db.commit.side_effect = IntegrityError("duplicate", None, None)
        data = {"name": "Duplicate Entity"}
        
        # Test
        with pytest.raises(DuplicateEntityError):
            repository.create(data)
        
        # Should rollback on error
        mock_db.rollback.assert_called_once()
    
    def test_get_by_id_success(self, repository, mock_db):
        """Test successful get by ID."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_entity
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.get_by_id(entity_id)
        
        # Assertions
        assert result == mock_entity
        mock_db.query.assert_called_with(TestModel)
    
    def test_get_by_id_not_found(self, repository, mock_db):
        """Test get by ID when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.get_by_id(entity_id)
        
        # Should return None
        assert result is None
    
    def test_get_by_id_or_raise_success(self, repository, mock_db):
        """Test successful get by ID or raise."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_entity
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.get_by_id_or_raise(entity_id)
        
        # Should return entity
        assert result == mock_entity
    
    def test_get_by_id_or_raise_not_found(self, repository, mock_db):
        """Test get by ID or raise when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Test
        with pytest.raises(EntityNotFoundError):
            repository.get_by_id_or_raise(entity_id)
    
    def test_update_success(self, repository, mock_db):
        """Test successful entity update."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Original")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_entity
        mock_db.query.return_value = mock_query
        
        update_data = {"name": "Updated"}
        
        # Test
        result = repository.update(entity_id, update_data)
        
        # Assertions
        assert mock_entity.name == "Updated"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        assert result == mock_entity
    
    def test_update_not_found(self, repository, mock_db):
        """Test update when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        update_data = {"name": "Updated"}
        
        # Test
        with pytest.raises(EntityNotFoundError):
            repository.update(entity_id, update_data)
    
    def test_delete_hard_delete(self, repository, mock_db):
        """Test hard delete (no soft delete support)."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="ToDelete")
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_entity
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.delete(entity_id)
        
        # Assertions
        mock_db.delete.assert_called_with(mock_entity)
        mock_db.commit.assert_called_once()
        assert result is True
    
    def test_delete_not_found(self, repository, mock_db):
        """Test delete when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Test
        with pytest.raises(EntityNotFoundError):
            repository.delete(entity_id)
    
    def test_list_with_filters(self, repository, mock_db):
        """Test listing entities with filters."""
        # Setup
        mock_entities = [TestModel(id=1, name="Test1"), TestModel(id=2, name="Test2")]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = mock_entities
        mock_db.query.return_value = mock_query
        
        filters = {"active": True}
        
        # Test
        result = repository.list(filters=filters)
        
        # Assertions
        assert result == mock_entities
        mock_db.query.assert_called_with(TestModel)
    
    def test_list_with_sorting(self, repository, mock_db):
        """Test listing entities with sorting."""
        # Setup
        mock_entities = [TestModel(id=1, name="Test1")]
        mock_query = Mock()
        mock_query.order_by.return_value.all.return_value = mock_entities
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.list(sort_by="name", sort_order="desc")
        
        # Assertions
        assert result == mock_entities
    
    def test_list_with_pagination(self, repository, mock_db):
        """Test listing entities with pagination."""
        # Setup
        mock_entities = [TestModel(id=1, name="Test1")]
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_entities
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.list(limit=10, offset=20)
        
        # Assertions
        assert result == mock_entities
    
    def test_count(self, repository, mock_db):
        """Test counting entities."""
        # Setup
        mock_query = Mock()
        mock_query.count.return_value = 5
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.count()
        
        # Assertions
        assert result == 5
        mock_db.query.assert_called_with(TestModel)
    
    def test_bulk_create(self, repository, mock_db):
        """Test bulk entity creation."""
        # Setup
        data_list = [{"name": "Test1"}, {"name": "Test2"}]
        
        # Create mock entities
        mock_entity1 = Mock()
        mock_entity1.id = uuid4()
        mock_entity1.name = "Test1"
        
        mock_entity2 = Mock()
        mock_entity2.id = uuid4()
        mock_entity2.name = "Test2"
        
        mock_entities = [mock_entity1, mock_entity2]
        
        # Test
        with patch.object(repository, 'model_class') as mock_model_class:
            mock_model_class.side_effect = mock_entities
            mock_model_class.__name__ = 'TestModel'
            
            result = repository.bulk_create(data_list)
        
        # Assertions
        assert len(result) == 2
        mock_db.commit.assert_called_once()
    
    def test_bulk_update(self, repository, mock_db):
        """Test bulk entity updates."""
        # Setup
        entity1 = TestModel(id=1, name="Original1")
        entity2 = TestModel(id=2, name="Original2")
        
        updates = [
            {"id": 1, "name": "Updated1"},
            {"id": 2, "name": "Updated2"}
        ]
        
        # Mock get_by_id calls
        repository.get_by_id = Mock()
        repository.get_by_id.side_effect = [entity1, entity2]
        
        # Test
        result = repository.bulk_update(updates)
        
        # Assertions
        assert result == 2
        assert entity1.name == "Updated1"
        assert entity2.name == "Updated2"
        mock_db.commit.assert_called_once()
    
    def test_exists_true(self, repository, mock_db):
        """Test exists when entity found."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = TestModel(id=1)
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.exists({"name": "Test"})
        
        # Assertions
        assert result is True
    
    def test_exists_false(self, repository, mock_db):
        """Test exists when entity not found."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        
        # Test
        result = repository.exists({"name": "Test"})
        
        # Assertions
        assert result is False


class TestBaseTenantRepository:
    """Test cases for BaseTenantRepository class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = Mock(spec=Session)
        db.query = Mock()
        return db
    
    def test_init_success(self, mock_db):
        """Test successful tenant repository initialization."""
        repo = BaseTenantRepository(mock_db, TestTenantModel, "tenant_123")
        
        assert repo.tenant_id == "tenant_123"
        assert repo.model_class == TestTenantModel
    
    def test_init_no_tenant_id(self, mock_db):
        """Test initialization without tenant ID should fail."""
        with pytest.raises(ValidationError, match="tenant_id is required"):
            BaseTenantRepository(mock_db, TestTenantModel, None)
    
    def test_init_non_tenant_model(self, mock_db):
        """Test initialization with non-tenant model should fail."""
        with pytest.raises(ValidationError, match="must inherit from TenantMixin"):
            BaseTenantRepository(mock_db, TestModel, "tenant_123")
    
    def test_get_tenant_stats(self, mock_db):
        """Test getting tenant statistics."""
        # Setup
        repo = BaseTenantRepository(mock_db, TestTenantModel, "tenant_123")
        mock_query = Mock()
        mock_query.count.return_value = 10
        
        # Mock the _build_base_query method to return our mock query
        with patch.object(repo, '_build_base_query', return_value=mock_query):
            # Test
            result = repo.get_tenant_stats()
        
        # Assertions
        assert result['total_entities'] == 10
        assert result['tenant_id'] == "tenant_123"
        assert result['entity_type'] == "TestTenantModel"


class TestCreateRepository:
    """Test cases for create_repository factory function."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    def test_create_base_repository(self, mock_db):
        """Test creating base repository."""
        repo = create_repository(mock_db, TestModel)
        
        assert isinstance(repo, BaseRepository)
        assert not isinstance(repo, BaseTenantRepository)
    
    def test_create_tenant_repository(self, mock_db):
        """Test creating tenant repository."""
        repo = create_repository(mock_db, TestTenantModel, "tenant_123")
        
        assert isinstance(repo, BaseTenantRepository)
    
    def test_create_base_for_tenant_model_without_tenant_id(self, mock_db):
        """Test creating base repository for tenant model without tenant ID."""
        repo = create_repository(mock_db, TestTenantModel)
        
        assert isinstance(repo, BaseRepository)
        assert not isinstance(repo, BaseTenantRepository)


class TestRepositoryFiltering:
    """Test cases for repository filtering functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def repository(self, mock_db):
        """Create repository instance."""
        return BaseRepository(mock_db, TestModel)
    
    def test_apply_filters_equality(self, repository, mock_db):
        """Test equality filters."""
        mock_query = Mock()
        # Mock the filter to return itself for chaining
        mock_query.filter.return_value = mock_query
        mock_db.query.return_value = mock_query
        
        filters = {"name": "Test", "active": True}
        
        # Test internal method
        result_query = repository._apply_filters(mock_query, filters)
        
        # Should call filter for each condition
        assert mock_query.filter.call_count >= len(filters)
        assert result_query == mock_query
    
    def test_apply_filters_advanced(self, repository, mock_db):
        """Test advanced filters with operators."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        filters = {
            "id": {"gt": 10},
            "name": {"like": "Test"},
            "active": {"is_null": False}
        }
        
        # Test internal method
        result_query = repository._apply_filters(mock_query, filters)
        
        # Should handle advanced filter operators
        assert mock_query.filter.called
    
    def test_apply_filters_list(self, repository, mock_db):
        """Test list filters (IN operator)."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        
        filters = {"id": [1, 2, 3]}
        
        # Test internal method
        result_query = repository._apply_filters(mock_query, filters)
        
        # Should use IN operator for lists
        assert mock_query.filter.called