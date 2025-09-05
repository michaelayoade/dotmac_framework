"""
Module template system for generating standardized module structures.
"""

from dataclasses import dataclass
from enum import Enum
from string import Template


class Platform(Enum):
    """Platform types for module generation."""

    ISP = "isp"
    MANAGEMENT = "management"


@dataclass
class ComponentConfig:
    """Configuration for a component template."""

    name: str
    filename: str
    template_content: str
    required: bool = True
    dependencies: list[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class ComponentTemplate:
    """Templates for individual module components."""

    @staticmethod
    def get_init_template() -> ComponentConfig:
        """Generate __init__.py template."""
        template = '''"""
${module_name} module for ${platform_name}.

This module provides:
- ${description}
"""

from .router import router
from .service import ${service_class}
from .models import ${model_classes}
from .schemas import ${schema_classes}

__all__ = [
    "router",
    "${service_class}",
    ${model_exports},
    ${schema_exports}
]
'''
        return ComponentConfig(
            name="module_init",
            filename="__init__.py",
            template_content=template,
            required=True,
        )

    @staticmethod
    def get_router_template() -> ComponentConfig:
        """Generate router.py template."""
        template = '''"""
${module_name} API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ${relative_import_base}.database import get_db
from dotmac.auth import get_current_user, require_scopes
from dotmac.core.cache import CacheService
from dotmac_shared.files import FileService
from dotmac_shared.webhooks import WebhookService
from .service import ${service_class}
from .schemas import (
    ${schema_class}Response,
    ${schema_class}Create,
    ${schema_class}Update,
    ${schema_class}Query
)

router = APIRouter(
    prefix="/${module_name}",
    tags=["${module_name}"]
)

# Initialize service
${service_var} = ${service_class}()


@router.get("/", response_model=list[${schema_class}Response])
async def list_${module_name}(
    skip: int = Query(0, ge=0),  # noqa: B008
    limit: int = Query(100, ge=1, le=1000),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    current_user = Depends(get_current_user)  # noqa: B008
):
    """List all ${module_name}."""
    try:
        query = ${schema_class}Query(skip=skip, limit=limit)  # noqa: B008
        return await ${service_var}.list_${module_name}(query, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}", response_model=${schema_class}Response)
async def get_${module_name_singular}(
    item_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current_user = Depends(get_current_user)  # noqa: B008
):
    """Get ${module_name_singular} by ID."""
    try:
        item = await ${service_var}.get_${module_name_singular}(item_id, db, current_user)
        if not item:
            raise HTTPException(status_code=404, detail="${module_name_singular} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=${schema_class}Response)
async def create_${module_name_singular}(
    item: ${schema_class}Create,
    db: Session = Depends(get_db),  # noqa: B008
    current_user = Depends(get_current_user)  # noqa: B008
):
    """Create new ${module_name_singular}."""
    try:
        return await ${service_var}.create_${module_name_singular}(item, db, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{item_id}", response_model=${schema_class}Response)
async def update_${module_name_singular}(
    item_id: int,
    item: ${schema_class}Update,
    db: Session = Depends(get_db),  # noqa: B008
    current_user = Depends(get_current_user)  # noqa: B008
):
    """Update ${module_name_singular}."""
    try:
        updated_item = await ${service_var}.update_${module_name_singular}(item_id, item, db, current_user)
        if not updated_item:
            raise HTTPException(status_code=404, detail="${module_name_singular} not found")
        return updated_item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def delete_${module_name_singular}(
    item_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current_user = Depends(get_current_user)  # noqa: B008
):
    """Delete ${module_name_singular}."""
    try:
        success = await ${service_var}.delete_${module_name_singular}(item_id, db, current_user)
        if not success:
            raise HTTPException(status_code=404, detail="${module_name_singular} not found")
        return {"message": "${module_name_singular} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "module": "${module_name}"}
'''
        return ComponentConfig(
            name="router",
            filename="router.py",
            template_content=template,
            required=True,
            dependencies=["service", "schemas"],
        )

    @staticmethod
    def get_service_template() -> ComponentConfig:
        """Generate service.py template."""
        template = '''"""
${module_name} business logic service.
"""

import logging
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ${relative_import_base}.core.exceptions import ValidationError, NotFoundError, PermissionError
from dotmac.auth import JWTService
from dotmac.core.cache import CacheService
from dotmac_shared.files import FileService
from dotmac_shared.webhooks import WebhookService
from .repository import ${repository_class}
from .models import ${model_class}
from .schemas import (
    ${schema_class}Create,
    ${schema_class}Update,
    ${schema_class}Response,
    ${schema_class}Query
)

logger = logging.getLogger(__name__)


class ${service_class}:
    """${module_name} service for business logic operations."""

    def __init__(self):
        self.repository = ${repository_class}()
        self.auth_service = AuthService()
        self.cache_service = CacheService()
        self.file_service = FileService()
        self.webhook_service = WebhookService()

    async def list_${module_name}(
        self,
        query: ${schema_class}Query,
        db: Session,
        current_user: Any
    ) -> list[${schema_class}Response]:
        """List ${module_name} with filtering and pagination."""
        try:
            # Apply tenant filtering if needed
            filters = self._build_filters(query, current_user)

            # Check cache first
            cache_key = f"${module_name}_list_{current_user.tenant_id}_{hash(str(filters))}"
            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                return cached_result

            items = await self.repository.list_with_pagination(
                db,
                skip=query.skip,
                limit=query.limit,
                filters=filters
            )

            result = [${schema_class}Response.model_validate(item) for item in items]

            # Cache the result
            await self.cache_service.set(cache_key, result, ttl=300)  # 5 minutes

            return result

        except SQLAlchemyError as e:
            logger.error(f"Database error in list_${module_name}: {e}")
            raise ValidationError("Failed to retrieve ${module_name}")

    async def get_${module_name_singular}(
        self,
        item_id: int,
        db: Session,
        current_user: Any
    ) -> Optional[${schema_class}Response]:
        """Get ${module_name_singular} by ID."""
        try:
            item = await self.repository.get_by_id(db, item_id)

            if not item:
                return None

            # Check permissions
            if not self._can_access_item(item, current_user):
                raise PermissionError("Access denied to this ${module_name_singular}")

            return ${schema_class}Response.model_validate(item)

        except SQLAlchemyError as e:
            logger.error(f"Database error in get_${module_name_singular}: {e}")
            raise ValidationError("Failed to retrieve ${module_name_singular}")

    async def create_${module_name_singular}(
        self,
        item_data: ${schema_class}Create,
        db: Session,
        current_user: Any
    ) -> ${schema_class}Response:
        """Create new ${module_name_singular}."""
        try:
            # Validate business rules
            await self._validate_create_data(item_data, current_user)

            # Create model instance
            item_dict = item_data.model_dump()
            item_dict = self._enrich_create_data(item_dict, current_user)

            item = ${model_class}(**item_dict)
            created_item = await self.repository.create(db, item)

            # Clear related cache entries
            await self.cache_service.delete_pattern(f"${module_name}_list_{current_user.tenant_id}*")

            # Send webhook notification
            await self.webhook_service.trigger(
                event_type="${module_name_singular}.created",
                data=created_item.to_dict() if hasattr(created_item, 'to_dict') else {"id": created_item.id},
                tenant_id=current_user.tenant_id
            )

            logger.info(f"Created ${module_name_singular} {created_item.id} by user {current_user.id}")
            return ${schema_class}Response.model_validate(created_item)

        except SQLAlchemyError as e:
            logger.error(f"Database error in create_${module_name_singular}: {e}")
            db.rollback()
            raise ValidationError("Failed to create ${module_name_singular}")

    async def update_${module_name_singular}(
        self,
        item_id: int,
        item_data: ${schema_class}Update,
        db: Session,
        current_user: Any
    ) -> Optional[${schema_class}Response]:
        """Update ${module_name_singular}."""
        try:
            # Get existing item
            existing_item = await self.repository.get_by_id(db, item_id)
            if not existing_item:
                return None

            # Check permissions
            if not self._can_modify_item(existing_item, current_user):
                raise PermissionError("Permission denied to modify this ${module_name_singular}")

            # Validate update data
            await self._validate_update_data(item_data, existing_item, current_user)

            # Update item
            update_dict = item_data.model_dump(exclude_unset=True)
            update_dict = self._enrich_update_data(update_dict, current_user)

            updated_item = await self.repository.update(db, existing_item, update_dict)

            logger.info(f"Updated ${module_name_singular} {item_id} by user {current_user.id}")
            return ${schema_class}Response.model_validate(updated_item)

        except SQLAlchemyError as e:
            logger.error(f"Database error in update_${module_name_singular}: {e}")
            db.rollback()
            raise ValidationError("Failed to update ${module_name_singular}")

    async def delete_${module_name_singular}(
        self,
        item_id: int,
        db: Session,
        current_user: Any
    ) -> bool:
        """Delete ${module_name_singular}."""
        try:
            # Get existing item
            existing_item = await self.repository.get_by_id(db, item_id)
            if not existing_item:
                return False

            # Check permissions
            if not self._can_delete_item(existing_item, current_user):
                raise PermissionError("Permission denied to delete this ${module_name_singular}")

            # Validate deletion
            await self._validate_delete(existing_item, current_user)

            # Delete item
            success = await self.repository.delete(db, existing_item)

            if success:
                logger.info(f"Deleted ${module_name_singular} {item_id} by user {current_user.id}")

            return success

        except SQLAlchemyError as e:
            logger.error(f"Database error in delete_${module_name_singular}: {e}")
            db.rollback()
            raise ValidationError("Failed to delete ${module_name_singular}")

    def _build_filters(self, query: ${schema_class}Query, current_user: Any) -> dict[str, Any]:
        """Build database filters from query parameters."""
        filters = {}

        # Add tenant filtering for multi-tenant platforms
        if hasattr(current_user, 'tenant_id'):
            filters['tenant_id'] = current_user.tenant_id

        return filters

    def _can_access_item(self, item: ${model_class}, current_user: Any) -> bool:
        """Check if user can access this item."""
        # Implement access control logic
        if hasattr(item, 'tenant_id') and hasattr(current_user, 'tenant_id'):
            return item.tenant_id == current_user.tenant_id
        return True

    def _can_modify_item(self, item: ${model_class}, current_user: Any) -> bool:
        """Check if user can modify this item."""
        return self._can_access_item(item, current_user)

    def _can_delete_item(self, item: ${model_class}, current_user: Any) -> bool:
        """Check if user can delete this item."""
        return self._can_modify_item(item, current_user)

    def _enrich_create_data(self, data: dict[str, Any], current_user: Any) -> dict[str, Any]:
        """Enrich create data with user and tenant info."""
        if hasattr(current_user, 'id'):
            data['created_by'] = current_user.id
        if hasattr(current_user, 'tenant_id'):
            data['tenant_id'] = current_user.tenant_id
        return data

    def _enrich_update_data(self, data: dict[str, Any], current_user: Any) -> dict[str, Any]:
        """Enrich update data with user info."""
        if hasattr(current_user, 'id'):
            data['updated_by'] = current_user.id
        return data

    async def _validate_create_data(self, data: ${schema_class}Create, current_user: Any):
        """Validate data for creation."""
        # Implement custom validation logic
        pass

    async def _validate_update_data(self, data: ${schema_class}Update, existing: ${model_class}, current_user: Any):
        """Validate data for update."""
        # Implement custom validation logic
        pass

    async def _validate_delete(self, item: ${model_class}, current_user: Any):
        """Validate item can be deleted."""
        # Implement deletion validation logic
        pass
'''
        return ComponentConfig(
            name="service",
            filename="service.py",
            template_content=template,
            required=True,
            dependencies=["repository", "models", "schemas"],
        )

    @staticmethod
    def get_repository_template() -> ComponentConfig:
        """Generate repository.py template."""
        template = '''"""
${module_name} data access repository.
"""

from typing import Any, Optional
from sqlalchemy.orm import Session, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, func

from ${relative_import_base}.shared.repositories.base_repository import BaseRepository
from .models import ${model_class}


class ${repository_class}(BaseRepository[${model_class}]):
    """Repository for ${module_name} data access operations."""

    def __init__(self):
        super().__init__(${model_class})

    async def list_with_pagination(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None
    ) -> list[${model_class}]:
        """List items with pagination and filtering."""
        try:
            query = db.query(self.model)

            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)

            # Apply ordering (customize as needed)
            query = query.order_by(self.model.id.desc())

            # Apply pagination
            return query.offset(skip).limit(limit).all()

        except SQLAlchemyError as e:
            raise e

    async def count_with_filters(
        self,
        db: Session,
        filters: Optional[dict[str, Any]] = None
    ) -> int:
        """Count items with filtering."""
        try:
            query = db.query(func.count(self.model.id))

            if filters:
                query = self._apply_filters(query, filters)

            return query.scalar()

        except SQLAlchemyError as e:
            raise e

    async def find_by_attribute(
        self,
        db: Session,
        attribute: str,
        value: Any
    ) -> Optional[${model_class}]:
        """Find item by specific attribute."""
        try:
            return db.query(self.model).filter(
                getattr(self.model, attribute) == value
            ).first()

        except SQLAlchemyError as e:
            raise e

    async def find_all_by_attribute(
        self,
        db: Session,
        attribute: str,
        value: Any
    ) -> list[${model_class}]:
        """Find all items by specific attribute."""
        try:
            return db.query(self.model).filter(
                getattr(self.model, attribute) == value
            ).all()

        except SQLAlchemyError as e:
            raise e

    async def search(
        self,
        db: Session,
        search_term: str,
        search_fields: Optional[list[str]] = None
    ) -> list[${model_class}]:
        """Search items by text in specified fields."""
        try:
            if not search_fields:
                search_fields = self._get_searchable_fields()

            query = db.query(self.model)

            # Build search conditions
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    search_conditions.append(
                        field_attr.ilike(f"%{search_term}%")
                    )

            if search_conditions:
                query = query.filter(or_(*search_conditions))

            return query.all()

        except SQLAlchemyError as e:
            raise e

    def _apply_filters(self, query: Query, filters: dict[str, Any]) -> Query:
        """Apply filters to query."""
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                if isinstance(value, list):
                    # Handle list filters (IN clause)
                    query = query.filter(getattr(self.model, key).in_(value))
                elif isinstance(value, dict):
                    # Handle range filters
                    field_attr = getattr(self.model, key)
                    if 'gte' in value:
                        query = query.filter(field_attr >= value['gte'])
                    if 'lte' in value:
                        query = query.filter(field_attr <= value['lte'])
                    if 'gt' in value:
                        query = query.filter(field_attr > value['gt'])
                    if 'lt' in value:
                        query = query.filter(field_attr < value['lt'])
                else:
                    # Handle exact match
                    query = query.filter(getattr(self.model, key) == value)

        return query

    def _get_searchable_fields(self) -> list[str]:
        """Get list of searchable text fields."""
        # Override this method in subclasses to specify searchable fields
        searchable_fields = []
        for column in self.model.__table__.columns:
            if str(column.type).lower().startswith(('varchar', 'text', 'string')):
                searchable_fields.append(column.name)
        return searchable_fields
'''
        return ComponentConfig(
            name="repository",
            filename="repository.py",
            template_content=template,
            required=True,
            dependencies=["models"],
        )

    @staticmethod
    def get_models_template() -> ComponentConfig:
        """Generate models.py template."""
        template = '''"""
${module_name} database models.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

from ${relative_import_base}.shared.models.base_model import BaseTenantModel, AuditMixin, StatusMixin


class ${model_class}(BaseTenantModel, AuditMixin, StatusMixin):
    """${module_name_singular} model."""

    __tablename__ = "${table_name}"

    # Primary fields
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Add your specific fields here
    # Example fields:
    # email = Column(String(255), nullable=True, index=True)
    # phone = Column(String(50), nullable=True)
    # address = Column(Text, nullable=True)
    # category = Column(String(100), nullable=True, index=True)
    # priority = Column(Integer, default=0)
    # tags = Column(JSON, nullable=True)

    # Relationships (add as needed)
    # Example:
    # user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # user = relationship("User", back_populates="${module_name}")

    def __repr__(self):
        return f"<${model_class}(id={self.id}, name='{self.name}')>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tenant_id': self.tenant_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }


# Add additional models as needed
# class ${model_class}Detail(BaseTenantModel):
#     """Detail model for ${module_name_singular}."""
#
#     __tablename__ = "${table_name}_details"
#
#     id = Column(Integer, primary_key=True, index=True)
#     ${module_name_singular}_id = Column(Integer, ForeignKey("${table_name}.id"), nullable=False)
#     detail_name = Column(String(255), nullable=False)
#     detail_value = Column(Text, nullable=True)
#
#     # Relationship
#     ${module_name_singular} = relationship("${model_class}", back_populates="details")
'''
        return ComponentConfig(
            name="models",
            filename="models.py",
            template_content=template,
            required=True,
        )

    @staticmethod
    def get_schemas_template() -> ComponentConfig:
        """Generate schemas.py template."""
        template = '''"""
${module_name} Pydantic schemas for request/response validation.
"""

from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ${relative_import_base}.shared.schemas.base_schemas import (
    BaseSchema,
    TenantSchema,
    AuditSchema,
    PaginationSchema
)


class ${schema_class}Base(BaseSchema):
    """Base schema for ${module_name_singular}."""
    name: str = Field(..., min_length=1, max_length=255, description="${module_name_singular} name")
    description: Optional[str] = Field(None, max_length=2000, description="Description")

    # Add your specific fields here
    # email: Optional[str] = Field(None, max_length=255)
    # phone: Optional[str] = Field(None, max_length=50)
    # category: Optional[str] = Field(None, max_length=100)
    # priority: int = Field(0, ge=0, le=10)
    # tags: Optional[List[str]] = Field(None)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate name field."""
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class ${schema_class}Create(${schema_class}Base):
    """Schema for creating ${module_name_singular}."""
    pass

    # Add create-specific validations
    # @field_validator('email')
    # @classmethod
    # def validate_email(cls, v):
    #     if v and '@' not in v:
    #         raise ValueError('Invalid email format')
    #     return v


class ${schema_class}Update(${schema_class}Base):
    """Schema for updating ${module_name_singular}."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)

    # Make all fields optional for updates
    # Override base fields to make them optional


class ${schema_class}Response(${schema_class}Base, TenantSchema, AuditSchema):
    """Schema for ${module_name_singular} responses."""
    id: int = Field(..., description="Unique identifier")

    model_config = ConfigDict(from_attributes=True)

    json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Example ${module_name_singular}",
                "description": "Example description",
                "tenant_id": "tenant123",
                "status": "active",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "created_by": 1,
                "updated_by": 1
            }
        }


class ${schema_class}Query(PaginationSchema):
    """Schema for querying ${module_name}."""
    name: Optional[str] = Field(None, description="Filter by name (partial match)")
    category: Optional[str] = Field(None, description="Filter by category")
    status: Optional[str] = Field(None, description="Filter by status")

    # Add search and filter fields
    search: Optional[str] = Field(None, description="Search term for full-text search")
    created_after: Optional[datetime] = Field(None, description="Filter items created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter items created before this date")

    @field_validator('search')
    @classmethod
    def validate_search(cls, v):
        """Validate search term."""
        if v and len(v.strip()) < 2:
            raise ValueError('Search term must be at least 2 characters')
        return v.strip() if v else None


class ${schema_class}List(BaseModel):
    """Schema for ${module_name} list responses with pagination."""
    items: list[${schema_class}Response]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


# Add additional schemas as needed
class ${schema_class}Summary(BaseModel):
    """Summary schema for ${module_name_singular}."""
    id: int
    name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
'''
        return ComponentConfig(
            name="schemas",
            filename="schemas.py",
            template_content=template,
            required=True,
        )

    @staticmethod
    def get_tasks_template() -> ComponentConfig:
        """Generate tasks.py template."""
        template = '''"""
${module_name} background tasks.
"""

import logging
from typing import Any, Optional
from celery import shared_task
from sqlalchemy.orm import Session

from ${relative_import_base}.database import get_db_session
from ${relative_import_base}.core.celery_app import app
from .service import ${service_class}
from .models import ${model_class}
from .schemas import ${schema_class}Create, ${schema_class}Update

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_${module_name_singular}_async(self, item_data: dict[str, Any], user_id: int):
    """Process ${module_name_singular} asynchronously."""
    try:
        logger.info(f"Starting async processing for ${module_name_singular}: {item_data}")

        with get_db_session() as db:
            service = ${service_class}()

            # Mock user object (in real implementation, fetch from DB)
            class MockUser:
                def __init__(self, user_id: int):
                    self.id = user_id

            user = MockUser(user_id)

            # Process the item
            create_schema = ${schema_class}Create(**item_data)
            result = await service.create_${module_name_singular}(create_schema, db, user)

            logger.info(f"Successfully processed ${module_name_singular} {result.id}")
            return {"success": True, "item_id": result.id}

    except Exception as e:
        logger.error(f"Error processing ${module_name_singular}: {e}")

        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Failed to process ${module_name_singular} after max retries: {e}")
            return {"success": False, "error": str(e)}


@shared_task(bind=True)
def bulk_update_${module_name}(self, item_ids: list[int], update_data: dict[str, Any], user_id: int):
    """Bulk update ${module_name}."""
    try:
        logger.info(f"Starting bulk update for {len(item_ids)} ${module_name}")

        with get_db_session() as db:
            service = ${service_class}()

            class MockUser:
                def __init__(self, user_id: int):
                    self.id = user_id

            user = MockUser(user_id)
            update_schema = ${schema_class}Update(**update_data)

            results = []
            for item_id in item_ids:
                try:
                    result = await service.update_${module_name_singular}(item_id, update_schema, db, user)
                    if result:
                        results.append({"id": item_id, "success": True})
                    else:
                        results.append({"id": item_id, "success": False, "error": "Item not found"})
                except Exception as e:
                    results.append({"id": item_id, "success": False, "error": str(e)})

            success_count = sum(1 for r in results if r["success"])
            logger.info(f"Bulk update completed: {success_count}/{len(item_ids)} items updated")

            return {
                "success": True,
                "updated_count": success_count,
                "total_count": len(item_ids),
                "results": results
            }

    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        return {"success": False, "error": str(e)}


@shared_task
def cleanup_old_${module_name}(days: int = 30):
    """Cleanup old ${module_name} records."""
    try:
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        logger.info(f"Cleaning up ${module_name} older than {cutoff_date}")

        with get_db_session() as db:
            # Delete old records based on your business logic
            deleted_count = db.query(${model_class}).filter(
                ${model_class}.created_at < cutoff_date,
                ${model_class}.status == 'inactive'  # Only cleanup inactive items
            ).delete()

            db.commit()

            logger.info(f"Cleaned up {deleted_count} old ${module_name} records")
            return {"success": True, "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {"success": False, "error": str(e)}


@shared_task
def generate_${module_name}_report(filters: dict[str, Any], user_id: int):
    """Generate ${module_name} report."""
    try:
        logger.info(f"Generating ${module_name} report for user {user_id}")

        with get_db_session() as db:
            # Query data based on filters
            query = db.query(${model_class})

            # Apply filters
            if 'status' in filters:
                query = query.filter(${model_class}.status == filters['status'])

            if 'created_after' in filters:
                query = query.filter(${model_class}.created_at >= filters['created_after'])

            items = query.all()

            # Generate report data
            report_data = {
                "total_items": len(items),
                "items_by_status": {},
                "generated_at": datetime.utcnow().isoformat(),
                "generated_by": user_id
            }

            # Count by status
            for item in items:
                status = item.status
                report_data["items_by_status"][status] = report_data["items_by_status"].get(status, 0) + 1

            logger.info(f"Report generated with {len(items)} items")
            return {"success": True, "report_data": report_data}

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return {"success": False, "error": str(e)}
'''
        return ComponentConfig(name="tasks", filename="tasks.py", template_content=template, required=False)

    @staticmethod
    def get_dependencies_template() -> ComponentConfig:
        """Generate dependencies.py template."""
        template = '''"""
${module_name} module dependencies.
"""

from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from ${relative_import_base}.database import get_db
from dotmac.auth import get_current_user, require_scopes
from dotmac.core.cache import CacheService
from dotmac_shared.files import FileService
from dotmac_shared.webhooks import WebhookService
from .service import ${service_class}
from .repository import ${repository_class}


def get_${module_name}_service() -> ${service_class}:
    """Get ${module_name} service instance."""
    return ${service_class}()


def get_${module_name}_repository() -> ${repository_class}:
    """Get ${module_name} repository instance."""
    return ${repository_class}()


def get_cache_service() -> CacheService:
    """Get cache service instance."""
    return CacheService()


def get_file_service() -> FileService:
    """Get file service instance."""
    return FileService()


def get_webhook_service() -> WebhookService:
    """Get webhook service instance."""
    return WebhookService()


async def get_valid_${module_name_singular}(
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[${service_class}, Depends(get_${module_name}_service)]
):
    """Get and validate ${module_name_singular} exists and user has access."""
    item = await service.get_${module_name_singular}(item_id, db, current_user)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="${module_name_singular} not found"
        )
    return item


def require_${module_name}_permission(action: str = "read"):
    """Require specific permission for ${module_name} operations."""
    def permission_dependency(
        current_user: Annotated[dict, Depends(get_current_user)]
    ):
        permission_name = f"${module_name}:{action}"
        if not require_scopes([permission_name], current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' required"
            )
        return current_user

    return permission_dependency


# Specialized dependencies
def require_${module_name}_admin():
    """Require admin permission for ${module_name} operations."""
    return require_${module_name}_permission("admin")


def require_${module_name}_write():
    """Require write permission for ${module_name} operations."""
    return require_${module_name}_permission("write")


def require_${module_name}_delete():
    """Require delete permission for ${module_name} operations."""
    return require_${module_name}_permission("delete")


# Validation dependencies
async def validate_${module_name}_ownership(
    item_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: Annotated[${service_class}, Depends(get_${module_name}_service)],
    db: Annotated[Session, Depends(get_db)]
):
    """Validate user owns the ${module_name_singular}."""
    item = await service.get_${module_name_singular}(item_id, db, current_user)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="${module_name_singular} not found"
        )

    # Check ownership based on your business logic
    if hasattr(current_user, 'id') and hasattr(item, 'created_by'):
        if item.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't own this ${module_name_singular}"
            )

    return item


# Caching dependencies (if needed)
def get_cached_${module_name}_service():
    """Get cached ${module_name} service instance."""
    # Implement caching logic if needed
    return ${service_class}()
'''
        return ComponentConfig(
            name="dependencies",
            filename="dependencies.py",
            template_content=template,
            required=False,
            dependencies=["service", "repository"],
        )

    @staticmethod
    def get_exceptions_template() -> ComponentConfig:
        """Generate exceptions.py template."""
        template = '''"""
${module_name} module specific exceptions.
"""

from ${relative_import_base}.core.exceptions import DotMacError, ValidationError, NotFoundError
from dotmac.application import standard_exception_handler


class ${module_name_singular}Error(DotMacError):
    """Base exception for ${module_name_singular} operations."""
    pass


class ${module_name_singular}NotFoundError(NotFoundError):
    """Exception raised when ${module_name_singular} is not found."""

    def __init__(self, item_id: int):
        super().__init__(f"${module_name_singular} with ID {item_id} not found")
        self.item_id = item_id


class ${module_name_singular}ValidationError(ValidationError):
    """Exception raised for ${module_name_singular} validation errors."""
    pass


class ${module_name_singular}PermissionError(${module_name_singular}Error):
    """Exception raised for ${module_name_singular} permission errors."""

    def __init__(self, message: str = "Permission denied for ${module_name_singular} operation"):
        super().__init__(message)


class ${module_name_singular}AlreadyExistsError(${module_name_singular}ValidationError):
    """Exception raised when ${module_name_singular} already exists."""

    def __init__(self, identifier: str):
        super().__init__(f"${module_name_singular} with identifier '{identifier}' already exists")
        self.identifier = identifier


class ${module_name_singular}InUseError(${module_name_singular}Error):
    """Exception raised when trying to delete ${module_name_singular} that is in use."""

    def __init__(self, item_id: int, usage_details: str = ""):
        message = f"${module_name_singular} {item_id} cannot be deleted as it is in use"
        if usage_details:
            message += f": {usage_details}"
        super().__init__(message)
        self.item_id = item_id
        self.usage_details = usage_details


class ${module_name_singular}ConfigurationError(${module_name_singular}Error):
    """Exception raised for ${module_name_singular} configuration errors."""
    pass


class ${module_name_singular}ProcessingError(${module_name_singular}Error):
    """Exception raised during ${module_name_singular} processing operations."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


# Utility functions for exception handling
def handle_${module_name}_exception(func):
    """Decorator to handle ${module_name} exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ${module_name_singular}Error:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Convert other exceptions to our custom exception
            raise ${module_name_singular}ProcessingError(
                f"Unexpected error in ${module_name} operation: {str(e)}",
                original_error=e
            )
    return wrapper
'''
        return ComponentConfig(
            name="exceptions",
            filename="exceptions.py",
            template_content=template,
            required=False,
        )


class ModuleTemplate:
    """Main module template system."""

    def __init__(self):
        self.component_templates = {
            "init": ComponentTemplate.get_init_template(),
            "router": ComponentTemplate.get_router_template(),
            "service": ComponentTemplate.get_service_template(),
            "repository": ComponentTemplate.get_repository_template(),
            "models": ComponentTemplate.get_models_template(),
            "schemas": ComponentTemplate.get_schemas_template(),
            "tasks": ComponentTemplate.get_tasks_template(),
            "dependencies": ComponentTemplate.get_dependencies_template(),
            "exceptions": ComponentTemplate.get_exceptions_template(),
        }

    def generate_module_variables(self, module_name: str, platform: Platform) -> dict[str, str]:
        """Generate template variables for a module."""
        # Convert module name formats
        module_name_clean = module_name.lower().replace("-", "_").replace(" ", "_")
        module_name_singular = self._singularize(module_name_clean)
        module_name_title = module_name_clean.replace("_", " ").title()
        module_name_singular_title = module_name_singular.replace("_", " ").title()

        # Generate class names
        model_class = f"{module_name_singular_title.replace(' ', '')}"
        service_class = f"{model_class}Service"
        repository_class = f"{model_class}Repository"
        schema_class = f"{model_class}"

        # Generate variable names
        service_var = f"{module_name_singular}_service"
        table_name = module_name_clean

        # Platform-specific imports
        if platform == Platform.ISP:
            relative_import_base = "..."
            platform_name = "ISP Framework"
        else:
            relative_import_base = ".."
            platform_name = "Management Platform"

        return {
            "module_name": module_name_clean,
            "module_name_singular": module_name_singular,
            "module_name_title": module_name_title,
            "model_class": model_class,
            "service_class": service_class,
            "repository_class": repository_class,
            "schema_class": schema_class,
            "service_var": service_var,
            "table_name": table_name,
            "platform_name": platform_name,
            "relative_import_base": relative_import_base,
            "description": f"{module_name_title} management functionality",
            "model_classes": model_class,
            "schema_classes": f"{schema_class}Response, {schema_class}Create, {schema_class}Update",
            "model_exports": f'"{model_class}"',
            "schema_exports": f'"{schema_class}Response", "{schema_class}Create", "{schema_class}Update"',
        }

    def _singularize(self, word: str) -> str:
        """Simple singularization (extend as needed)."""
        if word.endswith("s") and len(word) > 1:
            return word[:-1]
        return word

    def generate_component(self, component_name: str, variables: dict[str, str]) -> str:
        """Generate a specific component with template variables."""
        if component_name not in self.component_templates:
            raise ValueError(f"Unknown component: {component_name}")

        template = self.component_templates[component_name]
        template_obj = Template(template.template_content)

        return template_obj.safe_substitute(variables)

    def get_required_components(self) -> list[str]:
        """Get list of required component names."""
        return [name for name, config in self.component_templates.items() if config.required]

    def get_all_components(self) -> list[str]:
        """Get list of all component names."""
        return list(self.component_templates.keys())

    def get_component_dependencies(self, component_name: str) -> list[str]:
        """Get dependencies for a specific component."""
        if component_name not in self.component_templates:
            return []
        return self.component_templates[component_name].dependencies
