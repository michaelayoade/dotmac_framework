from pydantic import BaseModel

"""
Database Base Module - Compatibility Module

Provides database base classes for backward compatibility.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class BaseModel(Base):
    """Base model for all database entities."""

    __abstract__ = True

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self):
        """Convert model to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.__dict__})>"


class AuditableMixin:
    """Mixin for auditable models."""

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)


__all__ = ["Base", "BaseModel", "AuditableMixin"]
