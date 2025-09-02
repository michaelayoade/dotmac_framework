"""Shared API components for DRY patterns across the ISP framework."""

from .dependencies import (
    StandardDependencies,
    PaginatedDependencies, 
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps
)
from .exception_handlers import standard_exception_handler
from .router_factory import RouterFactory

__all__ = [
    "StandardDependencies",
    "PaginatedDependencies",
    "SearchParams",
    "get_standard_deps",
    "get_paginated_deps", 
    "get_admin_deps",
    "standard_exception_handler",
    "RouterFactory",
]
