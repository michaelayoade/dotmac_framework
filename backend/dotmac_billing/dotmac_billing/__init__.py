"""
DotMac Billing - Billing services and financial operations for ISP platform.

This package provides billing event integration, metrics collection,
notification services, and database migration management for the
DotMac ISP platform.

Note: This is a specialized service module with limited SDK exposure.
Billing operations are accessed via event integration and service APIs.
"""

__version__ = "1.0.0"
__author__ = "DotMac Team"
__email__ = "support@dotmac.com"

# Core components
from .core.events import BillingEvent, EventType, get_event_manager
from .core.metrics import BillingMetrics, get_billing_metrics
from .core.migrations import MigrationManager, get_migration_manager
from .services.notifications import NotificationService, get_notification_service

__all__ = [
    # Event management
    "get_event_manager",
    "BillingEvent",
    "EventType",
    # Metrics
    "get_billing_metrics",
    "BillingMetrics",
    # Migration management
    "get_migration_manager",
    "MigrationManager",
    # Notifications
    "get_notification_service",
    "NotificationService",
]
