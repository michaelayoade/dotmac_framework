"""Customer management service."""

import logging
import secrets
import string
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dotmac_isp.sdks import create_sdk_registry
from dotmac_isp.modules.identity import models, schemas
from dotmac_isp.modules.identity.repository import CustomerRepository, UserRepository
from dotmac_isp.modules.identity.portal_id_generator import get_portal_id_generator
from dotmac_isp.modules.identity.portal_service import PortalAccountService
from dotmac_isp.modules.portal_management.models import PortalAccountType
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)
from .base_service import BaseIdentityService

logger = logging.getLogger(__name__)


class CustomerService(BaseIdentityService):
    """Service for customer management operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize customer service."""
        super().__init__(db, tenant_id)
        self.customer_repo = CustomerRepository(db, self.tenant_id)
        self.user_repo = UserRepository(db, self.tenant_id)
        self.portal_service = PortalAccountService(db, str(self.tenant_id))
        self.sdk_registry = create_sdk_registry(str(self.tenant_id))

    async def create_customer(
        self, customer_data: schemas.CustomerCreate
    ) -> schemas.CustomerResponse:
        """Create a new customer with full data validation and business rules."""
        try:
            # Validate business rules
            self._validate_customer_creation_sync(customer_data)

            # Generate portal ID for the customer using configurable generator
            existing_portal_ids = self._get_existing_portal_ids()
            portal_id = get_portal_id_generator().generate_portal_id(
                existing_portal_ids
            )

            # Generate secure password for the customer
            generated_password = self._generate_secure_password()

            # Prepare customer data for repository
            repo_data = {
                "customer_number": customer_data.customer_number,
                "display_name": (
                    customer_data.display_name
                    or f"{customer_data.first_name} {customer_data.last_name}"
                ),
                "customer_type": (
                    customer_data.customer_type.value
                    if hasattr(customer_data.customer_type, "value")
                    else customer_data.customer_type
                ),
                "account_status": models.AccountStatus.PENDING.value,
                "first_name": customer_data.first_name,
                "last_name": customer_data.last_name,
                "company_name": getattr(customer_data, "company_name", None),
                "email": getattr(customer_data, "email", None),
                "phone": getattr(customer_data, "phone", None),
                "portal_id": portal_id,
            }

            # Create customer in database
            db_customer = self.customer_repo.create(repo_data)

            # Create portal account for customer
            if hasattr(customer_data, "email") and customer_data.email:
                try:
                    portal_account_data = {
                        "customer_id": db_customer.id,
                        "portal_id": portal_id,
                        "account_type": PortalAccountType.CUSTOMER,
                        "email": customer_data.email,
                        "password": generated_password,
                        "first_name": customer_data.first_name,
                        "last_name": customer_data.last_name,
                        "is_active": True,
                    }

                    await self.portal_service.create_portal_account(portal_account_data)
                    logger.info(f"Created portal account for customer: {portal_id}")
                except Exception as portal_error:
                    logger.warning(f"Failed to create portal account: {portal_error}")
                    # Don't fail customer creation if portal creation fails

            # Update customer status to active after successful setup
            db_customer = self.customer_repo.update(
                db_customer.id, {"account_status": models.AccountStatus.ACTIVE.value}
            )

            logger.info(
                f"Successfully created customer: {db_customer.id} with portal ID: {portal_id}"
            )

            return self._map_customer_to_response(
                db_customer, portal_id, generated_password
            )

        except ValidationError:
            raise
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Failed to create customer: {str(e)}")
            raise ServiceError(f"Customer creation failed: {str(e)}")

    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Get customer by ID."""
        try:
            db_customer = self.customer_repo.get_by_id(customer_id)
            if not db_customer:
                raise NotFoundError(f"Customer not found: {customer_id}")

            return self._map_customer_to_response(db_customer)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get customer {customer_id}: {str(e)}")
            raise ServiceError(f"Failed to retrieve customer: {str(e)}")

    async def update_customer(
        self, customer_id: UUID, update_data: schemas.CustomerUpdate
    ) -> schemas.CustomerResponse:
        """Update customer information."""
        try:
            # Validate customer exists
            existing_customer = self.customer_repo.get_by_id(customer_id)
            if not existing_customer:
                raise NotFoundError(f"Customer not found: {customer_id}")

            # Validate update data
            await self._validate_customer_update(customer_id, update_data)

            # Update customer
            update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                db_customer = self.customer_repo.update(customer_id, update_dict)
                logger.info(f"Updated customer: {customer_id}")

                return self._map_customer_to_response(db_customer)
            else:
                return self._map_customer_to_response(existing_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update customer {customer_id}: {str(e)}")
            raise ServiceError(f"Customer update failed: {str(e)}")

    async def list_customers(
        self,
        filters: Optional[schemas.CustomerFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> schemas.CustomerListResponse:
        """List customers with optional filtering."""
        try:
            # Build filter dictionary from filters object
            filter_dict = {}
            if filters:
                if filters.customer_type:
                    filter_dict["customer_type"] = filters.customer_type
                if filters.account_status:
                    filter_dict["account_status"] = filters.account_status
                if filters.search_term:
                    # This would be implemented in repository
                    filter_dict["search_term"] = filters.search_term

            # Get customers from repository
            customers, total_count = self.customer_repo.list_with_filters(
                filters=filter_dict, limit=limit, offset=offset
            )

            # Map to response format
            customer_responses = [
                self._map_customer_to_response(customer) for customer in customers
            ]

            return schemas.CustomerListResponse(
                customers=customer_responses,
                total_count=total_count,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            logger.error(f"Failed to list customers: {str(e)}")
            raise ServiceError(f"Failed to list customers: {str(e)}")

    async def activate_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Activate customer account."""
        try:
            await self._validate_customer_activation(customer_id)

            db_customer = self.customer_repo.update(
                customer_id, {"account_status": models.AccountStatus.ACTIVE.value}
            )

            logger.info(f"Activated customer: {customer_id}")
            return self._map_customer_to_response(db_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to activate customer {customer_id}: {str(e)}")
            raise ServiceError(f"Customer activation failed: {str(e)}")

    async def suspend_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Suspend customer account."""
        try:
            await self._validate_customer_suspension(customer_id)

            db_customer = self.customer_repo.update(
                customer_id, {"account_status": models.AccountStatus.SUSPENDED.value}
            )

            logger.info(f"Suspended customer: {customer_id}")
            return self._map_customer_to_response(db_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to suspend customer {customer_id}: {str(e)}")
            raise ServiceError(f"Customer suspension failed: {str(e)}")

    # Validation methods
    def _validate_customer_creation_sync(
        self, customer_data: schemas.CustomerCreate
    ) -> None:
        """Validate customer creation data (synchronous)."""
        if not customer_data.customer_number:
            raise ValidationError("Customer number is required")

        if not customer_data.first_name or not customer_data.last_name:
            raise ValidationError("First name and last name are required")

        # Check for duplicate customer number
        if self.customer_repo.get_by_customer_number(customer_data.customer_number):
            raise ConflictError(
                f"Customer number already exists: {customer_data.customer_number}"
            )

    async def _validate_customer_update(
        self, customer_id: UUID, update_data: schemas.CustomerUpdate
    ) -> None:
        """Validate customer update data."""
        # Add validation logic as needed
        pass

    async def _validate_customer_activation(self, customer_id: UUID) -> None:
        """Validate customer can be activated."""
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundError(f"Customer not found: {customer_id}")

    async def _validate_customer_suspension(self, customer_id: UUID) -> None:
        """Validate customer can be suspended."""
        customer = self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise NotFoundError(f"Customer not found: {customer_id}")

    def _get_existing_portal_ids(self) -> set:
        """Get existing portal IDs to avoid duplicates."""
        existing_customers = self.customer_repo.get_all()
        return {
            customer.portal_id for customer in existing_customers if customer.portal_id
        }

    def _generate_secure_password(self) -> str:
        """Generate a secure random password."""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(characters) for _ in range(12))

    def _map_customer_to_response(
        self,
        db_customer,
        portal_id: Optional[str] = None,
        password: Optional[str] = None,
    ) -> schemas.CustomerResponse:
        """Map database customer to response schema."""
        return schemas.CustomerResponse(
            id=db_customer.id,
            customer_number=db_customer.customer_number,
            display_name=db_customer.display_name,
            customer_type=db_customer.customer_type,
            account_status=db_customer.account_status,
            first_name=db_customer.first_name,
            last_name=db_customer.last_name,
            company_name=getattr(db_customer, "company_name", None),
            email=getattr(db_customer, "email", None),
            phone=getattr(db_customer, "phone", None),
            portal_id=portal_id or db_customer.portal_id,
            created_at=db_customer.created_at,
            updated_at=db_customer.updated_at,
            generated_password=password,  # Only included on creation
        )
