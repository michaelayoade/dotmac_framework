"""
Common schema base classes for DotMac Framework.
Exports the standard schema classes used throughout the framework.
"""

from ..schemas.base_schemas import BaseCreateSchema, BaseResponseSchema, BaseUpdateSchema, PaginatedResponseSchema

__all__ = ["BaseCreateSchema", "BaseResponseSchema", "BaseUpdateSchema", "PaginatedResponseSchema"]
