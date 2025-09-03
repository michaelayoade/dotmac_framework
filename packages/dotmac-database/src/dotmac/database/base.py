"""
Base classes and declarative base for dotmac-database.

Provides the foundation for all database models with common patterns
like primary keys, timestamps, and table naming conventions.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from .types import GUID


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models in the DotMac ecosystem.
    
    Provides the declarative base with type mapping for UUID support
    and common configuration.
    """
    
    # Type mapping for cross-database compatibility
    type_annotation_map = {
        uuid.UUID: GUID,
    }


class BaseModel(Base):
    """
    Base model class with common fields and functionality.
    
    Provides:
    - UUID primary key
    - Created/updated timestamps with automatic updates
    - Automatic table naming from class name
    - Common repr implementation
    - Utility methods for serialization
    """
    
    __abstract__ = True

    # Primary key - UUID for global uniqueness
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.
        
        Converts CamelCase to snake_case and optionally adds prefix.
        Override get_table_prefix() in subclasses for custom prefixes.
        """
        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        
        # Add prefix if defined
        prefix = cls.get_table_prefix()
        if prefix:
            name = f"{prefix}{name}"
        
        return name

    @classmethod
    def get_table_prefix(cls) -> str:
        """
        Get table prefix for this model.
        
        Override in base classes to provide organization-wide prefixes.
        Returns empty string by default.
        """
        return ""

    def __repr__(self) -> str:
        """Generate readable representation of the model."""
        class_name = self.__class__.__name__
        
        # Show ID and any name-like fields
        parts = [f"id={self.id!r}"]
        
        # Common name fields to display
        name_fields = ['name', 'title', 'email', 'username', 'code', 'slug']
        for field in name_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    parts.append(f"{field}={value!r}")
                break  # Only show first name-like field found
        
        return f"{class_name}({', '.join(parts)})"

    def to_dict(self, exclude: Optional[set] = None) -> dict[str, Any]:
        """
        Convert model to dictionary representation.
        
        Args:
            exclude: Set of field names to exclude from output
            
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                
                # Handle special types
                if isinstance(value, uuid.UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                
                result[column.name] = value
        
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseModel":
        """
        Create model instance from dictionary.
        
        Args:
            data: Dictionary of field values
            
        Returns:
            New model instance
        """
        # Filter data to only include valid columns
        valid_data = {}
        for column in cls.__table__.columns:
            if column.name in data:
                value = data[column.name]
                
                # Handle UUID conversion
                if column.name == 'id' and isinstance(value, str):
                    try:
                        value = uuid.UUID(value)
                    except ValueError:
                        pass  # Let SQLAlchemy handle validation
                
                valid_data[column.name] = value
        
        return cls(**valid_data)

    def update_from_dict(self, data: dict[str, Any], exclude: Optional[set] = None) -> None:
        """
        Update model fields from dictionary.
        
        Args:
            data: Dictionary of field values to update
            exclude: Set of field names to exclude from update
        """
        exclude = exclude or {'id', 'created_at'}  # Never update these
        
        for column in self.__table__.columns:
            if column.name not in exclude and column.name in data:
                setattr(self, column.name, data[column.name])

    def refresh_updated_at(self) -> None:
        """Manually refresh the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


def create_index_name(table_name: str, *column_names: str, suffix: str = "idx") -> str:
    """
    Generate standardized index name.
    
    Args:
        table_name: Name of the table
        column_names: Names of columns in the index
        suffix: Optional suffix (default: 'idx')
        
    Returns:
        Standardized index name
    """
    columns = "_".join(column_names)
    return f"{suffix}_{table_name}_{columns}"


def create_unique_constraint_name(table_name: str, *column_names: str) -> str:
    """
    Generate standardized unique constraint name.
    
    Args:
        table_name: Name of the table
        column_names: Names of columns in the constraint
        
    Returns:
        Standardized unique constraint name
    """
    columns = "_".join(column_names)
    return f"uq_{table_name}_{columns}"


def create_foreign_key_name(table_name: str, column_name: str, target_table: str) -> str:
    """
    Generate standardized foreign key constraint name.
    
    Args:
        table_name: Name of the source table
        column_name: Name of the foreign key column
        target_table: Name of the target table
        
    Returns:
        Standardized foreign key constraint name
    """
    return f"fk_{table_name}_{column_name}_{target_table}"


def create_check_constraint_name(table_name: str, constraint_desc: str) -> str:
    """
    Generate standardized check constraint name.
    
    Args:
        table_name: Name of the table
        constraint_desc: Description of the constraint
        
    Returns:
        Standardized check constraint name
    """
    # Clean up constraint description
    desc = re.sub(r'[^\w]', '_', constraint_desc.lower())
    desc = re.sub(r'_+', '_', desc).strip('_')
    
    return f"ck_{table_name}_{desc}"