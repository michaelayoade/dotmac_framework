"""
Tests for Base Service Classes

TESTING IMPROVEMENT: Comprehensive unit tests for base service classes
to ensure reliability of the business logic layer across all modules.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from uuid import UUID as PythonUUID
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError as PydanticValidationError

from dotmac_isp.shared.base_service import BaseService, BaseTenantService, BaseReadOnlyService
from dotmac_isp.shared.base_repository import BaseRepository
from dotmac_isp.shared.database.base import Base, TenantMixin
from dotmac_isp.shared.exceptions import (
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    ServiceError
)


# Test model and schema classes
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID

class TestModel(Base):
    __tablename__ = 'test_model'
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100))
    active = Column(Boolean, default=True)
    
    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestTenantModel(Base, TenantMixin):
    __tablename__ = 'test_tenant_model'
    __table_args__ = {"extend_existing": True}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100))
    
    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestCreateSchema(BaseModel):
    name: str
    active: bool = True


class TestUpdateSchema(BaseModel):
    name: str = None
    active: bool = None


class TestResponseSchema(BaseModel):
    id: PythonUUID
    name: str
    active: bool
    
    class Config:
        from_attributes = True


# Concrete service for testing
class ConcreteTestService(BaseService[TestModel, TestCreateSchema, TestUpdateSchema, TestResponseSchema]):
    """Concrete service implementation for testing."""
    
    def __init__(self, db, tenant_id=None):
        super().__init__(
            db=db,
            model_class=TestModel,
            create_schema=TestCreateSchema,
            update_schema=TestUpdateSchema,
            response_schema=TestResponseSchema,
            tenant_id=tenant_id
        )


class TestBaseService:
    """Test cases for BaseService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository."""
        repo = Mock(spec=BaseRepository)
        return repo
    
    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """Create service instance."""
        service = ConcreteTestService(mock_db)
        service.repository = mock_repository
        return service
    
    def test_init(self, mock_db):
        """Test service initialization."""
        service = ConcreteTestService(mock_db, tenant_id="tenant_123")
        
        assert service.db == mock_db
        assert service.model_class == TestModel
        assert service.create_schema == TestCreateSchema
        assert service.update_schema == TestUpdateSchema
        assert service.response_schema == TestResponseSchema
        assert service.tenant_id == "tenant_123"
    
    @pytest.mark.asyncio
    async def test_create_success(self, service, mock_repository):
        """Test successful entity creation."""
        # Setup
        create_data = TestCreateSchema(name="Test Entity", active=True)
        mock_entity = TestModel(id=uuid4(), name="Test Entity", active=True)
        mock_repository.create.return_value = mock_entity
        
        # Mock the _to_response_schema method
        expected_response = TestResponseSchema(
            id=mock_entity.id,
            name=mock_entity.name,
            active=mock_entity.active
        )
        service._to_response_schema = Mock(return_value=expected_response)
        
        # Test
        result = await service.create(create_data)
        
        # Assertions
        mock_repository.create.assert_called_once()
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_create_validation_error(self, service, mock_repository):
        """Test creation with validation error."""
        # Setup - invalid data
        invalid_data = {"name": 123}  # name should be string
        
        # Test
        with pytest.raises(ValidationError):
            await service.create(invalid_data)
    
    @pytest.mark.asyncio
    async def test_create_with_hooks(self, service, mock_repository):
        """Test creation with pre/post hooks."""
        # Setup
        create_data = TestCreateSchema(name="Test Entity")
        mock_entity = TestModel(id=uuid4(), name="Test Entity", active=True)
        mock_repository.create.return_value = mock_entity
        
        # Mock hooks
        service._pre_create_hook = AsyncMock()
        service._post_create_hook = AsyncMock()
        service._validate_create_rules = AsyncMock()
        service._to_response_schema = Mock()
        
        # Test
        await service.create(create_data)
        
        # Assertions
        service._pre_create_hook.assert_called_once_with(create_data)
        service._validate_create_rules.assert_called_once_with(create_data)
        service._post_create_hook.assert_called_once_with(mock_entity, create_data)
    
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, service, mock_repository):
        """Test successful get by ID."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test", active=True)
        mock_repository.get_by_id.return_value = mock_entity
        
        expected_response = TestResponseSchema(
            id=entity_id,
            name="Test",
            active=True
        )
        service._to_response_schema = Mock(return_value=expected_response)
        
        # Test
        result = await service.get_by_id(entity_id)
        
        # Assertions
        assert result == expected_response
        mock_repository.get_by_id.assert_called_once_with(entity_id)
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_repository):
        """Test get by ID when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_repository.get_by_id.return_value = None
        
        # Test
        result = await service.get_by_id(entity_id)
        
        # Should return None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_success(self, service, mock_repository):
        """Test successful get by ID or raise."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test", active=True)
        mock_repository.get_by_id.return_value = mock_entity
        
        expected_response = TestResponseSchema(
            id=entity_id,
            name="Test",
            active=True
        )
        service._to_response_schema = Mock(return_value=expected_response)
        
        # Test
        result = await service.get_by_id_or_raise(entity_id)
        
        # Should return response
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_not_found(self, service, mock_repository):
        """Test get by ID or raise when entity not found."""
        # Setup
        entity_id = uuid4()
        mock_repository.get_by_id.return_value = None
        
        # Test
        with pytest.raises(EntityNotFoundError):
            await service.get_by_id_or_raise(entity_id)
    
    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_repository):
        """Test successful entity update."""
        # Setup
        entity_id = uuid4()
        update_data = TestUpdateSchema(name="Updated Name")
        
        mock_existing = TestModel(id=entity_id, name="Original", active=True)
        mock_updated = TestModel(id=entity_id, name="Updated Name", active=True)
        
        mock_repository.get_by_id_or_raise.return_value = mock_existing
        mock_repository.update.return_value = mock_updated
        
        expected_response = TestResponseSchema(
            id=entity_id,
            name="Updated Name",
            active=True
        )
        service._to_response_schema = Mock(return_value=expected_response)
        
        # Mock hooks
        service._pre_update_hook = AsyncMock()
        service._post_update_hook = AsyncMock()
        service._validate_update_rules = AsyncMock()
        
        # Test
        result = await service.update(entity_id, update_data)
        
        # Assertions
        assert result == expected_response
        mock_repository.update.assert_called_once()
        service._pre_update_hook.assert_called_once_with(mock_existing, update_data)
        service._validate_update_rules.assert_called_once_with(mock_existing, update_data)
        service._post_update_hook.assert_called_once_with(mock_updated, update_data)
    
    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_repository):
        """Test update when entity not found."""
        # Setup
        entity_id = uuid4()
        update_data = TestUpdateSchema(name="Updated")
        mock_repository.get_by_id_or_raise.side_effect = EntityNotFoundError("Not found")
        
        # Test
        with pytest.raises(EntityNotFoundError):
            await service.update(entity_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_repository):
        """Test successful entity deletion."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="ToDelete", active=True)
        
        mock_repository.get_by_id_or_raise.return_value = mock_entity
        mock_repository.delete.return_value = True
        
        # Mock hooks
        service._pre_delete_hook = AsyncMock()
        service._post_delete_hook = AsyncMock()
        service._validate_delete_rules = AsyncMock()
        
        # Test
        result = await service.delete(entity_id)
        
        # Assertions
        assert result is True
        mock_repository.delete.assert_called_once_with(entity_id, commit=True)
        service._pre_delete_hook.assert_called_once_with(mock_entity)
        service._validate_delete_rules.assert_called_once_with(mock_entity)
        service._post_delete_hook.assert_called_once_with(mock_entity)
    
    @pytest.mark.asyncio
    async def test_delete_business_rule_violation(self, service, mock_repository):
        """Test delete with business rule violation."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Protected", active=True)
        
        mock_repository.get_by_id_or_raise.return_value = mock_entity
        service._validate_delete_rules = AsyncMock(side_effect=BusinessRuleError("Cannot delete"))
        
        # Test
        with pytest.raises(BusinessRuleError):
            await service.delete(entity_id)
    
    @pytest.mark.asyncio
    async def test_list_with_filters(self, service, mock_repository):
        """Test listing entities with filters."""
        # Setup
        mock_entities = [
            TestModel(id=uuid4(), name="Test1", active=True),
            TestModel(id=uuid4(), name="Test2", active=True)
        ]
        mock_repository.list.return_value = mock_entities
        
        mock_responses = [
            TestResponseSchema(id=e.id, name=e.name, active=e.active)
            for e in mock_entities
        ]
        service._to_response_schema = Mock(side_effect=mock_responses)
        service._apply_access_control_filters = AsyncMock(side_effect=lambda f: f)
        
        filters = {"active": True}
        
        # Test
        result = await service.list(filters=filters)
        
        # Assertions
        assert len(result) == 2
        mock_repository.list.assert_called_once_with(
            filters=filters,
            sort_by=None,
            sort_order='asc',
            limit=None,
            offset=None
        )
    
    @pytest.mark.asyncio
    async def test_count(self, service, mock_repository):
        """Test counting entities."""
        # Setup
        mock_repository.count.return_value = 5
        service._apply_access_control_filters = AsyncMock(side_effect=lambda f: f)
        
        # Test
        result = await service.count()
        
        # Assertions
        assert result == 5
        mock_repository.count.assert_called_once()
    
    def test_to_response_schema(self, service):
        """Test converting entity to response schema."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test", active=True)
        
        # Mock the entity's table columns
        mock_column1 = Mock()
        mock_column1.name = 'id'
        mock_column2 = Mock()
        mock_column2.name = 'name'
        mock_column3 = Mock()
        mock_column3.name = 'active'
        
        mock_entity.__table__ = Mock()
        mock_entity.__table__.columns = [mock_column1, mock_column2, mock_column3]
        
        service._add_relationship_data = Mock(side_effect=lambda e, d: d)
        
        # Test
        result = service._to_response_schema(mock_entity)
        
        # Assertions
        assert isinstance(result, TestResponseSchema)
        assert result.id == entity_id
        assert result.name == "Test"
        assert result.active is True


class TestBaseTenantService:
    """Test cases for BaseTenantService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    def test_init_success(self, mock_db):
        """Test successful tenant service initialization."""
        # This would need a concrete implementation for testing
        # Skipping for now as it requires more complex setup
        pass
    
    def test_init_no_tenant_id(self, mock_db):
        """Test initialization without tenant ID should fail."""
        # Would test with actual tenant service implementation
        pass


class TestBaseReadOnlyService:
    """Test cases for BaseReadOnlyService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository."""
        return Mock(spec=BaseRepository)
    
    @pytest.fixture
    def service(self, mock_db, mock_repository):
        """Create read-only service instance."""
        service = BaseReadOnlyService(
            db=mock_db,
            model_class=TestModel,
            response_schema=TestResponseSchema
        )
        service.repository = mock_repository
        return service
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, service, mock_repository):
        """Test get by ID in read-only service."""
        # Setup
        entity_id = uuid4()
        mock_entity = TestModel(id=entity_id, name="Test", active=True)
        mock_repository.get_by_id.return_value = mock_entity
        
        # Mock _to_response_schema
        expected_response = TestResponseSchema(
            id=entity_id,
            name="Test", 
            active=True
        )
        service._to_response_schema = Mock(return_value=expected_response)
        
        # Test
        result = await service.get_by_id(entity_id)
        
        # Assertions
        assert result == expected_response
    
    @pytest.mark.asyncio
    async def test_list(self, service, mock_repository):
        """Test list in read-only service."""
        # Setup
        mock_entities = [TestModel(id=uuid4(), name="Test", active=True)]
        mock_repository.list.return_value = mock_entities
        
        expected_responses = [TestResponseSchema(
            id=mock_entities[0].id,
            name="Test",
            active=True
        )]
        service._to_response_schema = Mock(side_effect=expected_responses)
        
        # Test
        result = await service.list()
        
        # Assertions
        assert len(result) == 1
        mock_repository.list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count(self, service, mock_repository):
        """Test count in read-only service."""
        # Setup
        mock_repository.count.return_value = 10
        
        # Test
        result = await service.count()
        
        # Assertions
        assert result == 10


class TestServiceHooks:
    """Test cases for service hook functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service with custom hooks."""
        class ServiceWithHooks(ConcreteTestService):
            def __init__(self, db):
                super().__init__(db)
                self.pre_create_called = False
                self.post_create_called = False
                self.validate_create_called = False
            
            async def _pre_create_hook(self, data):
                self.pre_create_called = True
            
            async def _post_create_hook(self, entity, data):
                self.post_create_called = True
            
            async def _validate_create_rules(self, data):
                self.validate_create_called = True
                if data.name == "forbidden":
                    raise BusinessRuleError("Forbidden name")
        
        service = ServiceWithHooks(mock_db)
        service.repository = Mock()
        service.repository.create.return_value = TestModel(id=uuid4(), name="Test", active=True)
        service._to_response_schema = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_hooks_called_during_create(self, service):
        """Test that hooks are called during create operation."""
        # Setup
        create_data = TestCreateSchema(name="Test")
        
        # Test
        await service.create(create_data)
        
        # Assertions
        assert service.pre_create_called
        assert service.post_create_called
        assert service.validate_create_called
    
    @pytest.mark.asyncio
    async def test_business_rule_validation(self, service):
        """Test business rule validation in hooks."""
        # Setup
        create_data = TestCreateSchema(name="forbidden")
        
        # Test
        with pytest.raises(BusinessRuleError, match="Forbidden name"):
            await service.create(create_data)


class TestServiceErrorHandling:
    """Test cases for service error handling."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        service = ConcreteTestService(mock_db)
        service.repository = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_create_database_error(self, service):
        """Test handling database errors during create."""
        # Setup
        create_data = TestCreateSchema(name="Test")
        service.repository.create.side_effect = Exception("Database error")
        
        # Test
        with pytest.raises(ServiceError, match="Failed to create entity"):
            await service.create(create_data)
    
    @pytest.mark.asyncio
    async def test_update_database_error(self, service):
        """Test handling database errors during update."""
        # Setup
        entity_id = uuid4()
        update_data = TestUpdateSchema(name="Updated")
        service.repository.get_by_id_or_raise.side_effect = Exception("Database error")
        
        # Test
        with pytest.raises(ServiceError, match="Failed to retrieve entity"):
            await service.update(entity_id, update_data)