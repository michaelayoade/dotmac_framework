"""Portal Account service layer for authentication and account management."""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from dotmac_isp.core.settings import get_settings
from dotmac_isp.modules.identity.portal_repository import PortalAccountRepository
from dotmac_isp.modules.portal_management.models import (
    PortalAccount,
    PortalAccountType,
    PortalAccountStatus,
)
from dotmac_isp.modules.identity.portal_id_generator import get_portal_id_generator
from dotmac_isp.shared.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError,
    ServiceError,
)


class PortalAccountService:
    """Service layer for Portal Account management operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize Portal Account service with database session."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.portal_repo = PortalAccountRepository(db, self.tenant_id)

    async def create_portal_account(
        self,
        portal_id: str,
        password: str,
        account_type: PortalAccountType = PortalAccountType.CUSTOMER,
        customer_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        force_password_change: bool = True,
    ) -> PortalAccount:
        """
        Create a new Portal Account.

        Args:
            portal_id: Portal identifier
            password: Plain text password (will be hashed)
            account_type: Type of account (customer, admin, etc.)
            customer_id: Associated customer ID (if any)
            user_id: Associated user ID (if any)
            force_password_change: Whether to force password change on first login

        Returns:
            Created Portal Account

        Raises:
            ConflictError: Portal ID already exists
            ValidationError: Invalid data
            ServiceError: Service operation failed
        """
        try:
            # Validate inputs
            self._validate_portal_account_creation(portal_id, password, account_type)

            # Hash the password
            password_hash = PortalAccountRepository.hash_password(password)

            # Prepare account data
            account_data = {
                "portal_id": portal_id,
                "password_hash": password_hash,
                "account_type": account_type.value,
                "status": PortalAccountStatus.PENDING_ACTIVATION.value,
                "must_change_password": force_password_change,
                "customer_id": str(customer_id) if customer_id else None,
                "user_id": str(user_id) if user_id else None,
            }

            # Create the account
            portal_account = self.portal_repo.create(account_data)

            return portal_account

        except (ConflictError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create Portal Account: {str(e)}")

    async def authenticate_portal_user(
        self, portal_id: str, password: str
    ) -> Optional[PortalAccount]:
        """
        Authenticate a Portal user.

        Args:
            portal_id: Portal identifier
            password: Plain text password

        Returns:
            Portal Account if authentication successful, None otherwise
        """
        try:
            # Get the account
            account = self.portal_repo.get_by_portal_id(portal_id)
            if not account:
                return None

            # Check if account can login
            if not account.can_login:
                # Record failed attempt for security logging
                self.portal_repo.record_login_attempt(portal_id, success=False)
                return None

            # Verify password
            if not PortalAccountRepository.verify_password(
                password, account.password_hash
            ):
                # Record failed login attempt
                self.portal_repo.record_login_attempt(portal_id, success=False)
                return None

            # Record successful login
            self.portal_repo.record_login_attempt(portal_id, success=True)

            return account

        except Exception as e:
            raise ServiceError(f"Authentication failed: {str(e)}")

    async def change_portal_password(
        self, portal_id: str, current_password: str, new_password: str
    ) -> bool:
        """
        Change Portal Account password (user-initiated).

        Args:
            portal_id: Portal identifier
            current_password: Current password for verification
            new_password: New password

        Returns:
            True if password changed successfully

        Raises:
            NotFoundError: Portal Account not found
            ValidationError: Current password incorrect or new password invalid
        """
        try:
            # Get the account
            account = self.portal_repo.get_by_portal_id(portal_id)
            if not account:
                raise NotFoundError(f"Portal Account {portal_id} not found")

            # Verify current password
            if not PortalAccountRepository.verify_password(
                current_password, account.password_hash
            ):
                raise ValidationError("Current password is incorrect")

            # Validate new password
            self._validate_password(new_password)

            # Hash new password
            new_password_hash = PortalAccountRepository.hash_password(new_password)

            # Update password
            success = self.portal_repo.update_password(
                portal_id, new_password_hash, force_change=False
            )

            if not success:
                raise ServiceError("Failed to update password")

            return True

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to change password: {str(e)}")

    async def reset_portal_password(
        self, portal_id: str, new_password: str, force_change: bool = True
    ) -> bool:
        """
        Reset Portal Account password (admin-initiated).

        Args:
            portal_id: Portal identifier
            new_password: New password
            force_change: Whether to force password change on next login

        Returns:
            True if password reset successfully
        """
        try:
            # Get the account
            account = self.portal_repo.get_by_portal_id(portal_id)
            if not account:
                raise NotFoundError(f"Portal Account {portal_id} not found")

            # Validate new password
            self._validate_password(new_password)

            # Hash new password
            new_password_hash = PortalAccountRepository.hash_password(new_password)

            # Update password
            success = self.portal_repo.update_password(
                portal_id, new_password_hash, force_change=force_change
            )

            if not success:
                raise ServiceError("Failed to reset password")

            return True

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to reset password: {str(e)}")

    async def initiate_password_reset(self, portal_id: str) -> str:
        """
        Initiate password reset process.

        Args:
            portal_id: Portal identifier

        Returns:
            Password reset token

        Raises:
            NotFoundError: Portal Account not found
        """
        try:
            # Get the account
            account = self.portal_repo.get_by_portal_id(portal_id)
            if not account:
                raise NotFoundError(f"Portal Account {portal_id} not found")

            # Generate reset token
            reset_token = PortalAccountRepository.generate_reset_token()

            # Set reset token with 60 minute expiry
            success = self.portal_repo.set_password_reset_token(
                portal_id, reset_token, 60
            )

            if not success:
                raise ServiceError("Failed to set password reset token")

            return reset_token

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to initiate password reset: {str(e)}")

    async def complete_password_reset(
        self, reset_token: str, new_password: str
    ) -> bool:
        """
        Complete password reset using token.

        Args:
            reset_token: Password reset token
            new_password: New password

        Returns:
            True if password reset successfully
        """
        try:
            # Get account by reset token
            account = self.portal_repo.get_by_reset_token(reset_token)
            if not account:
                raise ValidationError("Invalid or expired reset token")

            # Validate new password
            self._validate_password(new_password)

            # Hash new password
            new_password_hash = PortalAccountRepository.hash_password(new_password)

            # Update password (clear reset token)
            success = self.portal_repo.update_password(
                account.portal_id, new_password_hash, force_change=False
            )

            if not success:
                raise ServiceError("Failed to complete password reset")

            return True

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to complete password reset: {str(e)}")

    async def activate_portal_account(self, portal_id: str) -> bool:
        """Activate a Portal Account."""
        try:
            success = self.portal_repo.activate_account(portal_id)
            if not success:
                raise NotFoundError(f"Portal Account {portal_id} not found")
            return True
        except Exception as e:
            raise ServiceError(f"Failed to activate account: {str(e)}")

    async def suspend_portal_account(self, portal_id: str) -> bool:
        """Suspend a Portal Account."""
        try:
            success = self.portal_repo.suspend_account(portal_id)
            if not success:
                raise NotFoundError(f"Portal Account {portal_id} not found")
            return True
        except Exception as e:
            raise ServiceError(f"Failed to suspend account: {str(e)}")

    async def unlock_portal_account(self, portal_id: str) -> bool:
        """Unlock a Portal Account."""
        try:
            success = self.portal_repo.unlock_account(portal_id)
            if not success:
                raise NotFoundError(f"Portal Account {portal_id} not found")
            return True
        except Exception as e:
            raise ServiceError(f"Failed to unlock account: {str(e)}")

    def _validate_portal_account_creation(
        self, portal_id: str, password: str, account_type: PortalAccountType
    ) -> None:
        """Validate Portal Account creation data."""
        # Validate Portal ID
        if not portal_id or len(portal_id.strip()) < 4:
            raise ValidationError("Portal ID must be at least 4 characters")

        if len(portal_id) > 20:
            raise ValidationError("Portal ID must not exceed 20 characters")

        # Validate password
        self._validate_password(password)

        # Validate account type
        if not isinstance(account_type, PortalAccountType):
            raise ValidationError(f"Invalid account type: {account_type}")

    def _validate_password(self, password: str) -> None:
        """Validate password strength."""
        if not password or len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        if len(password) > 128:
            raise ValidationError("Password must not exceed 128 characters")

        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain at least one digit")

        # Check for at least one letter
        if not any(c.isalpha() for c in password):
            raise ValidationError("Password must contain at least one letter")

    def get_portal_account_by_id(self, portal_id: str) -> Optional[PortalAccount]:
        """Get Portal Account by Portal ID."""
        return self.portal_repo.get_by_portal_id(portal_id)

    def get_portal_account_status(self, portal_id: str) -> Dict[str, Any]:
        """Get Portal Account status and security info."""
        account = self.portal_repo.get_by_portal_id(portal_id)
        if not account:
            raise NotFoundError(f"Portal Account {portal_id} not found")

        return {
            "portal_id": account.portal_id,
            "account_type": account.account_type,
            "status": account.status,
            "is_active": account.is_active,
            "is_locked": account.is_locked,
            "can_login": account.can_login,
            "needs_password_change": account.needs_password_change,
            "failed_login_attempts": account.failed_login_attempts,
            "last_successful_login": account.last_successful_login,
            "locked_until": account.locked_until,
            "password_changed_at": account.password_changed_at,
            "two_factor_enabled": account.two_factor_enabled,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }
