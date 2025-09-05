"""Test data factories for licensing scenarios."""

import importlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

factory = importlib.import_module("factory")

from dotmac_shared.container_config.schemas.tenant_schemas import SubscriptionPlan
from dotmac_shared.licensing.models import LicenseStatus


@dataclass
class TenantData:
    """Test tenant data structure."""

    tenant_id: str
    name: str
    subdomain: str
    subscription_plan: SubscriptionPlan
    primary_domain: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class LicenseContractData:
    """Test license contract data structure."""

    contract_id: str
    subscription_id: str
    tenant_id: str
    status: LicenseStatus
    valid_from: datetime
    valid_until: datetime
    contract_type: str
    max_customers: Optional[int]
    max_concurrent_users: Optional[int]
    max_api_calls_per_hour: Optional[int]
    max_network_devices: Optional[int]
    enabled_features: list[str]
    disabled_features: list[str]
    feature_limits: dict[str, int]
    enforcement_mode: str = "strict"


@dataclass
class FeatureFlagData:
    """Test feature flag data structure."""

    feature_name: str
    tenant_id: str
    enabled: bool
    rollout_percentage: float
    target_user_ids: list[str]
    target_groups: list[str]
    exclude_user_ids: list[str]
    exclude_groups: list[str]
    conditions: dict[str, Any]
    config: dict[str, Any]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TenantFactory(factory.Factory):
    """Factory for creating test tenant data."""

    class Meta:
        model = TenantData

    tenant_id = factory.LazyFunction(lambda: f"tenant-{uuid.uuid4().hex[:8]}")
    name = factory.Faker("company")
    subdomain = factory.LazyAttribute(lambda obj: obj.tenant_id.replace("tenant-", ""))
    subscription_plan = factory.Faker(
        "random_element", elements=["basic", "premium", "enterprise"]
    )
    primary_domain = factory.LazyAttribute(lambda obj: f"{obj.subdomain}.isp.local")
    is_active = True
    created_at = factory.LazyFunction(datetime.now)

    @classmethod
    def basic_plan(cls, **kwargs):
        """Create a tenant with basic plan."""
        return cls(subscription_plan="basic", **kwargs)

    @classmethod
    def premium_plan(cls, **kwargs):
        """Create a tenant with premium plan."""
        return cls(subscription_plan="premium", **kwargs)

    @classmethod
    def enterprise_plan(cls, **kwargs):
        """Create a tenant with enterprise plan."""
        return cls(subscription_plan="enterprise", **kwargs)

    @classmethod
    def inactive_tenant(cls, **kwargs):
        """Create an inactive tenant."""
        return cls(is_active=False, **kwargs)


class LicenseContractFactory(factory.Factory):
    """Factory for creating test license contracts."""

    class Meta:
        model = LicenseContractData

    contract_id = factory.LazyFunction(lambda: f"contract-{uuid.uuid4().hex[:12]}")
    subscription_id = factory.LazyFunction(lambda: f"sub-{uuid.uuid4().hex[:8]}")
    tenant_id = factory.LazyFunction(lambda: f"tenant-{uuid.uuid4().hex[:8]}")
    status = LicenseStatus.ACTIVE
    valid_from = factory.LazyFunction(lambda: datetime.now() - timedelta(days=1))
    valid_until = factory.LazyFunction(lambda: datetime.now() + timedelta(days=365))
    contract_type = "premium"

    # Basic limits for premium plan
    max_customers = 1000
    max_concurrent_users = 50
    max_api_calls_per_hour = 10000
    max_network_devices = 100

    enabled_features = factory.LazyFunction(
        lambda: [
            "basic_analytics",
            "premium_api",
            "custom_branding",
            "email_support",
            "phone_support",
        ]
    )
    disabled_features = factory.LazyFunction(lambda: [])
    feature_limits = factory.LazyFunction(
        lambda: {"max_integrations": 10, "max_webhooks": 5}
    )
    enforcement_mode = "strict"

    @classmethod
    def basic_license(cls, **kwargs):
        """Create a basic license contract."""
        return cls(
            contract_type="basic",
            max_customers=100,
            max_concurrent_users=10,
            max_api_calls_per_hour=1000,
            max_network_devices=20,
            enabled_features=["basic_analytics", "standard_api", "email_support"],
            feature_limits={"max_integrations": 3},
            **kwargs,
        )

    @classmethod
    def enterprise_license(cls, **kwargs):
        """Create an enterprise license contract."""
        return cls(
            contract_type="enterprise",
            max_customers=10000,
            max_concurrent_users=500,
            max_api_calls_per_hour=100000,
            max_network_devices=1000,
            enabled_features=[
                "basic_analytics",
                "advanced_analytics",
                "enterprise_api",
                "sso",
                "advanced_security",
                "white_label",
                "priority_support",
                "enterprise_integration",
            ],
            feature_limits={
                "max_integrations": -1,  # Unlimited
                "max_webhooks": -1,
            },
            **kwargs,
        )

    @classmethod
    def expired_license(cls, **kwargs):
        """Create an expired license contract."""
        return cls(
            status=LicenseStatus.EXPIRED,
            valid_until=datetime.now() - timedelta(days=30),
            **kwargs,
        )

    @classmethod
    def suspended_license(cls, **kwargs):
        """Create a suspended license contract."""
        return cls(status=LicenseStatus.SUSPENDED, **kwargs)

    @classmethod
    def trial_license(cls, **kwargs):
        """Create a trial license (short duration)."""
        return cls(
            contract_type="trial",
            valid_until=datetime.now() + timedelta(days=14),
            max_customers=10,
            max_concurrent_users=5,
            max_api_calls_per_hour=500,
            max_network_devices=5,
            enabled_features=["basic_analytics", "standard_api", "email_support"],
            **kwargs,
        )


class FeatureFlagFactory(factory.Factory):
    """Factory for creating test feature flags."""

    class Meta:
        model = FeatureFlagData

    feature_name = factory.Faker(
        "random_element",
        elements=[
            "advanced_analytics",
            "premium_api",
            "sso",
            "custom_branding",
            "white_label",
            "enterprise_integration",
            "priority_support",
        ],
    )
    tenant_id = factory.LazyFunction(lambda: f"tenant-{uuid.uuid4().hex[:8]}")
    enabled = True
    rollout_percentage = 100.0
    target_user_ids = factory.LazyFunction(list)
    target_groups = factory.LazyFunction(list)
    exclude_user_ids = factory.LazyFunction(list)
    exclude_groups = factory.LazyFunction(list)
    conditions = factory.LazyFunction(dict)
    config = factory.LazyFunction(dict)

    @classmethod
    def disabled_feature(cls, **kwargs):
        """Create a disabled feature flag."""
        return cls(enabled=False, rollout_percentage=0.0, **kwargs)

    @classmethod
    def partial_rollout(cls, percentage: float = 50.0, **kwargs):
        """Create a feature flag with partial rollout."""
        return cls(rollout_percentage=percentage, **kwargs)

    @classmethod
    def targeted_rollout(
        cls, user_ids: list[str] = None, groups: list[str] = None, **kwargs
    ):
        """Create a feature flag with targeted rollout."""
        return cls(
            target_user_ids=user_ids or [],
            target_groups=groups or [],
            rollout_percentage=0.0,  # Use targeting instead of percentage
            **kwargs,
        )

    @classmethod
    def scheduled_feature(
        cls, start_date: datetime = None, end_date: datetime = None, **kwargs
    ):
        """Create a scheduled feature flag."""
        return cls(
            start_date=start_date or datetime.now() + timedelta(hours=1),
            end_date=end_date or datetime.now() + timedelta(days=30),
            **kwargs,
        )


class UserFactory(factory.Factory):
    """Factory for creating test users."""

    class Meta:
        model = dict  # Simple dict for user data

    user_id = factory.LazyFunction(lambda: f"user-{uuid.uuid4().hex[:8]}")
    tenant_id = factory.LazyFunction(lambda: f"tenant-{uuid.uuid4().hex[:8]}")
    email = factory.Faker("email")
    role = factory.Faker("random_element", elements=["admin", "manager", "user"])
    permissions = factory.LazyFunction(lambda: ["read", "write"])
    groups = factory.LazyFunction(list)
    is_active = True

    @classmethod
    def admin_user(cls, **kwargs):
        """Create an admin user."""
        return cls(
            role="admin", permissions=["read", "write", "admin", "billing"], **kwargs
        )

    @classmethod
    def basic_user(cls, **kwargs):
        """Create a basic user."""
        return cls(role="user", permissions=["read"], **kwargs)


class TestScenarioFactory:
    """Factory for creating complete test scenarios."""

    @staticmethod
    def basic_tenant_with_license():
        """Create a basic tenant with matching license."""
        tenant = TenantFactory.basic_plan()
        license = LicenseContractFactory.basic_license(tenant_id=tenant.tenant_id)
        return tenant, license

    @staticmethod
    def premium_tenant_with_license():
        """Create a premium tenant with matching license."""
        tenant = TenantFactory.premium_plan()
        license = LicenseContractFactory(tenant_id=tenant.tenant_id)
        return tenant, license

    @staticmethod
    def enterprise_tenant_with_license():
        """Create an enterprise tenant with matching license."""
        tenant = TenantFactory.enterprise_plan()
        license = LicenseContractFactory.enterprise_license(tenant_id=tenant.tenant_id)
        return tenant, license

    @staticmethod
    def tenant_approaching_limits():
        """Create a tenant near license limits."""
        tenant = TenantFactory.basic_plan()
        license = LicenseContractFactory.basic_license(
            tenant_id=tenant.tenant_id,
            max_customers=100,  # Will test with 95+ customers
            max_api_calls_per_hour=1000,  # Will test with 950+ calls
        )
        return tenant, license

    @staticmethod
    def tenant_with_expired_license():
        """Create a tenant with expired license."""
        tenant = TenantFactory.basic_plan()
        license = LicenseContractFactory.expired_license(tenant_id=tenant.tenant_id)
        return tenant, license

    @staticmethod
    def multi_app_tenant():
        """Create a tenant with multiple app subscriptions."""
        tenant = TenantFactory.enterprise_plan()
        license = LicenseContractFactory.enterprise_license(
            tenant_id=tenant.tenant_id,
            enabled_features=[
                "basic_analytics",
                "advanced_analytics",
                "enterprise_api",
                "sso",
                "white_label",
                "enterprise_integration",
                "priority_support",
            ],
        )

        # Feature flags for different apps
        feature_flags = [
            FeatureFlagFactory(feature_name="crm_access", tenant_id=tenant.tenant_id),
            FeatureFlagFactory(
                feature_name="field_ops_access", tenant_id=tenant.tenant_id
            ),
            FeatureFlagFactory(
                feature_name="reseller_portal", tenant_id=tenant.tenant_id
            ),
        ]

        return tenant, license, feature_flags
