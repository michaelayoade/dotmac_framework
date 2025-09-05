"""Feature flag and capability schemas."""
import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class FeatureStatus(str, Enum):
    """Feature status options."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    BETA = "beta"
    DEPRECATED = "deprecated"
    COMING_SOON = "coming_soon"


class FeatureCategory(str, Enum):
    """Feature categories for organization."""

    CORE = "core"
    ANALYTICS = "analytics"
    BILLING = "billing"
    INTEGRATION = "integration"
    SECURITY = "security"
    NETWORKING = "networking"
    UI_UX = "ui_ux"
    API = "api"
    MONITORING = "monitoring"
    CUSTOM = "custom"


class RolloutStrategy(str, Enum):
    """Feature rollout strategies."""

    INSTANT = "instant"
    GRADUAL = "gradual"
    TARGETED = "targeted"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"


class FeatureDefinition(BaseModel):
    """Feature definition and metadata."""

    # Basic information
    name: str = Field(..., min_length=1, max_length=100, description="Feature name/key")
    display_name: str = Field(..., min_length=1, description="Human-readable feature name")
    description: str = Field(..., min_length=1, description="Feature description")
    category: FeatureCategory = Field(..., description="Feature category")

    # Status and lifecycle
    status: FeatureStatus = Field(default=FeatureStatus.DISABLED, description="Feature status")
    version: str = Field(default="1.0.0", description="Feature version")

    # Availability
    available_plans: list[str] = Field(..., description="Plans that can use this feature")
    requires_features: list[str] = Field(default_factory=list, description="Required dependency features")
    conflicts_with: list[str] = Field(default_factory=list, description="Conflicting features")

    # Configuration schema
    config_schema: dict[str, Any] = Field(default_factory=dict, description="Configuration schema")
    default_config: dict[str, Any] = Field(default_factory=dict, description="Default configuration")

    # Limits and quotas
    resource_limits: dict[str, Union[int, float]] = Field(default_factory=dict, description="Resource limits")
    usage_quotas: dict[str, int] = Field(default_factory=dict, description="Usage quotas")

    # Rollout configuration
    rollout_strategy: RolloutStrategy = Field(default=RolloutStrategy.INSTANT, description="Rollout strategy")
    rollout_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Rollout percentage")

    # Documentation and support
    documentation_url: Optional[str] = Field(None, description="Feature documentation URL")
    support_contact: Optional[str] = Field(None, description="Support contact for feature")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Feature creator")

    # Tags for organization
    tags: list[str] = Field(default_factory=list, description="Feature tags")

    @field_validator("name")
    @classmethod
    def validate_feature_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Feature name must contain only lowercase letters, numbers, and underscores")
        return v

    @field_validator("available_plans")
    @classmethod
    def validate_available_plans(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Feature must be available to at least one plan")
        return v

    def is_available_for_plan(self, plan: str) -> bool:
        """Check if feature is available for a specific plan."""
        return plan in self.available_plans

    def get_config_for_plan(self, plan: str, custom_config: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Get feature configuration for a specific plan."""
        if not self.is_available_for_plan(plan):
            return {}

        config = self.default_config.copy()
        if custom_config:
            config.update(custom_config)
        return config


class FeatureFlag(BaseModel):
    """Individual feature flag instance for a tenant."""

    # Reference to feature definition
    feature_name: str = Field(..., description="Feature name (references FeatureDefinition)")
    tenant_id: UUID = Field(..., description="Tenant this flag applies to")

    # Flag state
    enabled: bool = Field(default=False, description="Whether feature is enabled")
    rollout_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Rollout percentage")

    # Configuration
    config: dict[str, Any] = Field(default_factory=dict, description="Feature-specific configuration")

    # Targeting
    target_user_ids: list[str] = Field(default_factory=list, description="Specific user IDs to target")
    target_groups: list[str] = Field(default_factory=list, description="User groups to target")
    exclude_user_ids: list[str] = Field(default_factory=list, description="User IDs to exclude")
    exclude_groups: list[str] = Field(default_factory=list, description="User groups to exclude")

    # Conditions
    conditions: dict[str, Any] = Field(default_factory=dict, description="Conditional logic for enabling")

    # Scheduling
    start_date: Optional[datetime] = Field(None, description="Feature start date")
    end_date: Optional[datetime] = Field(None, description="Feature end date")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Flag creator")

    # Override settings
    override_global: bool = Field(default=False, description="Override global feature settings")
    priority: int = Field(default=0, description="Priority for conflict resolution")

    def is_enabled_for_user(self, user_id: str, user_groups: Optional[list[str]] = None) -> bool:
        """Check if feature is enabled for a specific user."""
        if not self.enabled:
            return False

        # Check scheduling
        now = datetime.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False

        # Check exclusions first
        if user_id in self.exclude_user_ids:
            return False
        if user_groups and any(group in self.exclude_groups for group in user_groups):
            return False

        # Check explicit inclusions
        if user_id in self.target_user_ids:
            return True
        if user_groups and any(group in self.target_groups for group in user_groups):
            return True

        # Check rollout percentage
        if self.rollout_percentage >= 100.0:
            return True
        if self.rollout_percentage <= 0.0:
            return False

        # Use consistent hash of user ID for deterministic rollout
        hash_value = int(hashlib.sha256(f"{self.tenant_id}:{self.feature_name}:{user_id}".encode()).hexdigest(), 16)
        return (hash_value % 100) < self.rollout_percentage

    def evaluate_conditions(self, context: dict[str, Any]) -> bool:
        """Evaluate conditional logic for feature enablement."""
        if not self.conditions:
            return True

        # Simple condition evaluation - can be extended
        for condition_key, condition_value in self.conditions.items():
            context_value = context.get(condition_key)

            if isinstance(condition_value, dict):
                for operator, operand in condition_value.items():
                    if not self._evaluate_operator(context_value, operator, operand):
                        return False
            else:
                if context_value != condition_value:
                    return False

        return True

    def _evaluate_operator(self, value: Any, operator: str, operand: Any) -> bool:
        """Evaluate a single operator condition."""
        try:
            if operator == ">":
                return value > operand
            if operator == ">=":
                return value >= operand
            if operator == "<":
                return value < operand
            if operator == "<=":
                return value <= operand
            if operator == "==":
                return value == operand
            if operator == "!=":
                return value != operand
            if operator == "in":
                return value in operand
            if operator == "contains":
                return operand in value
        except Exception:
            return False
        return False
        """Evaluate a single condition operator."""
        try:
            if operator == "==":
                return value == operand
            elif operator == "!=":
                return value != operand
            elif operator == ">":
                return value > operand
            elif operator == ">=":
                return value >= operand
            elif operator == "<":
                return value < operand
            elif operator == "<=":
                return value <= operand
            elif operator == "in":
                return value in operand
            elif operator == "not_in":
                return value not in operand
            elif operator == "contains":
                return operand in str(value)
            elif operator == "starts_with":
                return str(value).startswith(str(operand))
            elif operator == "ends_with":
                return str(value).endswith(str(operand))
            else:
                return False
        except (TypeError, AttributeError):
            return False


class PlanFeatures(BaseModel):
    """Feature configuration for a subscription plan."""

    plan_name: str = Field(..., description="Subscription plan name")
    features: dict[str, dict] = Field(default_factory=dict, description="Feature configurations for this plan")

    # Plan-level limits
    feature_limits: dict[str, Union[int, float]] = Field(default_factory=dict, description="Plan feature limits")

    # Inheritance
    inherits_from: Optional[str] = Field(None, description="Plan to inherit features from")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")

    def get_feature_config(self, feature_name: str) -> Optional[dict]:
        """Get configuration for a specific feature."""
        return self.features.get(feature_name)

    def is_feature_available(self, feature_name: str) -> bool:
        """Check if a feature is available in this plan."""
        config = self.get_feature_config(feature_name)
        return config is not None and config.enabled

    def get_feature_limit(self, feature_name: str, limit_type: str) -> Optional[Union[int, float]]:
        """Get a specific limit for a feature."""
        config = self.get_feature_config(feature_name)
        if not config:
            return None
        return config.limits.get(limit_type, self.feature_limits.get(f"{feature_name}_{limit_type}"))


class FeatureConfigurationPlaceholder(BaseModel):
    """Configuration for a feature within a plan."""

    enabled: bool = Field(default=False, description="Feature enabled in plan")
    config: dict[str, Any] = Field(default_factory=dict, description="Feature configuration")
    limits: dict[str, Union[int, float]] = Field(default_factory=dict, description="Feature-specific limits")

    # Access control
    requires_admin: bool = Field(default=False, description="Requires admin access")
    requires_permission: Optional[str] = Field(None, description="Required permission")

    # Billing
    billable: bool = Field(default=False, description="Feature is billable")
    billing_metric: Optional[str] = Field(None, description="Billing metric name")

    # Usage tracking
    track_usage: bool = Field(default=False, description="Track feature usage")
    usage_metrics: list[str] = Field(default_factory=list, description="Usage metrics to track")


# Factory functions for common feature configurations
def create_basic_feature_config(enabled: bool = True) -> dict:
    """Create a basic feature configuration."""
    return {"enabled": enabled}


def create_limited_feature_config(enabled: bool = True, limits: Optional[dict[str, Union[int, float]]] = None) -> dict:
    """Create a feature configuration with limits."""
    return {"enabled": enabled, "limits": limits or {}, "track_usage": True}


def create_billable_feature_config(enabled: bool = True, billing_metric: str = "usage_count") -> dict:
    """Create a billable feature configuration."""
    return {
        "enabled": enabled,
        "billable": True,
        "billing_metric": billing_metric,
        "track_usage": True,
        "usage_metrics": ["count", "duration"],
    }


def create_admin_feature_config(enabled: bool = True) -> dict:
    """Create an admin-only feature configuration."""
    return {"enabled": enabled, "requires_admin": True}


# Predefined plan features
DEFAULT_PLAN_FEATURES = {
    "basic": PlanFeatures(
        plan_name="basic",
        features={
            "basic_analytics": create_basic_feature_config(),
            "email_support": create_basic_feature_config(),
            "standard_api": create_limited_feature_config(limits={"requests_per_hour": 1000}),
            "basic_integration": create_basic_feature_config(),
        },
    ),
    "premium": PlanFeatures(
        plan_name="premium",
        features={
            "basic_analytics": create_basic_feature_config(),
            "advanced_analytics": create_basic_feature_config(),
            "email_support": create_basic_feature_config(),
            "phone_support": create_basic_feature_config(),
            "premium_api": create_limited_feature_config(limits={"requests_per_hour": 10000}),
            "standard_integration": create_basic_feature_config(),
            "premium_integration": create_basic_feature_config(),
            "custom_branding": create_basic_feature_config(),
        },
    ),
    "enterprise": PlanFeatures(
        plan_name="enterprise",
        features={
            "basic_analytics": create_basic_feature_config(),
            "advanced_analytics": create_basic_feature_config(),
            "email_support": create_basic_feature_config(),
            "phone_support": create_basic_feature_config(),
            "priority_support": create_basic_feature_config(),
            "enterprise_api": create_limited_feature_config(limits={"requests_per_hour": 100000}),
            "standard_integration": create_basic_feature_config(),
            "premium_integration": create_basic_feature_config(),
            "enterprise_integration": create_basic_feature_config(),
            "custom_branding": create_basic_feature_config(),
            "white_label": create_basic_feature_config(),
            "sso": create_admin_feature_config(),
            "advanced_security": create_admin_feature_config(),
            "custom_domains": create_admin_feature_config(),
        },
    ),
}
