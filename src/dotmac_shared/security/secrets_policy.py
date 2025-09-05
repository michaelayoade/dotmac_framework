"""
Minimal secrets policy stubs for test-time imports.

Provides Environment and HardenedSecretsManager used by environment_security_validator.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class Environment(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


class HardenedSecretsManager:
    """Lightweight stub secrets manager used for tests and default envs."""

    def __init__(self, env: Environment | str = Environment.development):
        self.env = Environment(env) if not isinstance(env, Environment) else env

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:  # noqa: ANN001
        return default

    def validate(self) -> dict[str, Any]:
        return {"status": "ok", "env": self.env.value}


__all__ = ["Environment", "HardenedSecretsManager"]

