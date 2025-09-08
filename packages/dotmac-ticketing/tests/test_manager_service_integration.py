"""
Integration tests for TicketManager and TicketService with dependency injection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from dotmac.ticketing.core.manager import TicketManager
from dotmac.ticketing.core.service import TicketService
from dotmac.ticketing.core.models import (
    Ticket, TicketStatus, TicketPriority, TicketCategory
)
from dotmac.ticketing.integrations.adapters import (
    NoopCommunicationService, NoopMonitoringService
)


@pytest.fixture
def mock_communication_service():
    """Mock communication service."""
    return AsyncMock(spec=NoopCommunicationService)


@pytest.fixture
def mock_monitoring_service():
    """Mock monitoring service."""
    return MagicMock(spec=NoopMonitoringService)


@pytest.fixture
def sample_ticket():
    """Sample ticket for testing."""
    return Ticket(
        id="ticket-123",
        ticket_number="TKT-123",
        tenant_id="test-tenant",
        title="Test Issue",
        description="Test description",
        status=TicketStatus.OPEN,
        priority=TicketPriority.NORMAL,
        category=TicketCategory.TECHNICAL_SUPPORT,
        customer_email="test@example.com",
        created_at=datetime.now(timezone.utc)
    )


class TestTicketManagerIntegration:
    """Test TicketManager with dependency injection."""

    def test_ticket_manager_default_initialization(self):
        """Test TicketManager initializes with default services."""
        manager = TicketManager()
        
        assert manager.communication_service is not None
        assert manager.monitoring_service is not None
        assert isinstance(manager.communication_service, NoopCommunicationService)
        assert isinstance(manager.monitoring_service, NoopMonitoringService)

    def test_ticket_manager_with_injected_services(
        self, mock_communication_service, mock_monitoring_service
    ):
        """Test TicketManager with injected services."""
        manager = TicketManager(
            communication_service=mock_communication_service,
            monitoring_service=mock_monitoring_service
        )
        
        assert manager.communication_service is mock_communication_service
        assert manager.monitoring_service is mock_monitoring_service

    async def test_create_ticket_triggers_events(
        self, mock_communication_service, mock_monitoring_service
    ):
        """Test create_ticket triggers appropriate events."""
        manager = TicketManager(
            communication_service=mock_communication_service,
            monitoring_service=mock_monitoring_service
        )
        
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        ticket_data = {
            "title": "Test Issue",
            "description": "Test description",
            "priority": TicketPriority.NORMAL,
            "category": TicketCategory.GENERAL_INQUIRY,
            "customer_email": "test@example.com"
        }
        
        # Mock the ticket that would be created
        created_ticket = Ticket(
            id="new-ticket-123",
            ticket_number="TKT-NEW-123",
            tenant_id="test-tenant",
            **ticket_data,
            status=TicketStatus.OPEN,
            created_at=datetime.now(timezone.utc)
        )
        mock_db.refresh.side_effect = lambda t: setattr(t, 'id', created_ticket.id)
        
        result = await manager.create_ticket(
            db=mock_db,
            tenant_id="test-tenant",
            **ticket_data
        )
        
        # Verify monitoring event was recorded
        mock_monitoring_service.record_event.assert_called_once()
        event_call = mock_monitoring_service.record_event.call_args
        assert event_call[1]["event_type"] == "ticket_created"
        assert event_call[1]["service"] == "dotmac-ticketing"
        
        # Verify communication service was called for notification
        mock_communication_service.send_notification.assert_called_once()
        notification_call = mock_communication_service.send_notification.call_args
        assert notification_call[1]["recipient"] == "test@example.com"
        assert "Support Ticket Created" in notification_call[1]["subject"]

    async def test_update_ticket_status_triggers_events(
        self, mock_communication_service, mock_monitoring_service, sample_ticket
    ):
        """Test update_ticket_status triggers appropriate events."""
        manager = TicketManager(
            communication_service=mock_communication_service,
            monitoring_service=mock_monitoring_service
        )
        
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Mock database query to return the ticket
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ticket
        mock_db.execute.return_value = mock_result
        
        await manager.update_ticket_status(
            db=mock_db,
            tenant_id="test-tenant",
            ticket_id="ticket-123",
            new_status=TicketStatus.RESOLVED,
            updated_by_id="admin-123"
        )
        
        # Verify status was updated
        assert sample_ticket.status == TicketStatus.RESOLVED
        
        # Verify monitoring event was recorded
        mock_monitoring_service.record_event.assert_called_once()
        event_call = mock_monitoring_service.record_event.call_args
        assert event_call[1]["event_type"] == "ticket_status_updated"
        
        # Verify notification was sent
        mock_communication_service.send_notification.assert_called_once()

    async def test_assign_ticket_triggers_events(
        self, mock_communication_service, mock_monitoring_service, sample_ticket
    ):
        """Test assign_ticket triggers appropriate events."""
        manager = TicketManager(
            communication_service=mock_communication_service,
            monitoring_service=mock_monitoring_service
        )
        
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Mock database query to return the ticket
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ticket
        mock_db.execute.return_value = mock_result
        
        await manager.assign_ticket(
            db=mock_db,
            tenant_id="test-tenant",
            ticket_id="ticket-123",
            assigned_to_id="agent-123",
            assigned_to_name="Agent Smith",
            assigned_by_id="admin-123"
        )
        
        # Verify assignment was made
        assert sample_ticket.assigned_to_id == "agent-123"
        assert sample_ticket.assigned_to_name == "Agent Smith"
        
        # Verify monitoring event was recorded
        mock_monitoring_service.record_event.assert_called_once()
        event_call = mock_monitoring_service.record_event.call_args
        assert event_call[1]["event_type"] == "ticket_assigned"
        
        # Verify notification was sent
        mock_communication_service.send_notification.assert_called_once()

    async def test_add_comment_triggers_events(
        self, mock_communication_service, mock_monitoring_service, sample_ticket
    ):
        """Test add_comment triggers appropriate events."""
        manager = TicketManager(
            communication_service=mock_communication_service,
            monitoring_service=mock_monitoring_service
        )
        
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock database query to return the ticket
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ticket
        mock_db.execute.return_value = mock_result
        
        await manager.add_comment(
            db=mock_db,
            tenant_id="test-tenant",
            ticket_id="ticket-123",
            content="This is a test comment",
            author_id="user-123",
            author_name="Test User",
            author_type="customer",
            is_internal=False
        )
        
        # Verify monitoring event was recorded
        mock_monitoring_service.record_event.assert_called_once()
        event_call = mock_monitoring_service.record_event.call_args
        assert event_call[1]["event_type"] == "comment_added"
        
        # Verify notification was sent (for non-internal comments)
        mock_communication_service.send_notification.assert_called_once()

    async def test_tenant_isolation_in_queries(self, sample_ticket):
        """Test that all queries include tenant isolation."""
        manager = TicketManager()
        mock_db = AsyncMock()
        
        # Test get_ticket includes tenant filter
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_ticket
        mock_db.execute.return_value = mock_result
        
        await manager.get_ticket(
            db=mock_db,
            tenant_id="test-tenant",
            ticket_id="ticket-123"
        )
        
        # Verify query includes tenant filter
        query_call = mock_db.execute.call_args[0][0]
        query_str = str(query_call)
        assert "tenant_id" in query_str.lower()

    async def test_error_handling_in_event_triggers(
        self, mock_communication_service, sample_ticket
    ):
        """Test error handling when event triggers fail."""
        # Make communication service raise exception
        mock_communication_service.send_notification.side_effect = Exception("Notification failed")
        
        manager = TicketManager(communication_service=mock_communication_service)
        
        # Should not raise exception even if notification fails
        await manager._trigger_ticket_created_events(sample_ticket)


class TestTicketServiceIntegration:
    """Test TicketService with TicketManager integration."""

    def test_ticket_service_initialization(self):
        """Test TicketService initializes with TicketManager."""
        mock_manager = MagicMock()
        service = TicketService(ticket_manager=mock_manager)
        
        assert service.ticket_manager is mock_manager

    def test_ticket_service_default_initialization(self):
        """Test TicketService with default manager."""
        service = TicketService()
        
        assert isinstance(service.ticket_manager, TicketManager)

    async def test_create_customer_ticket_delegates_to_manager(self):
        """Test create_customer_ticket delegates to manager."""
        mock_manager = AsyncMock(spec=TicketManager)
        service = TicketService(ticket_manager=mock_manager)
        
        expected_ticket = Ticket(
            id="new-ticket",
            ticket_number="TKT-NEW",
            tenant_id="test-tenant",
            title="Customer Issue",
            description="Customer description",
            status=TicketStatus.OPEN,
            priority=TicketPriority.NORMAL,
            category=TicketCategory.TECHNICAL_SUPPORT
        )
        mock_manager.create_ticket.return_value = expected_ticket
        
        result = await service.create_customer_ticket(
            db="mock_db",
            tenant_id="test-tenant",
            customer_id="customer-123",
            title="Customer Issue",
            description="Customer description",
            category=TicketCategory.TECHNICAL_SUPPORT,
            priority=TicketPriority.NORMAL
        )
        
        assert result is expected_ticket
        mock_manager.create_ticket.assert_called_once()
        call_args = mock_manager.create_ticket.call_args
        assert call_args[1]["tenant_id"] == "test-tenant"
        assert call_args[1]["title"] == "Customer Issue"

    async def test_create_internal_ticket_delegates_to_manager(self):
        """Test create_internal_ticket delegates to manager."""
        mock_manager = AsyncMock(spec=TicketManager)
        service = TicketService(ticket_manager=mock_manager)
        
        expected_ticket = Ticket(
            id="internal-ticket",
            ticket_number="TKT-INT",
            tenant_id="test-tenant",
            title="Internal Issue",
            description="Internal description",
            status=TicketStatus.OPEN,
            priority=TicketPriority.HIGH,
            category=TicketCategory.TECHNICAL_SUPPORT
        )
        mock_manager.create_ticket.return_value = expected_ticket
        
        result = await service.create_internal_ticket(
            db="mock_db",
            tenant_id="test-tenant",
            created_by_id="admin-123",
            title="Internal Issue",
            description="Internal description",
            category=TicketCategory.TECHNICAL_SUPPORT,
            priority=TicketPriority.HIGH,
            assigned_to_id="tech-456"
        )
        
        assert result is expected_ticket
        mock_manager.create_ticket.assert_called_once()
        call_args = mock_manager.create_ticket.call_args
        assert call_args[1]["internal_ticket"] is True
        assert call_args[1]["assigned_to_id"] == "tech-456"


class TestNotificationIntegration:
    """Test integration with notification system."""

    def test_notification_manager_initialization(self):
        """Test TicketNotificationManager initialization."""
        from dotmac.ticketing.integrations.notifications import TicketNotificationManager
        
        mock_communication_service = MagicMock()
        manager = TicketNotificationManager(communication_service=mock_communication_service)
        
        assert manager.communication_service is mock_communication_service
        assert len(manager.templates) > 0
        assert "ticket_created" in manager.templates
        assert "ticket_assigned" in manager.templates

    async def test_notification_manager_sends_ticket_created(self, sample_ticket):
        """Test notification manager sends ticket created notification."""
        from dotmac.ticketing.integrations.notifications import TicketNotificationManager
        
        mock_communication_service = AsyncMock()
        manager = TicketNotificationManager(communication_service=mock_communication_service)
        
        await manager.notify_ticket_created(sample_ticket)
        
        mock_communication_service.send_notification.assert_called_once()
        call_args = mock_communication_service.send_notification.call_args
        assert call_args[1]["recipient"] == sample_ticket.customer_email
        assert "Support Ticket Created" in call_args[1]["subject"]
        assert call_args[1]["template"] == "ticket_created_email.html"

    async def test_notification_manager_with_no_service(self, sample_ticket, caplog):
        """Test notification manager without communication service."""
        from dotmac.ticketing.integrations.notifications import TicketNotificationManager
        import logging
        
        manager = TicketNotificationManager(communication_service=None)
        
        with caplog.at_level(logging.INFO):
            await manager.notify_ticket_created(sample_ticket)
        
        assert "No communication service configured" in caplog.text

    async def test_notification_manager_handles_errors(self, sample_ticket, caplog):
        """Test notification manager handles communication service errors."""
        from dotmac.ticketing.integrations.notifications import TicketNotificationManager
        import logging
        
        mock_communication_service = AsyncMock()
        mock_communication_service.send_notification.side_effect = Exception("Send failed")
        
        manager = TicketNotificationManager(communication_service=mock_communication_service)
        
        with caplog.at_level(logging.ERROR):
            await manager.notify_ticket_created(sample_ticket)
        
        assert "Failed to send ticket_created notification" in caplog.text


class TestDependencyInjectionPatterns:
    """Test various dependency injection patterns."""

    def test_constructor_injection(self):
        """Test constructor-based dependency injection."""
        mock_comm = MagicMock()
        mock_mon = MagicMock()
        
        manager = TicketManager(
            communication_service=mock_comm,
            monitoring_service=mock_mon
        )
        
        assert manager.communication_service is mock_comm
        assert manager.monitoring_service is mock_mon

    def test_optional_dependencies(self):
        """Test that dependencies are optional with fallbacks."""
        # Should not raise exception with no dependencies
        manager = TicketManager()
        
        assert manager.communication_service is not None
        assert manager.monitoring_service is not None

    def test_service_composition(self):
        """Test service composition with manager."""
        mock_manager = MagicMock()
        service = TicketService(ticket_manager=mock_manager)
        
        assert service.ticket_manager is mock_manager

    async def test_runtime_dependency_availability(self):
        """Test that services work regardless of dependency availability."""
        # Test with real adapters
        from dotmac.ticketing.integrations.adapters import (
            get_communication_service, get_monitoring_service
        )
        
        comm_service = get_communication_service()
        mon_service = get_monitoring_service()
        
        manager = TicketManager(
            communication_service=comm_service,
            monitoring_service=mon_service
        )
        
        # Should initialize without errors
        assert manager.communication_service is not None
        assert manager.monitoring_service is not None