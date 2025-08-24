"""
Phone SDK - verification (OTP), SMS delivery.
"""

import secrets
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import (
    VerificationError,
    VerificationExpiredError,
    VerificationFailedError,
)
from ..models.verification import PhoneVerification, VerificationStatus
from ..utils.datetime_compat import utcnow


class PhoneVerificationService:
    """In-memory service for phone verification operations."""

    def __init__(self):
        """  Init   operation."""
        self._verifications: Dict[UUID, PhoneVerification] = {}
        self._phone_verifications: Dict[str, List[UUID]] = {}

    async def create_verification(self, **kwargs) -> PhoneVerification:
        """Create phone verification."""
        # Generate 6-digit OTP
        verification_code = f"{secrets.randbelow(1000000):06d}"

        verification = PhoneVerification(verification_code=verification_code, **kwargs)

        self._verifications[verification.id] = verification

        phone_key = verification.get_formatted_number()
        if phone_key not in self._phone_verifications:
            self._phone_verifications[phone_key] = []
        self._phone_verifications[phone_key].append(verification.id)

        return verification

    async def get_verification(
        self, verification_id: UUID
    ) -> Optional[PhoneVerification]:
        """Get verification by ID."""
        return self._verifications.get(verification_id)

    async def verify_code(self, verification_id: UUID, code: str) -> bool:
        """Verify OTP code."""
        verification = self._verifications.get(verification_id)
        if not verification:
            return False

        verification.attempts_count += 1
        verification.last_attempt_at = verification.last_attempt_at.__class__.utcnow()

        if not verification.is_valid():
            return False

        if verification.verification_code == code:
            verification.status = VerificationStatus.VERIFIED
            verification.verified_at = verification.verified_at.__class__.utcnow()
            return True

        return False


class PhoneSDK:
    """Small, composable SDK for phone verification with OTP and SMS delivery."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = PhoneVerificationService()

    async def send_verification_sms(
        self,
        phone_number: str,
        country_code: Optional[str] = None,
        contact_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send verification SMS with OTP."""
        verification = await self._service.create_verification(
            tenant_id=self.tenant_id,
            phone_number=phone_number,
            country_code=country_code,
            contact_id=UUID(contact_id) if contact_id else None,
            account_id=UUID(account_id) if account_id else None,
        )

        # Simulate SMS sending
        verification.sms_sent_at = verification.sms_sent_at.__class__.utcnow()
        verification.sms_delivered_at = verification.sms_delivered_at.__class__.utcnow()

        return {
            "verification_id": str(verification.id),
            "phone_number": verification.get_formatted_number(),
            "status": verification.status.value,
            "expires_at": verification.expires_at.isoformat(),
            "sms_sent": verification.sms_sent_at is not None,
            "created_at": verification.created_at.isoformat(),
        }

    async def verify_phone_code(
        self, verification_id: str, code: str
    ) -> Dict[str, Any]:
        """Verify phone OTP code."""
        verification = await self._service.get_verification(UUID(verification_id))
        if not verification or verification.tenant_id != self.tenant_id:
            raise VerificationError("Verification not found")

        if verification.is_expired():
            raise VerificationExpiredError("phone")

        is_valid = await self._service.verify_code(UUID(verification_id), code)

        if not is_valid:
            attempts_remaining = verification.max_attempts - verification.attempts_count
            if attempts_remaining <= 0:
                verification.status = VerificationStatus.FAILED
            raise VerificationFailedError("phone", attempts_remaining)

        return {
            "verification_id": str(verification.id),
            "phone_number": verification.get_formatted_number(),
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
        """Get phone verification status."""
        verification = await self._service.get_verification(UUID(verification_id))
        if not verification or verification.tenant_id != self.tenant_id:
            return None

        return {
            "verification_id": str(verification.id),
            "phone_number": verification.get_formatted_number(),
            "status": verification.status.value,
            "attempts_count": verification.attempts_count,
            "max_attempts": verification.max_attempts,
            "expires_at": verification.expires_at.isoformat(),
            "is_expired": verification.is_expired(),
            "is_valid": verification.is_valid(),
            "sms_sent_at": (
                verification.sms_sent_at.isoformat()
                if verification.sms_sent_at
                else None
            ),
            "sms_delivered_at": (
                verification.sms_delivered_at.isoformat()
                if verification.sms_delivered_at
                else None
            ),
            "sms_failed_at": (
                verification.sms_failed_at.isoformat()
                if verification.sms_failed_at
                else None
            ),
            "sms_failure_reason": verification.sms_failure_reason,
            "created_at": verification.created_at.isoformat(),
            "verified_at": (
                verification.verified_at.isoformat()
                if verification.verified_at
                else None
            ),
        }
