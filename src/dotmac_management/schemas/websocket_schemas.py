"""WebSocket Event Schemas for the Management Platform."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ..models.websocket_event import DeliveryStatus, EventPriority, EventType, SubscriptionType


# Base Schemas

class BaseSchema(BaseModel):
    """Base schema with common fields."""
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[BaseModel]
    total: int
    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)
    pages: int


# WebSocket Event Schemas

class WebSocketEventBase(BaseModel):
    """Base WebSocket event schema."""
    event_type: EventType
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    event_data: Dict = Field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    requires_acknowledgment: bool = False
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760)  # Max 1 year
    
    @field_validator('event_data')
    @classmethod
    def validate_event_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError('event_data must be a dictionary')
        return v


class WebSocketEventCreate(WebSocketEventBase):
    """Schema for creating WebSocket events."""
    target_user_id: Optional[str] = Field(None, min_length=1)
    target_user_ids: Optional[List[str]] = Field(None, max_length=100)
    broadcast_to_tenant: bool = False
    source_entity_type: Optional[str] = Field(None, max_length=50)
    source_entity_id: Optional[str] = Field(None, max_length=100)
    
    @field_validator('target_user_ids')
    @classmethod
    def validate_target_users(cls, v, values):
        if v and values.get('target_user_id'):
            raise ValueError('Cannot specify both target_user_id and target_user_ids')
        if v and values.get('broadcast_to_tenant'):
            raise ValueError('Cannot specify target_user_ids when broadcasting to tenant')
        return v


class WebSocketEventUpdate(BaseModel):
    """Schema for updating WebSocket events."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[EventPriority] = None
    expires_in_hours: Optional[int] = Field(None, ge=1, le=8760)


class WebSocketEventResponse(WebSocketEventBase, BaseSchema):
    """Response schema for WebSocket events."""
    event_id: str
    tenant_id: str
    event_category: str
    target_user_id: Optional[str]
    target_user_ids: Optional[List[str]]
    broadcast_to_tenant: bool
    delivery_status: DeliveryStatus
    delivery_attempts: int = Field(ge=0)
    delivered_at: Optional[datetime]
    scheduled_for: Optional[datetime]
    expires_at: Optional[datetime]
    source_service: Optional[str]
    source_entity_type: Optional[str]
    source_entity_id: Optional[str]
    acknowledged_by: Optional[List[str]]
    acknowledged_at: Optional[datetime]
    error_message: Optional[str]
    
    # Computed properties
    is_expired: Optional[bool] = None
    is_due_for_delivery: Optional[bool] = None
    acknowledgment_rate: Optional[float] = None


class WebSocketEventListResponse(PaginatedResponse):
    """Paginated WebSocket event list response."""
    items: List[WebSocketEventResponse]


# WebSocket Connection Schemas

class WebSocketConnectionBase(BaseModel):
    """Base WebSocket connection schema."""
    session_id: Optional[str] = Field(None, max_length=100)
    client_ip: Optional[str] = Field(None, max_length=45)
    user_agent: Optional[str] = Field(None, max_length=500)
    origin: Optional[str] = Field(None, max_length=200)


class WebSocketConnectionCreate(WebSocketConnectionBase):
    """Schema for creating WebSocket connections."""
    user_id: str = Field(..., min_length=1)


class WebSocketConnectionResponse(WebSocketConnectionBase, BaseSchema):
    """Response schema for WebSocket connections."""
    connection_id: str
    tenant_id: str
    user_id: str
    connected_at: datetime
    last_ping: Optional[datetime]
    last_activity: Optional[datetime]
    disconnected_at: Optional[datetime]
    is_active: bool
    protocol_version: str = "1.0"
    compression_enabled: bool = False
    messages_sent: int = Field(ge=0)
    messages_received: int = Field(ge=0)
    bytes_sent: int = Field(ge=0)
    bytes_received: int = Field(ge=0)
    active_subscriptions: List[str] = Field(default_factory=list)
    error_count: int = Field(ge=0)
    last_error: Optional[str]
    average_latency_ms: Optional[int]
    connection_quality_score: int = Field(ge=0, le=100)
    
    # Computed properties
    connection_duration_seconds: Optional[float] = None
    is_stale: Optional[bool] = None


# WebSocket Subscription Schemas

class WebSocketSubscriptionBase(BaseModel):
    """Base WebSocket subscription schema."""
    subscription_name: str = Field(..., min_length=1, max_length=100)
    subscription_type: SubscriptionType = SubscriptionType.EVENT_TYPE
    event_types: Optional[List[EventType]] = Field(None, max_length=50)
    entity_filter: Optional[Dict] = Field(None)
    priority_filter: Optional[EventPriority] = None
    auto_acknowledge: bool = False


class WebSocketSubscriptionCreate(WebSocketSubscriptionBase):
    """Schema for creating WebSocket subscriptions."""
    connection_id: str = Field(..., min_length=1)


class WebSocketSubscriptionResponse(WebSocketSubscriptionBase, BaseSchema):
    """Response schema for WebSocket subscriptions."""
    connection_id: str
    user_id: str
    tenant_id: str
    is_active: bool
    events_received: int = Field(ge=0)
    last_event_received: Optional[datetime]
    subscribed_at: datetime
    unsubscribed_at: Optional[datetime]


# WebSocket Delivery Schemas

class WebSocketDeliveryResponse(BaseModel):
    """Response schema for WebSocket deliveries."""
    delivery_id: str
    event_id: str
    connection_id: str
    user_id: str
    tenant_id: str
    attempted_at: datetime
    delivered_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    status: DeliveryStatus
    attempt_count: int = Field(ge=1)
    delivery_latency_ms: Optional[int]
    message_size_bytes: Optional[int]
    error_code: Optional[str]
    error_message: Optional[str]
    client_response: Optional[Dict]
    
    # Computed properties
    was_successful: Optional[bool] = None
    needs_retry: Optional[bool] = None


# WebSocket Metrics Schemas

class WebSocketMetricsResponse(BaseModel):
    """Response schema for WebSocket metrics."""
    tenant_id: str
    metric_date: datetime
    metric_hour: int = Field(ge=0, le=23)
    user_id: Optional[str]
    total_connections: int = Field(ge=0)
    unique_users: int = Field(ge=0)
    average_connection_duration_seconds: int = Field(ge=0)
    total_connection_time_seconds: int = Field(ge=0)
    total_messages_sent: int = Field(ge=0)
    total_messages_received: int = Field(ge=0)
    total_bytes_sent: int = Field(ge=0)
    total_bytes_received: int = Field(ge=0)
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_priority: Dict[str, int] = Field(default_factory=dict)
    delivery_success_rate: int = Field(ge=0, le=100)
    average_delivery_latency_ms: int = Field(ge=0)
    total_errors: int = Field(ge=0)
    error_breakdown: Dict[str, int] = Field(default_factory=dict)
    peak_concurrent_connections: int = Field(ge=0)
    average_latency_ms: int = Field(ge=0)
    bandwidth_usage_mb: int = Field(ge=0)
    
    # Computed properties
    total_bandwidth_mb: Optional[float] = None
    messages_per_connection: Optional[float] = None


# Statistics and Analytics Schemas

class EventStatsResponse(BaseModel):
    """Event statistics response."""
    tenant_id: str
    total_events: int = Field(ge=0)
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_priority: Dict[str, int] = Field(default_factory=dict)
    delivery_success_rate: float = Field(ge=0, le=100)
    total_deliveries: int = Field(ge=0)
    successful_deliveries: int = Field(ge=0)
    active_connections: int = Field(ge=0)
    period_days: int = Field(ge=1)


class ConnectionStatsResponse(BaseModel):
    """Connection statistics response."""
    total_connections: int = Field(ge=0)
    connections_by_tenant: Dict[str, int] = Field(default_factory=dict)
    connections_by_user: Dict[str, int] = Field(default_factory=dict)
    total_subscriptions: int = Field(ge=0)


# WebSocket Message Schemas

class WebSocketMessageRequest(BaseModel):
    """WebSocket message request schema."""
    type: str = Field(..., min_length=1)
    data: Dict = Field(default_factory=dict)
    subscription_filter: Optional[str] = Field(None, max_length=100)


class BroadcastRequest(BaseModel):
    """Broadcast request schema."""
    event_type: EventType
    title: str = Field(..., min_length=1, max_length=200)
    data: Dict = Field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    target_user_ids: Optional[List[str]] = Field(None, max_length=100)
    requires_acknowledgment: bool = False


class EventAcknowledgmentRequest(BaseModel):
    """Event acknowledgment request schema."""
    event_id: str = Field(..., min_length=1)
    response_data: Optional[Dict] = Field(None)


# Export all schemas
__all__ = [
    # Base
    "BaseSchema",
    "PaginatedResponse",
    
    # Events
    "WebSocketEventBase",
    "WebSocketEventCreate",
    "WebSocketEventUpdate",
    "WebSocketEventResponse",
    "WebSocketEventListResponse",
    
    # Connections
    "WebSocketConnectionBase",
    "WebSocketConnectionCreate", 
    "WebSocketConnectionResponse",
    
    # Subscriptions
    "WebSocketSubscriptionBase",
    "WebSocketSubscriptionCreate",
    "WebSocketSubscriptionResponse",
    
    # Deliveries
    "WebSocketDeliveryResponse",
    
    # Metrics
    "WebSocketMetricsResponse",
    
    # Statistics
    "EventStatsResponse",
    "ConnectionStatsResponse",
    
    # Messages
    "WebSocketMessageRequest",
    "BroadcastRequest",
    "EventAcknowledgmentRequest",
]