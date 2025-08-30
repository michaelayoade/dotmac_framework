"""Audit contract definitions."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class AuditEventType(str, Enum):
    """Audit event type enumeration."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke"
    ADMIN_ACTION = "admin_action"
    SYSTEM_EVENT = "system_event"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditOutcome(str, Enum):
    """Audit event outcomes."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


@dataclass
class AuditEvent:
    """Audit event definition."""

    id: str
    event_type: AuditEventType
    resource_type: str
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    description: str = ""
    details: Dict[str, Any] = None
    severity: AuditSeverity = AuditSeverity.INFO
    timestamp: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    source: str = "system"

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class AuditQuery:
    """Audit query filter."""

    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    event_types: Optional[List[AuditEventType]] = None
    resource_types: Optional[List[str]] = None
    resource_ids: Optional[List[str]] = None
    severity_levels: Optional[List[AuditSeverity]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_text: Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort_by: str = "timestamp"
    sort_desc: bool = True


@dataclass
class AuditQueryResponse:
    """Audit query response."""

    events: List[AuditEvent]
    total_count: int
    page_count: int
    current_page: int
    has_more: bool


@dataclass
class AuditExportRequest:
    """Audit export request."""

    query: AuditQuery
    format: str = "csv"  # csv, json, excel
    include_details: bool = True
    filename: Optional[str] = None


@dataclass
class AuditExportResponse:
    """Audit export response."""

    export_id: str
    status: str  # pending, processing, completed, failed
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    record_count: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class AuditMetrics:
    """Audit metrics response."""

    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    events_by_user: Dict[str, int]
    events_by_resource: Dict[str, int]
    time_range: Dict[str, Any]


@dataclass
class AuditHealthCheck:
    """Audit system health check response."""

    status: str  # healthy, degraded, unhealthy
    total_events_24h: int
    error_rate_24h: float
    average_response_time: float
    storage_usage_percent: float
    last_event_timestamp: Optional[datetime] = None
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


@dataclass
class AuditRetentionPolicy:
    """Audit retention policy definition."""

    policy_id: str
    name: str
    description: str = ""
    retention_days: int = 365
    archive_after_days: int = 90
    auto_delete: bool = True
    event_types: Optional[List[str]] = None
    severity_levels: Optional[List[str]] = None
    tenant_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.event_types is None:
            self.event_types = []
        if self.severity_levels is None:
            self.severity_levels = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


@dataclass
class AuditStats:
    """Audit statistics response."""

    total_events: int
    events_last_24h: int
    events_last_7d: int
    events_last_30d: int
    top_event_types: Dict[str, int]
    top_users: Dict[str, int]
    error_count_24h: int
    warning_count_24h: int
    critical_count_24h: int
    average_events_per_hour: float
    peak_hour: Optional[str] = None
    generated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc)
