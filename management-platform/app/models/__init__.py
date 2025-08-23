"""
SQLAlchemy models for the DotMac Management Platform.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .base import BaseModel
from .user import User
from .tenant import Tenant, TenantConfiguration, TenantInvitation
from .billing import (
    Subscription, 
    Invoice, 
    Payment, 
    PricingPlan, 
    UsageRecord,
    Commission
)
from .deployment import (
    Deployment, 
    DeploymentEvent, 
    InfrastructureTemplate,
    DeploymentResource
)
from .plugin import (
    Plugin, 
    PluginLicense, 
    PluginUsage, 
    PluginCategory
)
from .monitoring import (
    HealthCheck, 
    Metric, 
    Alert, 
    SLARecord
)

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