"""
Basic usage example for the DotMac Services Framework.

This demonstrates how to create and use the service registry with common business services.
"""

import asyncio
import logging
from typing import Any

from dotmac_shared.application.config import DeploymentContext, DeploymentMode
from dotmac_shared.services_framework import (
    DeploymentAwareServiceFactory,
    HealthMonitor,
    HealthMonitorConfig,
    ServiceDiscovery,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_service_registry_example():
    """Basic example of creating and using a service registry."""
    logger.info("=== Basic Service Registry Example ===")

    # Create deployment context
    deployment_context = DeploymentContext(
        mode=DeploymentMode.DEVELOPMENT,
        platform="example_platform",
        environment="development",
    )

    # Create service factory
    factory = DeploymentAwareServiceFactory(deployment_context)

    # Create service registry with standard business services
    registry = await factory.create_service_registry()

    # Initialize all services
    logger.info("Initializing services...")
    initialization_results = await registry.initialize_all()

    # Print initialization results
    for service_name, success in initialization_results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {service_name}: {status}")

    # Check overall registry status
    registry_status = registry.get_registry_status()
    logger.info(f"Registry Status: {registry_status['all_ready']}")
    logger.info(
        f"Ready Services: {registry_status['ready_services']}/{registry_status['total_services']}"
    )

    # Use individual services if they're ready
    if registry.auth and registry.auth.is_ready():
        logger.info("Creating JWT token...")
        token = registry.auth.create_token(
            payload={"user": "demo_user", "role": "admin"}, user_id="demo_user"
        )
        logger.info(f"Token created: {token[:50]}...")

        # Verify the token
        payload = registry.auth.verify_token(token)
        logger.info(f"Token verified. Payload: {payload}")

    if registry.payment and registry.payment.is_ready():
        from decimal import Decimal

        logger.info("Creating payment intent...")
        payment_intent = await registry.payment.create_payment_intent(
            amount=Decimal("29.99"), currency="USD", customer_id="demo_customer"
        )
        logger.info(f"Payment intent created: {payment_intent['id']}")

    if registry.notification and registry.notification.is_ready():
        logger.info("Sending test email...")
        try:
            notification = await registry.notification.send_email(
                to_email="test@example.com",
                subject="Test from Services Framework",
                content="This is a test email from the DotMac Services Framework.",
            )
            logger.info(f"Email notification sent: {notification['id']}")
        except Exception as e:
            logger.info(f"Email sending simulated (no real provider): {e}")

    if registry.analytics and registry.analytics.is_ready():
        logger.info("Recording analytics metrics...")
        await registry.analytics.record_metric(
            "demo_metric", 42.0, {"source": "example"}
        )
        await registry.analytics.record_event("demo_event", {"action": "test"})
        logger.info("Analytics metrics recorded")

    # Perform health checks
    logger.info("Performing health checks...")
    health_results = await registry.health_check_all()

    for service_name, health in health_results.items():
        status_emoji = "🟢" if health.status.value == "ready" else "🔴"
        logger.info(f"  {status_emoji} {service_name}: {health.message}")

    # Shutdown services
    logger.info("Shutting down services...")
    shutdown_results = await registry.shutdown_all()

    for service_name, success in shutdown_results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {service_name} shutdown: {status}")


async def service_discovery_example():
    """Example of using service discovery."""
    logger.info("\n=== Service Discovery Example ===")

    # Create a basic registry with some services
    factory = DeploymentAwareServiceFactory()
    registry = await factory.create_service_registry()
    await registry.initialize_all()

    # Create service discovery
    discovery = ServiceDiscovery(registry)

    # Discover all services
    discovered_services = await discovery.discover_services()

    logger.info(f"Discovered {len(discovered_services)} services:")
    for name, info in discovered_services.items():
        logger.info(f"  📋 {name}: {info['status']} (ready: {info['ready']})")

    # Find services by criteria
    ready_services = discovery.find_ready_services()
    logger.info(f"Ready services: {ready_services}")

    high_priority_services = discovery.find_services_with_priority(min_priority=80)
    logger.info(f"High priority services (≥80): {high_priority_services}")

    # Check service connectivity
    connectivity_results = await discovery.check_all_services_connectivity()

    logger.info("Service connectivity check:")
    for service_name, result in connectivity_results.items():
        if result.get("available"):
            response_time = result.get("response_time_ms", 0)
            logger.info(f"  🔗 {service_name}: OK ({response_time}ms)")
        else:
            logger.info(f"  ❌ {service_name}: {result.get('error', 'Unknown error')}")

    # Get service topology
    topology = discovery.get_service_topology()
    logger.info(
        f"Service topology: {topology['total_services']} total, {topology['ready_services']} ready"
    )

    # Cleanup
    await registry.shutdown_all()


async def health_monitoring_example():
    """Example of using health monitoring."""
    logger.info("\n=== Health Monitoring Example ===")

    # Create registry
    factory = DeploymentAwareServiceFactory()
    registry = await factory.create_service_registry()
    await registry.initialize_all()

    # Alert callback function
    def handle_alert(alert):
        """handle_alert service method."""
        severity_emoji = {"low": "🔵", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        emoji = severity_emoji.get(alert.severity, "⚪")
        logger.info(f"  {emoji} ALERT [{alert.severity.upper()}]: {alert.message}")

    # Create health monitor with custom config
    monitor_config = HealthMonitorConfig(
        check_interval_seconds=5,  # Check every 5 seconds for demo
        enable_status_change_alerts=True,
        enable_health_degradation_alerts=True,
        enable_recovery_alerts=True,
    )

    monitor = HealthMonitor(registry, monitor_config, handle_alert)

    # Start monitoring
    await monitor.start_monitoring()
    logger.info("Health monitoring started...")

    # Let it monitor for a bit
    await asyncio.sleep(15)

    # Get monitoring stats
    stats = monitor.get_monitoring_stats()
    logger.info(
        f"Monitoring stats: {stats['statistics']['total_health_records']} records collected"
    )

    # Get overall health status
    overall_health = monitor.get_overall_health_status()
    logger.info(f"Overall health: {overall_health['health_percentage']}% healthy")

    # Get recent alerts
    recent_alerts = monitor.get_recent_alerts(limit=5)
    if recent_alerts:
        logger.info(f"Recent alerts: {len(recent_alerts)}")
        for alert in recent_alerts:
            logger.info(f"  - {alert.alert_type}: {alert.message}")
    else:
        logger.info("No recent alerts")

    # Stop monitoring and cleanup
    await monitor.stop_monitoring()
    await registry.shutdown_all()


async def custom_service_example():
    """Example of adding custom services to the registry."""
    logger.info("\n=== Custom Service Example ===")

    from dotmac_shared.services_framework import (
        BaseService,
        ServiceHealth,
        ServiceStatus,
    )

    class CustomBusinessService(BaseService):
        """Example custom business service."""

        def __init__(self):
            """__init__ service method."""
            super().__init__("custom_business", {"feature_enabled": True})
            self.priority = 60
            self.data_processed = 0

        async def initialize(self) -> bool:
            await self._set_status(
                ServiceStatus.INITIALIZING, "Starting custom business service"
            )

            # Simulate initialization work
            await asyncio.sleep(0.1)

            await self._set_status(ServiceStatus.READY, "Custom business service ready")
            return True

        async def shutdown(self) -> bool:
            await self._set_status(
                ServiceStatus.SHUTTING_DOWN, "Shutting down custom service"
            )
            await self._set_status(ServiceStatus.SHUTDOWN, "Custom service stopped")
            return True

        async def health_check(self) -> ServiceHealth:
            return ServiceHealth(
                status=ServiceStatus.READY,
                message=f"Custom service healthy, processed {self.data_processed} items",
                details={
                    "items_processed": self.data_processed,
                    "feature_enabled": True,
                },
            )

        async def process_data(self, data: Any) -> dict[str, Any]:
            """Custom business logic."""
            self.data_processed += 1
            return {
                "processed": True,
                "data": data,
                "timestamp": asyncio.get_event_loop().time(),
                "total_processed": self.data_processed,
            }

    # Create registry with standard services
    factory = DeploymentAwareServiceFactory()

    # Create custom services dictionary
    custom_service = CustomBusinessService()
    custom_services = {"custom_business": custom_service}

    # Create registry with additional custom services
    registry = await factory.create_service_registry(
        additional_services=custom_services
    )

    # Initialize all services (including custom)
    await registry.initialize_all()

    # Use the custom service
    if registry.has_service("custom_business"):
        custom_svc = registry.get_service("custom_business")

        logger.info("Using custom business service...")
        result1 = await custom_svc.process_data({"item": "test1", "value": 100})
        await custom_svc.process_data({"item": "test2", "value": 200})

        logger.info(f"Processed data: {result1['total_processed']} total items")

        # Check health
        health = await custom_svc.health_check()
        logger.info(f"Custom service health: {health.message}")

    # Cleanup
    await registry.shutdown_all()


async def main():
    """Run all examples."""
    try:
        await basic_service_registry_example()
        await service_discovery_example()
        await health_monitoring_example()
        await custom_service_example()

        logger.info("\n🎉 All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
