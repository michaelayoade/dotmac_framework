"""Authentication providers for HTTP client."""

import time
from abc import ABC, abstractmethod
from typing import Dict, Optional

import jwt

from dotmac_shared.api.exception_handlers import standard_exception_handler


class AuthProvider(ABC):
    """Base authentication provider."""

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        pass

    @abstractmethod
    def is_valid(self) -> bool:
        """Check if authentication is valid."""
        pass


class BearerTokenAuth(AuthProvider):
    """Bearer token authentication."""

    def __init__(self, token: str):
        self.token = token

    def get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def is_valid(self) -> bool:
        return bool(self.token)


class APIKeyAuth(AuthProvider):
    """API key authentication."""

    def __init__(self, api_key: str, header_name: str = "X-API-Key"):
        self.api_key = api_key
        self.header_name = header_name

    def get_auth_headers(self) -> Dict[str, str]:
        return {self.header_name: self.api_key}

    def is_valid(self) -> bool:
        return bool(self.api_key)


class JWTAuth(AuthProvider):
    """JWT token authentication."""

    def __init__(self, token: str):
        self.token = token
        self._payload: Optional[dict] = None
        self._decode_token()

    def _decode_token(self):
        """Decode JWT token (without verification for expiry check)."""
        try:
            self._payload = jwt.decode(self.token, options={"verify_signature": False})
        except Exception:
            self._payload = None

    def get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def is_valid(self) -> bool:
        if not self.token or not self._payload:
            return False

        # Check expiry
        exp = self._payload.get("exp")
        if exp and exp < time.time():
            return False

        return True
