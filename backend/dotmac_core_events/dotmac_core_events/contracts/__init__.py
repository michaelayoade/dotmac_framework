"""
Contracts package for dotmac_core_events.

Provides shared contract definitions for:
- Event schemas and data models
- API request/response models
- Common validation schemas
- Type definitions
"""

from .common_schemas import (
    CompatibilityLevel,
    ComponentHealth,
    EventMessage,
    EventMetadata,
    HealthStatus,
    MetricsData,
    PublishResult,
    SubscriptionConfig,
    ValidationResult,
)
from .events_contract import (
    EventHistoryRequest,
    EventHistoryResponse,
    PublishEventRequest,
    PublishEventResponse,
    ReplayRequest,
    ReplayResponse,
    SubscribeRequest,
    SubscribeResponse,
    TopicInfoResponse,
    UnsubscribeRequest,
)

__all__ = [
    # Common schemas
    "EventMetadata",
    "EventMessage",
    "PublishResult",
    "SubscriptionConfig",
    "ValidationResult",
    "CompatibilityLevel",
    "HealthStatus",
    "ComponentHealth",
    "MetricsData",

    # Event contracts
    "PublishEventRequest",
    "PublishEventResponse",
    "SubscribeRequest",
    "SubscribeResponse",
    "UnsubscribeRequest",
    "EventHistoryRequest",
    "EventHistoryResponse",
    "ReplayRequest",
    "ReplayResponse",
    "TopicInfoResponse",
]
