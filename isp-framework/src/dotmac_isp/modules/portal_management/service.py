"""Portal Management service layer for customer portal operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
import hashlib
import secrets
import string

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .repository import (
    PortalAccountRepository,
    PortalSessionRepository,
    PortalLoginAttemptRepository,
    PortalPreferencesRepository,
, timezone)
from .models import PortalAccountStatus, PortalAccountType, SessionStatus
from . import schemas
from dotmac_isp.shared.exceptions import (
    ServiceError,
    NotFoundError,
    ValidationError,
    ConflictError,
)


class PortalManagementService:
    """Service for portal account and session management."""

    def __init__(self, db: Session, tenant_id: str):
        """  Init   operation."""
        self.db = db
        self.tenant_id = UUID(tenant_id)
        self.account_repo = PortalAccountRepository(db, self.tenant_id)
        self.session_repo = PortalSessionRepository(db, self.tenant_id)
        self.login_repo = PortalLoginAttemptRepository(db, self.tenant_id)
        self.prefs_repo = PortalPreferencesRepository(db, self.tenant_id)

    # Account Management
    async def create_portal_account(
        self, account_data: Dict[str, Any]
    ) -> schemas.PortalAccount:
        """Create a new portal account."""
        try:
            # Generate portal ID if not provided
            if "portal_id" not in account_data:
                account_data["portal_id"] = self._generate_portal_id()

            # Hash password if provided
            if "password" in account_data:
                account_data["password_hash"] = self._hash_password(
                    account_data.pop("password")
                )

            # Set default values
            account_data.setdefault("account_status", PortalAccountStatus.ACTIVE)
            account_data.setdefault("account_type", PortalAccountType.CUSTOMER)

            account = self.account_repo.create(account_data)

            # Create default preferences
            await self._create_default_preferences(account.id)

            return schemas.PortalAccount.model_validate(account)

        except ConflictError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create portal account: {str(e)}")

    async def get_portal_account(self, account_id: str) -> schemas.PortalAccount:
        """Get portal account by ID."""
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError(f"Portal account not found: {account_id}")
        return schemas.PortalAccount.model_validate(account)

    async def get_portal_account_by_portal_id(
        self, portal_id: str
    ) -> schemas.PortalAccount:
        """Get portal account by portal ID."""
        account = self.account_repo.get_by_portal_id(portal_id)
        if not account:
            raise NotFoundError(f"Portal account not found: {portal_id}")
        return schemas.PortalAccount.model_validate(account)

    async def list_portal_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        account_type: Optional[PortalAccountType] = None,
        status: Optional[PortalAccountStatus] = None,
        search_term: Optional[str] = None,
    ) -> List[schemas.PortalAccount]:
        """List portal accounts with filtering."""
        try:
            accounts = self.account_repo.list_accounts(
                skip=skip,
                limit=limit,
                account_type=account_type,
                status=status,
                search_term=search_term,
            )
            return [
                schemas.PortalAccount.model_validate(account) for account in accounts
            ]
        except Exception as e:
            raise ServiceError(f"Failed to list portal accounts: {str(e)}")

    async def update_portal_account(
        self, account_id: str, update_data: Dict[str, Any]
    ) -> schemas.PortalAccount:
        """Update portal account."""
        try:
            # Hash new password if provided
            if "password" in update_data:
                update_data["password_hash"] = self._hash_password(
                    update_data.pop("password")
                )

            account = self.account_repo.update(account_id, update_data)
            if not account:
                raise NotFoundError(f"Portal account not found: {account_id}")

            return schemas.PortalAccount.model_validate(account)
        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to update portal account: {str(e)}")

    async def deactivate_portal_account(self, account_id: str) -> bool:
        """Deactivate a portal account."""
        try:
            update_data = {
                "account_status": PortalAccountStatus.SUSPENDED,
                "deactivated_at": datetime.now(timezone.utc),
            }
            account = self.account_repo.update(account_id, update_data)

            if account:
                # End all active sessions
                await self._end_all_sessions(account_id)
                return True
            return False
        except Exception as e:
            raise ServiceError(f"Failed to deactivate portal account: {str(e)}")

    # Authentication & Session Management
    async def authenticate(
        self,
        identifier: str,  # portal_id or email
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[schemas.PortalSession]:
        """Authenticate user and create session."""
        try:
            # Log login attempt
            await self._log_login_attempt(identifier, ip_address, False)

            # Check for too many failed attempts
            if await self._is_account_locked(identifier):
                raise ValidationError(
                    "Account temporarily locked due to failed login attempts"
                )

            # Find account by portal_id or email
            account = self.account_repo.get_by_portal_id(
                identifier
            ) or self.account_repo.get_by_email(identifier)

            if not account:
                raise ValidationError("Invalid credentials")

            # Verify password
            if not self._verify_password(password, account.password_hash):
                raise ValidationError("Invalid credentials")

            # Check account status
            if account.account_status != PortalAccountStatus.ACTIVE:
                raise ValidationError("Account is not active")

            # Create session
            session_data = {
                "account_id": account.id,
                "session_token": self._generate_session_token(),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            }

            session = self.session_repo.create(session_data)

            # Log successful login
            await self._log_login_attempt(identifier, ip_address, True, account.id)

            # Update last login
            await self.account_repo.update(
                account.id, {"last_login_at": datetime.now(timezone.utc)}
            )

            return schemas.PortalSession.model_validate(session)

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Authentication failed: {str(e)}")

    async def validate_session(
        self, session_token: str
    ) -> Optional[schemas.PortalSession]:
        """Validate session token and return session if valid."""
        try:
            session = self.session_repo.get_by_session_token(session_token)

            if not session:
                return None

            # Check if session is expired
            if session.expires_at < datetime.now(timezone.utc):
                await self.session_repo.expire_session(session.id)
                return None

            # Check if session is active
            if session.session_status != SessionStatus.ACTIVE:
                return None

            return schemas.PortalSession.model_validate(session)

        except Exception as e:
            raise ServiceError(f"Session validation failed: {str(e)}")

    async def logout(self, session_token: str) -> bool:
        """End user session."""
        try:
            session = self.session_repo.get_by_session_token(session_token)
            if session:
                return self.session_repo.expire_session(session.id)
            return False
        except Exception as e:
            raise ServiceError(f"Logout failed: {str(e)}")

    async def get_active_sessions(self, account_id: str) -> List[schemas.PortalSession]:
        """Get all active sessions for an account."""
        try:
            sessions = self.session_repo.get_active_sessions(account_id)
            return [
                schemas.PortalSession.model_validate(session) for session in sessions
            ]
        except Exception as e:
            raise ServiceError(f"Failed to get active sessions: {str(e)}")

    # Preferences Management
    async def get_user_preferences(self, account_id: str) -> schemas.PortalPreferences:
        """Get user preferences."""
        try:
            preferences = self.prefs_repo.get_or_create_preferences(account_id)
            return schemas.PortalPreferences.model_validate(preferences)
        except Exception as e:
            raise ServiceError(f"Failed to get user preferences: {str(e)}")

    async def update_user_preferences(
        self, account_id: str, preferences_data: Dict[str, Any]
    ) -> schemas.PortalPreferences:
        """Update user preferences."""
        try:
            preferences = self.prefs_repo.update(account_id, preferences_data)
            return schemas.PortalPreferences.model_validate(preferences)
        except Exception as e:
            raise ServiceError(f"Failed to update user preferences: {str(e)}")

    # Analytics and Reporting
    async def get_account_statistics(self) -> Dict[str, Any]:
        """Get portal account statistics."""
        try:
            stats = self.account_repo.count_by_type()
            recent_accounts = self.account_repo.get_recently_created(30)

            return {
                "total_accounts": sum(stat["count"] for stat in stats),
                "accounts_by_type": stats,
                "new_accounts_last_30_days": len(recent_accounts),
                "recent_accounts": [
                    {
                        "portal_id": acc.portal_id,
                        "account_type": acc.account_type,
                        "created_at": acc.created_at,
                    }
                    for acc in recent_accounts[:10]
                ],
            }
        except Exception as e:
            raise ServiceError(f"Failed to get account statistics: {str(e)}")

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            return self.session_repo.cleanup_expired_sessions()
        except Exception as e:
            raise ServiceError(f"Failed to cleanup expired sessions: {str(e)}")

    # Private Helper Methods
    def _generate_portal_id(self) -> str:
        """Generate a unique portal ID."""
        timestamp = int(datetime.now(timezone.utc).timestamp()
        random_chars = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        return f"PRT-{timestamp}-{random_chars}"

    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode().hexdigest()
        return f"{salt}:{password_hash}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            salt, stored_hash = password_hash.split(":")
            computed_hash = hashlib.sha256((password + salt).encode().hexdigest()
            return computed_hash == stored_hash
        except (ValueError, AttributeError):
            return False

    async def _log_login_attempt(
        self,
        identifier: str,
        ip_address: Optional[str],
        success: bool,
        account_id: Optional[str] = None,
    ):
        """Log login attempt."""
        try:
            attempt_data = {
                "login_identifier": identifier,
                "ip_address": ip_address,
                "success": success,
                "account_id": account_id,
                "attempt_time": datetime.now(timezone.utc),
            }
            self.login_repo.create(attempt_data)
        except Exception:
            # Don't fail authentication if logging fails
            pass

    async def _is_account_locked(self, identifier: str) -> bool:
        """Check if account is locked due to failed attempts."""
        try:
            failed_attempts = self.login_repo.count_failed_attempts(identifier, 15)
            return failed_attempts >= 5
        except Exception:
            return False

    async def _end_all_sessions(self, account_id: str):
        """End all active sessions for an account."""
        try:
            sessions = self.session_repo.get_active_sessions(account_id)
            for session in sessions:
                self.session_repo.expire_session(session.id)
        except Exception:
            pass

    async def _create_default_preferences(self, account_id: str):
        """Create default preferences for new account."""
        try:
            default_data = {
                "account_id": account_id,
                "theme": "light",
                "language": "en",
                "timezone": "UTC",
                "email_notifications": True,
                "sms_notifications": False,
                "marketing_emails": False,
                "security_alerts": True,
            }
            self.prefs_repo.create(default_data)
        except Exception:
            pass
