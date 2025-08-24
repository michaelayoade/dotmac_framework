"""Secure authentication and authorization system."""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Union
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.settings import get_settings

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_secret_key() -> str:
    """Get JWT secret key from secure secrets management."""
    from dotmac_isp.shared.secrets import get_jwt_secret

    return get_jwt_secret()


def get_algorithm() -> str:
    """Get JWT algorithm from settings."""
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_access_token_expire_minutes() -> int:
    """Get access token expiration from settings."""
    return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def get_refresh_token_expire_days() -> int:
    """Get refresh token expiration from settings."""
    return int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=get_access_token_expire_minutes()
        )

    to_encode.update({"exp": expire, "type": "access"})

    return jwt.encode(to_encode, get_secret_key(), algorithm=get_algorithm())


def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=get_refresh_token_expire_days())
    to_encode.update({"exp": expire, "type": "refresh"})

    return jwt.encode(to_encode, get_secret_key(), algorithm=get_algorithm())


def verify_token(token: str, token_type: str = "access") -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[get_algorithm()])

        # Verify token type
        if payload.get("type") != token_type:
            raise JWTError("Invalid token type")

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token, "access")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Import here to avoid circular imports
    from dotmac_isp.modules.identity.models import User

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_tenant(
    current_user: dict = Depends(get_current_user_from_token),
) -> str:
    """Get current user's tenant ID."""
    return current_user.tenant_id


async def get_current_tenant_id(
    current_user: dict = Depends(get_current_user_from_token),
) -> str:
    """Get current user's tenant ID (alias for get_current_tenant)."""
    return current_user.tenant_id


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """Get current authenticated user (alias for get_current_user_from_token)."""
    return await get_current_user_from_token(credentials, db)


def require_permissions(required_permissions: List[str]):
    """Decorator factory to require specific permissions."""

    def decorator(current_user: dict = Depends(get_current_user_from_token)):
        """Decorator operation."""
        user_permissions = current_user.permissions or []

        # Super admin has all permissions
        if "*" in user_permissions:
            return current_user

        # Check if user has all required permissions
        missing_permissions = set(required_permissions) - set(user_permissions)
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}",
            )

        return current_user

    return decorator


def require_role(required_roles: Union[str, List[str]]):
    """Decorator factory to require specific roles."""
    if isinstance(required_roles, str):
        required_roles = [required_roles]

    def decorator(current_user: dict = Depends(get_current_user_from_token)):
        """Decorator operation."""
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(required_roles)}",
            )

        return current_user

    return decorator


class AuthenticationError(HTTPException):
    """Authentication error exception."""

    def __init__(self, detail: str = "Could not validate credentials"):
        """  Init   operation."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Authorization error exception."""

    def __init__(self, detail: str = "Insufficient permissions"):
        """  Init   operation."""
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Get current authenticated customer."""
    from dotmac_isp.modules.identity.models import Customer, AccountStatus
    from dotmac_isp.modules.identity.repository import CustomerRepository

    # Verify token first
    current_user = await get_current_user_from_token(credentials, db)
    
    # Initialize customer repository
    customer_repo = CustomerRepository(db, current_user.tenant_id)
    
    # Try to find customer by user relationship
    # First check if user has customer role or customer-like username
    if current_user.username.startswith("CUST-") or "customer" in str(current_user.username).lower():
        # Try to find customer by customer number from username
        customer = customer_repo.get_by_customer_number(current_user.username)
        if customer:
            return customer
    
    # Try to find customer by email match
    customer = (
        db.query(Customer)
        .filter(
            Customer.email == current_user.email,
            Customer.tenant_id == current_user.tenant_id,
            Customer.is_deleted == False,
        )
        .first()
    )
    
    if customer:
        return customer
    
    # If no customer found but user is authenticated, 
    # this might be a staff user trying to access customer portal
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Customer account required for this portal."
    )


# Optional user dependency (doesn't raise exception if no user)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None

    try:
        return await get_current_user_from_token(credentials, db)
    except HTTPException:
        return None


async def verify_websocket_token(token: str) -> dict:
    """
    Verify WebSocket authentication token.
    
    Args:
        token: JWT token
        
    Returns:
        User information from token
    """
    try:
        payload = verify_token(token, "access")
        
        # Return user information from token payload
        return {
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "exp": payload.get("exp"),
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user (optional authentication) - simplified for API usage.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        User information or None
    """
    if not credentials:
        return None
        
    try:
        token = credentials.credentials
        return await verify_websocket_token(token)
    except:
        return None
