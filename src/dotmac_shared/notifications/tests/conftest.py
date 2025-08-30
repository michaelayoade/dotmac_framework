"""
Test fixtures and configuration for notification service tests.

Provides common fixtures, mocks, and test utilities for comprehensive testing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from dotmac_shared.notifications.models import (
    BulkNotificationRequest,
    BulkNotificationResponse,
    NotificationPriority,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)


@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_secrets_manager():
    """Mock secrets manager for testing"""
    mock = Mock()
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    mock.get_secret = AsyncMock(return_value="test-secret-value")
    mock.set_secret = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_cache_service():
    """Mock cache service for testing"""
    mock = Mock()
    mock.initialize = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.health_check = AsyncMock(return_value={"status": "healthy"})
    return mock


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher for testing"""
    mock = Mock()
    mock.publish = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_omnichannel_plugin_manager():
    """Mock omnichannel plugin manager"""
    mock = Mock()
    mock.initialize = AsyncMock(return_value=True)
    mock.shutdown = AsyncMock(return_value=True)
    mock.get_active_plugins = AsyncMock(return_value=[])
    mock.health_check = AsyncMock(return_value={"status": "healthy", "plugins": 0})
    return mock


@pytest.fixture
def mock_channel_orchestrator():
    """Mock channel orchestrator for message delivery"""
    mock = Mock()
    mock.initialize = AsyncMock(return_value=True)
    mock.shutdown = AsyncMock(return_value=True)
    mock.send_message = AsyncMock()
    return mock


@pytest.fixture
def sample_notification_request():
    """Sample notification request for testing"""
    return NotificationRequest(
        tenant_id="test-tenant-123",
        notification_type=NotificationType.SYSTEM_ALERT,
        recipients=["test@example.com"],
        channels=["email"],
        subject="Test Notification",
        body="This is a test notification for unit testing.",
        priority=NotificationPriority.NORMAL,
        metadata={"test": True, "source": "unit_test"},
    )


@pytest.fixture
def sample_notification_response():
    """Sample notification response for testing"""
    return NotificationResponse(
        success=True,
        notification_id=str(uuid.uuid4()),
        status=NotificationStatus.SENT,
        message="Notification sent successfully",
        channel_results={"email": {"status": "sent", "message_id": "test-123"}},
        metadata={"delivery_time": datetime.utcnow().isoformat()},
    )


@pytest.fixture
def sample_bulk_request():
    """Sample bulk notification request"""
    notifications = [
        NotificationRequest(
            tenant_id="test-tenant",
            notification_type=NotificationType.MARKETING,
            recipients=[f"user{i}@example.com"],
            channels=["email"],
            subject=f"Bulk Notification {i}",
            body=f"This is bulk message {i}",
            priority=NotificationPriority.LOW,
        )
        for i in range(5)
    ]

    return BulkNotificationRequest(
        notifications=notifications, batch_size=2, max_concurrent=3
    )


@pytest.fixture
def sample_notification_template():
    """Sample notification template"""
    return NotificationTemplate(
        template_id="test-template-1",
        name="Test Alert Template",
        subject_template="Alert: {{ alert_type }}",
        body_template="Alert detected: {{ message }}\nSeverity: {{ severity }}",
        channels=["email", "sms"],
        template_data_schema={
            "alert_type": {"type": "string", "required": True},
            "message": {"type": "string", "required": True},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        },
    )


@pytest.fixture
def mock_successful_omnichannel_response():
    """Mock successful omnichannel delivery response"""
    mock_response = Mock()
    mock_response.success = True
    mock_response.message_id = "omnichannel-123"
    mock_response.status = "sent"
    mock_response.message = "Message sent successfully"
    mock_response.channel_results = {
        "email": {"status": "sent", "provider": "sendgrid", "message_id": "sg-123"}
    }
    return mock_response


@pytest.fixture
def mock_failed_omnichannel_response():
    """Mock failed omnichannel delivery response"""
    mock_response = Mock()
    mock_response.success = False
    mock_response.message_id = None
    mock_response.status = "failed"
    mock_response.message = "Delivery failed: Invalid recipient"
    mock_response.channel_results = {
        "email": {"status": "failed", "error": "Invalid email address"}
    }
    return mock_response


@pytest.fixture
def mock_plugin_channels():
    """Mock available plugin channels"""
    return ["email", "sms", "slack", "webhook"]


# Test data generators


@pytest.fixture
def notification_request_factory():
    """Factory for creating test notification requests"""

    def create_request(
        tenant_id: str = "test-tenant",
        notification_type: NotificationType = NotificationType.SYSTEM_ALERT,
        recipients: List[str] = None,
        channels: List[str] = None,
        subject: str = "Test Subject",
        body: str = "Test body content",
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Dict[str, Any] = None,
    ) -> NotificationRequest:
        return NotificationRequest(
            tenant_id=tenant_id,
            notification_type=notification_type,
            recipients=recipients or ["test@example.com"],
            channels=channels or ["email"],
            subject=subject,
            body=body,
            priority=priority,
            metadata=metadata or {},
        )

    return create_request


@pytest.fixture
def notification_response_factory():
    """Factory for creating test notification responses"""

    def create_response(
        success: bool = True,
        notification_id: str = None,
        status: NotificationStatus = NotificationStatus.SENT,
        message: str = "Success",
        channel_results: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
    ) -> NotificationResponse:
        return NotificationResponse(
            success=success,
            notification_id=notification_id or str(uuid.uuid4()),
            status=status,
            message=message,
            channel_results=channel_results or {},
            metadata=metadata or {},
        )

    return create_response


# Async test helpers


@pytest.fixture
def async_test_timeout():
    """Standard timeout for async tests"""
    return 10.0


@pytest.fixture
def mock_async_context_manager():
    """Helper for mocking async context managers"""

    class AsyncContextManagerMock:
        """AsyncContextManagerMock implementation."""

        def __init__(self, return_value=None):
            self.return_value = return_value

        async def __aenter__(self):
            return self.return_value

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    return AsyncContextManagerMock


# Error simulation fixtures


@pytest.fixture
def connection_error_mock():
    """Mock that raises connection errors"""

    def create_error_mock(error_message="Connection failed"):
        mock = AsyncMock()
        mock.side_effect = ConnectionError(error_message)
        return mock

    return create_error_mock


@pytest.fixture
def timeout_error_mock():
    """Mock that raises timeout errors"""

    def create_timeout_mock(error_message="Operation timed out"):
        mock = AsyncMock()
        mock.side_effect = asyncio.TimeoutError(error_message)
        return mock

    return create_timeout_mock
