"""DEPRECATED: Customer domain service - use main service instead.

This file has been consolidated into modules/identity/service.py.
Use: from dotmac_isp.modules.identity.service import CustomerService

This domain-driven approach has been merged into the standardized service pattern.
This implementation will be removed in a future version.
"""

import warnings
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import logging

from .interfaces import ICustomerService, IUserValidationService, IIdentityEventService
from ..models import Customer, CustomerType
from .. import schemas
from ..repository import CustomerRepository
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)

logger = logging.getLogger(__name__)

warnings.warn(
    "This domain CustomerService is deprecated. Use dotmac_isp.modules.identity.service.CustomerService instead.",
    DeprecationWarning,
    stacklevel=2
)


class CustomerService(ICustomerService):
    """DEPRECATED: Domain service - use main CustomerService instead."""

    def __init__(
        self,
        customer_repo: CustomerRepository,
        validation_service: IUserValidationService,
        event_service: IIdentityEventService,
        tenant_id: UUID,
    ):
        warnings.warn(
            "This domain CustomerService is deprecated. Use dotmac_isp.modules.identity.service.CustomerService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.customer_repo = customer_repo
        self.validation_service = validation_service
        self.event_service = event_service
        self.tenant_id = tenant_id

    async def create_customer(
        self, customer_data: schemas.CustomerCreate
    ) -> schemas.CustomerResponse:
        """DEPRECATED: Use main CustomerService instead."""
        warnings.warn(
            "This method is deprecated. Use dotmac_isp.modules.identity.service.CustomerService.create_customer instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Redirect to main service
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

            # Prepare customer data
            customer_dict = {
                "customer_number": customer_number,
                "display_name": customer_data.display_name,
                "customer_type": customer_data.customer_type,
                "status": "active",
                "first_name": customer_data.first_name,
                "last_name": customer_data.last_name,
                "middle_name": customer_data.middle_name,
                "date_of_birth": customer_data.date_of_birth,
                "company_name": customer_data.company_name,
                "tax_id": customer_data.tax_id,
                "email_primary": customer_data.email_primary,
                "email_secondary": customer_data.email_secondary,
                "phone_primary": customer_data.phone_primary,
                "phone_secondary": customer_data.phone_secondary,
                "phone_mobile": customer_data.phone_mobile,
                "preferred_contact_method": customer_data.preferred_contact_method
                or "email",
                "language_preference": customer_data.language_preference or "en",
                "timezone": customer_data.timezone or "UTC",
                "notes": customer_data.notes,
                "tags": customer_data.tags or [],
                "custom_fields": customer_data.custom_fields or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Create customer
            customer = self.customer_repo.create(customer_dict)

            # Publish customer created event
            await self.event_service.publish_customer_created(customer)

            logger.info(f"Customer created successfully: {customer.id}")
            return self._to_response_schema(customer)

        except (ValidationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Failed to create customer: {str(e)}")
            raise ServiceError(f"Customer creation failed: {str(e)}")

    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Get customer by ID."""
        try:
            customer = self.customer_repo.get_by_id(customer_id)
            if not customer:
                raise NotFoundError(f"Customer not found: {customer_id}")

            return self._to_response_schema(customer)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve customer: {str(e)}")
            raise ServiceError(f"Failed to retrieve customer: {str(e)}")

    async def update_customer(
        self, customer_id: UUID, update_data: schemas.CustomerUpdate
    ) -> schemas.CustomerResponse:
        """Update customer information with validation."""
        try:
            logger.info(f"Updating customer: {customer_id}")

            # Get existing customer
            customer = self.customer_repo.get_by_id(customer_id)
            if not customer:
                raise NotFoundError(f"Customer not found: {customer_id}")

            # Validate update data
            await self._validate_update_data(update_data, customer_id)

            # Prepare update dictionary
            update_dict = {}
            if update_data.display_name is not None:
                update_dict["display_name"] = update_data.display_name
            if update_data.first_name is not None:
                update_dict["first_name"] = update_data.first_name
            if update_data.last_name is not None:
                update_dict["last_name"] = update_data.last_name
            if update_data.middle_name is not None:
                update_dict["middle_name"] = update_data.middle_name
            if update_data.date_of_birth is not None:
                update_dict["date_of_birth"] = update_data.date_of_birth
            if update_data.company_name is not None:
                update_dict["company_name"] = update_data.company_name
            if update_data.email_primary is not None:
                update_dict["email_primary"] = update_data.email_primary
            if update_data.phone_primary is not None:
                update_dict["phone_primary"] = update_data.phone_primary
            if update_data.preferred_contact_method is not None:
                update_dict["preferred_contact_method"] = (
                    update_data.preferred_contact_method
                )
            if update_data.language_preference is not None:
                update_dict["language_preference"] = update_data.language_preference
            if update_data.timezone is not None:
                update_dict["timezone"] = update_data.timezone
            if update_data.notes is not None:
                update_dict["notes"] = update_data.notes
            if update_data.tags is not None:
                update_dict["tags"] = update_data.tags
            if update_data.custom_fields is not None:
                # Merge custom fields instead of replacing
                existing_fields = customer.custom_fields or {}
                existing_fields.update(update_data.custom_fields)
                update_dict["custom_fields"] = existing_fields

            update_dict["updated_at"] = datetime.utcnow()

            # Update customer
            updated_customer = self.customer_repo.update(customer_id, update_dict)

            logger.info(f"Customer updated successfully: {customer_id}")
            return self._to_response_schema(updated_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update customer: {str(e)}")
            raise ServiceError(f"Customer update failed: {str(e)}")

    async def deactivate_customer(self, customer_id: UUID, reason: str) -> bool:
        """Deactivate customer account."""
        try:
            logger.info(f"Deactivating customer: {customer_id}")

            # Get customer
            customer = self.customer_repo.get_by_id(customer_id)
            if not customer:
                raise NotFoundError(f"Customer not found: {customer_id}")

            if customer.status == "inactive":
                logger.info(f"Customer {customer_id} is already inactive")
                return True

            # Update status
            update_data = {
                "status": "inactive",
                "deactivation_reason": reason,
                "deactivated_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            self.customer_repo.update(customer_id, update_data)

            # Publish deactivation event
            await self.event_service.publish_account_deactivated(customer_id, reason)

            logger.info(f"Customer deactivated successfully: {customer_id}")
            return True

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate customer: {str(e)}")
            raise ServiceError(f"Customer deactivation failed: {str(e)}")

    async def search_customers(
        self, filters: schemas.CustomerSearchFilters
    ) -> List[schemas.CustomerResponse]:
        """Search customers with filters."""
        try:
            customers = self.customer_repo.search(filters)
            return [self._to_response_schema(customer) for customer in customers]

        except Exception as e:
            logger.error(f"Customer search failed: {str(e)}")
            raise ServiceError(f"Customer search failed: {str(e)}")

    async def validate_customer_data(
        self, customer_data: schemas.CustomerCreate
    ) -> bool:
        """Validate customer creation data."""
        # Validate email format
        if not await self.validation_service.validate_email_format(
            customer_data.email_primary
        ):
            raise ValidationError("Invalid primary email format")

        # Validate email uniqueness
        if not await self.validation_service.validate_email_uniqueness(
            customer_data.email_primary
        ):
            raise ValidationError("Primary email already exists")

        # Validate secondary email if provided
        if customer_data.email_secondary:
            if not await self.validation_service.validate_email_format(
                customer_data.email_secondary
            ):
                raise ValidationError("Invalid secondary email format")

        # Validate phone numbers if provided
        if customer_data.phone_primary:
            if not await self.validation_service.validate_phone_format(
                customer_data.phone_primary
            ):
                raise ValidationError("Invalid primary phone format")

        # Validate customer number uniqueness if provided
        if customer_data.customer_number:
            if not await self.validation_service.validate_customer_number_uniqueness(
                customer_data.customer_number
            ):
                raise ValidationError("Customer number already exists")

        # Business rule validations
        if customer_data.customer_type == CustomerType.BUSINESS:
            if not customer_data.company_name:
                raise ValidationError("Company name is required for business customers")

        if customer_data.date_of_birth:
            # Check if customer is at least 18 years old
            from datetime import date

            today = date.today()
            age = today.year - customer_data.date_of_birth.year
            if today < customer_data.date_of_birth.replace(year=today.year):
                age -= 1
            if age < 18:
                raise ValidationError("Customer must be at least 18 years old")

        return True

    async def generate_customer_number(self) -> str:
        """Generate unique customer number."""
        try:
            # Get the next sequence number from repository
            sequence = self.customer_repo.get_next_customer_sequence()

            # Format: CUST-YYYYMMDD-NNNN
            today = datetime.now().strftime("%Y%m%d")
            customer_number = f"CUST-{today}-{sequence:04d}"

            # Ensure uniqueness (in case of race conditions)
            while not await self.validation_service.validate_customer_number_uniqueness(
                customer_number
            ):
                sequence += 1
                customer_number = f"CUST-{today}-{sequence:04d}"

            return customer_number

        except Exception as e:
            logger.error(f"Failed to generate customer number: {str(e)}")
            raise ServiceError(f"Failed to generate customer number: {str(e)}")

    async def _validate_update_data(
        self, update_data: schemas.CustomerUpdate, customer_id: UUID
    ) -> None:
        """Validate customer update data."""
        if update_data.email_primary:
            if not await self.validation_service.validate_email_format(
                update_data.email_primary
            ):
                raise ValidationError("Invalid primary email format")
            if not await self.validation_service.validate_email_uniqueness(
                update_data.email_primary, customer_id
            ):
                raise ValidationError("Primary email already exists")

        if update_data.email_secondary:
            if not await self.validation_service.validate_email_format(
                update_data.email_secondary
            ):
                raise ValidationError("Invalid secondary email format")

        if update_data.phone_primary:
            if not await self.validation_service.validate_phone_format(
                update_data.phone_primary
            ):
                raise ValidationError("Invalid primary phone format")

    def _to_response_schema(self, customer: Customer) -> schemas.CustomerResponse:
        """Convert customer model to response schema."""
        return schemas.CustomerResponse(
            id=customer.id,
            tenant_id=customer.tenant_id,
            customer_number=customer.customer_number,
            display_name=customer.display_name,
            customer_type=customer.customer_type,
            status=customer.status,
            first_name=customer.first_name,
            last_name=customer.last_name,
            middle_name=customer.middle_name,
            date_of_birth=customer.date_of_birth,
            company_name=customer.company_name,
            tax_id=customer.tax_id,
            email_primary=customer.email_primary,
            email_secondary=customer.email_secondary,
            phone_primary=customer.phone_primary,
            phone_secondary=customer.phone_secondary,
            phone_mobile=customer.phone_mobile,
            preferred_contact_method=customer.preferred_contact_method,
            language_preference=customer.language_preference,
            timezone=customer.timezone,
            notes=customer.notes,
            tags=customer.tags,
            custom_fields=customer.custom_fields,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            deactivated_at=customer.deactivated_at,
            deactivation_reason=customer.deactivation_reason,
        )
