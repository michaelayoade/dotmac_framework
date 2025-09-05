"""
from __future__ import annotations
Service factory for creating consistent service instances.
Enforces DRY patterns and consistent service usage across the framework.
"""

from typing import Optional, TypeVar, Union

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

# Try to import from multiple possible database sources
try:
    from dotmac.database.base import Base
except ImportError:
    try:
        from sqlalchemy.orm import DeclarativeBase as Base
    except ImportError:
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()
from .base_service import BaseService

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=PydanticBaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=PydanticBaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=PydanticBaseModel)


class ServiceFactory:
    """Factory for creating service instances with consistent patterns."""

    @staticmethod
    def create_service(
        db: Union[Session, AsyncSession],
        model_class: type[ModelType],
        create_schema: type[CreateSchemaType],
        update_schema: type[UpdateSchemaType],
        response_schema: type[ResponseSchemaType],
        tenant_id: Optional[str] = None,
        service_class: Optional[type] = None,
    ) -> BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]:
        """
        Create a service instance.

        Args:
            db: Database session (sync or async)
            model_class: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            tenant_id: Tenant identifier
            service_class: Custom service class (defaults to BaseService)

        Returns:
            Service instance
        """
        service_cls = service_class or BaseService

        return service_cls(
            db=db,
            model_class=model_class,
            create_schema=create_schema,
            update_schema=update_schema,
            response_schema=response_schema,
            tenant_id=tenant_id,
        )


# Convenience functions for common usage patterns
def create_service(
    db: Union[Session, AsyncSession],
    model_class: type[ModelType],
    create_schema: type[CreateSchemaType],
    update_schema: type[UpdateSchemaType],
    response_schema: type[ResponseSchemaType],
    tenant_id: Optional[str] = None,
    service_class: Optional[type] = None,
) -> BaseService[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]:
    """Convenience function for creating services."""
    return ServiceFactory.create_service(
        db=db,
        model_class=model_class,
        create_schema=create_schema,
        update_schema=update_schema,
        response_schema=response_schema,
        tenant_id=tenant_id,
        service_class=service_class,
    )
