"""Configuration generation service for ISP containers."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.feature_flags import FeatureFlagManager
from ..core.secret_manager import SecretManager
from ..core.template_engine import TemplateEngine
from ..core.validators import ConfigurationValidator, ValidationResult
from ..schemas.config_schemas import (
    DatabaseConfig,
    ISPConfiguration,
    RedisConfig,
    SecurityConfig,
)
from ..schemas.tenant_schemas import EnvironmentType, SubscriptionPlan, TenantInfo

logger = logging.getLogger(__name__)


class ConfigurationGenerator:
    """
    Main configuration generator for ISP container deployments.

    Generates complete ISP configurations based on tenant information,
    subscription plans, and environment settings.
    """

    def __init__(
        self,
        template_engine: Optional[TemplateEngine] = None,
        secret_manager: Optional[SecretManager] = None,
        feature_manager: Optional[FeatureFlagManager] = None,
        validator: Optional[ConfigurationValidator] = None,
    ):
        """Initialize the configuration generator."""
        self.template_engine = template_engine or TemplateEngine()
        self.secret_manager = secret_manager or SecretManager()
        self.feature_manager = feature_manager or FeatureFlagManager()
        self.validator = validator or ConfigurationValidator()

        # Default configuration templates
        self._default_configs = {
            "database": {
                SubscriptionPlan.BASIC: {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,
                },
                SubscriptionPlan.PREMIUM: {
                    "pool_size": 15,
                    "max_overflow": 30,
                    "pool_timeout": 60,
                    "pool_recycle": 1800,
                },
                SubscriptionPlan.ENTERPRISE: {
                    "pool_size": 30,
                    "max_overflow": 60,
                    "pool_timeout": 120,
                    "pool_recycle": 900,
                },
            },
            "redis": {
                SubscriptionPlan.BASIC: {
                    "connection_pool_size": 10,
                    "max_connections": 50,
                },
                SubscriptionPlan.PREMIUM: {
                    "connection_pool_size": 25,
                    "max_connections": 100,
                },
                SubscriptionPlan.ENTERPRISE: {
                    "connection_pool_size": 50,
                    "max_connections": 200,
                },
            },
        }

    async def generate_isp_config(
        self,
        isp_id: UUID,
        plan: SubscriptionPlan,
        environment: str,
        tenant_info: Optional[TenantInfo] = None,
        custom_overrides: Optional[Dict[str, Any]] = None,
    ) -> ISPConfiguration:
        """
        Generate complete ISP configuration for a specific tenant.

        Args:
            isp_id: Unique tenant identifier
            plan: Subscription plan (basic, premium, enterprise)
            environment: Target environment (dev, staging, production)
            tenant_info: Optional tenant information
            custom_overrides: Optional configuration overrides

        Returns:
            Complete ISP configuration with all components
        """
        logger.info(
            f"Generating ISP configuration for tenant {isp_id}, plan {plan}, env {environment}"
        )

        try:
            # Generate base configuration components
            database_config = await self._generate_database_config(
                isp_id, plan, environment
            )
            redis_config = await self._generate_redis_config(isp_id, plan, environment)
            security_config = await self._generate_security_config(
                isp_id, plan, environment
            )
            monitoring_config = await self._generate_monitoring_config(
                isp_id, plan, environment
            )
            logging_config = await self._generate_logging_config(
                isp_id, plan, environment
            )
            network_config = await self._generate_network_config(
                isp_id, plan, environment
            )

            # Generate service configurations
            services = await self._generate_service_configs(isp_id, plan, environment)
            external_services = await self._generate_external_service_configs(
                isp_id, plan, environment
            )

            # Create base configuration
            config = ISPConfiguration(
                tenant_id=isp_id,
                environment=environment,
                database=database_config,
                redis=redis_config,
                security=security_config,
                monitoring=monitoring_config,
                logging=logging_config,
                network=network_config,
                services=services,
                external_services=external_services,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Apply custom overrides
            if custom_overrides:
                config = await self._apply_custom_overrides(config, custom_overrides)

            # Apply feature flags
            if tenant_info:
                config = await self.feature_manager.apply_feature_flags(
                    config, tenant_info
                )
            else:
                # Generate basic feature flags based on plan
                feature_flags = await self.feature_manager.generate_plan_features(
                    isp_id, plan
                )
                config.feature_flags = feature_flags

            logger.info(f"Successfully generated configuration for tenant {isp_id}")
            return config

        except Exception as e:
            logger.error(
                f"Failed to generate configuration for tenant {isp_id}: {str(e)}"
            )
            raise

    async def inject_secrets(self, config: ISPConfiguration) -> ISPConfiguration:
        """
        Inject encrypted secrets into configuration.

        Args:
            config: Base configuration without secrets

        Returns:
            Configuration with secrets injected
        """
        logger.info(f"Injecting secrets for tenant {config.tenant_id}")

        try:
            return await self.secret_manager.inject_secrets(config)
        except Exception as e:
            logger.error(
                f"Failed to inject secrets for tenant {config.tenant_id}: {str(e)}"
            )
            raise

    async def validate_configuration(
        self, config: ISPConfiguration
    ) -> ValidationResult:
        """
        Comprehensive configuration validation.

        Args:
            config: Configuration to validate

        Returns:
            Validation result with errors/warnings
        """
        logger.info(f"Validating configuration for tenant {config.tenant_id}")

        try:
            return await self.validator.validate_configuration(config)
        except Exception as e:
            logger.error(
                f"Configuration validation failed for tenant {config.tenant_id}: {str(e)}"
            )
            raise

    async def apply_feature_flags(self, config: ISPConfiguration) -> ISPConfiguration:
        """
        Apply feature flags based on subscription plan.

        Args:
            config: Base configuration

        Returns:
            Configuration with feature flags applied
        """
        logger.info(f"Applying feature flags for tenant {config.tenant_id}")

        try:
            # This would typically get tenant info from database
            # For now, we'll create a basic tenant info from config
            tenant_info = await self._get_tenant_info(config.tenant_id)
            return await self.feature_manager.apply_feature_flags(config, tenant_info)
        except Exception as e:
            logger.error(
                f"Failed to apply feature flags for tenant {config.tenant_id}: {str(e)}"
            )
            raise

    async def _generate_database_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> DatabaseConfig:
        """Generate database configuration based on plan and environment."""
        base_config = self._default_configs["database"].get(
            plan, self._default_configs["database"][SubscriptionPlan.BASIC]
        )

        # Environment-specific adjustments
        if environment == "development":
            base_config = {**base_config, "pool_size": min(base_config["pool_size"], 5)}
        elif environment == "production":
            # Production gets higher limits
            base_config = {**base_config, "pool_size": base_config["pool_size"] + 5}

        return DatabaseConfig(
            host=f"db-{tenant_id}.{environment}.dotmac.io",
            port=5432,
            name=f"isp_{tenant_id}_{environment}".replace("-", "_"),
            username=f"isp_user_{tenant_id}".replace("-", "_")[
                :63
            ],  # PostgreSQL username limit
            password="${SECRET:database_password}",  # Will be replaced by secret manager
            **base_config,
        )

    async def _generate_redis_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> RedisConfig:
        """Generate Redis configuration based on plan and environment."""
        base_config = self._default_configs["redis"].get(
            plan, self._default_configs["redis"][SubscriptionPlan.BASIC]
        )

        return RedisConfig(
            host=f"redis-{tenant_id}.{environment}.dotmac.io",
            port=6379,
            database=0,
            password="${SECRET:redis_password}",  # Will be replaced by secret manager
            **base_config,
        )

    async def _generate_security_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> SecurityConfig:
        """Generate security configuration based on plan and environment."""
        # Enterprise plans get enhanced security features
        enhanced_security = plan == SubscriptionPlan.ENTERPRISE

        return SecurityConfig(
            jwt_secret_key="${SECRET:jwt_secret_key}",
            jwt_algorithm="RS256" if enhanced_security else "HS256",
            jwt_access_token_expire_minutes=15 if environment == "production" else 60,
            jwt_refresh_token_expire_days=30,
            encryption_key="${SECRET:encryption_key}",
            password_hash_rounds=12 if enhanced_security else 10,
            rate_limit_enabled=True,
            rate_limit_requests_per_minute=(
                1000 if plan == SubscriptionPlan.ENTERPRISE else 100
            ),
            cors_enabled=True,
            cors_origins=[f"https://{tenant_id}.dotmac.io"],
            enable_security_headers=True,
        )

    async def _generate_monitoring_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> "MonitoringConfig":
        """Generate monitoring configuration."""
        from ..schemas.config_schemas import MonitoringConfig

        # Premium and Enterprise plans get enhanced monitoring
        enhanced_monitoring = plan in [
            SubscriptionPlan.PREMIUM,
            SubscriptionPlan.ENTERPRISE,
        ]

        return MonitoringConfig(
            metrics_enabled=True,
            health_check_enabled=True,
            tracing_enabled=enhanced_monitoring,
            tracing_sample_rate=0.1 if enhanced_monitoring else 0.01,
            prometheus_enabled=enhanced_monitoring,
            grafana_dashboard_enabled=plan == SubscriptionPlan.ENTERPRISE,
        )

    async def _generate_logging_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> "LoggingConfig":
        """Generate logging configuration."""
        from ..schemas.config_schemas import LoggingConfig, LogLevel

        return LoggingConfig(
            level=LogLevel.DEBUG if environment == "development" else LogLevel.INFO,
            format="json" if environment == "production" else "text",
            log_to_file=environment != "development",
            log_file_path=f"/var/log/isp/{tenant_id}/app.log",
            structured_logging=True,
            external_logging_enabled=plan == SubscriptionPlan.ENTERPRISE,
        )

    async def _generate_network_config(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> "NetworkConfig":
        """Generate network configuration."""
        from ..schemas.config_schemas import NetworkConfig

        # Scale workers based on plan
        worker_counts = {
            SubscriptionPlan.BASIC: 2,
            SubscriptionPlan.PREMIUM: 4,
            SubscriptionPlan.ENTERPRISE: 8,
        }

        return NetworkConfig(
            host="0.0.0.0",
            port=8000,
            workers=worker_counts.get(plan, 2),
            request_timeout=60 if plan == SubscriptionPlan.ENTERPRISE else 30,
            max_concurrent_requests=(
                2000 if plan == SubscriptionPlan.ENTERPRISE else 1000
            ),
            websocket_enabled=True,
            websocket_max_connections=(
                500 if plan == SubscriptionPlan.ENTERPRISE else 100
            ),
        )

    async def _generate_service_configs(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> List["ServiceConfig"]:
        """Generate service configurations."""
        from ..schemas.config_schemas import ServiceConfig, ServiceStatus

        services = [
            ServiceConfig(
                name="api",
                version="latest",
                status=ServiceStatus.ENABLED,
                health_check_path="/health",
                environment_variables={
                    "TENANT_ID": str(tenant_id),
                    "ENVIRONMENT": environment,
                    "SUBSCRIPTION_PLAN": plan,
                },
            ),
            ServiceConfig(
                name="worker",
                version="latest",
                status=ServiceStatus.ENABLED,
                depends_on=["api"],
                environment_variables={
                    "TENANT_ID": str(tenant_id),
                    "WORKER_TYPE": "celery",
                },
            ),
            ServiceConfig(
                name="scheduler",
                version="latest",
                status=ServiceStatus.ENABLED,
                depends_on=["api", "worker"],
                environment_variables={
                    "TENANT_ID": str(tenant_id),
                    "SCHEDULER_TYPE": "celery-beat",
                },
            ),
        ]

        # Add premium services for higher plans
        if plan in [SubscriptionPlan.PREMIUM, SubscriptionPlan.ENTERPRISE]:
            services.append(
                ServiceConfig(
                    name="analytics",
                    version="latest",
                    status=ServiceStatus.ENABLED,
                    depends_on=["api"],
                    environment_variables={
                        "TENANT_ID": str(tenant_id),
                        "ANALYTICS_ENABLED": "true",
                    },
                )
            )

        return services

    async def _generate_external_service_configs(
        self, tenant_id: UUID, plan: SubscriptionPlan, environment: str
    ) -> List["ExternalServiceConfig"]:
        """Generate external service configurations."""
        from ..schemas.config_schemas import ExternalServiceConfig

        configs = []

        # All plans get email service
        configs.append(
            ExternalServiceConfig(
                service_name="email",
                endpoint="https://api.sendgrid.com/v3",
                api_key="${SECRET:sendgrid_api_key}",
                auth_type="bearer",
                timeout=30,
                max_retries=3,
            )
        )

        # Premium and Enterprise get SMS service
        if plan in [SubscriptionPlan.PREMIUM, SubscriptionPlan.ENTERPRISE]:
            configs.append(
                ExternalServiceConfig(
                    service_name="sms",
                    endpoint="https://api.twilio.com",
                    api_key="${SECRET:twilio_api_key}",
                    auth_type="basic",
                    auth_config={
                        "username": "${SECRET:twilio_username}",
                        "password": "${SECRET:twilio_password}",
                    },
                )
            )

        # Enterprise gets payment processing
        if plan == SubscriptionPlan.ENTERPRISE:
            configs.append(
                ExternalServiceConfig(
                    service_name="payment",
                    endpoint="https://api.stripe.com/v1",
                    api_key="${SECRET:stripe_secret_key}",
                    auth_type="bearer",
                    timeout=60,
                    max_retries=5,
                )
            )

        return configs

    async def _apply_custom_overrides(
        self, config: ISPConfiguration, overrides: Dict[str, Any]
    ) -> ISPConfiguration:
        """Apply custom configuration overrides."""

        # Deep merge overrides into configuration
        def deep_merge(base_dict: dict, override_dict: dict) -> dict:
            result = base_dict.copy()
            for key, value in override_dict.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        # Convert config to dict, apply overrides, then convert back
        config_dict = config.model_dump()
        merged_dict = deep_merge(config_dict, overrides)

        return ISPConfiguration.model_validate(merged_dict)

    async def _get_tenant_info(self, tenant_id: UUID) -> TenantInfo:
        """Get tenant information (placeholder - would typically query database)."""
        # This would typically query a database or service
        # For now, return a basic TenantInfo
        return TenantInfo(
            tenant_id=tenant_id,
            name=f"Tenant {tenant_id}",
            slug=str(tenant_id)[:8],
            subscription_plan=SubscriptionPlan.BASIC,
            admin_email=f"admin@{tenant_id}.dotmac.io",
            environment=EnvironmentType.PRODUCTION,
        )

    def get_template_context(
        self,
        tenant_id: UUID,
        plan: SubscriptionPlan,
        environment: str,
        tenant_info: Optional[TenantInfo] = None,
    ) -> Dict[str, Any]:
        """Get template context for configuration generation."""
        context = {
            "tenant_id": str(tenant_id),
            "plan": plan,
            "environment": environment,
            "timestamp": datetime.now().isoformat(),
            "defaults": self._default_configs,
        }

        if tenant_info:
            context.update(tenant_info.to_config_context())

        return context
