"""
Minimal database helpers for test collection.
"""

from __future__ import annotations

from typing import Any


def get_db_session(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN001
    class _DummySession:
        async def execute(self, *a, **k):  # noqa: ANN001
            return None

        async def commit(self):
            return None

        async def rollback(self):
            return None

    return _DummySession()


__all__ = ["get_db_session"]
