"""
Minimal current_user helpers for import.
"""

from __future__ import annotations

from typing import Any


def get_current_tenant(*args: Any, **kwargs: Any) -> str:  # noqa: ANN001
    return "tenant-test"


def get_current_user(*args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: ANN001
    return {"user_id": "user-test", "tenant_id": "tenant-test"}


__all__ = ["get_current_tenant", "get_current_user"]
