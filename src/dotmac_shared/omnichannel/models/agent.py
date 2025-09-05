"""
Agent management models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class AgentStatus(str, Enum):
    """Agent availability status."""

    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class AgentSkill(BaseModel):
    """Agent skill definition."""

    name: str = Field(..., min_length=1)
    level: int = Field(..., ge=1, le=5)  # 1=novice, 5=expert
    certified: bool = False
    certified_date: Optional[datetime] = None
    certified_by: Optional[str] = None


class AgentAvailability(BaseModel):
    """Agent availability schedule."""

    agent_id: UUID
    day_of_week: int = Field(..., ge=0, le=6)  # 0=Monday, 6=Sunday
    start_time: str = Field(..., pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")  # HH:MM format
    end_time: str = Field(..., pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = "UTC"
    is_available: bool = True


class AgentPerformanceMetrics(BaseModel):
    """Agent performance metrics."""

    agent_id: UUID
    period_start: datetime
    period_end: datetime

    # Interaction metrics
    total_interactions: int = 0
    resolved_interactions: int = 0
    escalated_interactions: int = 0

    # Timing metrics
    avg_response_time_minutes: Optional[float] = None
    avg_resolution_time_hours: Optional[float] = None

    # Quality metrics
    customer_satisfaction_score: Optional[float] = Field(None, ge=1.0, le=5.0)
    resolution_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    response_rate: Optional[float] = Field(None, ge=0.0, le=100.0)

    # Computed properties
    @property
    def resolution_rate(self) -> float:
        if self.total_interactions == 0:
            return 0.0
        return self.resolved_interactions / self.total_interactions


class AgentModel(BaseModel):
    """Core agent model."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    user_id: str  # Link to user management system

    # Personal information
    full_name: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = None

    # Status
    status: AgentStatus = AgentStatus.OFFLINE

    # Skills and capabilities
    skills: list[AgentSkill] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)

    # Capacity management
    max_concurrent_interactions: int = Field(default=5, ge=1, le=20)
    current_interaction_count: int = Field(default=0, ge=0)
    active_interactions: list[UUID] = Field(default_factory=list)

    # Organization
    team: Optional[str] = None
    department: Optional[str] = None
    manager_id: Optional[UUID] = None

    # Location and timezone
    location: Optional[str] = None
    timezone: str = "UTC"

    # Availability
    availability_schedule: list[AgentAvailability] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = None

    # Additional data
    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("current_interaction_count")
    @classmethod
    def validate_interaction_count(cls, v, values):
        """Ensure current count doesn't exceed maximum."""
        max_concurrent = values.get("max_concurrent_interactions", 5)
        if v > max_concurrent:
            raise ValueError(f"Current interaction count ({v}) cannot exceed maximum ({max_concurrent})")
        return v


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    user_id: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=1)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = None

    skills: list[AgentSkill] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)

    max_concurrent_interactions: int = Field(default=5, ge=1, le=20)
    team: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    timezone: str = "UTC"

    extra_data: dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class UpdateAgentRequest(BaseModel):
    """Request to update an existing agent."""

    full_name: Optional[str] = Field(None, min_length=1)
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")
    phone: Optional[str] = None

    status: Optional[AgentStatus] = None
    skills: Optional[list[AgentSkill]] = None
    languages: Optional[list[str]] = None
    channels: Optional[list[str]] = None

    max_concurrent_interactions: Optional[int] = Field(None, ge=1, le=20)
    team: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None

    extra_data: Optional[dict[str, Any]] = Field(None, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)
