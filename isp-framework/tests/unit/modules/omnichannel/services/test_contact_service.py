"""
Tests for Omnichannel Contact Service

TESTING IMPROVEMENT: Unit tests for the decomposed contact service,
ensuring the customer contact management functionality works correctly
after architecture refactoring.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy.orm import Session

from dotmac_isp.modules.omnichannel.services.contact_service import ContactService
from dotmac_isp.modules.omnichannel.models import (
    CustomerContact,
    ContactCommunicationChannel,
    ContactType,
    CommunicationChannel
)
from dotmac_isp.modules.omnichannel.schemas import (
    CustomerContactCreate,
    CustomerContactUpdate,
    CustomerContactResponse,
    ContactCommunicationChannelCreate
)
from dotmac_isp.shared.exceptions import EntityNotFoundError, ValidationError


class TestContactService:
    """Test cases for ContactService class."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def contact_service(self, mock_db):
        """Create contact service instance."""
        service = ContactService(mock_db, tenant_id="tenant_123")
        # Mock the repository to avoid database calls
        service.contact_repository = Mock()
        service.channel_repository = Mock()
        return service
    
    @pytest.fixture
    def sample_contact_data(self):
        """Sample contact creation data."""
        return CustomerContactCreate(
            customer_id=uuid4(),
            contact_type=ContactType.PRIMARY,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890"
        )
    
    @pytest.fixture
    def sample_contact_entity(self):
        """Sample contact entity."""
        contact_id = uuid4()
        customer_id = uuid4()
        return CustomerContact(
            id=contact_id,
            customer_id=customer_id,
            contact_type=ContactType.PRIMARY,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="+1234567890",
            tenant_id="tenant_123"
        )
    
    @pytest.mark.asyncio
    async def test_create_customer_contact_success(self, contact_service, sample_contact_data, sample_contact_entity):
        """Test successful customer contact creation."""
        # Setup
        contact_service.contact_repository.create.return_value = sample_contact_entity
        
        # Test
        result = await contact_service.create_customer_contact(sample_contact_data)
        
        # Assertions
        contact_service.contact_repository.create.assert_called_once()
        assert isinstance(result, UUID)
        assert result == sample_contact_entity.id
    
    @pytest.mark.asyncio
    async def test_create_customer_contact_validation_error(self, contact_service):
        """Test contact creation with validation error."""
        # Setup - invalid data (missing required fields)
        invalid_data = CustomerContactCreate(
            customer_id=uuid4(),
            contact_type=ContactType.PRIMARY,
            # Missing first_name, last_name, email
        )
        
        contact_service.contact_repository.create.side_effect = ValidationError("Invalid data")
        
        # Test
        with pytest.raises(ValidationError):
            await contact_service.create_customer_contact(invalid_data)
    
    @pytest.mark.asyncio
    async def test_update_customer_contact_success(self, contact_service, sample_contact_entity):
        """Test successful customer contact update."""
        # Setup
        contact_id = sample_contact_entity.id
        update_data = CustomerContactUpdate(
            first_name="Jane",
            last_name="Smith"
        )
        
        updated_entity = sample_contact_entity
        updated_entity.first_name = "Jane"
        updated_entity.last_name = "Smith"
        
        contact_service.contact_repository.get_by_id.return_value = sample_contact_entity
        contact_service.contact_repository.update.return_value = updated_entity
        
        # Test
        result = await contact_service.update_customer_contact(contact_id, update_data)
        
        # Assertions
        contact_service.contact_repository.update.assert_called_once()
        assert isinstance(result, CustomerContactResponse)
        assert result.first_name == "Jane"
        assert result.last_name == "Smith"
    
    @pytest.mark.asyncio
    async def test_update_customer_contact_not_found(self, contact_service):
        """Test updating non-existent contact."""
        # Setup
        contact_id = uuid4()
        update_data = CustomerContactUpdate(first_name="Jane")
        
        contact_service.contact_repository.get_by_id.return_value = None
        
        # Test
        with pytest.raises(EntityNotFoundError):
            await contact_service.update_customer_contact(contact_id, update_data)
    
    @pytest.mark.asyncio
    async def test_add_communication_channel_success(self, contact_service):
        """Test successful communication channel addition."""
        # Setup
        channel_data = ContactCommunicationChannelCreate(
            contact_id=uuid4(),
            channel_type=CommunicationChannel.EMAIL,
            channel_value="new.email@example.com",
            is_primary=False
        )
        
        mock_channel = ContactCommunicationChannel(
            id=uuid4(),
            **channel_data.dict()
        )
        
        contact_service.channel_repository.create.return_value = mock_channel
        
        # Test
        result = await contact_service.add_communication_channel(channel_data)
        
        # Assertions
        contact_service.channel_repository.create.assert_called_once()
        assert isinstance(result, UUID)
        assert result == mock_channel.id
    
    @pytest.mark.asyncio
    async def test_get_customer_contacts_success(self, contact_service):
        """Test successful retrieval of customer contacts."""
        # Setup
        customer_id = uuid4()
        mock_contacts = [
            CustomerContact(
                id=uuid4(),
                customer_id=customer_id,
                contact_type=ContactType.PRIMARY,
                first_name="John",
                last_name="Doe",
                email="john@example.com"
            ),
            CustomerContact(
                id=uuid4(),
                customer_id=customer_id,
                contact_type=ContactType.SECONDARY,
                first_name="Jane",
                last_name="Doe",
                email="jane@example.com"
            )
        ]
        
        contact_service.contact_repository.list.return_value = mock_contacts
        
        # Test
        result = await contact_service.get_customer_contacts(customer_id)
        
        # Assertions
        contact_service.contact_repository.list.assert_called_once_with(
            filters={"customer_id": customer_id}
        )
        assert len(result) == 2
        assert all(isinstance(contact, CustomerContactResponse) for contact in result)
    
    @pytest.mark.asyncio
    async def test_get_customer_contacts_empty(self, contact_service):
        """Test retrieval when customer has no contacts."""
        # Setup
        customer_id = uuid4()
        contact_service.contact_repository.list.return_value = []
        
        # Test
        result = await contact_service.get_customer_contacts(customer_id)
        
        # Assertions
        assert result == []
        contact_service.contact_repository.list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_communication_channel_success(self, contact_service):
        """Test successful communication channel verification."""
        # Setup
        channel_id = uuid4()
        mock_channel = ContactCommunicationChannel(
            id=channel_id,
            contact_id=uuid4(),
            channel_type=CommunicationChannel.EMAIL,
            channel_value="test@example.com",
            is_verified=False
        )
        
        contact_service.channel_repository.get_by_id.return_value = mock_channel
        contact_service.channel_repository.update.return_value = mock_channel
        
        # Test
        result = await contact_service.verify_communication_channel(channel_id)
        
        # Assertions
        assert result is True
        contact_service.channel_repository.update.assert_called_once()
        # Verify that is_verified was set to True
        update_call_args = contact_service.channel_repository.update.call_args
        assert update_call_args[0][1]['is_verified'] is True
    
    @pytest.mark.asyncio
    async def test_verify_communication_channel_not_found(self, contact_service):
        """Test verification of non-existent channel."""
        # Setup
        channel_id = uuid4()
        contact_service.channel_repository.get_by_id.return_value = None
        
        # Test
        with pytest.raises(EntityNotFoundError):
            await contact_service.verify_communication_channel(channel_id)
    
    @pytest.mark.asyncio
    async def test_verify_communication_channel_already_verified(self, contact_service):
        """Test verification of already verified channel."""
        # Setup
        channel_id = uuid4()
        mock_channel = ContactCommunicationChannel(
            id=channel_id,
            contact_id=uuid4(),
            channel_type=CommunicationChannel.EMAIL,
            channel_value="test@example.com",
            is_verified=True
        )
        
        contact_service.channel_repository.get_by_id.return_value = mock_channel
        
        # Test
        result = await contact_service.verify_communication_channel(channel_id)
        
        # Assertions
        assert result is True
        # Should not call update if already verified
        contact_service.channel_repository.update.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_contact_channels(self, contact_service):
        """Test retrieval of contact communication channels."""
        # Setup
        contact_id = uuid4()
        mock_channels = [
            ContactCommunicationChannel(
                id=uuid4(),
                contact_id=contact_id,
                channel_type=CommunicationChannel.EMAIL,
                channel_value="primary@example.com",
                is_primary=True
            ),
            ContactCommunicationChannel(
                id=uuid4(),
                contact_id=contact_id,
                channel_type=CommunicationChannel.PHONE,
                channel_value="+1234567890",
                is_primary=False
            )
        ]
        
        contact_service.channel_repository.list.return_value = mock_channels
        
        # Test
        result = await contact_service.get_contact_channels(contact_id)
        
        # Assertions
        contact_service.channel_repository.list.assert_called_once_with(
            filters={"contact_id": contact_id}
        )
        assert len(result) == 2
    
    def test_build_contact_response(self, contact_service, sample_contact_entity):
        """Test building contact response from entity."""
        # Test the private method that converts entity to response
        result = contact_service._build_contact_response(sample_contact_entity)
        
        # Assertions
        assert isinstance(result, CustomerContactResponse)
        assert result.id == sample_contact_entity.id
        assert result.customer_id == sample_contact_entity.customer_id
        assert result.first_name == sample_contact_entity.first_name
        assert result.last_name == sample_contact_entity.last_name
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_db):
        """Test service initialization and dependency injection."""
        # Test
        service = ContactService(mock_db, tenant_id="tenant_456")
        
        # Assertions
        assert service.db == mock_db
        assert service.tenant_id == "tenant_456"
        assert hasattr(service, 'contact_repository')
        assert hasattr(service, 'channel_repository')
    
    @pytest.mark.asyncio
    async def test_bulk_contact_creation(self, contact_service):
        """Test bulk contact creation functionality."""
        # Setup
        contacts_data = [
            CustomerContactCreate(
                customer_id=uuid4(),
                contact_type=ContactType.PRIMARY,
                first_name="John",
                last_name="Doe",
                email="john@example.com"
            ),
            CustomerContactCreate(
                customer_id=uuid4(),
                contact_type=ContactType.SECONDARY,
                first_name="Jane",
                last_name="Smith",
                email="jane@example.com"
            )
        ]
        
        mock_entities = [
            CustomerContact(id=uuid4(), **data.dict())
            for data in contacts_data
        ]
        
        contact_service.contact_repository.bulk_create.return_value = mock_entities
        
        # Test
        result = await contact_service.bulk_create_contacts(contacts_data)
        
        # Assertions
        contact_service.contact_repository.bulk_create.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(contact_id, UUID) for contact_id in result)