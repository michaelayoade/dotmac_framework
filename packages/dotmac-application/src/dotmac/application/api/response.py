"""
Standard API response envelope for DotMac applications.

Provides a generic Pydantic model that wraps endpoint responses in a consistent
structure with success flag, message, data payload and optional error code.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Generic API response envelope.

    Example usage:
        @router.get("/items", response_model=APIResponse[list[ItemSchema]])
        async def list_items(...):
            return APIResponse(success=True, data=[...])
    """

    success: bool = Field(True, description="Whether the request was successful")
    message: str = Field("", description="Optional human-readable message")
    data: T | None = Field(None, description="Response payload")
    error_code: str | None = Field(
        None, description="Optional machine-readable error code"
    )

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

