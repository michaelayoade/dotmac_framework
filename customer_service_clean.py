#!/usr/bin/env python3
"""Clean up the customer_service.py file by creating a minimal working version."""

def create_clean_customer_service():
    """Create a clean customer service file."""
    content = '''"""
DEPRECATED Customer service module.

This module has been deprecated. Use dotmac_isp.modules.identity.service.CustomerService instead.
"""

import warnings
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.shared.exceptions import NotImplementedError
from dotmac_isp.modules.identity import schemas


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
            stacklevel=2
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
'''
    
    # Write the clean file
    file_path = "/home/dotmac_framework/isp-framework/src/dotmac_isp/modules/identity/services/customer_service.py"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created clean customer_service.py")

if __name__ == "__main__":
    create_clean_customer_service()