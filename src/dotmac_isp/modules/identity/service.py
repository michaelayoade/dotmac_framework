"""
Main identity service orchestrator.
Coordinates all identity operations and integrates sub-services.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac.application import standard_exception_handler
from dotmac_shared.services.base import BaseService

from . import schemas
from .services.identity_orchestrator import IdentityOrchestrator

logger = logging.getLogger(__name__)


class IdentityService(BaseService):
    """Main identity service orchestrating all identity operations."""

    def __init__(self, db_session: Session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.orchestrator = IdentityOrchestrator(db_session, tenant_id)

    # User management operations
    @standard_exception_handler
    async def create_user(self, user_data: schemas.UserCreate) -> schemas.User:
        """Create a new user."""
        return await self.orchestrator.create_user(user_data)

    @standard_exception_handler
    async def get_user(self, user_id: UUID) -> Optional[schemas.User]:
        """Get user by ID."""
        return await self.orchestrator.get_user(user_id)

    @standard_exception_handler
    async def update_user(self, user_id: UUID, user_data: schemas.UserUpdate) -> schemas.User:
        """Update user information."""
        return await self.orchestrator.update_user(user_id, user_data)

    @standard_exception_handler
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        return await self.orchestrator.delete_user(user_id)

    @standard_exception_handler
    async def list_users(
        self, skip: int = 0, limit: int = 100, filters: Optional[dict[str, Any]] = None
    ) -> list[schemas.User]:
        """List users with optional filtering."""
        return await self.orchestrator.list_users(skip=skip, limit=limit, filters=filters)

    # Customer management operations
    @standard_exception_handler
    async def create_customer(self, customer_data: schemas.CustomerCreate) -> schemas.Customer:
        """Create a new customer."""
        return await self.orchestrator.create_customer(customer_data)

    @standard_exception_handler
    async def get_customer(self, customer_id: UUID) -> Optional[schemas.Customer]:
        """Get customer by ID."""
        return await self.orchestrator.get_customer(customer_id)

    @standard_exception_handler
    async def update_customer(self, customer_id: UUID, customer_data: schemas.CustomerUpdate) -> schemas.Customer:
        """Update customer information."""
        return await self.orchestrator.update_customer(customer_id, customer_data)

    @standard_exception_handler
    async def delete_customer(self, customer_id: UUID) -> bool:
        """Delete a customer."""
        return await self.orchestrator.delete_customer(customer_id)

    @standard_exception_handler
    async def list_customers(
        self, skip: int = 0, limit: int = 100, filters: Optional[dict[str, Any]] = None
    ) -> list[schemas.Customer]:
        """List customers with optional filtering."""
        return await self.orchestrator.list_customers(skip=skip, limit=limit, filters=filters)

    # Authentication operations
    @standard_exception_handler
    async def authenticate_user(self, username: str, password: str) -> Optional[schemas.User]:
        """Authenticate a user with username/password."""
        return await self.orchestrator.authenticate_user(username, password)

    @standard_exception_handler
    async def authenticate_customer_portal(self, portal_id: str, password: str) -> Optional[schemas.Customer]:
        """Authenticate customer via portal ID."""
        return await self.orchestrator.authenticate_customer_portal(portal_id, password)

    @standard_exception_handler
    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """Change user password."""
        return await self.orchestrator.change_password(user_id, old_password, new_password)

    @standard_exception_handler
    async def reset_password(self, email: str) -> bool:
        """Initiate password reset for user."""
        return await self.orchestrator.reset_password(email)

    # Portal management operations
    @standard_exception_handler
    async def generate_portal_id(self, customer_id: UUID) -> str:
        """Generate unique portal ID for customer."""
        return await self.orchestrator.generate_portal_id(customer_id)

    @standard_exception_handler
    async def get_customer_by_portal_id(self, portal_id: str) -> Optional[schemas.Customer]:
        """Get customer by portal ID."""
        return await self.orchestrator.get_customer_by_portal_id(portal_id)

    @standard_exception_handler
    async def validate_portal_id(self, portal_id: str) -> bool:
        """Validate portal ID format and availability."""
        return await self.orchestrator.validate_portal_id(portal_id)

    # Bulk operations
    @standard_exception_handler
    async def bulk_create_users(self, users_data: list[schemas.UserCreate]) -> list[schemas.User]:
        """Create multiple users in bulk."""
        return await self.orchestrator.bulk_create_users(users_data)

    @standard_exception_handler
    async def bulk_update_users(self, updates: dict[UUID, schemas.UserUpdate]) -> list[schemas.User]:
        """Update multiple users in bulk."""
        return await self.orchestrator.bulk_update_users(updates)

    # Search and analytics
    @standard_exception_handler
    async def search_users(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[schemas.User]:
        """Search users by query."""
        return await self.orchestrator.search_users(query, filters)

    @standard_exception_handler
    async def search_customers(self, query: str, filters: Optional[dict[str, Any]] = None) -> list[schemas.Customer]:
        """Search customers by query."""
        return await self.orchestrator.search_customers(query, filters)

    @standard_exception_handler
    async def get_identity_statistics(self) -> dict[str, Any]:
        """Get identity module statistics."""
        return await self.orchestrator.get_identity_statistics()

    # Validation and business rules
    @standard_exception_handler
    async def validate_user_data(self, user_data: schemas.UserCreate) -> dict[str, Any]:
        """Validate user data against business rules."""
        return await self.orchestrator.validate_user_data(user_data)

    @standard_exception_handler
    async def validate_customer_data(self, customer_data: schemas.CustomerCreate) -> dict[str, Any]:
        """Validate customer data against business rules."""
        return await self.orchestrator.validate_customer_data(customer_data)
