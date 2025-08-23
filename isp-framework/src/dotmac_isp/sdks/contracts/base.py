"""Base contract definitions."""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BaseContract:
    """Base contract for SDK operations."""

    id: Optional[str] = None
    version: str = "1.0"
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"id": self.id, "version": self.version, "metadata": self.metadata or {}}
