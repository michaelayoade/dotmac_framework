"""
API utilities for DotMac Framework.

This module provides consistent API patterns including:
- Router factories for CRUD operations
- Exception handling decorators
- Dependency injection patterns
- Rate limiting utilities

Usage:
    # Create CRUD router
    from dotmac_shared.api import RouterFactory
    router = RouterFactory.create_crud_router(
        service_class=MyService,
        create_schema=MyCreateSchema,
        update_schema=MyUpdateSchema,
        response_schema=MyResponseSchema,
        prefix="/api/items",
        tags=["Items"]
    )

    # Use exception handling
    from dotmac_shared.api import standard_exception_handler

    @router.post("/items")
    @standard_exception_handler
    async def create_item(...):
        pass
"""

from .dependencies import (
    BulkOperationParams,
    FileUploadParams,
    PaginatedDependencies,
    SearchParams,
    StandardDependencies,
    create_entity_id_validator,
    get_admin_deps,
    get_paginated_deps,
    get_standard_deps,
)
from .exception_handlers import (
    ErrorLogger,
    ErrorResponse,
    auth_exception_handler,
    billing_exception_handler,
    handle_generic_exception,
    handle_http_exception,
    handle_validation_exception,
    network_exception_handler,
    register_exception_handlers,
    standard_exception_handler,
)
from .rate_limiting import rate_limit
from .router_factory import RouterFactory, RouterValidationError

__all__ = [
    # Router factory
    "RouterFactory",
    "RouterValidationError",
    # Exception handling
    "standard_exception_handler",
    "auth_exception_handler",
    "billing_exception_handler",
    "network_exception_handler",
    "ErrorResponse",
    "ErrorLogger",
    "handle_http_exception",
    "handle_validation_exception",
    "handle_generic_exception",
    "register_exception_handlers",
    # Dependencies
    "StandardDependencies",
    "PaginatedDependencies",
    "SearchParams",
    "FileUploadParams",
    "BulkOperationParams",
    "get_standard_deps",
    "get_paginated_deps",
    "get_admin_deps",
    "create_entity_id_validator",
    # Rate limiting
    "rate_limit",
]
