"""
DEPRECATED Customer service module.

This module has been deprecated. Use dotmac_isp.modules.identity.service.CustomerService instead.
"""

import warnings
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.modules.identity import schemas
from dotmac_isp.shared.exceptions import NotImplementedError


class CustomerService:
    """DEPRECATED: Customer service for identity module."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize deprecated customer service."""
        self.db = db
        self.tenant_id = tenant_id

    async def create_customer(
        self, customer_data: schemas.CustomerCreate
    ) -> schemas.CustomerResponse:
        """DEPRECATED: Use main CustomerService instead."""
        warnings.warn(
            "This method is deprecated. Use dotmac_isp.modules.identity.service.CustomerService.create_customer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Redirect to main service
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """DEPRECATED: Get customer by ID."""
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

    async def update_customer(
        self, customer_id: UUID, update_data: schemas.CustomerUpdate
    ) -> schemas.CustomerResponse:
        """DEPRECATED: Update customer information."""
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

    async def list_customers(
        self,
        filters: Optional[schemas.CustomerFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> schemas.CustomerListResponse:
        """DEPRECATED: List customers with optional filtering."""
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

    async def activate_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """DEPRECATED: Activate customer account."""
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )

    async def suspend_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """DEPRECATED: Suspend customer account."""
        raise NotImplementedError(
            "Use dotmac_isp.modules.identity.service.CustomerService instead"
        )
