"""
DotMac Unified Notification Service - DRY Implementation

This is a thin orchestration layer that leverages existing DotMac infrastructure:
- Plugin system for channel providers
- Secrets management for credentials
- Cache system for templates and rate limiting
- Event system for delivery tracking
- Omnichannel service for actual message delivery

No duplicate implementations - pure orchestration using existing services.
"""

from .models import (
    BulkNotificationRequest,
    BulkNotificationResponse,
    NotificationPriority,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
    NotificationTemplate,
    NotificationType,
)
from .service import UnifiedNotificationService

__all__ = [
    "UnifiedNotificationService",
    "NotificationRequest",
    "NotificationResponse",
    "BulkNotificationRequest",
    "BulkNotificationResponse",
    "NotificationTemplate",
    "NotificationStatus",
    "NotificationPriority",
    "NotificationType",
]
