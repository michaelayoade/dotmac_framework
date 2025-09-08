"""Voucher authentication provider for captive portal."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from dotmac.core.exceptions import ValidationError
from dotmac_isp.modules.identity.services.user_service import UserService

from ..models import VoucherStatus
from ..repository import VoucherRepository
from ..schemas import AuthenticationRequest, VoucherAuthRequest
from .base import AuthenticationResult, BaseAuthProvider

logger = logging.getLogger(__name__)


class VoucherAuthProvider(BaseAuthProvider):
    """Voucher-based authentication provider for prepaid access."""

    def __init__(self, db_session, tenant_id: str, config: dict[str, Any]):
        """Initialize voucher auth provider."""
        super().__init__(db_session, tenant_id, config)
        self.voucher_repo = VoucherRepository(db_session, tenant_id)
        self.user_service = UserService(db_session, tenant_id)

        # Configuration options
        self.allow_multi_device = config.get("allow_multi_device", True)
        self.create_user_account = config.get("create_user_account", False)

    async def authenticate(self, request: AuthenticationRequest) -> AuthenticationResult:
        """Authenticate user via voucher code."""
        if not isinstance(request, VoucherAuthRequest):
            return AuthenticationResult(
                success=False,
                error_message="Invalid request type for voucher authentication",
            )
        try:
            # Validate voucher code format
            if not self._is_valid_voucher_code(request.voucher_code):
                return AuthenticationResult(success=False, error_message="Invalid voucher code format")
            # Find voucher
            voucher = self.voucher_repo.get_voucher_by_code(request.voucher_code, request.portal_id)
            if not voucher:
                return AuthenticationResult(success=False, error_message="Invalid voucher code")
            # Validate voucher
            validation_result = self._validate_voucher(voucher)
            if not validation_result["valid"]:
                return AuthenticationResult(success=False, error_message=validation_result["reason"])
            # Check device limits
            device_check = await self._check_device_limits(voucher, request)
            if not device_check["allowed"]:
                return AuthenticationResult(success=False, error_message=device_check["reason"])
            # Redeem voucher (increment usage count)
            user_id = None
            if self.create_user_account:
                user = await self._create_guest_user(voucher, request)
                if user:
                    user_id = str(user.id)

            # Update voucher redemption
            success = self.voucher_repo.redeem_voucher(voucher.id, user_id)
            if not success:
                return AuthenticationResult(success=False, error_message="Failed to redeem voucher")
            # Create session data with voucher limits
            session_data = self._create_session_data(
                {
                    "voucher_code": request.voucher_code,
                    "voucher_id": str(voucher.id),
                    "duration_minutes": voucher.duration_minutes,
                    "data_limit_mb": voucher.data_limit_mb,
                    "bandwidth_limit_down": voucher.bandwidth_limit_down,
                    "bandwidth_limit_up": voucher.bandwidth_limit_up,
                    "auth_method": "voucher",
                    "price_paid": voucher.price,
                    "currency": voucher.currency,
                }
            )

            return AuthenticationResult(success=True, user_id=user_id, session_data=session_data)
        except Exception as e:
            logger.error(f"Voucher authentication failed: {e}")
            return AuthenticationResult(success=False, error_message="Voucher authentication failed")

    async def prepare_authentication(self, request: AuthenticationRequest) -> dict[str, Any]:
        """Prepare voucher authentication (no preparation needed)."""
        if not isinstance(request, VoucherAuthRequest):
            raise ValidationError("Invalid request type for voucher authentication")

        return {
            "preparation_required": False,
            "message": "Enter your voucher code to access the network",
        }

    def validate_request(self, request: AuthenticationRequest) -> bool:
        """Validate voucher authentication request."""
        if not isinstance(request, VoucherAuthRequest):
            return False

        if not request.voucher_code:
            return False

        if not self._is_valid_voucher_code(request.voucher_code):
            return False

        return True

    def _validate_voucher(self, voucher) -> dict[str, Any]:
        """Validate voucher eligibility."""
        now = datetime.now(timezone.utc)

        # Check voucher status
        if voucher.voucher_status != VoucherStatus.ACTIVE:
            return {
                "valid": False,
                "reason": f"Voucher is {voucher.voucher_status.value}",
            }

        # Check if voucher is within validity period
        if voucher.valid_from and now < voucher.valid_from:
            return {"valid": False, "reason": "Voucher is not yet valid"}

        if voucher.valid_until and now > voucher.valid_until:
            return {"valid": False, "reason": "Voucher has expired"}

        # Check device usage limits
        if voucher.max_devices > 0 and voucher.redemption_count >= voucher.max_devices:
            return {"valid": False, "reason": "Voucher usage limit exceeded"}

        return {"valid": True}

    async def _check_device_limits(self, voucher, request: VoucherAuthRequest) -> dict[str, Any]:
        """Check if device can use this voucher."""
        # If multi-device is allowed and voucher supports it, allow
        if self.allow_multi_device and voucher.max_devices > 1:
            return {"allowed": True}

        # If voucher has been redeemed and max devices is 1, check if same device
        if voucher.redemption_count > 0 and voucher.max_devices == 1:
            # In a real implementation, you'd check device fingerprinting
            # For now, allow if not at max redemptions yet
            if voucher.redemption_count < voucher.max_devices:
                return {"allowed": True}
            else:
                return {
                    "allowed": False,
                    "reason": "Voucher already used on another device",
                }

        return {"allowed": True}

    async def _create_guest_user(self, voucher, request: VoucherAuthRequest) -> Optional[Any]:
        """Create a guest user account for voucher authentication."""
        try:
            user_data = {
                "username": f"voucher_user_{voucher.code}",
                "is_active": True,
                "user_type": "guest",
                "source": "captive_portal_voucher",
            }

            user = await self.user_service.create_user(user_data)
            return user

        except Exception as e:
            logger.error(f"Failed to create guest user for voucher: {e}")
            return None

    def _is_valid_voucher_code(self, code: str) -> bool:
        """Basic voucher code format validation."""
        if not code:
            return False

        # Basic length and character validation
        if len(code) < 4 or len(code) > 20:
            return False

        # Allow alphanumeric codes (could be customized per implementation)
        return code.replace("-", "").replace("_", "").isalnum()

    async def get_voucher_info(self, voucher_code: str, portal_id: str) -> Optional[dict[str, Any]]:
        """Get voucher information without redeeming (for preview)."""
        try:
            voucher = self.voucher_repo.get_voucher_by_code(voucher_code, portal_id)

            if not voucher:
                return None

            validation_result = self._validate_voucher(voucher)

            return {
                "code": voucher.code,
                "valid": validation_result["valid"],
                "reason": validation_result.get("reason"),
                "duration_minutes": voucher.duration_minutes,
                "data_limit_mb": voucher.data_limit_mb,
                "bandwidth_limit_down": voucher.bandwidth_limit_down,
                "bandwidth_limit_up": voucher.bandwidth_limit_up,
                "max_devices": voucher.max_devices,
                "redemptions_remaining": max(0, voucher.max_devices - voucher.redemption_count),
                "price": voucher.price,
                "currency": voucher.currency,
                "valid_until": (voucher.valid_until.isoformat() if voucher.valid_until else None),
            }

        except Exception as e:
            logger.error(f"Failed to get voucher info: {e}")
            return None
