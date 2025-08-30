"""Shared API components for DRY patterns across the ISP framework."""

from .dependencies import AdminDeps, PaginatedDeps, SearchDeps, StandardDeps
from .exception_handlers import standard_exception_handler
from .router_factory import RouterFactory

__all__ = [
    "StandardDeps",
    "PaginatedDeps",
    "SearchDeps",
    "AdminDeps",
    "standard_exception_handler",
    "RouterFactory",
]
