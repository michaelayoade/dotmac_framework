"""Core configuration utilities for SDKs."""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SDKConfig:
    """Base SDK configuration."""

    base_url: str = os.getenv("DOTMAC_API_BASE_URL", "https://api.dotmac.local")
    timeout: int = int(os.getenv("DOTMAC_API_TIMEOUT", "30"))
    retries: int = int(os.getenv("DOTMAC_API_RETRIES", "3"))
    api_key: Optional[str] = os.getenv("DOTMAC_API_KEY")

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
