"""Authentication and authorization service."""

import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.modules.identity import models, schemas
from dotmac_isp.modules.identity.repository import (
    UserRepository,
    AuthTokenRepository,
    LoginAttemptRepository,
)
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
)
from .base_service import BaseIdentityService

logger = logging.getLogger(__name__)


class AuthService(BaseIdentityService):
    """Service for authentication and authorization operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize auth service."""
        super().__init__(db, tenant_id)
        self.user_repo = UserRepository(db, self.tenant_id)
        self.token_repo = AuthTokenRepository(db, self.tenant_id)
        self.login_attempt_repo = LoginAttemptRepository(db, self.tenant_id)

    async def authenticate_user(
        self, username: str, password: str
    ) -> Optional[schemas.UserResponse]:
        """Authenticate user with username/password."""
        try:
            # Get user by username or email
            user = self.user_repo.get_by_username(username)
            if not user:
                user = self.user_repo.get_by_email(username)

            if not user:
                return None

            # Check if account is active
            if not user.is_active:
                raise AuthenticationError("Account is deactivated")

            # Verify password
            if not self._verify_password(password, user.password_hash):
                await self._handle_failed_login(user)
                return None

            # Reset failed login attempts on successful authentication
            await self._reset_failed_attempts(user)

            # Update last login
            await self._update_last_login(user)

            return self._map_user_to_response(user)

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            raise ServiceError(f"Authentication failed: {str(e)}")

    async def login(
        self,
        login_data: schemas.LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> schemas.LoginResponse:
        """Perform user login with JWT token generation."""
        try:
            # Authenticate user
            user_response = await self.authenticate_user(
                login_data.username, login_data.password
            )

            if not user_response:
                await self._log_login_attempt(
                    login_data.username,
                    ip_address,
                    user_agent,
                    False,
                    failure_reason="Invalid credentials",
                )
                raise AuthenticationError("Invalid username or password")

            # Get full user object for token generation
            user = self.user_repo.get_by_id(user_response.id)

            # Generate JWT tokens
            access_token = self._generate_jwt_token(
                user,
                "access",
                expires_in=self.settings.jwt_access_token_expire_minutes * 60,
            )
            refresh_token = self._generate_jwt_token(
                user,
                "refresh",
                expires_in=self.settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
            )

            # Store tokens
            await self._store_tokens(
                user, access_token, refresh_token, ip_address, user_agent
            )

            # Log successful login
            await self._log_login_attempt(
                login_data.username, ip_address, user_agent, True, user_id=user.id
            )

            return schemas.LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=self.settings.jwt_access_token_expire_minutes * 60,
                user=user_response,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Login failed for {login_data.username}: {e}")
            raise ServiceError(f"Login failed: {str(e)}")

    async def refresh_token(self, refresh_token: str) -> schemas.TokenResponse:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = self._decode_jwt_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")

            user_id = UUID(payload.get("user_id"))
            user = self.user_repo.get_by_id(user_id)

            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")

            # Check if token is valid in database
            stored_token = self.token_repo.get_by_refresh_token(refresh_token)
            if not stored_token or stored_token.is_expired():
                raise AuthenticationError("Token is expired or invalid")

            # Generate new access token
            access_token = self._generate_jwt_token(
                user,
                "access",
                expires_in=self.settings.jwt_access_token_expire_minutes * 60,
            )

            # Update stored token
            self.token_repo.update(stored_token.id, {"access_token": access_token})

            return schemas.TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=self.settings.jwt_access_token_expire_minutes * 60,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise ServiceError(f"Token refresh failed: {str(e)}")

    async def logout(self, access_token: str) -> bool:
        """Logout user by invalidating tokens."""
        try:
            # Decode token to get user
            payload = self._decode_jwt_token(access_token)
            user_id = UUID(payload.get("user_id"))

            # Invalidate all tokens for user
            self.token_repo.invalidate_user_tokens(user_id)

            logger.info(f"User logged out: {user_id}")
            return True

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

    async def verify_token(self, access_token: str) -> Optional[schemas.UserResponse]:
        """Verify access token and return user information."""
        try:
            # Decode token
            payload = self._decode_jwt_token(access_token)
            if payload.get("type") != "access":
                return None

            user_id = UUID(payload.get("user_id"))
            user = self.user_repo.get_by_id(user_id)

            if not user or not user.is_active:
                return None

            # Check if token is still valid in database
            stored_token = self.token_repo.get_by_access_token(access_token)
            if not stored_token or stored_token.is_expired():
                return None

            return self._map_user_to_response(user)

        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        """Change user password with current password verification."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User not found: {user_id}")

            # Verify current password
            if not self._verify_password(current_password, user.password_hash):
                raise AuthenticationError("Current password is incorrect")

            # Validate new password
            self._validate_password_strength(new_password)

            # Update password
            new_password_hash = self._hash_password(new_password)
            self.user_repo.update(
                user_id,
                {
                    "password_hash": new_password_hash,
                    "password_changed_at": datetime.utcnow(),
                    "force_password_change": False,
                },
            )

            # Invalidate all existing tokens
            self.token_repo.invalidate_user_tokens(user_id)

            logger.info(f"Password changed for user: {user_id}")
            return True

        except (NotFoundError, AuthenticationError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Password change failed for user {user_id}: {e}")
            raise ServiceError(f"Password change failed: {str(e)}")

    async def request_password_reset(self, email: str) -> str:
        """Request password reset and return reset token."""
        try:
            user = self.user_repo.get_by_email(email)
            if not user:
                # Don't reveal if email exists or not
                logger.info(f"Password reset requested for non-existent email: {email}")
                return "reset_token_placeholder"  # Return fake token

            # Generate reset token
            reset_token = self._generate_jwt_token(
                user, "reset", expires_in=3600
            )  # 1 hour

            # Store reset token
            self.token_repo.create(
                {
                    "user_id": user.id,
                    "token_type": "reset",
                    "access_token": reset_token,
                    "expires_at": datetime.utcnow() + timedelta(hours=1),
                    "tenant_id": self.tenant_id,
                }
            )

            logger.info(f"Password reset requested for user: {user.id}")
            return reset_token

        except Exception as e:
            logger.error(f"Password reset request failed for {email}: {e}")
            raise ServiceError(f"Password reset request failed: {str(e)}")

    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        try:
            # Verify reset token
            payload = self._decode_jwt_token(reset_token)
            if payload.get("type") != "reset":
                raise AuthenticationError("Invalid token type")

            user_id = UUID(payload.get("user_id"))
            user = self.user_repo.get_by_id(user_id)

            if not user:
                raise AuthenticationError("Invalid reset token")

            # Check if token is valid in database
            stored_token = self.token_repo.get_by_access_token(reset_token)
            if not stored_token or stored_token.is_expired():
                raise AuthenticationError("Reset token is expired or invalid")

            # Validate new password
            self._validate_password_strength(new_password)

            # Update password
            new_password_hash = self._hash_password(new_password)
            self.user_repo.update(
                user_id,
                {
                    "password_hash": new_password_hash,
                    "password_changed_at": datetime.utcnow(),
                    "force_password_change": False,
                },
            )

            # Invalidate all tokens for user
            self.token_repo.invalidate_user_tokens(user_id)

            logger.info(f"Password reset for user: {user_id}")
            return True

        except (AuthenticationError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            raise ServiceError(f"Password reset failed: {str(e)}")

    # Private methods
    def _generate_jwt_token(self, user, token_type: str, expires_in: int = None) -> str:
        """Generate JWT token."""
        now = datetime.utcnow()
        exp = (
            now + timedelta(seconds=expires_in)
            if expires_in
            else now + timedelta(hours=24)
        )

        payload = {
            "user_id": str(user.id),
            "username": user.username,
            "type": token_type,
            "iat": now,
            "exp": exp,
            "tenant_id": str(self.tenant_id),
        }

        return jwt.encode(
            payload, self.settings.jwt_secret_key, algorithm=self.settings.jwt_algorithm
        )

    def _decode_jwt_token(self, token: str) -> Dict[str, Any]:
        """Decode and verify JWT token."""
        try:
            return jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    def _hash_password(self, password: str) -> str:
        """Hash password using secure algorithm."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)

    def _validate_password_strength(self, password: str) -> None:
        """Validate password meets strength requirements."""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

    async def _store_tokens(
        self,
        user,
        access_token: str,
        refresh_token: str,
        ip_address: str = None,
        user_agent: str = None,
    ):
        """Store auth tokens in database."""
        self.token_repo.create(
            {
                "user_id": user.id,
                "token_type": "bearer",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_at": datetime.utcnow()
                + timedelta(days=self.settings.jwt_refresh_token_expire_days),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "tenant_id": self.tenant_id,
            }
        )

    async def _log_login_attempt(
        self,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        user_id: UUID = None,
        failure_reason: str = None,
    ):
        """Log login attempt."""
        self.login_attempt_repo.create(
            {
                "username": username,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "success": success,
                "failure_reason": failure_reason,
                "attempted_at": datetime.utcnow(),
                "tenant_id": self.tenant_id,
            }
        )

    async def _handle_failed_login(self, user) -> None:
        """Handle failed login attempt."""
        # Increment failed attempts
        failed_attempts = getattr(user, "failed_login_attempts", 0) + 1

        update_data = {
            "failed_login_attempts": failed_attempts,
            "last_failed_login": datetime.utcnow(),
        }

        # Lock account after 5 failed attempts
        if failed_attempts >= 5:
            update_data["is_active"] = False
            update_data["locked_until"] = datetime.utcnow() + timedelta(hours=1)

        self.user_repo.update(user.id, update_data)

    async def _reset_failed_attempts(self, user) -> None:
        """Reset failed login attempts."""
        self.user_repo.update(
            user.id,
            {
                "failed_login_attempts": 0,
                "last_failed_login": None,
                "locked_until": None,
            },
        )

    async def _update_last_login(self, user) -> None:
        """Update last login timestamp."""
        self.user_repo.update(user.id, {"last_login": datetime.utcnow()})

    def _map_user_to_response(self, user) -> schemas.UserResponse:
        """Map database user to response schema."""
        return schemas.UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=getattr(user, "last_login", None),
        )
