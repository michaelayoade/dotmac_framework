"""Portal Management Services - Business logic for Portal ID system."""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from passlib.context import CryptContext
from jose import JWTError, jwt
import pyotp

# import qrcode  # Commented out for development
import io
import base64

from dotmac_isp.core.settings import get_settings
from .models import (
    PortalAccount,
    PortalSession,
    PortalLoginAttempt,
    PortalAccountStatus,
)
from .schemas import (
    PortalAccountCreate,
    PortalAccountUpdate,
    PortalLoginRequest,
    PortalLoginResponse,
    PortalPasswordChangeRequest,
    PortalPasswordResetRequest,
    Portal2FASetupResponse,
)


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PortalPasswordGenerator:
    """Service for generating secure passwords for Portal accounts."""

    @staticmethod
    def generate_portal_password() -> str:
        """Generate a secure, memorable password for Portal accounts.

        Format: WordWordNumber! (e.g., "BlueSky47!")
        This is more user-friendly while maintaining security.
        """
        import secrets
        import random

        # Common words for password generation (avoiding offensive terms)
        words = [
            "Blue",
            "Green",
            "Red",
            "Gold",
            "Silver",
            "Bright",
            "Clear",
            "Fresh",
            "Quick",
            "Swift",
            "Strong",
            "Smart",
            "Cool",
            "Warm",
            "Light",
            "Dark",
            "Sky",
            "Star",
            "Moon",
            "Sun",
            "Wave",
            "Wind",
            "Fire",
            "Rain",
            "Oak",
            "Pine",
            "Rose",
            "Lily",
            "Tiger",
            "Eagle",
            "Wolf",
            "Bear",
            "River",
            "Ocean",
            "Lake",
            "Hill",
            "Rock",
            "Peak",
            "Valley",
            "Field",
        ]

        # Select two random words
        word1 = secrets.choice(words)
        word2 = secrets.choice(
            [w for w in words if w != word1]
        )  # Ensure different words

        # Generate 2-digit number
        number = secrets.randbelow(90) + 10  # 10-99

        # Add special character
        special_chars = "!@#$%"
        special = secrets.choice(special_chars)

        return f"{word1}{word2}{number}{special}"

    @staticmethod
    def generate_temporary_password() -> str:
        """Generate a temporary password for initial setup.

        Format: TEMP-XXXX where X are random alphanumeric characters.
        This password must be changed on first login.
        """
        import secrets
        import string

        # Use uppercase letters and digits, exclude confusing characters
        chars = string.ascii_uppercase + string.digits
        chars = (
            chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
        )

        temp_code = "".join(secrets.choice(chars) for _ in range(4))
        return f"TEMP-{temp_code}"


class PortalAccountService:
    """Service for managing Portal Accounts."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.password_generator = PortalPasswordGenerator()

    def create_portal_account(
        self,
        tenant_id: UUID,
        account_data: PortalAccountCreate,
        created_by_admin_id: Optional[UUID] = None,
    ) -> PortalAccount:
        """Create a new portal account."""

        # Generate portal ID if not provided
        if not account_data.portal_id:
            portal_id = self._generate_unique_portal_id(tenant_id)
        else:
            portal_id = account_data.portal_id
            # Verify uniqueness
            if self._portal_id_exists(tenant_id, portal_id):
                raise ValueError(f"Portal ID {portal_id} already exists")

        # Hash password
        password_hash = pwd_context.hash(account_data.password)

        # Create account
        portal_account = PortalAccount(
            tenant_id=tenant_id,
            portal_id=portal_id,
            password_hash=password_hash,
            customer_id=account_data.customer_id,
            user_id=account_data.user_id,
            account_type=account_data.account_type.value,
            email_notifications=account_data.email_notifications,
            sms_notifications=account_data.sms_notifications,
            theme_preference=account_data.theme_preference,
            language_preference=account_data.language_preference,
            timezone_preference=account_data.timezone_preference,
            session_timeout_minutes=account_data.session_timeout_minutes,
            created_by_admin_id=created_by_admin_id,
            password_changed_at=datetime.utcnow(),
        )

        self.db.add(portal_account)
        self.db.commit()
        self.db.refresh(portal_account)

        return portal_account

    def get_portal_account_by_id(
        self, tenant_id: UUID, account_id: UUID
    ) -> Optional[PortalAccount]:
        """Get portal account by ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == tenant_id,
                    PortalAccount.id == account_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def get_portal_account_by_portal_id(
        self, tenant_id: UUID, portal_id: str
    ) -> Optional[PortalAccount]:
        """Get portal account by Portal ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == tenant_id,
                    PortalAccount.portal_id == portal_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def update_portal_account(
        self,
        tenant_id: UUID,
        account_id: UUID,
        update_data: PortalAccountUpdate,
        admin_id: Optional[UUID] = None,
    ) -> Optional[PortalAccount]:
        """Update portal account."""
        account = self.get_portal_account_by_id(tenant_id, account_id)
        if not account:
            return None

        # Update fields
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(account, field, value)

        if admin_id:
            account.last_modified_by_admin_id = admin_id

        self.db.commit()
        self.db.refresh(account)

        return account

    def change_password(
        self,
        tenant_id: UUID,
        account_id: UUID,
        password_change: PortalPasswordChangeRequest,
    ) -> bool:
        """Change portal account password."""
        account = self.get_portal_account_by_id(tenant_id, account_id)
        if not account:
            return False

        # Verify current password
        if not pwd_context.verify(
            password_change.current_password, account.password_hash
        ):
            return False

        # Check password history (prevent reuse of last 5 passwords)
        new_password_hash = pwd_context.hash(password_change.new_password)
        if self._is_password_reused(account, new_password_hash):
            raise ValueError("Cannot reuse a recent password")

        # Update password
        account.password_hash = new_password_hash
        account.password_changed_at = datetime.utcnow()
        account.must_change_password = False

        # Update password history
        self._update_password_history(account, new_password_hash)

        self.db.commit()

        return True

    def initiate_password_reset(self, tenant_id: UUID, portal_id: str) -> Optional[str]:
        """Initiate password reset process."""
        account = self.get_portal_account_by_portal_id(tenant_id, portal_id)
        if not account:
            return None

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        # Set reset token and expiration (1 hour)
        account.password_reset_token = token_hash
        account.password_reset_expires = datetime.utcnow() + timedelta(hours=1)

        self.db.commit()

        return reset_token

    def confirm_password_reset(
        self, tenant_id: UUID, reset_token: str, new_password: str
    ) -> bool:
        """Confirm password reset with token."""
        token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

        account = (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == tenant_id,
                    PortalAccount.password_reset_token == token_hash,
                    PortalAccount.password_reset_expires > datetime.utcnow(),
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

        if not account:
            return False

        # Update password
        account.password_hash = pwd_context.hash(new_password)
        account.password_changed_at = datetime.utcnow()
        account.password_reset_token = None
        account.password_reset_expires = None
        account.must_change_password = False
        account.failed_login_attempts = 0
        account.locked_until = None

        # Update password history
        self._update_password_history(account, account.password_hash)

        self.db.commit()

        return True

    def setup_2fa(
        self, tenant_id: UUID, account_id: UUID, method: str = "totp"
    ) -> Portal2FASetupResponse:
        """Setup two-factor authentication."""
        account = self.get_portal_account_by_id(tenant_id, account_id)
        if not account:
            raise ValueError("Portal account not found")

        if method == "totp":
            # Generate TOTP secret
            secret = pyotp.random_base32()
            account.two_factor_secret = secret

            # Generate QR code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=account.portal_id, issuer_name=f"ISP Portal - {account.tenant_id}"
            )

            #             qr = qrcode.QRCode(version=1, box_size=10, border=5)
            #             qr.add_data(totp_uri)
            #             qr.make(fit=True)

            #             img = qr.make_image(fill_color="black", back_color="white")
            #             img_io = io.BytesIO()
            #             img.save(img_io, 'PNG')
            #             img_io.seek(0)

            #             qr_code_data = base64.b64encode(img_io.read()).decode()
            #             qr_code_url = f"data:image/png;base64,{qr_code_data}"

            # Generate backup codes
            backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            account.backup_codes = ",".join(backup_codes)

            self.db.commit()

            return Portal2FASetupResponse(
                secret=secret,
                qr_code_url=qr_code_url,
                backup_codes=backup_codes,
                setup_complete=False,
            )

        raise ValueError(f"Unsupported 2FA method: {method}")

    def verify_2fa_setup(self, tenant_id: UUID, account_id: UUID, code: str) -> bool:
        """Verify 2FA setup with TOTP code."""
        account = self.get_portal_account_by_id(tenant_id, account_id)
        if not account or not account.two_factor_secret:
            return False

        totp = pyotp.TOTP(account.two_factor_secret)
        if totp.verify(code):
            account.two_factor_enabled = True
            self.db.commit()
            return True

        return False

    def disable_2fa(
        self, tenant_id: UUID, account_id: UUID, admin_id: Optional[UUID] = None
    ) -> bool:
        """Disable two-factor authentication."""
        account = self.get_portal_account_by_id(tenant_id, account_id)
        if not account:
            return False

        account.two_factor_enabled = False
        account.two_factor_secret = None
        account.backup_codes = None

        if admin_id:
            account.last_modified_by_admin_id = admin_id
            account.security_notes = f"{datetime.utcnow().isoformat()}: 2FA disabled by admin\n{account.security_notes or ''}"

        self.db.commit()

        return True

    def list_portal_accounts(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[PortalAccountStatus] = None,
    ) -> List[PortalAccount]:
        """List portal accounts with pagination."""
        query = self.db.query(PortalAccount).filter(
            and_(
                PortalAccount.tenant_id == tenant_id, PortalAccount.is_deleted == False
            )
        )

        if status:
            query = query.filter(PortalAccount.status == status.value)

        return query.offset(skip).limit(limit).all()

    def _generate_unique_portal_id(self, tenant_id: UUID) -> str:
        """Generate a unique Portal ID within the tenant."""
        max_attempts = 10
        for _ in range(max_attempts):
            portal_id = PortalAccount._generate_portal_id()
            if not self._portal_id_exists(tenant_id, portal_id):
                return portal_id

        raise RuntimeError("Unable to generate unique Portal ID after maximum attempts")

    def _portal_id_exists(self, tenant_id: UUID, portal_id: str) -> bool:
        """Check if Portal ID already exists in tenant."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == tenant_id,
                    PortalAccount.portal_id == portal_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
            is not None
        )

    def _is_password_reused(
        self, account: PortalAccount, new_password_hash: str
    ) -> bool:
        """Check if password was recently used."""
        if not account.password_history:
            return False

        # Parse password history (comma-separated hashes)
        history = account.password_history.split(",")
        return new_password_hash in history[-5:]  # Check last 5 passwords

    def _update_password_history(self, account: PortalAccount, password_hash: str):
        """Update password history."""
        if account.password_history:
            history = account.password_history.split(",")
        else:
            history = []

        history.append(password_hash)

        # Keep only last 5 passwords
        if len(history) > 5:
            history = history[-5:]

        account.password_history = ",".join(history)


class PortalAuthService:
    """Service for Portal Authentication."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def authenticate_portal_login(
        self,
        tenant_id: UUID,
        login_request: PortalLoginRequest,
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> PortalLoginResponse:
        """Authenticate portal login request."""

        # Get portal account
        account = (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == tenant_id,
                    PortalAccount.portal_id == login_request.portal_id,
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

        # Record login attempt
        login_attempt = PortalLoginAttempt(
            tenant_id=tenant_id,
            portal_account_id=account.id if account else None,
            portal_id_attempted=login_request.portal_id,
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=login_request.device_fingerprint,
        )

        # Check if account exists
        if not account:
            login_attempt.failure_reason = "invalid_portal_id"
            self.db.add(login_attempt)
            self.db.commit()

            return PortalLoginResponse(
                success=False, message="Invalid Portal ID or password"
            )

        # Check if account is active
        if not account.is_active:
            login_attempt.failure_reason = "account_inactive"
            if account.is_locked:
                login_attempt.failure_reason = "account_locked"

            self.db.add(login_attempt)
            self.db.commit()

            return PortalLoginResponse(
                success=False, message="Account is not active or locked"
            )

        # Verify password
        if not pwd_context.verify(login_request.password, account.password_hash):
            login_attempt.failure_reason = "invalid_password"
            account.record_failed_login()

            self.db.add(login_attempt)
            self.db.commit()

            return PortalLoginResponse(
                success=False, message="Invalid Portal ID or password"
            )

        # Check 2FA if enabled
        if account.two_factor_enabled:
            if not login_request.two_factor_code:
                login_attempt.failure_reason = "2fa_required"
                self.db.add(login_attempt)
                self.db.commit()

                return PortalLoginResponse(
                    success=False,
                    require_two_factor=True,
                    two_factor_methods=["totp"],
                    message="Two-factor authentication required",
                )

            if not self._verify_2fa_code(account, login_request.two_factor_code):
                login_attempt.failure_reason = "invalid_2fa_code"
                account.record_failed_login()

                self.db.add(login_attempt)
                self.db.commit()

                return PortalLoginResponse(
                    success=False, message="Invalid two-factor authentication code"
                )

            login_attempt.two_factor_used = True

        # Check if password change required
        if account.must_change_password or account.password_expired:
            login_attempt.success = True
            account.record_successful_login()

            self.db.add(login_attempt)
            self.db.commit()

            return PortalLoginResponse(
                success=True,
                require_password_change=True,
                message="Password change required",
            )

        # Create session
        session = self._create_session(
            account,
            ip_address,
            user_agent,
            login_request.device_fingerprint,
            login_request.remember_me,
        )

        # Generate JWT tokens
        access_token = self._create_access_token(account, session)
        refresh_token = self._create_refresh_token(account, session)

        # Update login attempt
        login_attempt.success = True
        login_attempt.session_created_id = session.id
        account.record_successful_login()

        self.db.add(login_attempt)
        self.db.commit()

        return PortalLoginResponse(
            success=True,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
            token_type="bearer",
            message="Login successful",
        )

    def refresh_token(self, tenant_id: UUID, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                self.settings.secret_key,
                algorithms=[self.settings.algorithm],
            )

            session_id = payload.get("session_id")
            if not session_id:
                return None

            # Get session
            session = (
                self.db.query(PortalSession)
                .filter(
                    and_(
                        PortalSession.id == session_id,
                        PortalSession.tenant_id == tenant_id,
                        PortalSession.is_active == True,
                    )
                )
                .first()
            )

            if not session or not session.is_valid:
                return None

            # Extend session
            session.extend_session(session.portal_account.session_timeout_minutes)
            self.db.commit()

            # Generate new access token
            return self._create_access_token(session.portal_account, session)

        except JWTError:
            return None

    def logout_session(self, tenant_id: UUID, session_token: str) -> bool:
        """Logout and terminate session."""
        session = (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.tenant_id == tenant_id,
                    PortalSession.session_token == session_token,
                    PortalSession.is_active == True,
                )
            )
            .first()
        )

        if session:
            session.terminate_session("manual")
            self.db.commit()
            return True

        return False

    def get_active_sessions(
        self, tenant_id: UUID, account_id: UUID
    ) -> List[PortalSession]:
        """Get all active sessions for a portal account."""
        return (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.tenant_id == tenant_id,
                    PortalSession.portal_account_id == account_id,
                    PortalSession.is_active == True,
                    PortalSession.expires_at > datetime.utcnow(),
                )
            )
            .all()
        )

    def _verify_2fa_code(self, account: PortalAccount, code: str) -> bool:
        """Verify 2FA code (TOTP or backup code)."""
        if not account.two_factor_secret:
            return False

        # Check TOTP code
        totp = pyotp.TOTP(account.two_factor_secret)
        if totp.verify(code):
            return True

        # Check backup codes
        if account.backup_codes:
            backup_codes = account.backup_codes.split(",")
            if code.upper() in backup_codes:
                # Remove used backup code
                backup_codes.remove(code.upper())
                account.backup_codes = ",".join(backup_codes)
                return True

        return False

    def _create_session(
        self,
        account: PortalAccount,
        ip_address: str,
        user_agent: Optional[str],
        device_fingerprint: Optional[str],
        remember_me: bool = False,
    ) -> PortalSession:
        """Create a new portal session."""

        # Calculate expiration time
        if remember_me:
            expires_in_minutes = 60 * 24 * 30  # 30 days
        else:
            expires_in_minutes = account.session_timeout_minutes

        session = PortalSession(
            tenant_id=account.tenant_id,
            portal_account_id=account.id,
            session_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes),
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        return session

    def _create_access_token(
        self, account: PortalAccount, session: PortalSession
    ) -> str:
        """Create JWT access token."""
        to_encode = {
            "sub": str(account.id),
            "portal_id": account.portal_id,
            "tenant_id": str(account.tenant_id),
            "session_id": str(session.id),
            "account_type": account.account_type,
            "exp": datetime.utcnow()
            + timedelta(minutes=self.settings.access_token_expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access",
        }

        return jwt.encode(
            to_encode, self.settings.secret_key, algorithm=self.settings.algorithm
        )

    def _create_refresh_token(
        self, account: PortalAccount, session: PortalSession
    ) -> str:
        """Create JWT refresh token."""
        to_encode = {
            "sub": str(account.id),
            "session_id": str(session.id),
            "tenant_id": str(account.tenant_id),
            "exp": datetime.utcnow()
            + timedelta(days=self.settings.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh",
        }

        return jwt.encode(
            to_encode, self.settings.secret_key, algorithm=self.settings.algorithm
        )
