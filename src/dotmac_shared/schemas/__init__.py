"""
Common schema patterns for DotMac Framework.

This module provides consistent Pydantic models, validation patterns,
and response schemas across all modules.

Usage:
    # Base schemas for common patterns
    from dotmac_shared.schemas import (
        BaseCreateSchema, BaseUpdateSchema, BaseResponseSchema,
        BaseTenantCreateSchema, BaseTenantResponseSchema,
        PaginatedResponseSchema
    )

    # Mixins for common fields
    from dotmac_shared.schemas import (
        TimestampMixin, AuditMixin, TenantMixin, SoftDeleteMixin
    )

    # Validation utilities
    from dotmac_shared.schemas import CommonValidators, EntityStatus
"""

from .base_schemas import (
    # Mixins
    AuditMixin,
    # Base schemas
    BaseCreateSchema,
    BaseCreateWithAuditSchema,
    BaseResponseSchema,
    BaseResponseWithAuditSchema,
    BaseSchema,
    BaseTenantCreateSchema,
    BaseTenantResponseSchema,
    BaseTenantUpdateSchema,
    BaseUpdateSchema,
    BaseUpdateWithAuditSchema,
    # Response schemas
    BulkOperationResponseSchema,
    BulkOperationSchema,
    # Validators and utilities
    CommonValidators,
    EntityStatus,
    ErrorResponseSchema,
    # Pagination and filtering
    FilterParams,
    OperationStatus,
    PaginatedResponseSchema,
    PaginationParams,
    SoftDeleteMixin,
    SortParams,
    SuccessResponseSchema,
    TenantMixin,
    TimestampMixin,
)

__all__ = [
    # Base schemas
    "BaseSchema",
    "BaseCreateSchema",
    "BaseUpdateSchema",
    "BaseResponseSchema",
    "BaseCreateWithAuditSchema",
    "BaseUpdateWithAuditSchema",
    "BaseResponseWithAuditSchema",
    "BaseTenantCreateSchema",
    "BaseTenantUpdateSchema",
    "BaseTenantResponseSchema",
    # Mixins
    "TimestampMixin",
    "AuditMixin",
    "TenantMixin",
    "SoftDeleteMixin",
    # Pagination and filtering
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "PaginatedResponseSchema",
    # Response schemas
    "ErrorResponseSchema",
    "SuccessResponseSchema",
    "BulkOperationSchema",
    "BulkOperationResponseSchema",
    # Validators and utilities
    "CommonValidators",
    "EntityStatus",
    "OperationStatus",
]
