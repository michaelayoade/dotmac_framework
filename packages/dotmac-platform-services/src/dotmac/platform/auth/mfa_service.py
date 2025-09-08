"""
Multi-Factor Authentication (MFA) Service

Comprehensive MFA implementation supporting TOTP, SMS, email verification,
and backup codes with device management and JWT integration.
"""

import base64
import io
import logging
import secrets
import string
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

import pyotp
import qrcode
from pydantic import (
    BaseModel,
    Field,
    model_validator,
)
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

from .exceptions import (
    AuthenticationError,
    ValidationError,
)
from .jwt_service import JWTService

Base = declarative_base()


class MFAMethod(str, Enum):
    """Supported MFA methods."""

    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODE = "backup_code"


class MFAStatus(str, Enum):
    """MFA enrollment status."""

    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"
    SUSPENDED = "suspended"


class MFADevice(Base):
    """Database model for MFA devices."""

    __tablename__ = "mfa_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    device_name = Column(String(100), nullable=False)
    method = Column(String(20), nullable=False)
    secret = Column(Text, nullable=True)  # Encrypted TOTP secret
    phone_number = Column(String(20), nullable=True)  # For SMS
    email = Column(String(255), nullable=True)  # For email verification
    status = Column(String(20), nullable=False, default=MFAStatus.PENDING)
    backup_codes = Column(Text, nullable=True)  # JSON array of backup codes
    last_used = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_primary = Column(Boolean, default=False)
    failure_count = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)


class MFAChallenge(Base):
    """Database model for MFA challenges."""

    __tablename__ = "mfa_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), nullable=False)
    challenge_token = Column(String(255), nullable=False, unique=True)
    method = Column(String(20), nullable=False)
    verification_code = Column(String(10), nullable=True)  # For SMS/email
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class MFAEnrollmentRequest(BaseModel):
    """Request model for MFA enrollment."""

    method: MFAMethod
    device_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str | None = Field(None, pattern=r"^\+[1-9]\d{1,14}$")
    email: str | None = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")

    @model_validator(mode="after")
    def _verify_contact_for_method(self):
        if self.method == MFAMethod.SMS and not self.phone_number:
            raise ValueError("Phone number required for SMS method")
        if self.method == MFAMethod.EMAIL and not self.email:
            raise ValueError("Email required for email method")
        return self


class MFAVerificationRequest(BaseModel):
    """Request model for MFA verification."""

    challenge_token: str
    code: str = Field(..., min_length=4, max_length=10)


class TOTPSetupResponse(BaseModel):
    """Response model for TOTP setup."""

    secret: str
    qr_code: str  # Base64 encoded QR code
    backup_codes: list[str]
    device_id: str


class MFAServiceConfig(BaseModel):
    """Configuration for MFA Service."""

    issuer_name: str = "DotMac ISP"
    totp_window: int = 1  # Number of time steps to allow
    sms_expiry_minutes: int = 5
    email_expiry_minutes: int = 10
    backup_codes_count: int = 10
    max_verification_attempts: int = 3
    lockout_duration_minutes: int = 30
    challenge_token_expiry_minutes: int = 15


class SMSProvider:
    """SMS provider interface."""

    async def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message."""
        logger = logging.getLogger(__name__)
        logger.info(
            "SMS sent to %s for MFA verification",
            phone_number[-4:].rjust(len(phone_number), '*'),
            extra={
                "phone_number_hash": hash(phone_number),
                "message_type": "mfa_verification",
                "event_type": "sms_sent"
            }
        )
        return True


class EmailProvider:
    """Email provider interface."""

    async def send_email(self, email: str, subject: str, body: str) -> bool:
        """Send email message."""
        logger = logging.getLogger(__name__)
        logger.info(
            "Email sent to %s with subject: %s",
            email.split('@')[0][:3] + "***@" + email.split('@')[1],
            subject,
            extra={
                "email_hash": hash(email),
                "subject": subject,
                "message_type": "mfa_verification",
                "event_type": "email_sent"
            }
        )
        return True


class MFAService:
    """
    Comprehensive Multi-Factor Authentication Service.

    Features:
    - TOTP (Time-based One-Time Password) with QR codes
    - SMS verification with rate limiting
    - Email verification fallback
    - Backup codes generation and management
    - Device enrollment and management
    - Integration with JWT/session systems
    - Audit logging and security features
    """

    def __init__(
        self,
        database_session,
        jwt_service: JWTService,
        config: MFAServiceConfig | None = None,
        sms_provider: SMSProvider | None = None,
        email_provider: EmailProvider | None = None,
    ) -> None:
        self.db = database_session
        self.jwt = jwt_service
        self.config = config or MFAServiceConfig()
        self.sms_provider = sms_provider or SMSProvider()
        self.email_provider = email_provider or EmailProvider()

    async def enroll_device(
        self, user_id: str, enrollment_request: MFAEnrollmentRequest
    ) -> TOTPSetupResponse | dict[str, Any]:
        """
        Enroll a new MFA device for a user.

        Returns different response types based on MFA method:
        - TOTP: TOTPSetupResponse with QR code and backup codes
        - SMS/Email: Challenge token for verification
        """
        # Check if user already has maximum devices
        existing_devices = await self._get_user_devices(user_id)
        if len(existing_devices) >= 5:  # Configurable limit
            raise ValidationError("Maximum number of MFA devices reached")

        if enrollment_request.method == MFAMethod.TOTP:
            return await self._enroll_totp_device(user_id, enrollment_request)
        if enrollment_request.method == MFAMethod.SMS:
            return await self._enroll_sms_device(user_id, enrollment_request)
        if enrollment_request.method == MFAMethod.EMAIL:
            return await self._enroll_email_device(user_id, enrollment_request)
        raise ValidationError(f"Unsupported MFA method: {enrollment_request.method}")

    async def _enroll_totp_device(
        self, user_id: str, enrollment_request: MFAEnrollmentRequest
    ) -> TOTPSetupResponse:
        """Enroll TOTP device and generate QR code."""
        # Generate TOTP secret
        secret = pyotp.random_base32()

        # Create TOTP instance
        totp = pyotp.TOTP(secret)

        # Generate provisioning URI
        provisioning_uri = totp.provisioning_uri(
            name=f"user_{user_id}", issuer_name=self.config.issuer_name
        )

        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Convert QR code to base64
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_b64 = base64.b64encode(buffer.getvalue()).decode()

        # Generate backup codes
        backup_codes = self._generate_backup_codes()

        # Create device record
        device = MFADevice(
            user_id=user_id,
            device_name=enrollment_request.device_name,
            method=MFAMethod.TOTP,
            secret=secret,  # Should be encrypted in production
            backup_codes=",".join(backup_codes),  # Should be encrypted
            status=MFAStatus.PENDING,
        )

        self.db.add(device)
        await self.db.commit()

        return TOTPSetupResponse(
            secret=secret, qr_code=qr_code_b64, backup_codes=backup_codes, device_id=str(device.id)
        )

    async def _enroll_sms_device(
        self, user_id: str, enrollment_request: MFAEnrollmentRequest
    ) -> dict[str, Any]:
        """Enroll SMS device and send verification code."""
        # Generate verification code
        verification_code = self._generate_verification_code()

        # Create device record
        device = MFADevice(
            user_id=user_id,
            device_name=enrollment_request.device_name,
            method=MFAMethod.SMS,
            phone_number=enrollment_request.phone_number,
            status=MFAStatus.PENDING,
        )

        self.db.add(device)
        await self.db.flush()  # Get device ID

        # Create challenge
        challenge_token = secrets.token_urlsafe(32)
        challenge = MFAChallenge(
            user_id=user_id,
            device_id=device.id,
            challenge_token=challenge_token,
            method=MFAMethod.SMS,
            verification_code=verification_code,
            expires_at=datetime.now(UTC) + timedelta(minutes=self.config.sms_expiry_minutes),
        )

        self.db.add(challenge)
        await self.db.commit()

        # Send SMS
        message = f"Your {self.config.issuer_name} verification code is: {verification_code}"
        await self.sms_provider.send_sms(enrollment_request.phone_number, message)

        return {
            "challenge_token": challenge_token,
            "device_id": str(device.id),
            "expires_in": self.config.sms_expiry_minutes * 60,
        }

    async def _enroll_email_device(
        self, user_id: str, enrollment_request: MFAEnrollmentRequest
    ) -> dict[str, Any]:
        """Enroll email device and send verification code."""
        # Generate verification code
        verification_code = self._generate_verification_code()

        # Create device record
        device = MFADevice(
            user_id=user_id,
            device_name=enrollment_request.device_name,
            method=MFAMethod.EMAIL,
            email=enrollment_request.email,
            status=MFAStatus.PENDING,
        )

        self.db.add(device)
        await self.db.flush()

        # Create challenge
        challenge_token = secrets.token_urlsafe(32)
        challenge = MFAChallenge(
            user_id=user_id,
            device_id=device.id,
            challenge_token=challenge_token,
            method=MFAMethod.EMAIL,
            verification_code=verification_code,
            expires_at=datetime.now(UTC) + timedelta(minutes=self.config.email_expiry_minutes),
        )

        self.db.add(challenge)
        await self.db.commit()

        # Send email
        subject = f"{self.config.issuer_name} MFA Verification"
        body = f"Your verification code is: {verification_code}"
        await self.email_provider.send_email(enrollment_request.email, subject, body)

        return {
            "challenge_token": challenge_token,
            "device_id": str(device.id),
            "expires_in": self.config.email_expiry_minutes * 60,
        }

    async def verify_enrollment(
        self, verification_request: MFAVerificationRequest
    ) -> dict[str, Any]:
        """Verify MFA device enrollment."""
        challenge = await self._get_challenge(verification_request.challenge_token)

        if not challenge:
            raise AuthenticationError("Invalid or expired challenge token")

        if challenge.verified_at:
            raise AuthenticationError("Challenge already verified")

        # Check attempts
        if challenge.attempts >= self.config.max_verification_attempts:
            raise AuthenticationError("Maximum verification attempts exceeded")

        # Increment attempts
        challenge.attempts += 1

        # Get device
        device = await self._get_device(challenge.device_id)
        if not device:
            raise AuthenticationError("Device not found")

        # Verify based on method
        if device.method == MFAMethod.TOTP:
            is_valid = await self._verify_totp_code(device.secret, verification_request.code)
        elif device.method in [MFAMethod.SMS, MFAMethod.EMAIL]:
            is_valid = challenge.verification_code == verification_request.code
        else:
            raise ValidationError(f"Unsupported method: {device.method}")

        if is_valid:
            # Mark challenge as verified
            challenge.verified_at = datetime.now(UTC)

            # Activate device
            device.status = MFAStatus.ACTIVE

            # Set as primary if it's the first device
            user_devices = await self._get_user_devices(challenge.user_id)
            if len([d for d in user_devices if d.status == MFAStatus.ACTIVE]) == 0:
                device.is_primary = True

            await self.db.commit()

            return {"success": True, "device_id": str(device.id), "is_primary": device.is_primary}
        await self.db.commit()  # Save attempt increment
        attempts_remaining = self.config.max_verification_attempts - challenge.attempts
        raise AuthenticationError(
            f"Invalid verification code. {attempts_remaining} attempts remaining."
        )

    async def initiate_mfa_challenge(
        self, user_id: str, device_id: str | None = None
    ) -> dict[str, Any]:
        """Initiate MFA challenge for authentication."""
        # Get user's active devices
        devices = await self._get_active_user_devices(user_id)
        if not devices:
            raise AuthenticationError("No active MFA devices found")

        # Select device
        if device_id:
            device = next((d for d in devices if str(d.id) == device_id), None)
            if not device:
                raise AuthenticationError("Specified device not found or inactive")
        else:
            # Use primary device or first active device
            device = next((d for d in devices if d.is_primary), devices[0])

        # Check if device is locked
        if device.locked_until and device.locked_until > datetime.now(UTC):
            raise AuthenticationError("Device is temporarily locked due to failed attempts")

        # Create challenge
        challenge_token = secrets.token_urlsafe(32)

        if device.method == MFAMethod.TOTP:
            # TOTP doesn't need a challenge - user generates code
            challenge = MFAChallenge(
                user_id=user_id,
                device_id=device.id,
                challenge_token=challenge_token,
                method=MFAMethod.TOTP,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=self.config.challenge_token_expiry_minutes),
            )

            response = {
                "challenge_token": challenge_token,
                "method": device.method,
                "device_name": device.device_name,
                "expires_in": self.config.challenge_token_expiry_minutes * 60,
            }

        elif device.method == MFAMethod.SMS:
            verification_code = self._generate_verification_code()
            challenge = MFAChallenge(
                user_id=user_id,
                device_id=device.id,
                challenge_token=challenge_token,
                method=MFAMethod.SMS,
                verification_code=verification_code,
                expires_at=datetime.now(UTC) + timedelta(minutes=self.config.sms_expiry_minutes),
            )

            # Send SMS
            message = f"Your {self.config.issuer_name} authentication code is: {verification_code}"
            await self.sms_provider.send_sms(device.phone_number, message)

            response = {
                "challenge_token": challenge_token,
                "method": device.method,
                "device_name": device.device_name,
                "phone_hint": self._mask_phone_number(device.phone_number),
                "expires_in": self.config.sms_expiry_minutes * 60,
            }

        elif device.method == MFAMethod.EMAIL:
            verification_code = self._generate_verification_code()
            challenge = MFAChallenge(
                user_id=user_id,
                device_id=device.id,
                challenge_token=challenge_token,
                method=MFAMethod.EMAIL,
                verification_code=verification_code,
                expires_at=datetime.now(UTC) + timedelta(minutes=self.config.email_expiry_minutes),
            )

            # Send email
            subject = f"{self.config.issuer_name} Authentication Code"
            body = f"Your authentication code is: {verification_code}"
            await self.email_provider.send_email(device.email, subject, body)

            response = {
                "challenge_token": challenge_token,
                "method": device.method,
                "device_name": device.device_name,
                "email_hint": self._mask_email(device.email),
                "expires_in": self.config.email_expiry_minutes * 60,
            }

        self.db.add(challenge)
        await self.db.commit()

        return response

    async def verify_mfa_challenge(
        self, verification_request: MFAVerificationRequest
    ) -> dict[str, Any]:
        """Verify MFA challenge for authentication."""
        challenge = await self._get_challenge(verification_request.challenge_token)

        if not challenge:
            raise AuthenticationError("Invalid or expired challenge token")

        if challenge.verified_at:
            raise AuthenticationError("Challenge already used")

        # Check attempts
        if challenge.attempts >= self.config.max_verification_attempts:
            raise AuthenticationError("Maximum verification attempts exceeded")

        device = await self._get_device(challenge.device_id)
        if not device or device.status != MFAStatus.ACTIVE:
            raise AuthenticationError("Device not found or inactive")

        # Increment attempts
        challenge.attempts += 1

        # Verify code
        is_valid = False

        if device.method == MFAMethod.TOTP:
            is_valid = await self._verify_totp_code(device.secret, verification_request.code)
        elif device.method in [MFAMethod.SMS, MFAMethod.EMAIL]:
            is_valid = challenge.verification_code == verification_request.code
        elif device.method == MFAMethod.BACKUP_CODE:
            is_valid = await self._verify_backup_code(device, verification_request.code)

        if is_valid:
            # Mark challenge as verified
            challenge.verified_at = datetime.now(UTC)
            device.last_used = datetime.now(UTC)
            device.failure_count = 0  # Reset failure count on success

            await self.db.commit()

            # Generate MFA-verified JWT claims
            mfa_claims = {
                "mfa_verified": True,
                "mfa_method": device.method,
                "mfa_device_id": str(device.id),
                "mfa_timestamp": int(datetime.now(UTC).timestamp()),
            }

            return {"success": True, "mfa_claims": mfa_claims, "user_id": str(challenge.user_id)}
        # Handle failed attempt
        device.failure_count += 1

        # Lock device if too many failures
        if device.failure_count >= self.config.max_verification_attempts:
            device.locked_until = datetime.now(UTC) + timedelta(
                minutes=self.config.lockout_duration_minutes
            )

        await self.db.commit()

        attempts_remaining = self.config.max_verification_attempts - challenge.attempts
        raise AuthenticationError(
            f"Invalid verification code. {attempts_remaining} attempts remaining."
        )

    async def verify_backup_code(self, user_id: str, backup_code: str) -> dict[str, Any]:
        """Verify backup code for emergency access."""
        devices = await self._get_active_user_devices(user_id)

        for device in devices:
            if device.backup_codes and await self._verify_backup_code(device, backup_code):
                # Remove used backup code
                backup_codes = device.backup_codes.split(",")
                backup_codes.remove(backup_code)
                device.backup_codes = ",".join(backup_codes)
                device.last_used = datetime.now(UTC)

                await self.db.commit()

                # Generate MFA-verified JWT claims
                mfa_claims = {
                    "mfa_verified": True,
                    "mfa_method": MFAMethod.BACKUP_CODE,
                    "mfa_device_id": str(device.id),
                    "mfa_timestamp": int(datetime.now(UTC).timestamp()),
                }

                return {
                    "success": True,
                    "mfa_claims": mfa_claims,
                    "user_id": user_id,
                    "backup_codes_remaining": len(backup_codes),
                }

        raise AuthenticationError("Invalid backup code")

    async def get_user_devices(self, user_id: str) -> list[dict[str, Any]]:
        """Get user's MFA devices."""
        devices = await self._get_user_devices(user_id)

        return [
            {
                "id": str(device.id),
                "name": device.device_name,
                "method": device.method,
                "status": device.status,
                "is_primary": device.is_primary,
                "last_used": device.last_used.isoformat() if device.last_used else None,
                "created_at": device.created_at.isoformat(),
                "phone_hint": self._mask_phone_number(device.phone_number)
                if device.phone_number
                else None,
                "email_hint": self._mask_email(device.email) if device.email else None,
            }
            for device in devices
        ]

    async def delete_device(self, user_id: str, device_id: str) -> bool:
        """Delete MFA device."""
        device = await self._get_device(device_id)

        if not device or str(device.user_id) != user_id:
            raise AuthenticationError("Device not found")

        # Don't allow deleting the last active device
        active_devices = await self._get_active_user_devices(user_id)
        if len(active_devices) == 1 and device.id == active_devices[0].id:
            raise ValidationError("Cannot delete the last active MFA device")

        await self.db.delete(device)
        await self.db.commit()

        return True

    async def regenerate_backup_codes(self, user_id: str, device_id: str) -> list[str]:
        """Regenerate backup codes for a device."""
        device = await self._get_device(device_id)

        if not device or str(device.user_id) != user_id:
            raise AuthenticationError("Device not found")

        # Generate new backup codes
        backup_codes = self._generate_backup_codes()
        device.backup_codes = ",".join(backup_codes)

        await self.db.commit()

        return backup_codes

    # Helper methods

    async def _verify_totp_code(self, secret: str, code: str) -> bool:
        """Verify TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=self.config.totp_window)

    async def _verify_backup_code(self, device: MFADevice, code: str) -> bool:
        """Verify backup code."""
        if not device.backup_codes:
            return False
        backup_codes = device.backup_codes.split(",")
        return code in backup_codes

    def _generate_verification_code(self, length: int = 6) -> str:
        """Generate random verification code."""
        return "".join(secrets.choice(string.digits) for _ in range(length))

    def _generate_backup_codes(self) -> list[str]:
        """Generate backup codes."""
        codes = []
        for _ in range(self.config.backup_codes_count):
            # Generate 8-character alphanumeric code
            code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            codes.append(code)
        return codes

    def _mask_phone_number(self, phone: str) -> str:
        """Mask phone number for privacy."""
        if not phone or len(phone) < 6:
            return phone
        return phone[:-4] + "****"

    def _mask_email(self, email: str) -> str:
        """Mask email address for privacy."""
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            return f"{local}***@{domain}"
        return f"{local[:2]}***@{domain}"

    async def _get_challenge(self, challenge_token: str) -> MFAChallenge | None:
        """Get MFA challenge by token."""
        return (
            self.db.query(MFAChallenge)
            .filter(
                MFAChallenge.challenge_token == challenge_token,
                MFAChallenge.expires_at > datetime.now(UTC),
            )
            .first()
        )

    async def _get_device(self, device_id: str) -> MFADevice | None:
        """Get MFA device by ID."""
        return self.db.query(MFADevice).filter(MFADevice.id == device_id).first()

    async def _get_user_devices(self, user_id: str) -> list[MFADevice]:
        """Get all devices for a user."""
        return (
            self.db.query(MFADevice)
            .filter(MFADevice.user_id == user_id)
            .order_by(MFADevice.created_at.desc())
            .all()
        )

    async def _get_active_user_devices(self, user_id: str) -> list[MFADevice]:
        """Get active devices for a user."""
        return (
            self.db.query(MFADevice)
            .filter(MFADevice.user_id == user_id, MFADevice.status == MFAStatus.ACTIVE)
            .order_by(MFADevice.is_primary.desc(), MFADevice.created_at.desc())
            .all()
        )


# Utility functions for JWT integration


def extract_mfa_claims(token_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract MFA claims from JWT token payload."""
    if not token_payload.get("mfa_verified"):
        return None

    return {
        "verified": token_payload.get("mfa_verified"),
        "method": token_payload.get("mfa_method"),
        "device_id": token_payload.get("mfa_device_id"),
        "timestamp": token_payload.get("mfa_timestamp"),
    }


def is_mfa_required_for_scope(scope: str, mfa_required_scopes: list[str]) -> bool:
    """Check if MFA is required for given scope."""
    return scope in mfa_required_scopes


def is_mfa_token_valid(mfa_claims: dict[str, Any], max_age_seconds: int = 3600) -> bool:
    """Check if MFA token is still valid based on age."""
    if not mfa_claims or not mfa_claims.get("timestamp"):
        return False

    mfa_timestamp = mfa_claims["timestamp"]
    current_timestamp = int(datetime.now(UTC).timestamp())

    return (current_timestamp - mfa_timestamp) <= max_age_seconds
