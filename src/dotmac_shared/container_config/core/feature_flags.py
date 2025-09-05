"""Feature flag management for premium feature control."""

import hashlib
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from ..schemas.config_schemas import FeatureFlagConfig, ISPConfiguration
from ..schemas.feature_schemas import (
    DEFAULT_PLAN_FEATURES,
    FeatureCategory,
    FeatureDefinition,
    FeatureFlag,
    PlanFeatures,
)
from ..schemas.tenant_schemas import SubscriptionPlan, TenantInfo

logger = logging.getLogger(__name__)


class FeatureRegistry:
    """Registry for feature definitions and plan configurations."""

    def __init__(self):
        self.features: dict[str, FeatureDefinition] = {}
        self.plan_features: dict[str, PlanFeatures] = DEFAULT_PLAN_FEATURES.copy()

        # Load default features
        self._load_default_features()

    def _load_default_features(self):
        """Load default feature definitions."""
        default_features = [
            # Analytics Features
            FeatureDefinition(
                name="basic_analytics",
                display_name="Basic Analytics",
                description="Basic usage and performance analytics",
                category=FeatureCategory.ANALYTICS,
                available_plans=["basic", "premium", "enterprise"],
                default_config={"retention_days": 30, "max_reports": 5},
            ),
            FeatureDefinition(
                name="advanced_analytics",
                display_name="Advanced Analytics",
                description="Advanced analytics with custom dashboards",
                category=FeatureCategory.ANALYTICS,
                available_plans=["premium", "enterprise"],
                default_config={
                    "retention_days": 90,
                    "max_reports": 25,
                    "custom_dashboards": True,
                },
            ),
            # API Features
            FeatureDefinition(
                name="standard_api",
                display_name="Standard API",
                description="Standard API access with basic rate limits",
                category=FeatureCategory.API,
                available_plans=["basic", "premium", "enterprise"],
                resource_limits={"requests_per_hour": 1000},
                default_config={"rate_limit": 1000, "burst_limit": 100},
            ),
            FeatureDefinition(
                name="premium_api",
                display_name="Premium API",
                description="Premium API access with higher rate limits",
                category=FeatureCategory.API,
                available_plans=["premium", "enterprise"],
                resource_limits={"requests_per_hour": 10000},
                default_config={"rate_limit": 10000, "burst_limit": 1000},
            ),
            FeatureDefinition(
                name="enterprise_api",
                display_name="Enterprise API",
                description="Enterprise API with unlimited access",
                category=FeatureCategory.API,
                available_plans=["enterprise"],
                resource_limits={"requests_per_hour": 100000},
                default_config={"rate_limit": 100000, "burst_limit": 10000},
            ),
            # Integration Features
            FeatureDefinition(
                name="basic_integration",
                display_name="Basic Integration",
                description="Basic third-party integrations",
                category=FeatureCategory.INTEGRATION,
                available_plans=["basic", "premium", "enterprise"],
                resource_limits={"max_integrations": 3},
            ),
            FeatureDefinition(
                name="premium_integration",
                display_name="Premium Integration",
                description="Premium integrations with webhooks",
                category=FeatureCategory.INTEGRATION,
                available_plans=["premium", "enterprise"],
                resource_limits={"max_integrations": 10, "max_webhooks": 5},
            ),
            FeatureDefinition(
                name="enterprise_integration",
                display_name="Enterprise Integration",
                description="Enterprise integrations with custom connectors",
                category=FeatureCategory.INTEGRATION,
                available_plans=["enterprise"],
                resource_limits={
                    "max_integrations": -1,
                    "max_webhooks": -1,
                },  # Unlimited
            ),
            # Security Features
            FeatureDefinition(
                name="sso",
                display_name="Single Sign-On",
                description="SAML/OIDC single sign-on integration",
                category=FeatureCategory.SECURITY,
                available_plans=["enterprise"],
                default_config={"protocols": ["saml", "oidc"], "max_providers": 3},
            ),
            FeatureDefinition(
                name="advanced_security",
                display_name="Advanced Security",
                description="Advanced security features and compliance",
                category=FeatureCategory.SECURITY,
                available_plans=["enterprise"],
                default_config={
                    "audit_logging": True,
                    "compliance_reports": True,
                    "security_scanning": True,
                },
            ),
            # UI/UX Features
            FeatureDefinition(
                name="custom_branding",
                display_name="Custom Branding",
                description="Customize colors, logos, and themes",
                category=FeatureCategory.UI_UX,
                available_plans=["premium", "enterprise"],
                default_config={"custom_logo": True, "custom_colors": True},
            ),
            FeatureDefinition(
                name="white_label",
                display_name="White Label",
                description="Complete white-label experience",
                category=FeatureCategory.UI_UX,
                available_plans=["enterprise"],
                default_config={
                    "custom_logo": True,
                    "custom_colors": True,
                    "custom_domain": True,
                    "hide_branding": True,
                },
            ),
            # Support Features
            FeatureDefinition(
                name="email_support",
                display_name="Email Support",
                description="Email-based customer support",
                category=FeatureCategory.CORE,
                available_plans=["basic", "premium", "enterprise"],
                default_config={"response_time_hours": 24},
            ),
            FeatureDefinition(
                name="phone_support",
                display_name="Phone Support",
                description="Phone-based customer support",
                category=FeatureCategory.CORE,
                available_plans=["premium", "enterprise"],
                default_config={"business_hours": "9-5", "response_time_hours": 4},
            ),
            FeatureDefinition(
                name="priority_support",
                display_name="Priority Support",
                description="Priority support with dedicated team",
                category=FeatureCategory.CORE,
                available_plans=["enterprise"],
                default_config={"response_time_hours": 1, "dedicated_team": True},
            ),
        ]

        for feature in default_features:
            self.features[feature.name] = feature

    def register_feature(self, feature: FeatureDefinition):
        """Register a new feature definition."""
        self.features[feature.name] = feature
        logger.info(f"Registered feature: {feature.name}")

    def get_feature(self, name: str) -> Optional[FeatureDefinition]:
        """Get a feature definition by name."""
        return self.features.get(name)

    def list_features(
        self, category: Optional[FeatureCategory] = None, plan: Optional[str] = None
    ) -> list[FeatureDefinition]:
        """List features, optionally filtered by category or plan."""
        features = list(self.features.values())

        if category:
            features = [f for f in features if f.category == category]

        if plan:
            features = [f for f in features if plan in f.available_plans]

        return features

    def get_plan_features(self, plan: str) -> Optional[PlanFeatures]:
        """Get feature configuration for a plan."""
        return self.plan_features.get(plan)


class FeatureFlagEvaluator:
    """Evaluates feature flags based on conditions and rollout strategies."""

    def __init__(self):
        self.evaluation_cache: dict[str, Any] = {}

    def evaluate_flag(
        self,
        flag: FeatureFlag,
        context: dict[str, Any],
        user_id: Optional[str] = None,
        user_groups: Optional[list[str]] = None,
    ) -> bool:
        """
        Evaluate whether a feature flag should be enabled.

        Args:
            flag: Feature flag to evaluate
            context: Evaluation context
            user_id: Optional user ID
            user_groups: Optional user groups

        Returns:
            True if feature should be enabled
        """
        # Check if flag is globally disabled
        if not flag.enabled:
            return False

        # Check scheduling
        now = datetime.now()
        if flag.start_date and now < flag.start_date:
            return False
        if flag.end_date and now > flag.end_date:
            return False

        # Check user-specific targeting
        if user_id:
            # Check exclusions first
            if user_id in flag.exclude_user_ids:
                return False
            if user_groups and any(
                group in flag.exclude_groups for group in user_groups
            ):
                return False

            # Check explicit inclusions
            if user_id in flag.target_user_ids:
                return True
            if user_groups and any(
                group in flag.target_groups for group in user_groups
            ):
                return True

        # Evaluate conditions
        if not flag.evaluate_conditions(context):
            return False

        # Apply rollout percentage
        if flag.rollout_percentage >= 100.0:
            return True
        elif flag.rollout_percentage <= 0.0:
            return False
        else:
            # Deterministic rollout based on tenant + feature + user
            rollout_key = f"{flag.tenant_id}:{flag.feature_name}"
            if user_id:
                rollout_key += f":{user_id}"

            hash_value = int(hashlib.sha256(rollout_key.encode()).hexdigest(), 16)
            return (hash_value % 100) < flag.rollout_percentage

    def batch_evaluate(
        self,
        flags: list[FeatureFlag],
        context: dict[str, Any],
        user_id: Optional[str] = None,
        user_groups: Optional[list[str]] = None,
    ) -> dict[str, bool]:
        """Evaluate multiple feature flags at once."""
        results = {}
        for flag in flags:
            results[flag.feature_name] = self.evaluate_flag(
                flag, context, user_id, user_groups
            )
        return results


class FeatureFlagManager:
    """
    Manages feature flags and applies them to configurations.

    Handles feature flag evaluation, configuration injection,
    and integration with subscription plans.
    """

    def __init__(
        self,
        feature_registry: Optional[FeatureRegistry] = None,
        evaluator: Optional[FeatureFlagEvaluator] = None,
    ):
        """Initialize the feature flag manager."""
        self.registry = feature_registry or FeatureRegistry()
        self.evaluator = evaluator or FeatureFlagEvaluator()

        # In-memory storage for tenant feature flags
        # In production, this would be backed by a database
        self.tenant_flags: dict[UUID, dict[str, FeatureFlag]] = {}

    async def apply_feature_flags(
        self,
        config: ISPConfiguration,
        tenant_info: TenantInfo,
        user_context: Optional[dict[str, Any]] = None,
    ) -> ISPConfiguration:
        """
        Apply feature flags to configuration based on tenant information.

        Args:
            config: Base configuration
            tenant_info: Tenant information including subscription plan
            user_context: Optional user context for evaluation

        Returns:
            Configuration with feature flags applied
        """
        logger.info(f"Applying feature flags for tenant {tenant_info.tenant_id}")

        try:
            # Get or create feature flags for tenant
            tenant_flags = await self._get_tenant_flags(
                tenant_info.tenant_id, tenant_info.subscription_plan
            )

            # Evaluate flags
            evaluation_context = {
                "tenant_id": str(tenant_info.tenant_id),
                "plan": tenant_info.subscription_plan,
                "environment": config.environment,
                "timestamp": datetime.now().isoformat(),
                **(user_context or {}),
            }

            enabled_flags = {}
            for flag in tenant_flags.values():
                enabled_flags[flag.feature_name] = self.evaluator.evaluate_flag(
                    flag, evaluation_context
                )

            # Convert to FeatureFlagConfig objects
            feature_flag_configs = []
            for feature_name, enabled in enabled_flags.items():
                flag = tenant_flags.get(feature_name)
                if flag and enabled:
                    feature_definition = self.registry.get_feature(feature_name)
                    feature_config = FeatureFlagConfig(
                        feature_name=feature_name,
                        enabled=enabled,
                        rollout_percentage=flag.rollout_percentage,
                        config=self._merge_feature_config(
                            (
                                feature_definition.default_config
                                if feature_definition
                                else {}
                            ),
                            flag.config,
                        ),
                        description=(
                            feature_definition.description
                            if feature_definition
                            else None
                        ),
                    )
                    feature_flag_configs.append(feature_config)

            # Apply feature-specific configuration changes
            config = await self._apply_feature_configurations(
                config, enabled_flags, tenant_info
            )

            # Update config with feature flags
            config.feature_flags = feature_flag_configs

            logger.info(
                f"Applied {len(feature_flag_configs)} feature flags for tenant {tenant_info.tenant_id}"
            )
            return config

        except Exception as e:
            logger.error(
                f"Failed to apply feature flags for tenant {tenant_info.tenant_id}: {e}"
            )
            raise

    async def _get_tenant_flags(
        self, tenant_id: UUID, plan: SubscriptionPlan
    ) -> dict[str, FeatureFlag]:
        """Get or create feature flags for a tenant."""
        if tenant_id not in self.tenant_flags:
            self.tenant_flags[tenant_id] = {}

            # Create flags based on plan
            plan_features = self.registry.get_plan_features(plan)
            if plan_features:
                for feature_name, feature_config in plan_features.features.items():
                    if feature_config.enabled:
                        flag = FeatureFlag(
                            feature_name=feature_name,
                            tenant_id=tenant_id,
                            enabled=feature_config.enabled,
                            rollout_percentage=100.0,  # Default to full rollout
                            config=feature_config.config,
                        )
                        self.tenant_flags[tenant_id][feature_name] = flag

        return self.tenant_flags[tenant_id]

    async def _apply_feature_configurations(
        self,
        config: ISPConfiguration,
        enabled_flags: dict[str, bool],
        tenant_info: TenantInfo,
    ) -> ISPConfiguration:
        """Apply feature-specific configuration changes."""

        # Advanced Analytics Configuration
        if enabled_flags.get("advanced_analytics"):
            # Enable additional monitoring
            config.monitoring.tracing_enabled = True
            config.monitoring.grafana_dashboard_enabled = True

            # Add analytics service
            analytics_service_exists = any(
                s.name == "analytics" for s in config.services
            )
            if not analytics_service_exists:
                from ..schemas.config_schemas import ServiceConfig, ServiceStatus

                analytics_service = ServiceConfig(
                    name="analytics",
                    version="latest",
                    status=ServiceStatus.ENABLED,
                    environment_variables={
                        "ANALYTICS_MODE": "advanced",
                        "TENANT_ID": str(tenant_info.tenant_id),
                    },
                )
                config.services.append(analytics_service)

        # Premium API Configuration
        if enabled_flags.get("premium_api") or enabled_flags.get("enterprise_api"):
            feature_name = (
                "enterprise_api"
                if enabled_flags.get("enterprise_api")
                else "premium_api"
            )
            feature_def = self.registry.get_feature(feature_name)
            if feature_def:
                rate_limit = feature_def.resource_limits.get("requests_per_hour", 1000)
                config.security.rate_limit_requests_per_minute = min(
                    rate_limit // 60, 10000
                )

        # SSO Configuration
        if enabled_flags.get("sso"):
            # Add SSO service
            sso_service_exists = any(s.name == "sso" for s in config.services)
            if not sso_service_exists:
                from ..schemas.config_schemas import ServiceConfig, ServiceStatus

                sso_service = ServiceConfig(
                    name="sso",
                    version="latest",
                    status=ServiceStatus.ENABLED,
                    environment_variables={
                        "SSO_ENABLED": "true",
                        "TENANT_ID": str(tenant_info.tenant_id),
                    },
                    config={"protocols": ["saml", "oidc"], "max_providers": 3},
                )
                config.services.append(sso_service)

        # Custom Branding Configuration
        if enabled_flags.get("custom_branding") or enabled_flags.get("white_label"):
            # Update network configuration for custom domains
            if enabled_flags.get("white_label") and tenant_info.primary_domain:
                if tenant_info.primary_domain not in config.security.cors_origins:
                    config.security.cors_origins.append(
                        f"https://{tenant_info.primary_domain}"
                    )

        # Enterprise Integration Configuration
        if enabled_flags.get("enterprise_integration"):
            # Add webhook service
            webhook_service_exists = any(s.name == "webhook" for s in config.services)
            if not webhook_service_exists:
                from ..schemas.config_schemas import ServiceConfig, ServiceStatus

                webhook_service = ServiceConfig(
                    name="webhook",
                    version="latest",
                    status=ServiceStatus.ENABLED,
                    environment_variables={
                        "WEBHOOK_ENABLED": "true",
                        "TENANT_ID": str(tenant_info.tenant_id),
                    },
                )
                config.services.append(webhook_service)

        return config

    def _merge_feature_config(
        self, default_config: dict[str, Any], override_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge default feature config with overrides."""
        merged = default_config.copy()
        merged.update(override_config)
        return merged

    async def generate_plan_features(
        self, tenant_id: UUID, plan: SubscriptionPlan
    ) -> list[FeatureFlagConfig]:
        """Generate feature flags based on subscription plan."""
        plan_features = self.registry.get_plan_features(plan)
        if not plan_features:
            return []

        feature_configs = []
        for feature_name, feature_config in plan_features.features.items():
            if feature_config.enabled:
                feature_def = self.registry.get_feature(feature_name)
                config = FeatureFlagConfig(
                    feature_name=feature_name,
                    enabled=feature_config.enabled,
                    rollout_percentage=100.0,
                    config=feature_config.config,
                    description=feature_def.description if feature_def else None,
                )
                feature_configs.append(config)

        return feature_configs

    async def create_feature_flag(
        self,
        tenant_id: UUID,
        feature_name: str,
        enabled: bool = False,
        rollout_percentage: float = 0.0,
        target_users: Optional[list[str]] = None,
        conditions: Optional[dict[str, Any]] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> FeatureFlag:
        """Create a new feature flag for a tenant."""
        flag = FeatureFlag(
            feature_name=feature_name,
            tenant_id=tenant_id,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
            target_user_ids=target_users or [],
            conditions=conditions or {},
            config=config or {},
        )

        if tenant_id not in self.tenant_flags:
            self.tenant_flags[tenant_id] = {}

        self.tenant_flags[tenant_id][feature_name] = flag

        logger.info(f"Created feature flag {feature_name} for tenant {tenant_id}")
        return flag

    async def update_feature_flag(
        self,
        tenant_id: UUID,
        feature_name: str,
        enabled: Optional[bool] = None,
        rollout_percentage: Optional[float] = None,
        config: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Update an existing feature flag."""
        if tenant_id not in self.tenant_flags:
            return False

        flag = self.tenant_flags[tenant_id].get(feature_name)
        if not flag:
            return False

        if enabled is not None:
            flag.enabled = enabled
        if rollout_percentage is not None:
            flag.rollout_percentage = rollout_percentage
        if config is not None:
            flag.config.update(config)

        flag.updated_at = datetime.now()

        logger.info(f"Updated feature flag {feature_name} for tenant {tenant_id}")
        return True

    async def delete_feature_flag(self, tenant_id: UUID, feature_name: str) -> bool:
        """Delete a feature flag."""
        if tenant_id not in self.tenant_flags:
            return False

        if feature_name in self.tenant_flags[tenant_id]:
            del self.tenant_flags[tenant_id][feature_name]
            logger.info(f"Deleted feature flag {feature_name} for tenant {tenant_id}")
            return True

        return False

    async def list_tenant_flags(self, tenant_id: UUID) -> list[FeatureFlag]:
        """List all feature flags for a tenant."""
        if tenant_id not in self.tenant_flags:
            return []

        return list(self.tenant_flags[tenant_id].values())

    async def get_feature_usage_stats(self, tenant_id: UUID) -> dict[str, Any]:
        """Get feature usage statistics for a tenant."""
        if tenant_id not in self.tenant_flags:
            return {}

        flags = self.tenant_flags[tenant_id]
        stats = {
            "total_features": len(flags),
            "enabled_features": sum(1 for flag in flags.values() if flag.enabled),
            "features_by_category": {},
            "rollout_summary": {"full_rollout": 0, "partial_rollout": 0, "disabled": 0},
        }

        for flag in flags.values():
            feature_def = self.registry.get_feature(flag.feature_name)
            if feature_def:
                category = feature_def.category.value
                stats["features_by_category"][category] = (
                    stats["features_by_category"].get(category, 0) + 1
                )

            if not flag.enabled:
                stats["rollout_summary"]["disabled"] += 1
            elif flag.rollout_percentage >= 100:
                stats["rollout_summary"]["full_rollout"] += 1
            else:
                stats["rollout_summary"]["partial_rollout"] += 1

        return stats

    def register_custom_feature(self, feature: FeatureDefinition):
        """Register a custom feature definition."""
        self.registry.register_feature(feature)
