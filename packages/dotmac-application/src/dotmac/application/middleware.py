"""
Standard middleware stack for all DotMac applications.
Provider-based composition approach for decoupled architecture.
"""

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import DeploymentMode, PlatformConfig, Providers

logger = logging.getLogger(__name__)


def apply_standard_middleware(
    app: FastAPI, *, config: PlatformConfig, providers: Providers | None = None
) -> list[str]:
    """
    Apply standard middleware stack using provider-based composition.

    Args:
        app: FastAPI application instance
        config: Platform configuration
        providers: Optional providers for middleware components

    Returns:
        List of applied middleware names
    """
    middleware_stack = StandardMiddlewareStack(config, providers)
    return middleware_stack.apply_to_app(app)


class StandardMiddlewareStack:
    """Standard middleware stack applied to all DotMac applications."""

    def __init__(
        self, platform_config: PlatformConfig, providers: Providers | None = None
    ):
        self.platform_config = platform_config
        self.providers = providers or Providers()
        self.applied_middleware: list[str] = []

    def apply_to_app(self, app: FastAPI) -> list[str]:
        """Apply standard middleware stack to FastAPI application."""
        logger.info(
            f"Applying standard middleware stack for {self.platform_config.platform_name}"
        )

        # Apply middleware in reverse order (FastAPI applies them in reverse)
        self._apply_observability_middleware(app)
        self._apply_security_middleware(app)
        self._apply_tenant_boundary_enforcement(app)
        self._apply_cors_middleware(app)
        self._apply_trusted_host_middleware(app)

        logger.info(f"Applied middleware: {self.applied_middleware}")
        return self.applied_middleware

    def _apply_trusted_host_middleware(self, app: FastAPI):
        """Apply trusted host middleware."""
        try:
            # Get allowed hosts from deployment context or use defaults
            allowed_hosts = self._get_allowed_hosts()

            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

            self.applied_middleware.append("TrustedHostMiddleware")
            logger.debug(f"Applied TrustedHostMiddleware with hosts: {allowed_hosts}")

        except Exception as e:
            logger.error(f"Failed to apply TrustedHostMiddleware: {e}")

    def _apply_cors_middleware(self, app: FastAPI):
        """Apply CORS middleware if enabled."""
        if not self.platform_config.security_config.cors_enabled:
            return

        try:
            cors_config = self._get_cors_config()

            app.add_middleware(CORSMiddleware, **cors_config)

            self.applied_middleware.append("CORSMiddleware")
            logger.debug("Applied CORSMiddleware")

        except Exception as e:
            logger.error(f"Failed to apply CORSMiddleware: {e}")

    def _apply_security_middleware(self, app: FastAPI):
        """Apply security middleware using providers."""
        if not self.platform_config.security_config.api_security_suite:
            return

        if not self.providers.security:
            logger.warning(
                "Security provider not available, skipping security middleware"
            )
            return

        try:
            security_config = {
                "csrf_enabled": self.platform_config.security_config.csrf_enabled,
                "rate_limiting_enabled": self.platform_config.security_config.rate_limiting_enabled,
                "deployment_mode": self.platform_config.deployment_context.mode
                if self.platform_config.deployment_context
                else None,
                "custom_settings": self.platform_config.custom_settings,
            }

            # Apply JWT Authentication
            try:
                self.providers.security.apply_jwt_authentication(app, security_config)
                self.applied_middleware.extend(
                    ["JWTAuthenticationMiddleware", "APIKeyAuthenticationMiddleware"]
                )
                logger.debug("Applied JWT authentication via security provider")
            except Exception as e:
                logger.warning(f"JWT authentication setup failed: {e}")

            # Apply CSRF Protection
            if self.platform_config.security_config.csrf_enabled:
                try:
                    self.providers.security.apply_csrf_protection(app, security_config)
                    self.applied_middleware.append("CSRFProtection")
                    logger.debug("Applied CSRF protection via security provider")
                except Exception as e:
                    logger.warning(f"CSRF protection setup failed: {e}")

            # Apply Rate Limiting
            if self.platform_config.security_config.rate_limiting_enabled:
                try:
                    self.providers.security.apply_rate_limiting(app, security_config)
                    self.applied_middleware.append("RateLimitingMiddleware")
                    logger.debug("Applied rate limiting via security provider")
                except Exception as e:
                    logger.warning(f"Rate limiting setup failed: {e}")

        except Exception as e:
            logger.error(f"Failed to apply security middleware: {e}")

    def _apply_tenant_boundary_enforcement(self, app: FastAPI):
        """Apply tenant boundary enforcement using providers."""
        if not self.platform_config.security_config.tenant_isolation:
            return

        if not self.providers.tenant:
            logger.warning(
                "Tenant provider not available, skipping tenant boundary enforcement"
            )
            return

        try:
            tenant_config = {
                "deployment_mode": self.platform_config.deployment_context.mode
                if self.platform_config.deployment_context
                else None,
                "tenant_id": self.platform_config.deployment_context.tenant_id
                if self.platform_config.deployment_context
                else None,
                "isolation_level": self.platform_config.deployment_context.isolation_level
                if self.platform_config.deployment_context
                else None,
                "custom_settings": self.platform_config.custom_settings,
            }

            # Apply tenant security enforcement
            try:
                self.providers.tenant.apply_tenant_security(app, tenant_config)
                self.applied_middleware.append("TenantSecurityEnforcerMiddleware")
                logger.debug("Applied tenant security enforcement via tenant provider")
            except Exception as e:
                logger.warning(f"Tenant security enforcement setup failed: {e}")

            # Apply tenant isolation based on deployment mode
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                try:
                    if mode == DeploymentMode.TENANT_CONTAINER:
                        self.providers.tenant.apply_tenant_isolation(app, tenant_config)
                        self.applied_middleware.append("TenantIsolationMiddleware")
                        logger.debug(
                            "Applied tenant container isolation via tenant provider"
                        )
                    elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                        self.providers.tenant.apply_tenant_isolation(app, tenant_config)
                        self.applied_middleware.append("ManagementTenantMiddleware")
                        logger.debug(
                            "Applied management platform tenant middleware via tenant provider"
                        )
                except Exception as e:
                    logger.warning(f"Tenant isolation setup failed: {e}")

        except Exception as e:
            logger.error(f"Failed to apply tenant boundary enforcement: {e}")

    def _apply_observability_middleware(self, app: FastAPI):
        """Apply observability middleware using providers."""
        if not self.platform_config.observability_config.enabled:
            return

        if not self.providers.observability:
            logger.warning(
                "Observability provider not available, skipping observability middleware"
            )
            return

        try:
            observability_config = {
                "tier": self.platform_config.observability_config.tier,
                "metrics_enabled": self.platform_config.observability_config.metrics_enabled,
                "tracing_enabled": self.platform_config.observability_config.tracing_enabled,
                "logging_level": self.platform_config.observability_config.logging_level,
                "custom_metrics": self.platform_config.observability_config.custom_metrics,
                "platform_name": self.platform_config.platform_name,
            }

            # Apply metrics collection
            if self.platform_config.observability_config.metrics_enabled:
                try:
                    self.providers.observability.apply_metrics(
                        app, observability_config
                    )
                    self.applied_middleware.append("MetricsMiddleware")
                    logger.debug(
                        "Applied metrics collection via observability provider"
                    )
                except Exception as e:
                    logger.warning(f"Metrics collection setup failed: {e}")

            # Apply tracing
            if self.platform_config.observability_config.tracing_enabled:
                try:
                    self.providers.observability.apply_tracing(
                        app, observability_config
                    )
                    self.applied_middleware.append("TracingMiddleware")
                    logger.debug("Applied tracing via observability provider")
                except Exception as e:
                    logger.warning(f"Tracing setup failed: {e}")

            # Apply structured logging
            try:
                self.providers.observability.apply_logging(app, observability_config)
                self.applied_middleware.append("StructuredLoggingMiddleware")
                logger.debug("Applied structured logging via observability provider")
            except Exception as e:
                logger.warning(f"Structured logging setup failed: {e}")

        except Exception as e:
            logger.error(f"Failed to apply observability middleware: {e}")

    def _get_allowed_hosts(self) -> list[str]:
        """Get allowed hosts based on deployment context."""
        # Default hosts
        allowed_hosts = ["localhost", "127.0.0.1", "testserver"]

        # Add deployment-specific hosts
        if self.platform_config.deployment_context:
            context = self.platform_config.deployment_context

            if context.mode == DeploymentMode.TENANT_CONTAINER and context.tenant_id:
                allowed_hosts.extend(
                    [
                        f"tenant-{context.tenant_id}.dotmac.app",
                        f"tenant-{context.tenant_id}.internal",
                        f"{context.tenant_id}.portal.dotmac.app",
                    ]
                )
            elif context.mode == DeploymentMode.MANAGEMENT_PLATFORM:
                allowed_hosts.extend(
                    ["*.dotmac.app", "management.dotmac.app", "admin.dotmac.app"]
                )

        # Add custom hosts from platform config
        custom_settings = self.platform_config.custom_settings
        if (
            "networking" in custom_settings
            and "allowed_hosts" in custom_settings["networking"]
        ):
            allowed_hosts.extend(custom_settings["networking"]["allowed_hosts"])

        return allowed_hosts

    def _get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration."""
        cors_config = {
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

        # Set origins based on deployment context
        if self.platform_config.deployment_context:
            context = self.platform_config.deployment_context

            if context.mode == DeploymentMode.TENANT_CONTAINER and context.tenant_id:
                cors_config["allow_origins"] = [
                    f"https://tenant-{context.tenant_id}.dotmac.app",
                    f"https://{context.tenant_id}.portal.dotmac.app",
                ]
            elif context.mode == DeploymentMode.MANAGEMENT_PLATFORM:
                cors_config["allow_origins"] = [
                    "https://management.dotmac.app",
                    "https://admin.dotmac.app",
                    "https://*.dotmac.app",
                ]
            else:
                cors_config["allow_origins"] = ["*"]  # Development mode
        else:
            cors_config["allow_origins"] = ["*"]  # Default

        # Override with custom settings
        custom_settings = self.platform_config.custom_settings
        if (
            "networking" in custom_settings
            and "cors_origins" in custom_settings["networking"]
        ):
            cors_config["allow_origins"] = custom_settings["networking"]["cors_origins"]

        return cors_config


# Legacy compatibility - will be removed in future versions
class StandardMiddlewareStackLegacy(StandardMiddlewareStack):
    """Legacy middleware stack for backward compatibility."""

    def __init__(self, platform_config: PlatformConfig):
        super().__init__(platform_config, None)
        logger.warning(
            "StandardMiddlewareStackLegacy is deprecated. "
            "Use StandardMiddlewareStack with providers instead."
        )
