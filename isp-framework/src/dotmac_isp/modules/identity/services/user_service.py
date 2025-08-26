"""User management service."""

import logging
import secrets
import string
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from dotmac_isp.modules.identity import models, schemas
from dotmac_isp.modules.identity.repository import UserRepository, RoleRepository
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)
from .base_service import BaseIdentityService

logger = logging.getLogger(__name__)


class UserService(BaseIdentityService):
    """Service for user management operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize user service."""
        super().__init__(db, tenant_id)
        self.user_repo = UserRepository(db, self.tenant_id)
        self.role_repo = RoleRepository(db, self.tenant_id)

    async def create_user(self, user_data: schemas.UserCreate) -> schemas.UserResponse:
        """Create a new user account."""
        try:
            # Validate user data
            await self._validate_user_creation(user_data)

            # Hash password
            password_hash = self._hash_password(user_data.password)

            # Prepare user data for repository
            repo_data = {
                "username": user_data.username,
                "email": user_data.email,
                "password_hash": password_hash,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "is_active": True,
                "is_verified": False,
                "created_at": datetime.now(timezone.utc),
            }

            # Create user
            db_user = self.user_repo.create(repo_data)

            # Assign default roles if specified
            if hasattr(user_data, "roles") and user_data.roles:
                await self._assign_user_roles(db_user.id, user_data.roles)

            logger.info(f"Created user: {db_user.id}")
            return self._map_user_to_response(db_user)

        except (ValidationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise ServiceError(f"User creation failed: {str(e)}")

    async def get_user(self, user_id: UUID) -> schemas.UserResponse:
        """Get user by ID."""
        try:
            db_user = self.user_repo.get_by_id(user_id)
            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            return self._map_user_to_response(db_user)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise ServiceError(f"Failed to retrieve user: {str(e)}")

    async def get_user_by_username(
        self, username: str
    ) -> Optional[schemas.UserResponse]:
        """Get user by username."""
        try:
            db_user = self.user_repo.get_by_username(username)
            if not db_user:
                return None

            return self._map_user_to_response(db_user)

        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise ServiceError(f"Failed to retrieve user: {str(e)}")

    async def get_user_by_email(self, email: str) -> Optional[schemas.UserResponse]:
        """Get user by email."""
        try:
            db_user = self.user_repo.get_by_email(email)
            if not db_user:
                return None

            return self._map_user_to_response(db_user)

        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise ServiceError(f"Failed to retrieve user: {str(e)}")

    async def update_user(
        self, user_id: UUID, update_data: schemas.UserUpdate
    ) -> schemas.UserResponse:
        """Update user information."""
        try:
            # Validate user exists
            existing_user = self.user_repo.get_by_id(user_id)
            if not existing_user:
                raise NotFoundError(f"User not found: {user_id}")

            # Validate update data
            await self._validate_user_update(user_id, update_data)

            # Prepare update data
            update_dict = update_data.model_dump(exclude_unset=True)

            # Hash new password if provided
            if "password" in update_dict:
                update_dict["password_hash"] = self._hash_password(
                    update_dict.pop("password")
                )

            # Update user
            if update_dict:
                db_user = self.user_repo.update(user_id, update_dict)
                logger.info(f"Updated user: {user_id}")
                return self._map_user_to_response(db_user)
            else:
                return self._map_user_to_response(existing_user)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise ServiceError(f"User update failed: {str(e)}")

    async def deactivate_user(self, user_id: UUID) -> schemas.UserResponse:
        """Deactivate user account."""
        try:
            db_user = self.user_repo.update(user_id, {"is_active": False})
            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            logger.info(f"Deactivated user: {user_id}")
            return self._map_user_to_response(db_user)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to deactivate user {user_id}: {e}")
            raise ServiceError(f"User deactivation failed: {str(e)}")

    async def activate_user(self, user_id: UUID) -> schemas.UserResponse:
        """Activate user account."""
        try:
            db_user = self.user_repo.update(user_id, {"is_active": True})
            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            logger.info(f"Activated user: {user_id}")
            return self._map_user_to_response(db_user)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to activate user {user_id}: {e}")
            raise ServiceError(f"User activation failed: {str(e)}")

    async def verify_user(self, user_id: UUID) -> schemas.UserResponse:
        """Verify user account."""
        try:
            db_user = self.user_repo.update(
                user_id, {"is_verified": True, "verified_at": datetime.now(timezone.utc)}
            )
            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            logger.info(f"Verified user: {user_id}")
            return self._map_user_to_response(db_user)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to verify user {user_id}: {e}")
            raise ServiceError(f"User verification failed: {str(e)}")

    async def change_password(
        self, user_id: UUID, old_password: str, new_password: str
    ) -> bool:
        """Change user password with validation."""
        try:
            # Get user
            db_user = self.user_repo.get_by_id(user_id)
            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            # Verify old password
            if not self._verify_password(old_password, db_user.password_hash):
                raise ValidationError("Current password is incorrect")

            # Validate new password
            self._validate_password_strength(new_password)

            # Update password
            new_password_hash = self._hash_password(new_password)
            self.user_repo.update(
                user_id,
                {
                    "password_hash": new_password_hash,
                    "password_changed_at": datetime.now(timezone.utc),
                },
            )

            logger.info(f"Changed password for user: {user_id}")
            return True

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise ServiceError(f"Password change failed: {str(e)}")

    async def reset_password(self, user_id: UUID) -> str:
        """Reset user password and return new temporary password."""
        try:
            # Generate temporary password
            temp_password = self._generate_secure_password()
            temp_password_hash = self._hash_password(temp_password)

            # Update user
            db_user = self.user_repo.update(
                user_id,
                {
                    "password_hash": temp_password_hash,
                    "password_changed_at": datetime.now(timezone.utc),
                    "force_password_change": True,
                },
            )

            if not db_user:
                raise NotFoundError(f"User not found: {user_id}")

            logger.info(f"Reset password for user: {user_id}")
            return temp_password

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to reset password for user {user_id}: {e}")
            raise ServiceError(f"Password reset failed: {str(e)}")

    # Role management methods
    async def assign_user_roles(self, user_id: UUID, role_names: List[str]) -> None:
        """Assign roles to user."""
        try:
            await self._assign_user_roles(user_id, role_names)
            logger.info(f"Assigned roles {role_names} to user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to assign roles to user {user_id}: {e}")
            raise ServiceError(f"Role assignment failed: {str(e)}")

    async def remove_user_roles(self, user_id: UUID, role_names: List[str]) -> None:
        """Remove roles from user."""
        try:
            for role_name in role_names:
                role = self.role_repo.get_by_name(role_name)
                if role:
                    self.user_repo.remove_role(user_id, role.id)

            logger.info(f"Removed roles {role_names} from user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to remove roles from user {user_id}: {e}")
            raise ServiceError(f"Role removal failed: {str(e)}")

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        """Get user roles."""
        try:
            roles = self.user_repo.get_user_roles(user_id)
            return [role.name for role in roles]
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id}: {e}")
            raise ServiceError(f"Failed to get user roles: {str(e)}")

    # Private methods
    async def _validate_user_creation(self, user_data: schemas.UserCreate) -> None:
        """Validate user creation data."""
        # Check for duplicate username
        if self.user_repo.get_by_username(user_data.username):
            raise ConflictError(f"Username already exists: {user_data.username}")

        # Check for duplicate email
        if self.user_repo.get_by_email(user_data.email):
            raise ConflictError(f"Email already exists: {user_data.email}")

        # Validate password strength
        self._validate_password_strength(user_data.password)

    async def _validate_user_update(
        self, user_id: UUID, update_data: schemas.UserUpdate
    ) -> None:
        """Validate user update data."""
        if hasattr(update_data, "username") and update_data.username:
            existing = self.user_repo.get_by_username(update_data.username)
            if existing and existing.id != user_id:
                raise ConflictError(f"Username already exists: {update_data.username}")

        if hasattr(update_data, "email") and update_data.email:
            existing = self.user_repo.get_by_email(update_data.email)
            if existing and existing.id != user_id:
                raise ConflictError(f"Email already exists: {update_data.email}")

    def _validate_password_strength(self, password: str) -> None:
        """Validate password meets strength requirements."""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")

        # Add more password strength validation as needed

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

    def _generate_secure_password(self) -> str:
        """Generate a secure random password."""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(characters) for _ in range(12))

    async def _assign_user_roles(self, user_id: UUID, role_names: List[str]) -> None:
        """Assign roles to user by name."""
        for role_name in role_names:
            role = self.role_repo.get_by_name(role_name)
            if role:
                self.user_repo.add_role(user_id, role.id)

    def _map_user_to_response(self, db_user) -> schemas.UserResponse:
        """Map database user to response schema."""
        return schemas.UserResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            first_name=db_user.first_name,
            last_name=db_user.last_name,
            is_active=db_user.is_active,
            is_verified=db_user.is_verified,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at,
            last_login=getattr(db_user, "last_login", None),
        )
