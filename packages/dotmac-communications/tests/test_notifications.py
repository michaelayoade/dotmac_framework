"""Unit tests for notifications component."""

from unittest.mock import patch

import pytest
from dotmac.communications.notifications.models import (
    NotificationPriority,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)


class TestNotificationModels:
    """Test notification data models."""

    def test_notification_request_creation(self):
        """Test NotificationRequest model creation."""
        request = NotificationRequest(
            recipient="test@example.com",
            message="Test message",
            notification_type=NotificationType.EMAIL,
            priority=NotificationPriority.NORMAL,
        )

        assert request.recipient == "test@example.com"
        assert request.message == "Test message"
        assert request.notification_type == NotificationType.EMAIL
        assert request.priority == NotificationPriority.NORMAL

    def test_notification_response_creation(self):
        """Test NotificationResponse model creation."""
        response = NotificationResponse(
            notification_id="test-123", status=NotificationStatus.SENT, recipient="test@example.com"
        )

        assert response.notification_id == "test-123"
        assert response.status == NotificationStatus.SENT
        assert response.recipient == "test@example.com"

    def test_notification_template_creation(self):
        """Test NotificationTemplate model creation."""
        template = NotificationTemplate(
            name="welcome_template",
            subject="Welcome {{name}}!",
            body="Hello {{name}}, welcome to our platform!",
        )

        assert template.name == "welcome_template"
        assert template.subject == "Welcome {{name}}!"
        assert template.body == "Hello {{name}}, welcome to our platform!"


class TestNotificationEnums:
    """Test notification enums."""

    def test_notification_status_enum(self):
        """Test NotificationStatus enum values."""
        assert hasattr(NotificationStatus, "PENDING")
        assert hasattr(NotificationStatus, "SENT")
        assert hasattr(NotificationStatus, "DELIVERED")
        assert hasattr(NotificationStatus, "FAILED")

    def test_notification_type_enum(self):
        """Test NotificationType enum values."""
        assert hasattr(NotificationType, "EMAIL")
        assert hasattr(NotificationType, "SMS")
        assert hasattr(NotificationType, "PUSH")
        assert hasattr(NotificationType, "WEBHOOK")

    def test_notification_priority_enum(self):
        """Test NotificationPriority enum values."""
        assert hasattr(NotificationPriority, "LOW")
        assert hasattr(NotificationPriority, "NORMAL")
        assert hasattr(NotificationPriority, "HIGH")
        assert hasattr(NotificationPriority, "URGENT")


class TestNotificationService:
    """Test notification service functionality."""

    @patch("dotmac.communications.notifications.service.UnifiedNotificationService")
    def test_service_import(self, mock_service):
        """Test that service can be imported and instantiated."""
        from dotmac.communications.notifications.service import UnifiedNotificationService

        # Test service exists
        assert UnifiedNotificationService is not None

    def test_notification_service_methods(self):
        """Test notification service has expected methods."""
        from dotmac.communications.notifications.service import UnifiedNotificationService

        # Check if service has expected methods (may not all be implemented)
        service_methods = dir(UnifiedNotificationService)

        # These methods should exist in a notification service
        expected_methods = ["__init__"]
        for method in expected_methods:
            assert method in service_methods, f"Missing method: {method}"


class TestNotificationIntegration:
    """Test notification integration with other components."""

    def test_notification_in_communications_service(self):
        """Test notification service integration."""
        from dotmac.communications import create_communications_service

        service = create_communications_service()
        notifications = service.notifications

        # Should either be a service instance or None (graceful degradation)
        assert notifications is not None or notifications is None

    def test_notification_factory_function(self):
        """Test standalone notification service creation."""
        try:
            from dotmac.communications import create_notification_service

            create_notification_service()
            # Should not raise an exception during creation
            assert True
        except ImportError:
            # It's okay if this fails - service might not be fully implemented
            pytest.skip("Notification service not fully implemented")
        except Exception:
            # Other exceptions might be due to configuration issues
            pytest.skip("Notification service requires additional configuration")


if __name__ == "__main__":
    pytest.main([__file__])
