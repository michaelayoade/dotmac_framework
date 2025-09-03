"""
Type definitions and utilities for dotmac-database.
"""

import uuid
from typing import Any, TypeVar, Union, Optional
from typing_extensions import Annotated

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import TypeDecorator, CHAR


# Type variables for generic usage
T = TypeVar("T")
ModelType = TypeVar("ModelType", bound="BaseModel")


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise
    stores as a CHAR(36) string.
    """
    
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgresUUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Optional[str]:
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Optional[uuid.UUID]:
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# Type annotations for common use cases
UUIDType = Annotated[uuid.UUID, GUID()]
OptionalUUID = Optional[uuid.UUID]
UUIDOrString = Union[uuid.UUID, str]


# Database URL type
DatabaseURL = Union[str, sa.URL]


# Common field types for consistent usage
IdType = UUIDType
TenantIdType = Union[str, uuid.UUID]
UserIdType = Union[str, uuid.UUID, int]
RequestIdType = Union[str, uuid.UUID]