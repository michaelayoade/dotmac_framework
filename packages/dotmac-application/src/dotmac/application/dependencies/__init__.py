"""Dependency injection utilities for DotMac Application Framework."""

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


# Placeholder functions - to be implemented when auth is consolidated
def get_current_user():
    """Get current authenticated user."""
    # TODO: Implement when auth is fully consolidated
    return {}


__all__ = [
    "StandardDependencies",
    "PaginatedDependencies",
    "get_standard_deps",
    "get_paginated_deps",
    "get_admin_deps",
    "get_current_user",
    "SearchParams",
    "FileUploadParams",
    "BulkOperationParams",
    "create_entity_id_validator",
]
