"""Base CRUD router classes to eliminate code duplication across modules."""

from typing import Type, TypeVar, Generic, List, Optional, Any, Dict
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from pydantic import BaseModel

from dotmac_isp.shared.database import get_db
from dotmac_isp.shared.auth import get_current_tenant
from dotmac_isp.shared.database.base import TenantModel

# Type variables for generic CRUD operations
ModelType = TypeVar("ModelType", bound=TenantModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
ResponseSchemaType = TypeVar("ResponseSchemaType", bound=BaseModel)


class BaseCRUDRouter(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType], ABC
):
    """Base CRUD router class to eliminate duplicate endpoint patterns."""

    def __init__(
        self,
        model: Type[ModelType],
        create_schema: Type[CreateSchemaType],
        update_schema: Type[UpdateSchemaType],
        response_schema: Type[ResponseSchemaType],
        prefix: str,
        tags: List[str],
        entity_name: str = None,
    ):
        """Initialize the base CRUD router.

        Args:
            model: SQLAlchemy model class
            create_schema: Pydantic schema for creation
            update_schema: Pydantic schema for updates
            response_schema: Pydantic schema for responses
            prefix: Router prefix (e.g., "/customers")
            tags: OpenAPI tags for the router
            entity_name: Human-readable entity name for messages
        """
        self.model = model
        self.create_schema = create_schema
        self.update_schema = update_schema
        self.response_schema = response_schema
        self.entity_name = entity_name or model.__name__.lower()

        self.router = APIRouter(prefix=prefix, tags=tags)
        self._register_endpoints()

    def _register_endpoints(self):
        """Register all CRUD endpoints."""
        self.router.post("/", response_model=self.response_schema, status_code=201)(
            self._create_item
        )
        self.router.get("/", response_model=List[self.response_schema])(
            self._list_items
        )
        self.router.get("/{item_id}", response_model=self.response_schema)(
            self._get_item
        )
        self.router.put("/{item_id}", response_model=self.response_schema)(
            self._update_item
        )
        self.router.delete("/{item_id}")(self._delete_item)

    async def _create_item(
        self,
        item_data: CreateSchemaType,
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> ModelType:
        """Create a new item."""
        # Prepare data with tenant_id and unique ID
        item_dict = item_data.model_dump()
        item_dict["tenant_id"] = tenant_id
        item_dict["id"] = str(uuid4())

        # Allow subclasses to modify creation data
        item_dict = self.prepare_create_data(item_dict, db, tenant_id)

        # Check for uniqueness constraints
        await self.validate_create(item_dict, db, tenant_id)

        db_item = self.model(**item_dict)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)

        return db_item

    async def _list_items(
        self,
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(
            100, ge=1, le=1000, description="Maximum number of records to return"
        ),
        search: Optional[str] = Query(None, description="Search term"),
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_desc: bool = Query(False, description="Sort in descending order"),
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
        **filters,
    ) -> List[ModelType]:
        """List items with filtering, search, and pagination."""
        query = db.query(self.model).filter(self.model.tenant_id == tenant_id)

        # Apply search if supported
        if search:
            query = self.apply_search(query, search)

        # Apply filters
        query = self.apply_filters(query, filters, db, tenant_id)

        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            order_field = getattr(self.model, sort_by)
            query = query.order_by(desc(order_field) if sort_desc else asc(order_field))
        else:
            # Default sorting by created_at if available
            if hasattr(self.model, "created_at"):
                query = query.order_by(desc(self.model.created_at))

        return query.offset(skip).limit(limit).all()

    async def _get_item(
        self,
        item_id: str = Path(..., description="Item ID"),
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> ModelType:
        """Get a specific item by ID."""
        db_item = (
            db.query(self.model)
            .filter(and_(self.model.id == item_id, self.model.tenant_id == tenant_id))
            .first()
        )

        if not db_item:
            raise HTTPException(
                status_code=404, detail=f"{self.entity_name.title()} not found"
            )

        return db_item

    async def _update_item(
        self,
        item_id: str = Path(..., description="Item ID"),
        item_update: UpdateSchemaType = None,
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> ModelType:
        """Update an existing item."""
        db_item = await self._get_item(item_id, db, tenant_id)

        update_data = item_update.model_dump(exclude_unset=True) if item_update else {}
        update_data = self.prepare_update_data(update_data, db_item, db, tenant_id)

        # Validate update
        await self.validate_update(update_data, db_item, db, tenant_id)

        for field, value in update_data.items():
            setattr(db_item, field, value)

        # Update timestamp if available
        if hasattr(db_item, "updated_at"):
            db_item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_item)

        return db_item

    async def _delete_item(
        self,
        item_id: str = Path(..., description="Item ID"),
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> Dict[str, str]:
        """Delete an item."""
        db_item = await self._get_item(item_id, db, tenant_id)

        # Allow subclasses to perform pre-delete validation
        await self.validate_delete(db_item, db, tenant_id)

        db.delete(db_item)
        db.commit()

        return {"message": f"{self.entity_name.title()} deleted successfully"}

    # Abstract methods for subclasses to override
    def prepare_create_data(
        self, data: Dict[str, Any], db: Session, tenant_id: str
    ) -> Dict[str, Any]:
        """Override to modify data before creation."""
        return data

    def prepare_update_data(
        self, data: Dict[str, Any], db_item: ModelType, db: Session, tenant_id: str
    ) -> Dict[str, Any]:
        """Override to modify data before update."""
        return data

    async def validate_create(self, data: Dict[str, Any], db: Session, tenant_id: str):
        """Override to add creation validation."""
        pass

    async def validate_update(
        self, data: Dict[str, Any], db_item: ModelType, db: Session, tenant_id: str
    ):
        """Override to add update validation."""
        pass

    async def validate_delete(self, db_item: ModelType, db: Session, tenant_id: str):
        """Override to add deletion validation."""
        pass

    def apply_search(self, query, search_term: str):
        """Override to implement search functionality."""
        # Default implementation - no search
        return query

    def apply_filters(
        self, query, filters: Dict[str, Any], db: Session, tenant_id: str
    ):
        """Override to apply custom filters."""
        # Default implementation - no additional filters
        return query


class BaseStatusRouter(
    BaseCRUDRouter[ModelType, CreateSchemaType, UpdateSchemaType, ResponseSchemaType]
):
    """Extended CRUD router for entities with status management."""

    def __init__(self, status_field: str = "status", **kwargs):
        """Initialize with status field name."""
        self.status_field = status_field
        super().__init__(**kwargs)

        # Add status-specific endpoints
        self.router.put("/{item_id}/status")(self._update_status)
        self.router.get(
            "/by-status/{status_value}", response_model=List[self.response_schema]
        )(self._list_by_status)

    async def _update_status(
        self,
        item_id: str = Path(..., description="Item ID"),
        status_value: str = None,
        reason: Optional[str] = None,
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> ModelType:
        """Update item status."""
        db_item = await self._get_item(item_id, db, tenant_id)

        # Validate status transition
        await self.validate_status_change(db_item, status_value, db, tenant_id)

        old_status = getattr(db_item, self.status_field)
        setattr(db_item, self.status_field, status_value)

        # Record status change if there's a notes field
        if hasattr(db_item, "notes") and reason:
            current_notes = db_item.notes or ""
            status_note = (
                f"Status changed from {old_status} to {status_value}: {reason}"
            )
            db_item.notes = (
                f"{current_notes}\n{status_note}" if current_notes else status_note
            )

        if hasattr(db_item, "updated_at"):
            from datetime import datetime

            db_item.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_item)

        return db_item

    async def _list_by_status(
        self,
        status_value: str = Path(..., description="Status value"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> List[ModelType]:
        """List items by status."""
        query = db.query(self.model).filter(
            and_(
                self.model.tenant_id == tenant_id,
                getattr(self.model, self.status_field) == status_value,
            )
        )

        if hasattr(self.model, "created_at"):
            query = query.order_by(desc(self.model.created_at))

        return query.offset(skip).limit(limit).all()

    async def validate_status_change(
        self, db_item: ModelType, new_status: str, db: Session, tenant_id: str
    ):
        """Override to validate status transitions."""
        pass


class BaseDashboardMixin:
    """Mixin to add dashboard endpoints."""

    def add_dashboard_endpoints(self):
        """Add dashboard endpoints to the router."""
        self.router.get("/dashboard")(self._get_dashboard)

    async def _get_dashboard(
        self,
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> Dict[str, Any]:
        """Get dashboard data."""
        return await self.get_dashboard_data(db, tenant_id)

    async def get_dashboard_data(self, db: Session, tenant_id: str) -> Dict[str, Any]:
        """Override to implement dashboard logic."""
        total_count = (
            db.query(self.model).filter(self.model.tenant_id == tenant_id).count()
        )
        return {"total_count": total_count, "entity_type": self.entity_name}


class BaseReportMixin:
    """Mixin to add reporting endpoints."""

    def add_report_endpoints(self):
        """Add report endpoints to the router."""
        self.router.get("/reports/summary")(self._get_summary_report)

    async def _get_summary_report(
        self,
        start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
        db: Session = Depends(get_db),
        tenant_id: str = Depends(get_current_tenant),
    ) -> Dict[str, Any]:
        """Get summary report."""
        return await self.get_summary_report_data(start_date, end_date, db, tenant_id)

    async def get_summary_report_data(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        db: Session,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Override to implement report logic."""
        query = db.query(self.model).filter(self.model.tenant_id == tenant_id)

        if start_date and hasattr(self.model, "created_at"):
            from datetime import datetime

            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(self.model.created_at >= start_dt)

        if end_date and hasattr(self.model, "created_at"):
            from datetime import datetime

            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(self.model.created_at <= end_dt)

        return {
            "total_count": query.count(),
            "period": {"start_date": start_date, "end_date": end_date},
        }


# Utility functions for common patterns
def generate_unique_code(prefix: str) -> str:
    """Generate a unique code with timestamp."""
    from datetime import datetime

    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"{prefix}-{timestamp}"


def generate_sequential_number(prefix: str, sequence_field: str) -> str:
    """Generate a sequential number (to be implemented with database sequences)."""
    from datetime import datetime

    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"{prefix}-{timestamp}"


class CommonSearchMixin:
    """Mixin to add common search functionality."""

    def apply_search(self, query, search_term: str):
        """Apply search to common fields like name, description, code."""
        if not search_term:
            return query

        search_conditions = []
        search_pattern = f"%{search_term}%"

        # Common searchable fields
        searchable_fields = ["name", "title", "description", "code", "email"]

        for field_name in searchable_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                search_conditions.append(field.ilike(search_pattern))

        if search_conditions:
            query = query.filter(or_(*search_conditions))

        return query
