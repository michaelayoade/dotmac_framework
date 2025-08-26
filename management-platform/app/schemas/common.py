"""
Common schemas for pagination and responses.
"""

from datetime import datetime, timezone
from typing import Generic, TypeVar, List, Optional, Any, Dict
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(50, ge=1, le=100, description="Number of records to return")
    search: Optional[str] = Field(None, description="Search query")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: str = Field("asc", pattern="^(asc|desc)$", description="Sort order")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")


class BaseResponse(BaseModel):
    """Base response model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: Dict[str, Any] = Field(..., description="Error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Optional[Dict[str, Any]] = None


class MetricsResponse(BaseModel):
    """Metrics response."""
    metrics: Dict[str, Any] = Field(..., description="Metrics data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period: str = Field(..., description="Metrics period")


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    success_count: int = Field(..., ge=0, description="Number of successful operations")
    error_count: int = Field(..., ge=0, description="Number of failed operations")
    total_count: int = Field(..., ge=0, description="Total number of operations")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Error details")


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    timestamp: datetime
    user_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class StatusUpdate(BaseModel):
    """Generic status update."""
    status: str = Field(..., description="New status")
    reason: Optional[str] = Field(None, description="Reason for status change")
    effective_date: Optional[datetime] = Field(None, description="When the status change takes effect")


class ConfigurationUpdate(BaseModel):
    """Generic configuration update."""
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    category: Optional[str] = Field(None, description="Configuration category")