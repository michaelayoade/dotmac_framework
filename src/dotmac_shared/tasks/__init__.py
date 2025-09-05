"""
Minimal tasks stubs to satisfy plugin imports in test collection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NotificationChannel:
    name: str


class NotificationChannelProvider:
    def get_channel(self, name: str) -> NotificationChannel:  # noqa: ANN001
        return NotificationChannel(name=name)


__all__ = ["NotificationChannel", "NotificationChannelProvider"]
