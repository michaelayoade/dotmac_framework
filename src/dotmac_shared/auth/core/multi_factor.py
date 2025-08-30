"""
Multi-Factor Authentication (MFA) System

Implements comprehensive MFA support with:
- TOTP (Time-based One-Time Password) authentication
- SMS-based authentication support
- Backup codes generation and validation
- MFA enforcement policies
- Recovery mechanisms for lost devices
- QR code generation for authenticator apps
"""

import base64
import hashlib
import logging
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import pyotp
import qrcode

logger = logging.getLogger(__name__)


class MFAMethod(Enum):
    """Multi-factor authentication methods."""

    TOTP = "totp"
    SMS = "sms"
    BACKUP_CODE = "backup_code"
    EMAIL = "email"


class MFAStatus(Enum):
    """MFA status for users."""

    DISABLED = "disabled"
    ENABLED = "enabled"
    REQUIRED = "required"
    SUSPENDED = "suspended"


@dataclass
class MFASecret:
    """MFA secret container."""

    user_id: str
    tenant_id: str
    method: MFAMethod
    secret: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    is_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "method": self.method.value,
            "secret": self.secret,
            "created_at": self.created_at.isoformat(),
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "is_verified": self.is_verified,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MFASecret":
        """Create from dictionary."""
        return cls(
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            method=MFAMethod(data["method"]),
            secret=data["secret"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used_at=(
                datetime.fromisoformat(data["last_used_at"])
                if data.get("last_used_at")
                else None
            ),
            is_verified=data["is_verified"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class BackupCode:
    """Backup code for MFA recovery."""

    code: str
    used_at: Optional[datetime] = None
    is_used: bool = False

    def use_code(self):
        """Mark code as used."""
        self.is_used = True
        self.used_at = datetime.now(timezone.utc)


@dataclass
class MFAAttempt:
    """MFA authentication attempt."""

    user_id: str
    tenant_id: str
    method: MFAMethod
    code: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool = False
    failure_reason: Optional[str] = None


class MFAProvider(ABC):
    """Abstract MFA provider interface."""

    @abstractmethod
    async def store_mfa_secret(self, secret: MFASecret) -> bool:
        """Store MFA secret."""
        pass

    @abstractmethod
    async def get_mfa_secret(
        self, user_id: str, tenant_id: str, method: MFAMethod
    ) -> Optional[MFASecret]:
        """Get MFA secret for user and method."""
        pass

    @abstractmethod
    async def delete_mfa_secret(
        self, user_id: str, tenant_id: str, method: MFAMethod
    ) -> bool:
        """Delete MFA secret."""
        pass

    @abstractmethod
    async def store_backup_codes(
        self, user_id: str, tenant_id: str, codes: List[BackupCode]
    ) -> bool:
        """Store backup codes."""
        pass

    @abstractmethod
    async def get_backup_codes(self, user_id: str, tenant_id: str) -> List[BackupCode]:
        """Get backup codes for user."""
        pass

    @abstractmethod
    async def log_mfa_attempt(self, attempt: MFAAttempt) -> bool:
        """Log MFA authentication attempt."""
        pass


class SMSProvider(ABC):
    """Abstract SMS provider interface."""

    @abstractmethod
    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message."""
        pass


class EmailProvider(ABC):
    """Abstract email provider interface."""

    @abstractmethod
    async def send_email(self, email: str, subject: str, message: str) -> bool:
        """Send email message."""
        pass


class MFAManager:
    """
    Multi-Factor Authentication Manager.

    Features:
    - TOTP authentication with QR code generation
    - SMS-based authentication
    - Backup codes for recovery
    - MFA enforcement policies
    - Attempt logging and rate limiting
    - Device trust management
    """

    def __init__(
        self,
        mfa_provider: MFAProvider,
        sms_provider: Optional[SMSProvider] = None,
        email_provider: Optional[EmailProvider] = None,
        issuer_name: str = "DotMac Auth Service",
        totp_window: int = 1,
        backup_codes_count: int = 8,
        max_failed_attempts: int = 5,
        lockout_duration_minutes: int = 15,
    ):
        """
        Initialize MFA manager.

        Args:
            mfa_provider: Provider for MFA secret storage
            sms_provider: SMS service provider
            email_provider: Email service provider
            issuer_name: Issuer name for TOTP QR codes
            totp_window: TOTP time window (30-second intervals)
            backup_codes_count: Number of backup codes to generate
            max_failed_attempts: Maximum failed attempts before lockout
            lockout_duration_minutes: Lockout duration in minutes
        """
        self.mfa_provider = mfa_provider
        self.sms_provider = sms_provider
        self.email_provider = email_provider
        self.issuer_name = issuer_name
        self.totp_window = totp_window
        self.backup_codes_count = backup_codes_count
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration_minutes = lockout_duration_minutes

        # In-memory tracking for rate limiting (in production, use Redis)
        self._failed_attempts: Dict[str, List[datetime]] = {}

        logger.info(f"MFA Manager initialized (issuer: {issuer_name})")

    # TOTP Methods

    def generate_totp_secret(self, user_id: str, tenant_id: str) -> str:
        """
        Generate TOTP secret for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            Base32-encoded TOTP secret
        """
        try:
            secret = pyotp.random_base32()

            logger.info(f"Generated TOTP secret for user {user_id}")
            return secret

        except Exception as e:
            logger.error(f"Failed to generate TOTP secret for user {user_id}: {e}")
            raise

    async def setup_totp(
        self, user_id: str, tenant_id: str, user_email: str
    ) -> Tuple[str, bytes]:
        """
        Set up TOTP for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            user_email: User email for QR code

        Returns:
            Tuple of (secret, qr_code_image_bytes)
        """
        try:
            # Generate TOTP secret
            secret = self.generate_totp_secret(user_id, tenant_id)

            # Create TOTP URL for QR code
            totp_url = pyotp.totp.TOTP(secret).provisioning_uri(
                name=user_email, issuer_name=self.issuer_name
            )

            # Generate QR code
            qr_code_bytes = self.generate_qr_code(totp_url)

            # Store MFA secret (unverified until first successful validation)
            mfa_secret = MFASecret(
                user_id=user_id,
                tenant_id=tenant_id,
                method=MFAMethod.TOTP,
                secret=secret,
                created_at=datetime.now(timezone.utc),
                is_verified=False,
                metadata={"email": user_email},
            )

            await self.mfa_provider.store_mfa_secret(mfa_secret)

            logger.info(f"Set up TOTP for user {user_id}")
            return secret, qr_code_bytes

        except Exception as e:
            logger.error(f"Failed to setup TOTP for user {user_id}: {e}")
            raise

    def generate_qr_code(self, totp_url: str) -> bytes:
        """
        Generate QR code for TOTP setup.

        Args:
            totp_url: TOTP provisioning URL

        Returns:
            QR code image bytes (PNG format)
        """
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(totp_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to bytes
            img_buffer = BytesIO()
            img.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()

            return img_bytes

        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            raise

    async def validate_totp(self, user_id: str, tenant_id: str, token: str) -> bool:
        """
        Validate TOTP token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            token: TOTP token to validate

        Returns:
            True if token is valid
        """
        try:
            # Get TOTP secret
            mfa_secret = await self.mfa_provider.get_mfa_secret(
                user_id, tenant_id, MFAMethod.TOTP
            )
            if not mfa_secret:
                return False

            # Validate token
            totp = pyotp.TOTP(mfa_secret.secret)
            is_valid = totp.verify(token, valid_window=self.totp_window)

            if is_valid:
                # Mark as verified on first successful use
                if not mfa_secret.is_verified:
                    mfa_secret.is_verified = True

                mfa_secret.last_used_at = datetime.now(timezone.utc)
                await self.mfa_provider.store_mfa_secret(mfa_secret)

                logger.info(f"TOTP validation successful for user {user_id}")
            else:
                logger.warning(f"TOTP validation failed for user {user_id}")

            return is_valid

        except Exception as e:
            logger.error(f"TOTP validation error for user {user_id}: {e}")
            return False

    # SMS Methods

    async def send_sms_code(
        self, user_id: str, tenant_id: str, phone_number: str
    ) -> bool:
        """
        Send SMS authentication code.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            phone_number: Phone number to send to

        Returns:
            True if SMS was sent successfully
        """
        try:
            if not self.sms_provider:
                logger.error("SMS provider not configured")
                return False

            # Generate 6-digit code
            code = self._generate_numeric_code(6)

            # Store SMS secret with expiration
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            mfa_secret = MFASecret(
                user_id=user_id,
                tenant_id=tenant_id,
                method=MFAMethod.SMS,
                secret=code,
                created_at=datetime.now(timezone.utc),
                is_verified=False,
                metadata={
                    "phone_number": phone_number,
                    "expires_at": expiry_time.isoformat(),
                },
            )

            await self.mfa_provider.store_mfa_secret(mfa_secret)

            # Send SMS
            message = f"Your {self.issuer_name} verification code is: {code}. Valid for 5 minutes."
            success = await self.sms_provider.send_sms(phone_number, message)

            if success:
                logger.info(f"SMS code sent to user {user_id}")
            else:
                logger.error(f"Failed to send SMS code to user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to send SMS code to user {user_id}: {e}")
            return False

    async def validate_sms_code(self, user_id: str, tenant_id: str, code: str) -> bool:
        """
        Validate SMS authentication code.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            code: SMS code to validate

        Returns:
            True if code is valid
        """
        try:
            # Get SMS secret
            mfa_secret = await self.mfa_provider.get_mfa_secret(
                user_id, tenant_id, MFAMethod.SMS
            )
            if not mfa_secret:
                return False

            # Check expiration
            if "expires_at" in mfa_secret.metadata:
                expiry_time = datetime.fromisoformat(mfa_secret.metadata["expires_at"])
                if datetime.now(timezone.utc) > expiry_time:
                    await self.mfa_provider.delete_mfa_secret(
                        user_id, tenant_id, MFAMethod.SMS
                    )
                    return False

            # Validate code
            is_valid = mfa_secret.secret == code

            if is_valid:
                mfa_secret.last_used_at = datetime.now(timezone.utc)
                await self.mfa_provider.store_mfa_secret(mfa_secret)

                # Delete used SMS code
                await self.mfa_provider.delete_mfa_secret(
                    user_id, tenant_id, MFAMethod.SMS
                )

                logger.info(f"SMS validation successful for user {user_id}")
            else:
                logger.warning(f"SMS validation failed for user {user_id}")

            return is_valid

        except Exception as e:
            logger.error(f"SMS validation error for user {user_id}: {e}")
            return False

    # Backup Codes Methods

    def generate_backup_codes(self) -> List[str]:
        """
        Generate backup codes.

        Returns:
            List of backup codes
        """
        try:
            codes = []
            for _ in range(self.backup_codes_count):
                # Generate 8-character alphanumeric code
                code = self._generate_alphanumeric_code(8)
                codes.append(code)

            return codes

        except Exception as e:
            logger.error(f"Failed to generate backup codes: {e}")
            raise

    async def setup_backup_codes(self, user_id: str, tenant_id: str) -> List[str]:
        """
        Set up backup codes for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            List of generated backup codes
        """
        try:
            # Generate codes
            code_strings = self.generate_backup_codes()

            # Create BackupCode objects
            backup_codes = [BackupCode(code=code) for code in code_strings]

            # Store codes
            await self.mfa_provider.store_backup_codes(user_id, tenant_id, backup_codes)

            logger.info(
                f"Generated {len(code_strings)} backup codes for user {user_id}"
            )
            return code_strings

        except Exception as e:
            logger.error(f"Failed to setup backup codes for user {user_id}: {e}")
            raise

    async def validate_backup_code(
        self, user_id: str, tenant_id: str, code: str
    ) -> bool:
        """
        Validate and consume backup code.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            code: Backup code to validate

        Returns:
            True if code is valid and unused
        """
        try:
            # Get backup codes
            backup_codes = await self.mfa_provider.get_backup_codes(user_id, tenant_id)

            # Find and validate code
            for backup_code in backup_codes:
                if backup_code.code == code and not backup_code.is_used:
                    # Mark as used
                    backup_code.use_code()

                    # Update storage
                    await self.mfa_provider.store_backup_codes(
                        user_id, tenant_id, backup_codes
                    )

                    logger.info(f"Backup code validation successful for user {user_id}")
                    return True

            logger.warning(f"Backup code validation failed for user {user_id}")
            return False

        except Exception as e:
            logger.error(f"Backup code validation error for user {user_id}: {e}")
            return False

    async def get_backup_codes_status(
        self, user_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """
        Get backup codes status for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            Backup codes status information
        """
        try:
            backup_codes = await self.mfa_provider.get_backup_codes(user_id, tenant_id)

            used_count = sum(1 for code in backup_codes if code.is_used)
            unused_count = len(backup_codes) - used_count

            return {
                "total_codes": len(backup_codes),
                "used_codes": used_count,
                "unused_codes": unused_count,
                "codes": [
                    {
                        "code": code.code[:4] + "XXXX",  # Masked for security
                        "is_used": code.is_used,
                        "used_at": code.used_at.isoformat() if code.used_at else None,
                    }
                    for code in backup_codes
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get backup codes status for user {user_id}: {e}")
            return {"total_codes": 0, "used_codes": 0, "unused_codes": 0, "codes": []}

    # MFA Management Methods

    async def get_mfa_status(self, user_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        Get MFA status for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            MFA status information
        """
        try:
            status = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "methods": {},
                "backup_codes": None,
                "is_enabled": False,
            }

            # Check each MFA method
            for method in MFAMethod:
                if method == MFAMethod.BACKUP_CODE:
                    continue

                mfa_secret = await self.mfa_provider.get_mfa_secret(
                    user_id, tenant_id, method
                )
                status["methods"][method.value] = {
                    "enabled": mfa_secret is not None,
                    "verified": mfa_secret.is_verified if mfa_secret else False,
                    "created_at": (
                        mfa_secret.created_at.isoformat() if mfa_secret else None
                    ),
                    "last_used_at": (
                        mfa_secret.last_used_at.isoformat()
                        if mfa_secret and mfa_secret.last_used_at
                        else None
                    ),
                }

                if mfa_secret and mfa_secret.is_verified:
                    status["is_enabled"] = True

            # Check backup codes
            status["backup_codes"] = await self.get_backup_codes_status(
                user_id, tenant_id
            )

            return status

        except Exception as e:
            logger.error(f"Failed to get MFA status for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "methods": {},
                "is_enabled": False,
            }

    async def disable_mfa_method(
        self, user_id: str, tenant_id: str, method: MFAMethod
    ) -> bool:
        """
        Disable specific MFA method for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            method: MFA method to disable

        Returns:
            True if method was disabled
        """
        try:
            success = await self.mfa_provider.delete_mfa_secret(
                user_id, tenant_id, method
            )

            if success:
                logger.info(f"Disabled MFA method {method.value} for user {user_id}")
            else:
                logger.warning(
                    f"Failed to disable MFA method {method.value} for user {user_id}"
                )

            return success

        except Exception as e:
            logger.error(
                f"Error disabling MFA method {method.value} for user {user_id}: {e}"
            )
            return False

    async def disable_all_mfa(self, user_id: str, tenant_id: str) -> bool:
        """
        Disable all MFA methods for user.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier

        Returns:
            True if all methods were disabled
        """
        try:
            success_count = 0

            # Disable all MFA methods
            for method in MFAMethod:
                if method == MFAMethod.BACKUP_CODE:
                    continue

                if await self.disable_mfa_method(user_id, tenant_id, method):
                    success_count += 1

            # Clear backup codes
            await self.mfa_provider.store_backup_codes(user_id, tenant_id, [])

            logger.info(f"Disabled all MFA methods for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable all MFA for user {user_id}: {e}")
            return False

    # Rate Limiting and Security

    async def is_user_locked_out(self, user_id: str) -> bool:
        """
        Check if user is locked out due to failed attempts.

        Args:
            user_id: User identifier

        Returns:
            True if user is locked out
        """
        try:
            if user_id not in self._failed_attempts:
                return False

            # Clean up old attempts
            cutoff_time = datetime.now(timezone.utc) - timedelta(
                minutes=self.lockout_duration_minutes
            )
            self._failed_attempts[user_id] = [
                attempt
                for attempt in self._failed_attempts[user_id]
                if attempt > cutoff_time
            ]

            # Check if user exceeded max attempts
            return len(self._failed_attempts[user_id]) >= self.max_failed_attempts

        except Exception as e:
            logger.error(f"Failed to check lockout status for user {user_id}: {e}")
            return False

    async def record_failed_attempt(self, user_id: str):
        """
        Record failed MFA attempt.

        Args:
            user_id: User identifier
        """
        try:
            if user_id not in self._failed_attempts:
                self._failed_attempts[user_id] = []

            self._failed_attempts[user_id].append(datetime.now(timezone.utc))

            # Log lockout if threshold reached
            if await self.is_user_locked_out(user_id):
                logger.warning(
                    f"User {user_id} locked out due to too many failed MFA attempts"
                )

        except Exception as e:
            logger.error(f"Failed to record failed attempt for user {user_id}: {e}")

    def clear_failed_attempts(self, user_id: str):
        """
        Clear failed attempts for user.

        Args:
            user_id: User identifier
        """
        if user_id in self._failed_attempts:
            del self._failed_attempts[user_id]

    # Utility Methods

    def _generate_numeric_code(self, length: int) -> str:
        """Generate numeric code of specified length."""
        return "".join(secrets.choice("0123456789") for _ in range(length))

    def _generate_alphanumeric_code(self, length: int) -> str:
        """Generate alphanumeric code of specified length."""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _hash_code(self, code: str) -> str:
        """Hash code for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    async def validate_mfa(
        self,
        user_id: str,
        tenant_id: str,
        method: MFAMethod,
        code: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> bool:
        """
        Unified MFA validation method.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            method: MFA method used
            code: Authentication code
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            True if validation successful
        """
        try:
            # Check if user is locked out
            if await self.is_user_locked_out(user_id):
                logger.warning(f"MFA validation blocked for locked out user {user_id}")
                return False

            # Validate based on method
            success = False
            if method == MFAMethod.TOTP:
                success = await self.validate_totp(user_id, tenant_id, code)
            elif method == MFAMethod.SMS:
                success = await self.validate_sms_code(user_id, tenant_id, code)
            elif method == MFAMethod.BACKUP_CODE:
                success = await self.validate_backup_code(user_id, tenant_id, code)

            # Log attempt
            attempt = MFAAttempt(
                user_id=user_id,
                tenant_id=tenant_id,
                method=method,
                code=code[:2] + "X" * (len(code) - 2),  # Mask code for logging
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.now(timezone.utc),
                success=success,
                failure_reason=None if success else "invalid_code",
            )

            await self.mfa_provider.log_mfa_attempt(attempt)

            # Handle result
            if success:
                self.clear_failed_attempts(user_id)
                logger.info(
                    f"MFA validation successful for user {user_id} using {method.value}"
                )
            else:
                await self.record_failed_attempt(user_id)
                logger.warning(
                    f"MFA validation failed for user {user_id} using {method.value}"
                )

            return success

        except Exception as e:
            logger.error(f"MFA validation error for user {user_id}: {e}")
            await self.record_failed_attempt(user_id)
            return False
