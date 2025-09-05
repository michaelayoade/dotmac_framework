"""
Minimal core exceptions to satisfy imports.
Prefer importing from dotmac_shared.core.exceptions when available.
"""

from __future__ import annotations

try:
    from dotmac_shared.core.exceptions import ValidationError as _ValidationError
    from dotmac_shared.core.exceptions import EntityNotFoundError as _EntityNotFoundError
except Exception:  # pragma: no cover
    _ValidationError = None  # type: ignore
    _EntityNotFoundError = None  # type: ignore


class ValidationError(_ValidationError if _ValidationError is not None else Exception):  # type: ignore
    pass


class EntityNotFoundError(_EntityNotFoundError if _EntityNotFoundError is not None else Exception):  # type: ignore
    pass


__all__ = ["ValidationError", "EntityNotFoundError"]

