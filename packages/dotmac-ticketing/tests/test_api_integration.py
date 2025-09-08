"""
Integration tests for API routes with wired dependencies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from dotmac.ticketing.api.routes import ticketing_router
from dotmac.ticketing.core.models import Ticket, TicketPriority, TicketStatus, TicketCategory
from dotmac.ticketing.core.manager import TicketManager
from dotmac.ticketing.core.service import TicketService


@pytest.fixture
def app():
    """Create FastAPI app with ticketing router."""
    app = FastAPI()
    app.include_router(ticketing_router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_ticket_manager():
    """Mock ticket manager."""
    manager = AsyncMock(spec=TicketManager)
    return manager


@pytest.fixture
def mock_ticket_service():
    """Mock ticket service."""
    service = AsyncMock(spec=TicketService)
    return service


@pytest.fixture
def sample_ticket():
    """Sample ticket for tests."""
    return Ticket(
        id="ticket-123",
        ticket_number="TKT-12345678-9999",
        tenant_id="test-tenant",
        title="Test Issue",
        description="Test description",
        status=TicketStatus.OPEN,
        priority=TicketPriority.NORMAL,
        category=TicketCategory.TECHNICAL_SUPPORT,
        customer_email="test@example.com",
        customer_name="Test User",
    )


class TestAPIRouteIntegration:
    """Test API routes with dependency injection."""

    @patch('dotmac.ticketing.api.routes.get_ticket_manager')
    @patch('dotmac.ticketing.api.routes.get_db_session')
    @patch('dotmac.ticketing.api.routes.get_paginated_deps')
    async def test_list_tickets_with_real_db(
        self, mock_deps, mock_db, mock_manager, client, mock_ticket_manager, sample_ticket
    ):
        """Test list tickets endpoint with real database session."""
        # Setup mocks
        mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_manager.return_value = mock_ticket_manager
        
        # Mock pagination dependencies
        mock_pagination = MagicMock()
        mock_pagination.pagination.page = 1
        mock_pagination.pagination.size = 50
        mock_pagination.tenant_id = "test-tenant"
        mock_deps.return_value = mock_pagination
        
        # Mock manager response
        mock_ticket_manager.list_tickets.return_value = ([sample_ticket], 1)
        
        response = client.get("/tickets/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["data"]) == 1
        assert data["data"][0]["ticket_number"] == "TKT-12345678-9999"
        
        # Verify manager was called with correct parameters
        mock_ticket_manager.list_tickets.assert_called_once()
        call_args = mock_ticket_manager.list_tickets.call_args
        assert call_args[1]["tenant_id"] == "test-tenant"
        assert call_args[1]["page"] == 1
        assert call_args[1]["page_size"] == 50

    @patch('dotmac.ticketing.api.routes.get_db_session')
    async def test_list_tickets_fallback_without_db(self, mock_db, client):
        """Test list tickets falls back to mock data when no DB."""
        # Mock no database session
        mock_db.return_value.__aenter__ = AsyncMock(return_value=None)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        response = client.get("/tickets/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 1
        assert data["data"][0]["ticket_number"] == "TKT-001"

    @patch('dotmac.ticketing.api.routes.get_ticket_service')
    @patch('dotmac.ticketing.api.routes.get_db_session')
    @patch('dotmac.ticketing.api.routes.get_standard_deps')
    async def test_create_ticket_with_service(
        self, mock_deps, mock_db, mock_service, client, mock_ticket_service, sample_ticket
    ):
        """Test create ticket endpoint with real service."""
        # Setup mocks
        mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_service.return_value = mock_ticket_service
        
        # Mock standard dependencies
        mock_standard_deps = MagicMock()
        mock_standard_deps.tenant_id = "test-tenant"
        mock_standard_deps.user_id = "test-user"
        mock_deps.return_value = mock_standard_deps
        
        # Mock service response
        mock_ticket_service.create_customer_ticket.return_value = sample_ticket
        
        ticket_data = {
            "title": "Test Issue",
            "description": "Test description",
            "priority": "normal",
            "category": "general",
            "customer_email": "test@example.com",
            "customer_name": "Test User",
            "tags": ["test", "api"]
        }
        
        response = client.post("/tickets/", json=ticket_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Issue"
        assert data["ticket_number"] == "TKT-12345678-9999"
        assert data["message"] == "Ticket created successfully"
        
        # Verify service was called correctly
        mock_ticket_service.create_customer_ticket.assert_called_once()
        call_args = mock_ticket_service.create_customer_ticket.call_args
        assert call_args[1]["tenant_id"] == "test-tenant"
        assert call_args[1]["customer_id"] == "test-user"
        assert call_args[1]["title"] == "Test Issue"

    @patch('dotmac.ticketing.api.routes.get_ticket_manager')
    @patch('dotmac.ticketing.api.routes.get_db_session')
    @patch('dotmac.ticketing.api.routes.get_standard_deps')
    async def test_get_ticket_with_manager(
        self, mock_deps, mock_db, mock_manager, client, mock_ticket_manager, sample_ticket
    ):
        """Test get ticket endpoint with real manager."""
        # Setup mocks
        mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_manager.return_value = mock_ticket_manager
        
        # Mock standard dependencies
        mock_standard_deps = MagicMock()
        mock_standard_deps.tenant_id = "test-tenant"
        mock_deps.return_value = mock_standard_deps
        
        # Mock manager response
        mock_ticket_manager.get_ticket.return_value = sample_ticket
        
        response = client.get("/tickets/ticket-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "ticket-123"
        assert data["ticket_number"] == "TKT-12345678-9999"
        
        # Verify manager was called correctly
        mock_ticket_manager.get_ticket.assert_called_once_with(
            db="mock_db_session",
            tenant_id="test-tenant",
            ticket_id="ticket-123"
        )

    async def test_get_ticket_not_found(self, client):
        """Test get ticket returns 404 when ticket not found."""
        with patch('dotmac.ticketing.api.routes.get_ticket_manager') as mock_manager:
            with patch('dotmac.ticketing.api.routes.get_db_session') as mock_db:
                # Setup mocks
                mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
                mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_ticket_manager = AsyncMock()
                mock_ticket_manager.get_ticket.return_value = None
                mock_manager.return_value = mock_ticket_manager
                
                response = client.get("/tickets/nonexistent")
                
                assert response.status_code == 404
                assert "Ticket not found" in response.json()["detail"]

    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/tickets/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "total_tickets" in data
        assert "open_tickets" in data

    async def test_create_ticket_validation_errors(self, client):
        """Test create ticket with validation errors."""
        # Missing required fields
        response = client.post("/tickets/", json={})
        assert response.status_code == 422
        
        # Invalid priority
        invalid_data = {
            "title": "Test",
            "description": "Test",
            "priority": "invalid-priority"
        }
        response = client.post("/tickets/", json=invalid_data)
        assert response.status_code == 422

    async def test_list_tickets_with_filters(self, client):
        """Test list tickets with query filters."""
        with patch('dotmac.ticketing.api.routes.get_ticket_manager') as mock_manager:
            with patch('dotmac.ticketing.api.routes.get_db_session') as mock_db:
                # Setup mocks
                mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
                mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
                
                mock_ticket_manager = AsyncMock()
                mock_ticket_manager.list_tickets.return_value = ([], 0)
                mock_manager.return_value = mock_ticket_manager
                
                response = client.get(
                    "/tickets/?status=open&priority=high&search=network&customer_id=123"
                )
                
                assert response.status_code == 200
                
                # Verify filters were passed correctly
                call_args = mock_ticket_manager.list_tickets.call_args
                filters = call_args[1]["filters"]
                assert filters["status"] == "open"
                assert filters["priority"] == "high"
                assert filters["search"] == "network"
                assert filters["customer_id"] == "123"


class TestDependencyInjectionIntegration:
    """Test dependency injection works correctly."""

    def test_get_ticket_manager_returns_instance(self):
        """Test get_ticket_manager dependency returns instance."""
        from dotmac.ticketing.api.routes import get_ticket_manager
        
        manager = get_ticket_manager()
        assert isinstance(manager, TicketManager)

    def test_get_ticket_service_returns_instance(self):
        """Test get_ticket_service dependency returns instance."""
        from dotmac.ticketing.api.routes import get_ticket_service
        
        service = get_ticket_service()
        assert isinstance(service, TicketService)

    @patch('dotmac.ticketing.api.routes._ticket_manager')
    def test_get_ticket_manager_uses_injected_instance(self, mock_manager):
        """Test get_ticket_manager uses injected instance if available."""
        from dotmac.ticketing.api.routes import get_ticket_manager
        
        # Set up injected manager
        injected_manager = MagicMock()
        mock_manager.__bool__ = MagicMock(return_value=True)
        mock_manager.__eq__ = MagicMock(return_value=False)
        
        with patch('dotmac.ticketing.api.routes._ticket_manager', injected_manager):
            result = get_ticket_manager()
            assert result is injected_manager

    async def test_get_db_session_with_factory(self):
        """Test get_db_session uses session factory if available."""
        from dotmac.ticketing.api.routes import get_db_session
        
        # Mock session factory
        mock_session = AsyncMock()
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
        
        with patch('dotmac.ticketing.api.routes._db_session_factory', mock_factory):
            async for session in get_db_session():
                assert session is mock_session
                break


class TestErrorHandling:
    """Test error handling in API routes."""

    @patch('dotmac.ticketing.api.routes.get_ticket_manager')
    @patch('dotmac.ticketing.api.routes.get_db_session')
    async def test_list_tickets_handles_manager_exception(self, mock_db, mock_manager, client):
        """Test list tickets handles manager exceptions."""
        # Setup mocks to raise exception
        mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_ticket_manager = AsyncMock()
        mock_ticket_manager.list_tickets.side_effect = Exception("Database error")
        mock_manager.return_value = mock_ticket_manager
        
        response = client.get("/tickets/")
        
        assert response.status_code == 500
        assert "Error listing tickets" in response.json()["detail"]

    @patch('dotmac.ticketing.api.routes.get_ticket_service')
    @patch('dotmac.ticketing.api.routes.get_db_session')
    async def test_create_ticket_handles_service_exception(self, mock_db, mock_service, client):
        """Test create ticket handles service exceptions."""
        # Setup mocks to raise exception
        mock_db.return_value.__aenter__ = AsyncMock(return_value="mock_db_session")
        mock_db.return_value.__aexit__ = AsyncMock(return_value=None)
        
        mock_ticket_service = AsyncMock()
        mock_ticket_service.create_customer_ticket.side_effect = Exception("Service error")
        mock_service.return_value = mock_ticket_service
        
        ticket_data = {
            "title": "Test Issue",
            "description": "Test description"
        }
        
        response = client.post("/tickets/", json=ticket_data)
        
        assert response.status_code == 400
        assert "Error creating ticket" in response.json()["detail"]