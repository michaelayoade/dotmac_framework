"""Repository pattern for Portal Account database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func
import hashlib
import secrets

from dotmac_isp.modules.portal_management.models import (
    PortalAccount,
    PortalAccountType,
    PortalAccountStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class PortalAccountRepository:
    """Repository for Portal Account database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, portal_data: Dict[str, Any]) -> PortalAccount:
        """Create a new Portal Account in the database."""
        try:
            portal_account = PortalAccount(
                id=uuid4(), tenant_id=self.tenant_id, **portal_data
            )

            self.db.add(portal_account)
            self.db.commit()
            self.db.refresh(portal_account)
            return portal_account

        except IntegrityError as e:
            self.db.rollback()
            if "portal_id" in str(e):
                raise ConflictError(
                    f"Portal ID {portal_data.get('portal_id')} already exists"
                )
            else:
                raise ConflictError(
                    "Portal Account creation failed due to data conflict"
                )

    def get_by_id(self, account_id: UUID) -> Optional[PortalAccount]:
        """Get Portal Account by ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.id == account_id,
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_portal_id(self, portal_id: str) -> Optional[PortalAccount]:
        """Get Portal Account by Portal ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.portal_id == portal_id,
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_customer_id(self, customer_id: UUID) -> Optional[PortalAccount]:
        """Get Portal Account by Customer ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.customer_id == customer_id,
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def update(
        self, account_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[PortalAccount]:
        """Update Portal Account by ID."""
        account = self.get_by_id(account_id)
        if not account:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(account, key):
                    setattr(account, key, value)

            account.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(account)
            return account

        except IntegrityError as e:
            self.db.rollback()
            if "portal_id" in str(e):
                raise ConflictError(
                    f"Portal ID {update_data.get('portal_id')} already exists"
                )
            else:
                raise ConflictError("Portal Account update failed due to data conflict")

    def update_password(
        self, portal_id: str, password_hash: str, force_change: bool = False
    ) -> bool:
        """Update Portal Account password."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        account.password_hash = password_hash
        account.password_changed_at = datetime.utcnow()
        account.must_change_password = force_change
        account.password_reset_token = None
        account.password_reset_expires = None

        # Clear failed login attempts on password change
        account.failed_login_attempts = 0
        account.locked_until = None

        # Reactivate account if it was locked due to failed attempts
        if account.status == PortalAccountStatus.LOCKED.value:
            account.status = PortalAccountStatus.ACTIVE.value

        account.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def set_password_reset_token(
        self, portal_id: str, token: str, expires_minutes: int = 60
    ) -> bool:
        """Set password reset token for Portal Account."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        account.password_reset_token = token
        account.password_reset_expires = datetime.utcnow() + timedelta(
            minutes=expires_minutes
        )
        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def get_by_reset_token(self, token: str) -> Optional[PortalAccount]:
        """Get Portal Account by password reset token."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.password_reset_token == token,
                    PortalAccount.password_reset_expires > datetime.utcnow(),
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def activate_account(self, portal_id: str) -> bool:
        """Activate a Portal Account."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        if account.status == PortalAccountStatus.ACTIVE.value:
            raise ValidationError("Portal Account is already active")

        account.status = PortalAccountStatus.ACTIVE.value
        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def suspend_account(self, portal_id: str) -> bool:
        """Suspend a Portal Account."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        if account.status == PortalAccountStatus.SUSPENDED.value:
            raise ValidationError("Portal Account is already suspended")

        account.status = PortalAccountStatus.SUSPENDED.value
        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def lock_account(self, portal_id: str, lockout_minutes: int = 30) -> bool:
        """Lock a Portal Account temporarily."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        account.status = PortalAccountStatus.LOCKED.value
        account.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def unlock_account(self, portal_id: str) -> bool:
        """Unlock a Portal Account."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        account.locked_until = None
        account.failed_login_attempts = 0

        # Restore to active if it was just locked
        if account.status == PortalAccountStatus.LOCKED.value:
            account.status = PortalAccountStatus.ACTIVE.value

        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def record_login_attempt(
        self, portal_id: str, success: bool, max_attempts: int = 5
    ) -> bool:
        """Record a login attempt and handle locking logic."""
        account = self.get_by_portal_id(portal_id)
        if not account:
            return False

        if success:
            account.reset_failed_login_attempts()
        else:
            account.increment_failed_login(max_attempts)

        account.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        account_type: Optional[PortalAccountType] = None,
        status: Optional[PortalAccountStatus] = None,
    ) -> List[PortalAccount]:
        """List Portal Accounts with filtering and pagination."""
        query = self.db.query(PortalAccount).filter(
            and_(
                PortalAccount.tenant_id == self.tenant_id,
                PortalAccount.is_deleted == False,
            )
        )

        # Apply filters
        if account_type:
            query = query.filter(PortalAccount.account_type == account_type.value)

        if status:
            query = query.filter(PortalAccount.status == status.value)

        return query.offset(offset).limit(limit).all()

    def count(
        self,
        account_type: Optional[PortalAccountType] = None,
        status: Optional[PortalAccountStatus] = None,
    ) -> int:
        """Count Portal Accounts with filters."""
        query = self.db.query(func.count(PortalAccount.id)).filter(
            and_(
                PortalAccount.tenant_id == self.tenant_id,
                PortalAccount.is_deleted == False,
            )
        )

        # Apply same filters as list method
        if account_type:
            query = query.filter(PortalAccount.account_type == account_type.value)

        if status:
            query = query.filter(PortalAccount.status == status.value)

        return query.scalar()

    def soft_delete(self, account_id: UUID) -> bool:
        """Soft delete Portal Account."""
        account = self.get_by_id(account_id)
        if not account:
            return False

        account.is_deleted = True
        account.deleted_at = datetime.utcnow()
        account.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password for storage."""
        # Use a proper password hashing library in production (e.g., bcrypt, scrypt, argon2)
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return f"{salt}${password_hash.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_hash = password_hash.split("$")
            password_hash_computed = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            )
            return stored_hash == password_hash_computed.hex()
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def generate_reset_token() -> str:
        """Generate a secure password reset token."""
        return secrets.token_urlsafe(32)
