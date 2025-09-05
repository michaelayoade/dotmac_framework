"""
Pagination utilities for DotMac Framework.
Provides consistent pagination patterns across all modules.
"""


from fastapi import Query
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Schema for pagination parameters."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset from page and size."""
        return (self.page - 1) * self.size


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """FastAPI dependency for pagination parameters."""
    return PaginationParams(page=page, size=size)
