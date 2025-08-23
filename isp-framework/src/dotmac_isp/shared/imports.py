"""Standardized imports to reduce duplication across modules."""

# Standard library imports
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import uuid4, UUID
from enum import Enum
from decimal import Decimal
from pathlib import Path
import json
import logging

# FastAPI imports
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path as PathParam,
    BackgroundTasks,
    status,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# SQLAlchemy imports
from sqlalchemy.orm import Session, relationship, selectinload, joinedload
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Date,
    Integer,
    Float,
    Numeric,
    JSON,
    ForeignKey,
    Index,
    and_,
    or_,
    func,
    desc,
    asc,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import expression

# Pydantic imports
from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr, HttpUrl

# Framework shared imports
from dotmac_isp.core.database import get_db
from dotmac_isp.shared.auth import get_current_tenant, get_current_user
from dotmac_isp.shared.database.base import TenantModel, StatusMixin, AuditMixin
from dotmac_isp.shared.models import ContactMixin, AddressMixin
from dotmac_isp.shared.enums import (
    CommonStatus,
    EntityLifecycle,
    ProcessingStatus,
    PaymentStatus,
    AlertSeverity,
    Priority,
    NetworkStatus,
    DeliveryStatus,
    AuditAction,
    ComplianceStatus,
    ContractStatus,
    TicketStatus,
    UserStatus,
    ServiceStatus,
    OrderStatus,
    InventoryMovementType,
    WorkOrderStatus,
    InstallationStatus,
    CommunicationChannel,
    ContactType,
    AddressType,
    DeviceType,
    MetricType,
    ReportFormat,
    TimeZone,
    Currency,
    Country,
    LanguageCode,
)
from dotmac_isp.shared.routers import (
    BaseCRUDRouter,
    BaseStatusRouter,
    BaseDashboardMixin,
    BaseReportMixin,
    CommonSearchMixin,
    generate_unique_code,
    generate_sequential_number,
)

# Common exception types
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError

# Logging setup
logger = logging.getLogger(__name__)

# Common HTTP status codes
HTTP_200_OK = status.HTTP_200_OK
HTTP_201_CREATED = status.HTTP_201_CREATED
HTTP_204_NO_CONTENT = status.HTTP_204_NO_CONTENT
HTTP_400_BAD_REQUEST = status.HTTP_400_BAD_REQUEST
HTTP_401_UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED
HTTP_403_FORBIDDEN = status.HTTP_403_FORBIDDEN
HTTP_404_NOT_FOUND = status.HTTP_404_NOT_FOUND
HTTP_409_CONFLICT = status.HTTP_409_CONFLICT
HTTP_422_UNPROCESSABLE_ENTITY = status.HTTP_422_UNPROCESSABLE_ENTITY
HTTP_500_INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR

# Common query parameters
CommonPagination = {
    "skip": Query(0, ge=0, description="Number of records to skip"),
    "limit": Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
}

CommonSearch = {
    "search": Query(None, description="Search term for filtering results"),
    "sort_by": Query(None, description="Field to sort by"),
    "sort_desc": Query(False, description="Sort in descending order"),
}


# Common response models
class MessageResponse(BaseModel):
    """Standard message response."""

    message: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# Common validation patterns
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
PHONE_REGEX = r"^\+?1?-?\.?\s?\(?[0-9]{3}\)?[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}$"
UUID_REGEX = (
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


# Common field validators
def validate_email(email: str) -> str:
    """Validate email format."""
    import re

    if not re.match(EMAIL_REGEX, email):
        raise ValueError("Invalid email format")
    return email.lower()


def validate_phone(phone: str) -> str:
    """Validate phone format."""
    import re

    if not re.match(PHONE_REGEX, phone):
        raise ValueError("Invalid phone format")
    return phone


def validate_uuid(uuid_str: str) -> str:
    """Validate UUID format."""
    try:
        UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise ValueError("Invalid UUID format")


# Common utility functions
def utcnow() -> datetime:
    """Get current UTC datetime."""
    return datetime.utcnow()


def today() -> date:
    """Get current date."""
    return date.today()


def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid4())


def serialize_datetime(dt: datetime) -> str:
    """Serialize datetime to ISO format."""
    return dt.isoformat() if dt else None


def parse_datetime(dt_str: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(dt_str) if dt_str else None


def calculate_days_between(start_date: date, end_date: date) -> int:
    """Calculate days between two dates."""
    return (end_date - start_date).days


def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """Format currency amount."""
    if currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_percentage(value: float, precision: int = 2) -> str:
    """Format percentage value."""
    return f"{value:.{precision}f}%"


# Database query helpers
def build_filters(model, filters: Dict[str, Any]):
    """Build SQLAlchemy filters from dictionary."""
    conditions = []
    for field, value in filters.items():
        if hasattr(model, field) and value is not None:
            field_attr = getattr(model, field)
            if isinstance(value, list):
                conditions.append(field_attr.in_(value))
            elif (
                isinstance(value, str) and value.startswith("%") and value.endswith("%")
            ):
                conditions.append(field_attr.ilike(value))
            else:
                conditions.append(field_attr == value)
    return conditions


def apply_tenant_filter(query, model, tenant_id: str):
    """Apply tenant isolation filter."""
    return query.filter(model.tenant_id == tenant_id)


def apply_pagination(query, skip: int = 0, limit: int = 100):
    """Apply pagination to query."""
    return query.offset(skip).limit(limit)


def apply_sorting(query, model, sort_by: str = None, sort_desc: bool = False):
    """Apply sorting to query."""
    if sort_by and hasattr(model, sort_by):
        field = getattr(model, sort_by)
        return query.order_by(desc(field) if sort_desc else asc(field))
    elif hasattr(model, "created_at"):
        return query.order_by(desc(model.created_at))
    return query


# Exception handlers
def handle_integrity_error(e: IntegrityError) -> HTTPException:
    """Handle SQLAlchemy integrity errors."""
    if "duplicate key" in str(e.orig):
        return HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="Resource with this identifier already exists",
        )
    elif "foreign key" in str(e.orig):
        return HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Referenced resource does not exist",
        )
    else:
        return HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Database constraint violation"
        )


def handle_validation_error(e: ValidationError) -> HTTPException:
    """Handle Pydantic validation errors."""
    return HTTPException(status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors())


def handle_not_found(entity_name: str) -> HTTPException:
    """Create not found exception."""
    return HTTPException(
        status_code=HTTP_404_NOT_FOUND, detail=f"{entity_name} not found"
    )


# Common model mixins (re-export for convenience)
__all__ = [
    # Standard library
    "datetime",
    "date",
    "timedelta",
    "List",
    "Optional",
    "Dict",
    "Any",
    "Union",
    "Tuple",
    "uuid4",
    "UUID",
    "Enum",
    "Decimal",
    "Path",
    "json",
    "logging",
    # FastAPI
    "APIRouter",
    "Depends",
    "HTTPException",
    "Query",
    "PathParam",
    "BackgroundTasks",
    "status",
    "UploadFile",
    "File",
    "Form",
    "JSONResponse",
    "FileResponse",
    "HTTPBearer",
    "HTTPAuthorizationCredentials",
    # SQLAlchemy
    "Session",
    "relationship",
    "selectinload",
    "joinedload",
    "Column",
    "String",
    "Text",
    "Boolean",
    "DateTime",
    "Date",
    "Integer",
    "Float",
    "Numeric",
    "JSON",
    "ForeignKey",
    "Index",
    "and_",
    "or_",
    "func",
    "desc",
    "asc",
    "PGUUID",
    "hybrid_property",
    "expression",
    "UniqueConstraint",
    "CheckConstraint",
    # Pydantic
    "BaseModel",
    "Field",
    "field_validator",
    "model_validator",
    "EmailStr",
    "HttpUrl",
    # Framework components
    "get_db",
    "get_current_tenant",
    "get_current_user",
    "TenantModel",
    "StatusMixin",
    "AuditMixin",
    "ContactMixin",
    "AddressMixin",
    "BaseCRUDRouter",
    "BaseStatusRouter",
    "BaseDashboardMixin",
    "BaseReportMixin",
    "CommonSearchMixin",
    "generate_unique_code",
    "generate_sequential_number",
    # Enums
    "CommonStatus",
    "EntityLifecycle",
    "ProcessingStatus",
    "PaymentStatus",
    "AlertSeverity",
    "Priority",
    "NetworkStatus",
    "DeliveryStatus",
    "AuditAction",
    "ComplianceStatus",
    "ContractStatus",
    "TicketStatus",
    "UserStatus",
    "ServiceStatus",
    "OrderStatus",
    "InventoryMovementType",
    "WorkOrderStatus",
    "InstallationStatus",
    "CommunicationChannel",
    "ContactType",
    "AddressType",
    "DeviceType",
    "MetricType",
    "ReportFormat",
    "TimeZone",
    "Currency",
    "Country",
    "LanguageCode",
    # Exceptions
    "IntegrityError",
    "SQLAlchemyError",
    "ValidationError",
    # HTTP status codes
    "HTTP_200_OK",
    "HTTP_201_CREATED",
    "HTTP_204_NO_CONTENT",
    "HTTP_400_BAD_REQUEST",
    "HTTP_401_UNAUTHORIZED",
    "HTTP_403_FORBIDDEN",
    "HTTP_404_NOT_FOUND",
    "HTTP_409_CONFLICT",
    "HTTP_422_UNPROCESSABLE_ENTITY",
    "HTTP_500_INTERNAL_SERVER_ERROR",
    # Response models
    "MessageResponse",
    "ErrorResponse",
    "SuccessResponse",
    # Utility functions
    "validate_email",
    "validate_phone",
    "validate_uuid",
    "utcnow",
    "today",
    "generate_id",
    "serialize_datetime",
    "parse_datetime",
    "calculate_days_between",
    "format_currency",
    "format_percentage",
    "build_filters",
    "apply_tenant_filter",
    "apply_pagination",
    "apply_sorting",
    "handle_integrity_error",
    "handle_validation_error",
    "handle_not_found",
    # Common patterns
    "CommonPagination",
    "CommonSearch",
    "EMAIL_REGEX",
    "PHONE_REGEX",
    "UUID_REGEX",
    # Logger
    "logger",
]
