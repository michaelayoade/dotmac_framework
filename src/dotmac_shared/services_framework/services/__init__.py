"""
Business service implementations.
"""

# Notification service consolidated to dotmac_shared.notifications.core
from .analytics_service import (
    AnalyticsService,
    AnalyticsServiceConfig,
    create_analytics_service,
)
from .auth_service import AuthService, AuthServiceConfig, create_auth_service
from .payment_service import (
    PaymentService,
    PaymentServiceConfig,
    create_payment_service,
)

__all__ = [
    "AuthService",
    "AuthServiceConfig",
    "PaymentService",
    "PaymentServiceConfig",
    # "NotificationService",  # Consolidated to dotmac_shared.notifications.core
    # "NotificationServiceConfig",  # Consolidated to dotmac_shared.notifications.core
    "AnalyticsService",
    "AnalyticsServiceConfig",
    "create_auth_service",
    "create_payment_service",
    # "create_notification_service",  # Consolidated to dotmac_shared.notifications.core
    "create_analytics_service",
]
