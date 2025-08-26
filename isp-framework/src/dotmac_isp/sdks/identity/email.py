"""
Email SDK - verification (OTP), deliverability results.
"""

import secrets
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime, timezone

from ..core.exceptions import (
    VerificationError,
    VerificationExpiredError,
    VerificationFailedError,
)
from ..models.verification import (
    DeliverabilityStatus,
    EmailVerification,
    VerificationStatus,
)
from ..utils.datetime_compat import utcnow


class EmailVerificationService:
    """In-memory service for email verification operations."""

    def __init__(self):
        """  Init   operation."""
        self._verifications: Dict[UUID, EmailVerification] = {}
        self._email_verifications: Dict[str, List[UUID]] = {}

    async def create_verification(self, **kwargs) -> EmailVerification:
        """Create email verification."""
        # Generate 6-digit OTP
        verification_code = f"{secrets.randbelow(1000000):06d}"

        verification = EmailVerification(verification_code=verification_code, **kwargs)

        self._verifications[verification.id] = verification

        if verification.email not in self._email_verifications:
            self._email_verifications[verification.email] = []
        self._email_verifications[verification.email].append(verification.id)

        return verification

    async def get_verification(
        self, verification_id: UUID
    ) -> Optional[EmailVerification]:
        """Get verification by ID."""
        return self._verifications.get(verification_id)

    async def verify_code(self, verification_id: UUID, code: str) -> bool:
        """Verify OTP code."""
        verification = self._verifications.get(verification_id)
        if not verification:
            return False

        verification.attempts_count += 1
        verification.last_attempt_at = datetime.now(timezone.utc)

        if not verification.is_valid():
            return False

        if verification.verification_code == code:
            verification.status = VerificationStatus.VERIFIED
            verification.verified_at = datetime.now(timezone.utc)
            return True

        return False


class EmailSDK:
    """Small, composable SDK for email verification with OTP and deliverability."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = EmailVerificationService()

    async def send_verification_email(
        self,
        email: str,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send verification email with OTP."""
        verification = await self._service.create_verification(
            tenant_id=self.tenant_id,
            email=email,
            contact_id=UUID(contact_id) if contact_id else None,
            account_id=UUID(account_id) if account_id else None,
        )

        # Simulate email sending
        verification.delivery_attempted_at = (
            datetime.now(timezone.utc)
        )
        verification.deliverability_status = DeliverabilityStatus.DELIVERED
        verification.delivery_confirmed_at = (
            datetime.now(timezone.utc)
        )

        return {
            "verification_id": str(verification.id),
            "email": verification.email,
            "status": verification.status.value,
            "expires_at": verification.expires_at.isoformat(),
            "deliverability_status": (
                verification.deliverability_status.value
                if verification.deliverability_status
                else None
            ),
            "created_at": verification.created_at.isoformat(),
        }

    async def verify_email_code(
        self, verification_id: str, code: str
    ) -> Dict[str, Any]:
        """Verify email OTP code."""
        verification = await self._service.get_verification(UUID(verification_id))
        if not verification or verification.tenant_id != self.tenant_id:
            raise VerificationError("Verification not found")

        if verification.is_expired():
            raise VerificationExpiredError("email")

        is_valid = await self._service.verify_code(UUID(verification_id), code)

        if not is_valid:
            attempts_remaining = verification.max_attempts - verification.attempts_count
            if attempts_remaining <= 0:
                verification.status = VerificationStatus.FAILED
            raise VerificationFailedError("email", attempts_remaining)

        return {
            "verification_id": str(verification.id),
            "email": verification.email,
            "status": verification.status.value,
            "verified_at": (
                verification.verified_at.isoformat()
                if verification.verified_at
                else None
            ),
            "is_verified": verification.status == VerificationStatus.VERIFIED,
        }

    async def get_verification_status(
        self, verification_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get email verification status."""
        verification = await self._service.get_verification(UUID(verification_id))
        if not verification or verification.tenant_id != self.tenant_id:
            return None

        return {
            "verification_id": str(verification.id),
            "email": verification.email,
            "status": verification.status.value,
            "attempts_count": verification.attempts_count,
            "max_attempts": verification.max_attempts,
            "expires_at": verification.expires_at.isoformat(),
            "is_expired": verification.is_expired(),
            "is_valid": verification.is_valid(),
            "deliverability_status": (
                verification.deliverability_status.value
                if verification.deliverability_status
                else None
            ),
            "bounce_reason": verification.bounce_reason,
            "created_at": verification.created_at.isoformat(),
            "verified_at": (
                verification.verified_at.isoformat()
                if verification.verified_at
                else None
            ),
        }

    async def check_email_deliverability(self, email: str) -> Dict[str, Any]:
        """Check email deliverability results."""
        # Simulate deliverability check
        # In real implementation, this would integrate with email validation services

        is_valid_format = "@" in email and "." in email.split("@")[1]
        deliverability_status = (
            DeliverabilityStatus.DELIVERED
            if is_valid_format
            else DeliverabilityStatus.REJECTED
        )

        return {
            "email": email,
            "is_deliverable": deliverability_status == DeliverabilityStatus.DELIVERED,
            "deliverability_status": deliverability_status.value,
            "bounce_reason": None if is_valid_format else "Invalid email format",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
