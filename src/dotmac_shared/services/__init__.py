"""
from __future__ import annotations
Unified service layer patterns for DotMac Framework.

This module consolidates service logic from ISP and Management modules,
providing consistent business logic operations, validation, and authorization.

Usage:
    # Create a service instance
    from dotmac_shared.services import create_service
    service = create_service(
        db=db,
        model_class=CustomerModel,
        create_schema=CustomerCreate,
        update_schema=CustomerUpdate,
        response_schema=CustomerResponse,
        tenant_id=tenant_id
    )

    # Use service methods
    customer = await service.create(customer_data, user_id)
    customers = await service.list(skip=0, limit=10, user_id=user_id)
"""

from .base_service import BaseService
from .factory import ServiceFactory, create_service

__all__ = [
    # Base service class
    "BaseService",
    # Factory and convenience functions
    "ServiceFactory",
    "create_service",
]
