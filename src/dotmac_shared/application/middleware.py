"""
Standard middleware stack for all DotMac applications.
"""

import logging
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import DeploymentMode, PlatformConfig

logger = logging.getLogger(__name__)


class StandardMiddlewareStack:
    """Standard middleware stack applied to all DotMac applications."""

    def __init__(self, platform_config: PlatformConfig):
        self.platform_config = platform_config
        self.applied_middleware: List[str] = []

    def apply_to_app(self, app: FastAPI) -> List[str]:
        """Apply standard middleware stack to FastAPI application."""
        logger.info(
            f"Applying standard middleware stack for {self.platform_config.platform_name}"
        )

        # Apply middleware in reverse order (FastAPI applies them in reverse)
        self._apply_security_middleware(app)
        self._apply_tenant_isolation_middleware(app)
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

    def _apply_tenant_isolation_middleware(self, app: FastAPI):
        """Apply tenant isolation middleware if enabled."""
        if not self.platform_config.security_config.tenant_isolation:
            return

        try:
            # Import and apply tenant isolation middleware based on deployment mode
            if self.platform_config.deployment_context:
                mode = self.platform_config.deployment_context.mode

                if mode == DeploymentMode.TENANT_CONTAINER:
                    self._apply_tenant_container_middleware(app)
                elif mode == DeploymentMode.MANAGEMENT_PLATFORM:
                    self._apply_management_tenant_middleware(app)

        except ImportError:
            logger.warning("Tenant isolation middleware not available")
        except Exception as e:
            logger.error(f"Failed to apply tenant isolation middleware: {e}")

    def _apply_tenant_container_middleware(self, app: FastAPI):
        """Apply tenant container specific middleware."""
        try:
            from dotmac_isp.core.tenant_security import add_tenant_security_middleware

            add_tenant_security_middleware(app)
            self.applied_middleware.append("TenantSecurityMiddleware")

        except ImportError:
            logger.warning("ISP tenant security middleware not available")

    def _apply_management_tenant_middleware(self, app: FastAPI):
        """Apply management platform tenant middleware."""
        try:
            from dotmac_management.core.tenant_security import (
                add_management_tenant_security_middleware,
            )

            add_management_tenant_security_middleware(app)
            self.applied_middleware.append("ManagementTenantSecurityMiddleware")

        except ImportError:
            logger.warning("Management tenant security middleware not available")

    def _apply_security_middleware(self, app: FastAPI):
        """Apply additional security middleware."""
        if not self.platform_config.security_config.api_security_suite:
            return

        try:
            # CSRF Protection
            if self.platform_config.security_config.csrf_enabled:
                self._apply_csrf_protection(app)

            # Rate limiting
            if self.platform_config.security_config.rate_limiting_enabled:
                self._apply_rate_limiting(app)

        except Exception as e:
            logger.error(f"Failed to apply security middleware: {e}")

    def _apply_csrf_protection(self, app: FastAPI):
        """Apply CSRF protection."""
        try:
            # Try ISP Framework CSRF first
            try:
                from dotmac_isp.core.csrf_middleware import add_csrf_protection

                add_csrf_protection(app)
                self.applied_middleware.append("CSRFProtection")
                return
            except ImportError:
                pass

            # Try Management Platform CSRF
            try:
                from dotmac_management.core.csrf_middleware import add_csrf_protection

                add_csrf_protection(app)
                self.applied_middleware.append("CSRFProtection")
                return
            except ImportError:
                pass

            logger.warning("CSRF protection not available")

        except Exception as e:
            logger.error(f"Failed to apply CSRF protection: {e}")

    def _apply_rate_limiting(self, app: FastAPI):
        """Apply rate limiting middleware."""
        try:
            # Apply universal rate limiting middleware using shared system
            from dotmac_shared.auth.middleware.rate_limiting import (
                RateLimitingMiddleware,
            )

            # Create and add the rate limiting middleware
            rate_limiting_middleware = RateLimitingMiddleware()
            app.add_middleware(RateLimitingMiddleware)

            self.applied_middleware.append("RateLimitingMiddleware")
            logger.info("Applied universal rate limiting middleware")

        except ImportError as e:
            # Fallback: try platform-specific implementations
            logger.warning(
                f"Universal rate limiting not available, trying platform-specific: {e}"
            )
            try:
                if self.platform_config.deployment_context:
                    mode = self.platform_config.deployment_context.mode

                    if mode == DeploymentMode.MANAGEMENT_PLATFORM:
                        from dotmac_management.core.middleware import (
                            RateLimitMiddleware,
                        )

                        app.add_middleware(RateLimitMiddleware)
                        self.applied_middleware.append("RateLimitMiddleware")

            except ImportError:
                logger.warning("No rate limiting middleware available")
            except Exception as e:
                logger.error(f"Failed to apply platform-specific rate limiting: {e}")

        except Exception as e:
            logger.error(f"Failed to apply rate limiting: {e}")

    def _get_allowed_hosts(self) -> List[str]:
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

    def _get_cors_config(self) -> Dict[str, Any]:
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
