"""
Lightweight application shims for tests.
Provides minimal RouterFactory and standard_exception_handler for import-time availability.
"""

from __future__ import annotations

from typing import Any, Callable

try:
    from fastapi import APIRouter
except Exception:  # pragma: no cover
    APIRouter = object  # type: ignore


def standard_exception_handler(func: Callable | None = None, *dargs: Any, **dkwargs: Any):  # type: ignore
    def _decorate(f: Callable):  # noqa: ANN001
        return f

    return _decorate if func is None else func


class RouterFactory:
    def __init__(self, name: str):  # noqa: D401
        self.name = name

    def create_router(
        self, prefix: str = "", tags: list[str] | None = None, **_: Any
    ):  # noqa: D401
        try:
            return APIRouter(prefix=prefix, tags=tags or [])  # type: ignore[misc]
        except Exception:
            return object()


__all__ = ["RouterFactory", "standard_exception_handler"]
