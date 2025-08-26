"""Authentication and authorization services."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import bcrypt
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from dotmac_isp.core.exceptions import (
    AuthenticationError, AuthorizationError, SecurityViolationError
)
from datetime import timezone


class AuthenticationService:
    """Authentication service for handling user authentication."""
    
    def __init__(self, db_session: AsyncSession, secret_key: str = "default_secret"):
        """  Init   operation."""
        self.db_session = db_session
        self.secret_key = secret_key
        self.algorithm = "HS256"
        self.token_expire_hours = 24
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_access_token(self, user_id: str, permissions: List[str] = None) -> str:
        """Create JWT access token."""
        expires = datetime.now(timezone.utc) + timedelta(hours=self.token_expire_hours)
        payload = {
            "sub": user_id,
            "exp": expires,
            "iat": datetime.now(timezone.utc),
            "permissions": permissions or []
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user credentials."""
        # This would typically query the user from database
        # For now, returning mock data
        if username and password:
            return {
                "user_id": "test_user_id",
                "username": username,
                "permissions": ["read", "write"]
            }
        raise AuthenticationError("Invalid credentials")


class AuthorizationService:
    """Authorization service for handling user permissions."""
    
    def __init__(self, db_session: AsyncSession):
        """  Init   operation."""
        self.db_session = db_session
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions
    
    def check_resource_access(self, user_id: str, resource_id: str, action: str) -> bool:
        """Check if user can access specific resource."""
        # This would typically check database for resource ownership/permissions
        return True
    
    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from database."""
        # This would typically query user roles and permissions
        return ["read", "write", "admin"]


class SecurityManager:
    """Central security manager coordinating all security services."""
    
    def __init__(self, db_session: AsyncSession):
        """  Init   operation."""
        self.db_session = db_session
        self.auth_service = AuthenticationService(db_session)
        self.authz_service = AuthorizationService(db_session)
        self._rate_limiter = None
        self._input_sanitizer = None
        self._audit_logger = None
    
    @property
    def rate_limiter(self):
        """Get rate limiter instance."""
        if not self._rate_limiter:
            from .rate_limiting import RateLimiter
            self._rate_limiter = RateLimiter()
        return self._rate_limiter
    
    @property
    def input_sanitizer(self):
        """Get input sanitizer instance.""" 
        if not self._input_sanitizer:
            from .input_sanitizer import InputSanitizer
            self._input_sanitizer = InputSanitizer()
        return self._input_sanitizer
    
    @property
    def audit_logger(self):
        """Get audit logger instance."""
        if not self._audit_logger:
            from .audit import AuditLogger
            self._audit_logger = AuditLogger()
        return self._audit_logger
    
    async def authenticate_and_authorize(self, token: str, required_permission: str) -> Dict[str, Any]:
        """Authenticate token and check authorization."""
        # Verify token
        payload = self.auth_service.verify_token(token)
        user_id = payload.get("sub")
        permissions = payload.get("permissions", [])
        
        # Check permission
        if not self.authz_service.check_permission(permissions, required_permission):
            raise AuthorizationError(f"Insufficient permissions for {required_permission}")
        
        return payload