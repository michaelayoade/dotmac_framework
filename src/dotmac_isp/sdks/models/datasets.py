"""Dataset models for analytics SDK."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID


class DataSourceType(str, Enum):
    """Data source type enumeration."""

    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    WEBHOOK = "webhook"


@dataclass
class DataSource:
    """Data source model."""

    source_id: UUID
    source_name: str
    source_type: DataSourceType
    connection_config: dict[str, Any]
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Dataset:
    """Dataset model."""

    dataset_id: UUID
    dataset_name: str
    source_id: UUID
    schema_definition: dict[str, Any]
    refresh_interval: Optional[int] = None  # seconds
    last_refresh: Optional[datetime] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DataPoint:
    """Data point model."""

    point_id: UUID
    dataset_id: UUID
    timestamp: datetime
    data: dict[str, Any]
    metadata: Optional[dict[str, Any]] = None
