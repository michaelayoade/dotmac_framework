"""Segment models for analytics SDK."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .enums import SegmentOperator


@dataclass
class SegmentRule:
    """Segment rule model."""

    rule_id: UUID
    field_name: str
    operator: SegmentOperator
    value: Any
    segment_id: Optional[UUID] = None


@dataclass
class Segment:
    """Segment model."""

    segment_id: UUID
    segment_name: str
    description: Optional[str] = None
    rules: List[SegmentRule] = None
    is_dynamic: bool = True
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.rules is None:
            self.rules = []


@dataclass
class SegmentMembership:
    """Segment membership model."""

    membership_id: UUID
    segment_id: UUID
    user_id: str
    added_at: datetime
    is_active: bool = True
