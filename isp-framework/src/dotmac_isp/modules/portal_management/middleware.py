"""Portal Management Middleware - Authentication and security middleware."""

from typing import Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from dotmac_isp.core.database import get_db
from dotmac_isp.core.settings import get_settings
from .models import PortalAccount, PortalSession
from .schemas import PortalAccountResponse


security = HTTPBearer(auto_error=False)
settings = get_settings()


class PortalAuthenticationError(HTTPException):
    """Portal authentication error."""

    def __init__(self, detail: str = "Authentication failed"):
        """  Init   operation."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PortalAuthorizationError(HTTPException):
    """Portal authorization error."""

    def __init__(self, detail: str = "Insufficient privileges"):
        """  Init   operation."""
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def verify_portal_token(token: str) -> Tuple[UUID, UUID, str]:
    """
    Verify Portal JWT token and extract claims.

    Returns:
        Tuple of (account_id, tenant_id, session_id)
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        account_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        session_id = payload.get("session_id")
        token_type = payload.get("type")

        if not account_id or not tenant_id or not session_id:
            raise PortalAuthenticationError("Invalid token claims")

        if token_type != "access":
            raise PortalAuthenticationError("Invalid token type")

        return UUID(account_id), UUID(tenant_id), UUID(session_id)

    except (JWTError, ValueError) as e:
        raise PortalAuthenticationError("Invalid token")


async def get_current_portal_account(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> PortalAccount:
    """
    Get current authenticated portal account from JWT token.
    """
    if not credentials:
        raise PortalAuthenticationError("Missing authentication token")

    account_id, tenant_id, session_id = verify_portal_token(credentials.credentials)

    # Verify session is still active
    session = (
        db.query(PortalSession)
        .filter(
            PortalSession.id == session_id,
            PortalSession.tenant_id == tenant_id,
            PortalSession.is_active == True,
        )
        .first()
    )

    if not session or not session.is_valid:
        raise PortalAuthenticationError("Session expired or invalid")

    # Get portal account
    account = (
        db.query(PortalAccount)
        .filter(
            PortalAccount.id == account_id,
            PortalAccount.tenant_id == tenant_id,
            PortalAccount.is_deleted == False,
        )
        .first()
    )

    if not account:
        raise PortalAuthenticationError("Portal account not found")

    if not account.is_active:
        raise PortalAuthenticationError("Portal account is not active")

    # Update session activity
    from datetime import datetime

    session.last_activity = datetime.utcnow()
    db.commit()

    return account


async def get_current_portal_account_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[PortalAccount]:
    """
    Get current portal account if authenticated, otherwise return None.
    """
    if not credentials:
        return None

    try:
        return await get_current_portal_account(credentials, db)
    except PortalAuthenticationError:
        return None


async def get_current_tenant_from_token(
    account: PortalAccount = Depends(get_current_portal_account),
) -> UUID:
    """
    Get current tenant ID from authenticated portal account.
    """
    return account.tenant_id


def require_portal_account_type(*allowed_types: str):
    """
    Dependency factory to require specific portal account types.

    Args:
        allowed_types: Account types that are allowed (e.g., "customer", "technician", "reseller")
    """

    async def _require_account_type(
        """ Require Account Type operation."""
        account: PortalAccount = Depends(get_current_portal_account),
    ) -> PortalAccount:
        if account.account_type not in allowed_types:
            raise PortalAuthorizationError(
                f"Account type '{account.account_type}' is not authorized for this operation"
            )
        return account

    return _require_account_type


def require_customer_portal():
    """Require customer portal account."""
    return require_portal_account_type("customer")


def require_technician_portal():
    """Require technician portal account."""
    return require_portal_account_type("technician")


def require_reseller_portal():
    """Require reseller portal account."""
    return require_portal_account_type("reseller")


def require_staff_portal():
    """Require staff portal account (technician or reseller)."""
    return require_portal_account_type("technician", "reseller")


async def verify_portal_account_ownership(
    account_id: UUID,
    current_account: PortalAccount = Depends(get_current_portal_account),
) -> PortalAccount:
    """
    Verify that the current account matches the requested account ID,
    or has sufficient privileges to access other accounts.
    """
    # Users can access their own account
    if current_account.id == account_id:
        return current_account

    # Staff accounts can access customer accounts in the same tenant
    if current_account.account_type in ["technician", "reseller"]:
        return current_account

    raise PortalAuthorizationError("Access denied to requested account")


async def get_portal_session_info(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[PortalSession]:
    """
    Get current portal session information.
    """
    if not credentials:
        return None

    try:
        account_id, tenant_id, session_id = verify_portal_token(credentials.credentials)

        session = (
            db.query(PortalSession)
            .filter(
                PortalSession.id == session_id,
                PortalSession.tenant_id == tenant_id,
                PortalSession.is_active == True,
            )
            .first()
        )

        return session if session and session.is_valid else None

    except (PortalAuthenticationError, JWTError):
        return None


class PortalRateLimitError(HTTPException):
    """Portal rate limit error."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        """  Init   operation."""
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "60"},
        )


def check_portal_rate_limit(
    account: PortalAccount = Depends(get_current_portal_account),
    db: Session = Depends(get_db),
) -> PortalAccount:
    """
    Check rate limits for portal account.

    This is a placeholder implementation. In production, you would use
    Redis or similar to track rate limits per account.
    """
    from datetime import datetime, timedelta
    from .models import PortalLoginAttempt

    # Example: Check for excessive login attempts in the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    recent_attempts = (
        db.query(PortalLoginAttempt)
        .filter(
            PortalLoginAttempt.portal_account_id == account.id,
            PortalLoginAttempt.created_at > one_hour_ago,
        )
        .count()
    )

    if recent_attempts > 100:  # Configurable limit
        raise PortalRateLimitError("Too many requests in the last hour")

    return account


def validate_tenant_access(
    tenant_id: UUID, account: PortalAccount = Depends(get_current_portal_account)
) -> UUID:
    """
    Validate that the account has access to the specified tenant.
    """
    if account.tenant_id != tenant_id:
        raise PortalAuthorizationError("Access denied to specified tenant")

    return tenant_id


async def extract_request_metadata(request) -> dict:
    """
    Extract metadata from the request for security logging.
    """
    return {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("User-Agent"),
        "method": request.method,
        "url": str(request.url),
        "timestamp": datetime.utcnow().isoformat(),
    }
