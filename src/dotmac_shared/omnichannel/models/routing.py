"""
Routing and assignment models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, ConfigDict


class RoutingStrategy(str, Enum):
    """Available routing strategies."""

    SKILL_BASED = "skill_based"
    ROUND_ROBIN = "round_robin"
    PRIORITY_BASED = "priority_based"
    RULE_BASED = "rule_based"
    GEOGRAPHIC = "geographic"
    WORKLOAD_BALANCED = "workload_balanced"
    CUSTOMER_PREFERENCE = "customer_preference"


class RoutingResult(BaseModel):
    """Result of routing operation."""

    success: bool
    interaction_id: UUID

    # Assignment details
    assigned_agent_id: Optional[UUID] = None
    assigned_agent_name: Optional[str] = None
    assigned_team: Optional[str] = None

    # Routing information
    routing_strategy: RoutingStrategy
    routing_reason: str = ""
    routing_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Timing
    routing_time_ms: Optional[int] = None
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

    # Failure information
    failure_reason: Optional[str] = None

    # Metrics
    agents_evaluated: int = 0
    rules_evaluated: int = 0

    # Additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class RoutingRule(BaseModel):
    """Rule-based routing configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str

    # Rule metadata
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    priority: int = Field(default=10, ge=1, le=100)  # Lower number = higher priority
    active: bool = True

    # Conditions (all must match)
    conditions: Dict[str, Any] = Field(default_factory=dict)

    # Actions to take when conditions match
    actions: List["RoutingAction"] = Field(default_factory=list)

    # Schedule (when rule is active)
    schedule: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Statistics
    times_triggered: int = 0
    last_triggered: Optional[datetime] = None

    # Additional data
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class RoutingAction(BaseModel):
    """Action to take when routing rule matches."""

    type: str = Field(
        ..., min_length=1
    )  # assign_to_team, assign_to_agent, escalate, etc.
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Conditional execution
    condition: Optional[str] = None

    # Order of execution
    order: int = 1


class RoutingConfiguration(BaseModel):
    """Tenant routing configuration."""

    tenant_id: str

    # Default strategy
    default_strategy: RoutingStrategy = RoutingStrategy.SKILL_BASED
    fallback_strategy: Optional[RoutingStrategy] = RoutingStrategy.ROUND_ROBIN

    # Strategy-specific settings
    skill_matching_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    workload_balance_factor: float = Field(default=0.8, ge=0.0, le=1.0)
    geographic_preference_weight: float = Field(default=0.3, ge=0.0, le=1.0)

    # Timeout and retry
    routing_timeout_seconds: int = Field(default=30, ge=1, le=300)
    max_routing_attempts: int = Field(default=3, ge=1, le=10)

    # Business hours and overflow
    business_hours: Optional[Dict[str, Any]] = None
    overflow_strategy: Optional[RoutingStrategy] = None
    overflow_team: Optional[str] = None

    # Rules
    routing_rules: List[RoutingRule] = Field(default_factory=list)

    # Updated timestamp
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        populate_by_name=True
    )


class SkillRequirement(BaseModel):
    """Skill requirement for routing."""

    skill_name: str = Field(..., min_length=1)
    minimum_level: int = Field(default=1, ge=1, le=5)
    required: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=10.0)


class RoutingContext(BaseModel):
    """Context information for routing decisions."""

    interaction_id: UUID
    customer_id: UUID
    tenant_id: str

    # Interaction details
    channel: str
    priority: str
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Skill requirements
    required_skills: List[SkillRequirement] = Field(default_factory=list)

    # Customer preferences
    customer_preferences: Dict[str, Any] = Field(default_factory=dict)

    # Historical context
    previous_interactions: int = 0
    previous_agent_id: Optional[UUID] = None
    customer_tier: Optional[str] = None

    # Timing constraints
    due_date: Optional[datetime] = None
    escalation_deadline: Optional[datetime] = None

    # Geographic information
    customer_location: Optional[Dict[str, str]] = None
    customer_timezone: Optional[str] = None

    # Additional context
    extra_data: Dict[str, Any] = Field(default_factory=dict, alias="metadata")

    model_config = ConfigDict(
        populate_by_name=True
    )


class RoutingMetrics(BaseModel):
    """Routing performance metrics."""

    tenant_id: str
    period_start: datetime
    period_end: datetime

    # Volume metrics
    total_routing_requests: int = 0
    successful_routings: int = 0
    failed_routings: int = 0

    # Timing metrics
    avg_routing_time_ms: Optional[float] = None
    median_routing_time_ms: Optional[float] = None
    max_routing_time_ms: Optional[int] = None

    # Strategy breakdown
    strategy_usage: Dict[str, int] = Field(default_factory=dict)
    strategy_success_rates: Dict[str, float] = Field(default_factory=dict)

    # Rule effectiveness
    rule_trigger_counts: Dict[str, int] = Field(default_factory=dict)
    rule_success_rates: Dict[str, float] = Field(default_factory=dict)

    # Agent metrics
    avg_workload_at_assignment: Optional[float] = None
    workload_distribution: Dict[str, int] = Field(default_factory=dict)

    # Quality metrics
    customer_satisfaction_score: Optional[float] = None
    escalation_rate: Optional[float] = None

    @property
    def success_rate(self) -> float:
        if self.total_routing_requests == 0:
            return 0.0
        return self.successful_routings / self.total_routing_requests
