"""
Service factory for creating deployment-aware business services.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ...application.config import DeploymentContext, DeploymentMode

# Notification service consolidated to dotmac_shared.notifications
# from ..services.notification_service import create_notification_service, NotificationServiceConfig
from ..services.analytics_service import (
    AnalyticsServiceConfig,
    create_analytics_service,
)
from ..services.auth_service import AuthServiceConfig, create_auth_service
from ..services.payment_service import PaymentServiceConfig, create_payment_service
from .registry import ServiceConfig, ServiceRegistry

logger = logging.getLogger(__name__)


@dataclass
class ServiceCreationResult:
    """Result of service creation."""

    success: bool
    service_name: str
    error_message: Optional[str] = None
    service: Optional[object] = None


class ServiceFactory:
    """Factory for creating business services with configuration."""

    @staticmethod
    def create_service_config(
        deployment_context: Optional[DeploymentContext] = None,
    ) -> ServiceConfig:
        """Create service configuration based on deployment context and environment."""

        # Base configuration from environment
        config = ServiceConfig(
            # Auth configuration
            auth_enabled=os.getenv("AUTH_ENABLED", "true").lower() == "true",
            auth_jwt_secret=os.getenv("JWT_SECRET"),
            auth_issuer=os.getenv("AUTH_ISSUER", "dotmac"),
            auth_expiry_hours=int(os.getenv("AUTH_EXPIRY_HOURS", "24")),
            # Payment configuration
            payment_enabled=os.getenv("PAYMENT_ENABLED", "true").lower() == "true",
            payment_provider=os.getenv("PAYMENT_PROVIDER", "stripe"),
            payment_api_key=os.getenv("PAYMENT_API_KEY"),
            payment_webhook_secret=os.getenv("PAYMENT_WEBHOOK_SECRET"),
            # Notification configuration
            notification_enabled=os.getenv("NOTIFICATION_ENABLED", "true").lower()
            == "true",
            notification_providers=os.getenv(
                "NOTIFICATION_PROVIDERS", "email,sms"
            ).split(","),
            email_provider=os.getenv("EMAIL_PROVIDER", "sendgrid"),
            sms_provider=os.getenv("SMS_PROVIDER", "twilio"),
            # Analytics configuration
            analytics_enabled=os.getenv("ANALYTICS_ENABLED", "true").lower() == "true",
            analytics_provider=os.getenv("ANALYTICS_PROVIDER", "prometheus"),
            analytics_endpoint=os.getenv("ANALYTICS_ENDPOINT"),
            # Registry configuration from environment
            initialization_timeout_seconds=int(
                os.getenv("SERVICE_INIT_TIMEOUT", "300")
            ),
            health_check_interval_seconds=int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
            retry_failed_services=os.getenv("RETRY_FAILED_SERVICES", "true").lower()
            == "true",
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
        )

        # Deployment-specific overrides
        if deployment_context:
            config = ServiceFactory._apply_deployment_overrides(
                config, deployment_context
            )

        return config

    @staticmethod
    def _apply_deployment_overrides(
        config: ServiceConfig, context: DeploymentContext
    ) -> ServiceConfig:
        """Apply deployment-specific configuration overrides."""

        if context.mode == DeploymentMode.TENANT_CONTAINER:
            # Tenant-specific configuration
            tenant_id = context.tenant_id

            # Override auth issuer for tenant isolation
            if tenant_id:
                config.auth_issuer = f"tenant-{tenant_id}"

                # Use tenant-specific secrets if available
                tenant_jwt_secret = os.getenv(f"TENANT_{tenant_id.upper()}_JWT_SECRET")
                if tenant_jwt_secret:
                    config.auth_jwt_secret = tenant_jwt_secret

                tenant_payment_key = os.getenv(
                    f"TENANT_{tenant_id.upper()}_PAYMENT_API_KEY"
                )
                if tenant_payment_key:
                    config.payment_api_key = tenant_payment_key

        elif context.mode == DeploymentMode.DEVELOPMENT:
            # Development overrides - more lenient settings
            config.auth_expiry_hours = 168  # 1 week for dev
            config.initialization_timeout_seconds = 600  # Longer timeout for dev

        elif context.mode == DeploymentMode.MANAGEMENT_PLATFORM:
            # Management platform needs enhanced capabilities
            config.analytics_enabled = True  # Always enabled for management
            config.notification_enabled = True  # Always enabled for management

        elif context.mode == DeploymentMode.PRODUCTION:
            # Production specific settings
            config.retry_failed_services = True
            config.max_retry_attempts = 5
            config.health_check_interval_seconds = 15  # More frequent health checks

        return config

    @staticmethod
    async def create_auth_service(
        config: ServiceConfig, deployment_context: Optional[DeploymentContext] = None
    ) -> ServiceCreationResult:
        """Create authentication service."""
        if not config.auth_enabled:
            return ServiceCreationResult(
                success=False,
                service_name="auth",
                error_message="Auth service disabled in configuration",
            )

        try:
            auth_config = AuthServiceConfig(
                jwt_secret=config.auth_jwt_secret,
                issuer=config.auth_issuer,
                expiry_hours=config.auth_expiry_hours,
                deployment_context=deployment_context,
            )

            service = await create_auth_service(auth_config)

            return ServiceCreationResult(
                success=True, service_name="auth", service=service
            )

        except Exception as e:
            logger.error(f"Failed to create auth service: {e}")
            return ServiceCreationResult(
                success=False, service_name="auth", error_message=str(e)
            )

    @staticmethod
    async def create_payment_service(
        config: ServiceConfig, deployment_context: Optional[DeploymentContext] = None
    ) -> ServiceCreationResult:
        """Create payment service."""
        if not config.payment_enabled:
            return ServiceCreationResult(
                success=False,
                service_name="payment",
                error_message="Payment service disabled in configuration",
            )

        try:
            payment_config = PaymentServiceConfig(
                provider=config.payment_provider,
                api_key=config.payment_api_key,
                webhook_secret=config.payment_webhook_secret,
                deployment_context=deployment_context,
            )

            service = await create_payment_service(payment_config)

            return ServiceCreationResult(
                success=True, service_name="payment", service=service
            )

        except Exception as e:
            logger.error(f"Failed to create payment service: {e}")
            return ServiceCreationResult(
                success=False, service_name="payment", error_message=str(e)
            )

    @staticmethod
    async def create_notification_service(
        config: ServiceConfig, deployment_context: Optional[DeploymentContext] = None
    ) -> ServiceCreationResult:
        """Create notification service."""
        if not config.notification_enabled:
            return ServiceCreationResult(
                success=False,
                service_name="notification",
                error_message="Notification service disabled in configuration",
            )

        try:
            notification_config = NotificationServiceConfig(
                providers=config.notification_providers,
                email_provider=config.email_provider,
                sms_provider=config.sms_provider,
                deployment_context=deployment_context,
            )

            service = await create_notification_service(notification_config)

            return ServiceCreationResult(
                success=True, service_name="notification", service=service
            )

        except Exception as e:
            logger.error(f"Failed to create notification service: {e}")
            return ServiceCreationResult(
                success=False, service_name="notification", error_message=str(e)
            )

    @staticmethod
    async def create_analytics_service(
        config: ServiceConfig, deployment_context: Optional[DeploymentContext] = None
    ) -> ServiceCreationResult:
        """Create analytics service."""
        if not config.analytics_enabled:
            return ServiceCreationResult(
                success=False,
                service_name="analytics",
                error_message="Analytics service disabled in configuration",
            )

        try:
            analytics_config = AnalyticsServiceConfig(
                provider=config.analytics_provider,
                endpoint=config.analytics_endpoint,
                deployment_context=deployment_context,
            )

            service = await create_analytics_service(analytics_config)

            return ServiceCreationResult(
                success=True, service_name="analytics", service=service
            )

        except Exception as e:
            logger.error(f"Failed to create analytics service: {e}")
            return ServiceCreationResult(
                success=False, service_name="analytics", error_message=str(e)
            )


class DeploymentAwareServiceFactory:
    """Enhanced service factory with full deployment awareness."""

    def __init__(self, deployment_context: Optional[DeploymentContext] = None):
        """__init__ service method."""
        self.deployment_context = deployment_context
        self.base_factory = ServiceFactory()

    async def create_service_registry(
        self, additional_services: Dict[str, Any] = None
    ) -> ServiceRegistry:
        """Create a fully configured service registry."""
        logger.info("Creating deployment-aware service registry...")

        # Create service configuration
        service_config = self.base_factory.create_service_config(
            self.deployment_context
        )

        # Create registry
        registry = ServiceRegistry(service_config)

        # Create and register standard services
        await self._register_standard_services(registry, service_config)

        # Register additional custom services if provided
        if additional_services:
            await self._register_custom_services(registry, additional_services)

        return registry

    async def _register_standard_services(
        self, registry: ServiceRegistry, service_config: ServiceConfig
    ):
        """Register standard business services."""
        service_creators = [
            ("auth", self.base_factory.create_auth_service),
            ("payment", self.base_factory.create_payment_service),
            ("notification", self.base_factory.create_notification_service),
            ("analytics", self.base_factory.create_analytics_service),
        ]

        creation_results = []

        for service_name, creator_func in service_creators:
            try:
                result = await creator_func(service_config, self.deployment_context)
                creation_results.append(result)

                if result.success and result.service:
                    # Assign priority based on service type
                    priority = self._get_service_priority(service_name)
                    registry.register_service(service_name, result.service, priority)

                    # Add common dependencies
                    self._add_service_dependencies(registry, service_name)

                    logger.info(f"✅ Created and registered {service_name} service")
                else:
                    logger.warning(
                        f"⚠️ Failed to create {service_name} service: {result.error_message}"
                    )

            except Exception as e:
                logger.error(f"❌ Exception creating {service_name} service: {e}")
                creation_results.append(
                    ServiceCreationResult(
                        success=False, service_name=service_name, error_message=str(e)
                    )
                )

        # Log summary
        successful_services = [r.service_name for r in creation_results if r.success]
        failed_services = [r.service_name for r in creation_results if not r.success]

        logger.info(
            f"Service registry created: {len(successful_services)} services ready"
        )
        if successful_services:
            logger.info(f"  Ready: {', '.join(successful_services)}")
        if failed_services:
            logger.warning(f"  Failed: {', '.join(failed_services)}")

    async def _register_custom_services(
        self, registry: ServiceRegistry, custom_services: Dict[str, Any]
    ):
        """Register custom services provided by the application."""
        for service_name, service_instance in custom_services.items():
            try:
                if hasattr(service_instance, "priority"):
                    priority = service_instance.priority
                else:
                    priority = 50  # Default priority

                registry.register_service(service_name, service_instance, priority)
                logger.info(f"✅ Registered custom service: {service_name}")

            except Exception as e:
                logger.error(
                    f"❌ Failed to register custom service {service_name}: {e}"
                )

    def _add_service_dependencies(self, registry: ServiceRegistry, service_name: str):
        """Add common service dependencies."""
        try:
            if service_name == "payment":
                # Payment service depends on auth
                if registry.has_service("auth"):
                    registry.add_dependency("payment", "auth", required=True)

            elif service_name == "notification":
                # Notification service may use auth for authenticated email/sms providers
                if registry.has_service("auth"):
                    registry.add_dependency("notification", "auth", required=False)

            elif service_name == "analytics":
                # Analytics is usually independent but may benefit from auth context
                if registry.has_service("auth"):
                    registry.add_dependency("analytics", "auth", required=False)

        except Exception as e:
            logger.warning(f"Failed to add dependencies for {service_name}: {e}")

    def _get_service_priority(self, service_name: str) -> int:
        """Get initialization priority for service."""
        # Higher numbers = higher priority (initialized first)
        priorities = {
            "auth": 100,  # Auth first - needed by others
            "analytics": 90,  # Analytics second - for monitoring
            "notification": 80,  # Notifications third
            "payment": 70,  # Payment last - depends on auth
        }
        return priorities.get(service_name, 50)

    def get_deployment_info(self) -> Dict[str, Any]:
        """Get information about the deployment context."""
        if not self.deployment_context:
            return {"deployment_context": None}

        return {
            "deployment_context": {
                "mode": (
                    self.deployment_context.mode.value
                    if self.deployment_context.mode
                    else None
                ),
                "tenant_id": self.deployment_context.tenant_id,
                "platform": self.deployment_context.platform,
                "environment": self.deployment_context.environment,
                "container_isolation": self.deployment_context.container_isolation,
            }
        }
