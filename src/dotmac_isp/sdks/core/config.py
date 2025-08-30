"""Core configuration utilities for SDKs."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SDKConfig:
    """Base SDK configuration."""

    base_url: str = "http://localhost:8000"
    timeout: int = 30
    retries: int = 3
    api_key: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "retries": self.retries,
            "api_key": self.api_key,
        }


def get_config() -> SDKConfig:
    """Get default SDK configuration."""
    return SDKConfig()
