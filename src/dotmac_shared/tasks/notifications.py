from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NotificationChannel:
    name: str


class NotificationChannelProvider:
    def get_channel(self, name: str) -> NotificationChannel:  # noqa: ANN001
        return NotificationChannel(name)


__all__ = ["NotificationChannel", "NotificationChannelProvider"]
