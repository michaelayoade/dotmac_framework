from pydantic import BaseModel

"""
Database Module - Compatibility Module

Provides database base classes for backward compatibility.
"""

from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from uuid import uuid4

Base = declarative_base()


class BaseModel(Base):
    """Base model for all database entities."""

    __abstract__ = True

    # Primary key for all ORM entities using this base
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"


__all__ = ["Base", "BaseModel"]
