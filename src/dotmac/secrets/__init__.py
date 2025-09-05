"""
Minimal secrets API for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Secret:
    key: str
    value: str


class Secrets:
    def __init__(self):
        self._store: dict[str, str] = {}

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:  # noqa: ANN001
        return self._store.get(key, default)

    def set(self, key: str, value: str) -> None:  # noqa: ANN001
        self._store[key] = value


def load_secrets() -> Secrets:
    return Secrets()


__all__ = ["Secret", "Secrets", "load_secrets"]

