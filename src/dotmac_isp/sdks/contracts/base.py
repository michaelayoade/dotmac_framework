"""Base contract definitions."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class BaseContract:
    """Base contract for SDK operations."""

    id: Optional[str] = None
    version: str = "1.0"
    metadata: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {"id": self.id, "version": self.version, "metadata": self.metadata or {}}
