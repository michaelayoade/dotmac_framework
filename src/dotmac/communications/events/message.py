"""
Minimal event message type for tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    topic: str
    payload: dict[str, Any]
    key: str | None = None


__all__ = ["Event"]
