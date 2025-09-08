"""
Integration adapters for optional platform services.
Provides clean abstractions without hard dependencies on src modules.
"""

import logging
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


class CommunicationServiceProtocol(Protocol):
    """Protocol for communication service implementations."""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template: str,
        context: dict[str, Any],
        channel: str = "email",
    ) -> bool:
        """Send a notification."""
        ...


class MonitoringServiceProtocol(Protocol):
    """Protocol for monitoring service implementations."""
    
    def record_event(
        self,
        event_type: str,
        service: str,
        details: dict[str, Any],
    ) -> None:
        """Record an event."""
        ...


class NoopCommunicationService:
    """No-op communication service for testing and fallback."""
    
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        template: str,
        context: dict[str, Any],
        channel: str = "email",
    ) -> bool:
        """Log notification instead of sending."""
        logger.info(
            f"NOTIFICATION: {channel} to {recipient} - {subject} "
            f"(template: {template}, ticket: {context.get('ticket_number', 'N/A')})"
        )
        return True


class NoopMonitoringService:
    """No-op monitoring service for testing and fallback."""
    
    def record_event(
        self,
        event_type: str,
        service: str,
        details: dict[str, Any],
    ) -> None:
        """Log event instead of recording."""
        logger.info(
            f"EVENT: {event_type} in {service} - "
            f"ticket: {details.get('ticket_number', 'N/A')}"
        )


# Optional platform integrations - graceful fallbacks if not available
def get_communication_service() -> CommunicationServiceProtocol:
    """Get communication service with fallback."""
    try:
        # Use platform facade for notifications/metrics
        from dotmac.platform.monitoring.integrations import NotificationService
        return NotificationService()
    except ImportError:
        logger.debug("Platform notification service not available, using noop")
        return NoopCommunicationService()


def get_monitoring_service() -> MonitoringServiceProtocol:
    """Get monitoring service with fallback."""
    try:
        # Use platform facade for monitoring integrations
        from dotmac.platform.monitoring.integrations import MetricsService
        return MetricsService(
            service_name="dotmac-ticketing",
            tenant_id="default"  # This should be injected in real usage
        )
    except ImportError:
        logger.debug("Platform monitoring service not available, using noop")
        return NoopMonitoringService()


def get_benchmark_manager() -> Optional[Any]:
    """Get benchmark manager for metrics storage (optional)."""
    try:
        # Optional benchmark integration
        from dotmac.platform.monitoring.benchmarks import BenchmarkManager
        return BenchmarkManager(service_name="dotmac-ticketing")
    except ImportError:
        logger.debug("Platform benchmark manager not available")
        return None