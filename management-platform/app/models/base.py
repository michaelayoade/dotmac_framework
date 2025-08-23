"""
Base model with common fields and utilities.
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import as_declarative

from ..database import Base

# Export GUID as UUID for compatibility
__all__ = ['BaseModel', 'GUID', 'UUID']


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    
    Uses PostgreSQL UUID when possible, otherwise stores as string.
    """
    impl = CHAR
    cache_ok = True

    def __init__(self, as_uuid=True, **kwargs):
        """Initialize GUID type, ignoring as_uuid for non-PostgreSQL databases."""
        self.as_uuid = as_uuid
        # Don't pass as_uuid to the base class
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


# Make GUID available as UUID for backward compatibility
UUID = GUID


@as_declarative()
class BaseModel(Base):
    """Base model with common fields."""
    
    __abstract__ = True
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Soft delete support
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Metadata for extensibility
    metadata_json = Column(JSON, default=dict, nullable=False)
    
    # Audit fields
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case and pluralize
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        
        # Simple pluralization
        if name.endswith('y'):
            name = name[:-1] + 'ies'
        elif name.endswith(('s', 'sh', 'ch', 'x', 'z')):
            name = name + 'es'
        else:
            name = name + 's'
        
        return name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[column.name] = value
        return result
    
    def update_from_dict(self, data: Dict[str, Any], exclude: list = None) -> None:
        """Update model from dictionary."""
        exclude = exclude or ['id', 'created_at', 'updated_at']
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def soft_delete(self, user_id: str = None) -> None:
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        if user_id:
            self.updated_by = user_id
    
    def restore(self, user_id: str = None) -> None:
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        if user_id:
            self.updated_by = user_id
    
    @property
    def is_active(self) -> bool:
        """Check if record is active (not deleted)."""
        return not self.is_deleted
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"