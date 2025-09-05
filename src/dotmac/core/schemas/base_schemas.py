"""
Minimal core schema stubs to satisfy imports.
"""

from __future__ import annotations

from pydantic import BaseModel


class BaseCreateSchema(BaseModel):
    pass


class BaseResponseSchema(BaseModel):
    success: bool = True


__all__ = ["BaseCreateSchema", "BaseResponseSchema"]

