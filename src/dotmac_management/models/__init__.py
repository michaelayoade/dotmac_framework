"""
SQLAlchemy models for the DotMac Management Platform.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .base import BaseModel
from .billing import (
    Commission,
    Invoice,
    Payment,
    PricingPlan,
    Subscription,
    UsageRecord,
)
from .deployment import (
    Deployment,
    DeploymentEvent,
    DeploymentResource,
    InfrastructureTemplate,
)
from .monitoring import Alert, HealthCheck, Metric, SLARecord
from .plugin import Plugin, PluginCategory, PluginLicense, PluginUsage
from .tenant import Tenant, TenantConfiguration, TenantInvitation
from .user import User

__all__ = [
    "BaseModel",
    "User",
    "Tenant",
    "TenantConfiguration",
    "TenantInvitation",
    "Subscription",
    "Invoice",
    "Payment",
    "PricingPlan",
    "UsageRecord",
    "Commission",
    "Deployment",
    "DeploymentEvent",
    "InfrastructureTemplate",
    "DeploymentResource",
    "Plugin",
    "PluginLicense",
    "PluginUsage",
    "PluginCategory",
    "HealthCheck",
    "Metric",
    "Alert",
    "SLARecord",
]
