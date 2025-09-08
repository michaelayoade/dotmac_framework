"""Base authentication provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..schemas import AuthenticationRequest


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    success: bool
    user_id: Optional[str] = None
    customer_id: Optional[str] = None
    session_data: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    requires_verification: bool = False
    verification_method: Optional[str] = None
    redirect_url: Optional[str] = None


class BaseAuthProvider(ABC):
    """Base class for authentication providers."""

    def __init__(self, db_session, tenant_id: str, config: dict[str, Any]):
        self.db = db_session
        self.tenant_id = tenant_id
        self.config = config

    @abstractmethod
    async def authenticate(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate user with provided credentials."""
        pass

    @abstractmethod
    async def prepare_authentication(self, request: AuthenticationRequest) -> dict[str, Any]:
        """Prepare authentication (e.g., send verification code, generate OAuth URL)."""
        pass

    def validate_request(self, request: AuthenticationRequest) -> bool:
        """Validate authentication request format."""
        return True

    def _create_session_data(self, user_data: dict[str, Any]) -> dict[str, Any]:
        """Create session data from authentication."""
        return {
            **user_data,
            "authenticated_at": datetime.now(timezone.utc).isoformat(),
            "provider": self.__class__.__name__,
        }
