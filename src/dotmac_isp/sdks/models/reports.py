"""Report models for analytics SDK."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from .enums import ReportType


class ReportStatus(str, Enum):
    """Report execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Report:
    """Report model."""

    report_id: UUID
    report_name: str
    report_type: ReportType
    query_config: dict[str, Any]
    schedule_config: Optional[dict[str, Any]] = None
    created_by: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ReportExecution:
    """Report execution model."""

    execution_id: UUID
    report_id: UUID
    status: ReportStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class ReportSubscription:
    """Report subscription model."""

    subscription_id: UUID
    report_id: UUID
    user_id: str
    email: str
    delivery_config: dict[str, Any]
    is_active: bool = True
    created_at: Optional[datetime] = None
