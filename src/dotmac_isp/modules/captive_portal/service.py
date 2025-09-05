"""
Captive Portal Service Layer

Provides business logic for captive portal operations with DRY patterns
leveraging existing base services and integrating with other ISP modules.
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from dotmac.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    EntityNotFoundError,
    ServiceError,
    ValidationError,
)
from dotmac_shared.logging import get_logger
from dotmac_shared.services.base import BaseTenantService

# Import existing ISP services for integration
# Note: These integrations can be added once the services are properly implemented
from .models import (
    AuthMethod,
    AuthMethodType,
    CaptivePortalConfig,
    CaptivePortalSession,
    PortalStatus,
    SessionStatus,
    Voucher,
    VoucherStatus,
)
from .repository import (
    AuthMethodRepository,
    CaptivePortalConfigRepository,
    CaptivePortalSessionRepository,
    PortalCustomizationRepository,
    PortalUsageStatsRepository,
    VoucherBatchRepository,
    VoucherRepository,
)
from .schemas import (
    AuthenticationRequest,
    AuthenticationResponse,
    CaptivePortalConfigCreate,
    CaptivePortalConfigResponse,
    CaptivePortalConfigUpdate,
    EmailAuthRequest,
    RadiusAuthRequest,
    SessionResponse,
    SessionTerminateRequest,
    SocialAuthRequest,
    VoucherAuthRequest,
    VoucherCreateRequest,
    VoucherResponse,
)

logger = get_logger(__name__)

# Import existing ISP services for integration
# Note: These integrations can be added once the services are properly implemented
try:
    from dotmac_isp.modules.billing.service import BillingService
    from dotmac_isp.modules.identity.service import CustomerService
    from dotmac_isp.modules.identity.services.user_service import UserService

    INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Integration services not available: {e}")
    INTEGRATIONS_AVAILABLE = False
    # Use placeholder classes for development
    CustomerService = None
    UserService = None
    BillingService = None


class CaptivePortalService(BaseTenantService):
    """
    Captive Portal Service providing WiFi hotspot authentication and session management.

    Integrates with existing ISP modules:
    - Identity module for user/customer management
    - Billing module for payment processing
    - Analytics module for usage reporting
    """

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(db, tenant_id)

        # Initialize repositories
        self.portal_repo = CaptivePortalConfigRepository(db, tenant_id)
        self.session_repo = CaptivePortalSessionRepository(db, tenant_id)
        self.auth_method_repo = AuthMethodRepository(db, tenant_id)
        self.voucher_repo = VoucherRepository(db, tenant_id)
        self.voucher_batch_repo = VoucherBatchRepository(db, tenant_id)
        self.customization_repo = PortalCustomizationRepository(db, tenant_id)
        self.stats_repo = PortalUsageStatsRepository(db, tenant_id)

        # Initialize integrated services if available
        if INTEGRATIONS_AVAILABLE:
            self.user_service = UserService(db, tenant_id) if UserService else None
            self.customer_service = (
                CustomerService(db, tenant_id) if CustomerService else None
            )
            self.billing_service = (
                BillingService(db, tenant_id) if BillingService else None
            )
        else:
            self.user_service = None
            self.customer_service = None
            self.billing_service = None

    # Portal Configuration Management

    async def create_portal(
        self, portal_data: CaptivePortalConfigCreate
    ) -> CaptivePortalConfigResponse:
        """Create a new captive portal configuration."""
        try:
            # Validate SSID availability
            if not self.portal_repo.check_ssid_availability(portal_data.ssid):
                raise BusinessRuleError(f"SSID '{portal_data.ssid}' is already in use")

            # Validate customer exists if provided and service is available
            if portal_data.customer_id and self.customer_service:
                try:
                    customer = await self.customer_service.get_customer_by_id(
                        portal_data.customer_id
                    )
                    if not customer:
                        raise ValidationError("Invalid customer ID")
                except Exception:
                    # If customer service is not available, log warning but allow creation
                    logger.warning(
                        f"Could not validate customer {portal_data.customer_id}: service unavailable"
                    )

            # Create portal configuration
            portal_dict = portal_data.model_dump(exclude_unset=True)
            portal_dict["id"] = str(uuid4())
            portal_dict["tenant_id"] = self.tenant_id
            portal_dict["portal_status"] = PortalStatus.ACTIVE

            portal = CaptivePortalConfig(**portal_dict)
            created_portal = self.portal_repo.create(portal)

            # Create default authentication methods if not specified
            if not portal_data.auth_methods:
                await self._create_default_auth_methods(created_portal.id)

            logger.info(
                f"Created captive portal {created_portal.id} for tenant {self.tenant_id}"
            )
            return CaptivePortalConfigResponse.model_validate(created_portal)

        except Exception as e:
            logger.error(f"Error creating portal: {e}")
            raise ServiceError(f"Failed to create portal: {str(e)}") from e

    async def get_portal(self, portal_id: str) -> Optional[CaptivePortalConfigResponse]:
        """Get portal configuration by ID."""
        try:
            portal = self.portal_repo.get_by_id(portal_id)
            if not portal:
                raise EntityNotFoundError(f"Portal {portal_id} not found")

            return CaptivePortalConfigResponse.model_validate(portal)
        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error retrieving portal {portal_id}: {e}")
            raise ServiceError(f"Failed to retrieve portal: {str(e)}") from e

    async def update_portal(
        self, portal_id: str, portal_updates: CaptivePortalConfigUpdate
    ) -> Optional[CaptivePortalConfigResponse]:
        """Update portal configuration."""
        try:
            portal = self.portal_repo.get_by_id(portal_id)
            if not portal:
                raise EntityNotFoundError(f"Portal {portal_id} not found")

            # Validate SSID availability if being updated
            update_data = portal_updates.model_dump(exclude_unset=True)
            if "ssid" in update_data:
                if not self.portal_repo.check_ssid_availability(
                    update_data["ssid"], portal_id
                ):
                    raise BusinessRuleError(
                        f"SSID '{update_data['ssid']}' is already in use"
                    )

            updated_portal = self.portal_repo.update(portal_id, update_data)

            logger.info(
                f"Updated captive portal {portal_id} for tenant {self.tenant_id}"
            )
            return CaptivePortalConfigResponse.model_validate(updated_portal)

        except (EntityNotFoundError, BusinessRuleError):
            raise
        except Exception as e:
            logger.error(f"Error updating portal {portal_id}: {e}")
            raise ServiceError(f"Failed to update portal: {str(e)}") from e

    async def delete_portal(self, portal_id: str) -> bool:
        """Delete portal configuration."""
        try:
            portal = self.portal_repo.get_by_id(portal_id)
            if not portal:
                raise EntityNotFoundError(f"Portal {portal_id} not found")

            # Check for active sessions
            active_sessions = self.session_repo.get_active_session_count(portal_id)
            if active_sessions > 0:
                raise BusinessRuleError(
                    f"Cannot delete portal with {active_sessions} active sessions"
                )

            # Soft delete
            self.portal_repo.soft_delete(portal_id)

            logger.info(
                f"Deleted captive portal {portal_id} for tenant {self.tenant_id}"
            )
            return True

        except (EntityNotFoundError, BusinessRuleError):
            raise
        except Exception as e:
            logger.error(f"Error deleting portal {portal_id}: {e}")
            raise ServiceError(f"Failed to delete portal: {str(e)}") from e

    # Authentication Methods

    async def authenticate_user(
        self, auth_request: AuthenticationRequest
    ) -> AuthenticationResponse:
        """Authenticate user based on the authentication method."""
        try:
            portal = self.portal_repo.get_by_id(auth_request.portal_id)
            if not portal or portal.portal_status != PortalStatus.ACTIVE:
                raise AuthenticationError("Portal not available for authentication")

            # Check session limits
            active_sessions = self.session_repo.get_active_session_count(
                auth_request.portal_id
            )
            if active_sessions >= portal.max_concurrent_sessions:
                raise BusinessRuleError(
                    "Portal has reached maximum concurrent sessions"
                )

            # Route to appropriate authentication method
            if isinstance(auth_request, EmailAuthRequest):
                return await self._authenticate_email(auth_request, portal)
            elif isinstance(auth_request, SocialAuthRequest):
                return await self._authenticate_social(auth_request, portal)
            elif isinstance(auth_request, VoucherAuthRequest):
                return await self._authenticate_voucher(auth_request, portal)
            elif isinstance(auth_request, RadiusAuthRequest):
                return await self._authenticate_radius(auth_request, portal)
            else:
                raise ValidationError("Unsupported authentication method")

        except (AuthenticationError, BusinessRuleError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            raise ServiceError(f"Authentication failed: {str(e)}") from e

    async def _authenticate_email(
        self, auth_request: EmailAuthRequest, portal: CaptivePortalConfig
    ) -> AuthenticationResponse:
        """Handle email-based authentication."""
        try:
            # Check if user exists or create new one (if user service available)
            user_id = None
            if self.user_service:
                try:
                    user = await self.user_service.get_user_by_email(auth_request.email)
                    if not user:
                        # Create new user
                        user_data = {
                            "email": auth_request.email,
                            "first_name": auth_request.first_name,
                            "last_name": auth_request.last_name,
                            "user_type": "guest",
                            "is_active": True,
                        }
                        user = await self.user_service.create_user(user_data)
                    user_id = user.id if user else None
                except Exception:
                    logger.warning(
                        "User service unavailable, proceeding without user linkage"
                    )
                    user_id = None

            # Create session
            session = await self._create_session(
                portal=portal,
                user_id=user_id,
                auth_method=AuthMethodType.EMAIL,
                client_ip=auth_request.client_ip,
                client_mac=auth_request.client_mac,
                user_agent=auth_request.user_agent,
                auth_data={"email": auth_request.email},
            )

            return AuthenticationResponse(
                success=True,
                session_id=session.id,
                session_token=session.session_token,
                expires_at=session.expires_at,
                user_id=user_id,
            )

        except Exception as e:
            logger.error(f"Email authentication failed: {e}")
            raise AuthenticationError(f"Email authentication failed: {str(e)}") from e

    async def _authenticate_social(
        self, auth_request: SocialAuthRequest, portal: CaptivePortalConfig
    ) -> AuthenticationResponse:
        """Handle social media authentication."""
        try:
            # This would integrate with OAuth providers
            # For now, return a simplified implementation

            # Generate session for social auth
            session = await self._create_session(
                portal=portal,
                auth_method=AuthMethodType.SOCIAL,
                client_ip=auth_request.client_ip,
                client_mac=auth_request.client_mac,
                user_agent=auth_request.user_agent,
                auth_data={
                    "provider": auth_request.provider,
                    "code": auth_request.code,
                },
            )

            return AuthenticationResponse(
                success=True,
                session_id=session.id,
                session_token=session.session_token,
                expires_at=session.expires_at,
            )

        except Exception as e:
            logger.error(f"Social authentication failed: {e}")
            raise AuthenticationError(f"Social authentication failed: {str(e)}") from e

    async def _authenticate_voucher(
        self, auth_request: VoucherAuthRequest, portal: CaptivePortalConfig
    ) -> AuthenticationResponse:
        """Handle voucher-based authentication."""
        try:
            voucher = self.voucher_repo.find_by_code(
                auth_request.voucher_code, auth_request.portal_id
            )

            if not voucher or not voucher.is_valid_for_redemption:
                raise AuthenticationError("Invalid or expired voucher")

            # Redeem voucher
            self.voucher_repo.redeem_voucher(
                voucher.id, None
            )  # No user ID for voucher auth

            # Create session with voucher limits
            session = await self._create_session(
                portal=portal,
                auth_method=AuthMethodType.VOUCHER,
                client_ip=auth_request.client_ip,
                client_mac=auth_request.client_mac,
                user_agent=auth_request.user_agent,
                auth_data={"voucher_code": auth_request.voucher_code},
                duration_override=voucher.duration_minutes,
            )

            return AuthenticationResponse(
                success=True,
                session_id=session.id,
                session_token=session.session_token,
                expires_at=session.expires_at,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Voucher authentication failed: {e}")
            raise AuthenticationError(f"Voucher authentication failed: {str(e)}") from e

    async def _authenticate_radius(
        self, auth_request: RadiusAuthRequest, portal: CaptivePortalConfig
    ) -> AuthenticationResponse:
        """Handle RADIUS authentication."""
        try:
            # This would integrate with RADIUS server
            # For now, return a simplified implementation

            # Validate credentials against RADIUS server
            # radius_valid = await self._validate_radius_credentials(
            #     auth_request.username, auth_request.password
            # )

            # For demo purposes, accept any non-empty credentials
            if not auth_request.username or not auth_request.password:
                raise AuthenticationError("Invalid RADIUS credentials")

            session = await self._create_session(
                portal=portal,
                auth_method=AuthMethodType.RADIUS,
                client_ip=auth_request.client_ip,
                client_mac=auth_request.client_mac,
                user_agent=auth_request.user_agent,
                auth_data={"username": auth_request.username},
            )

            return AuthenticationResponse(
                success=True,
                session_id=session.id,
                session_token=session.session_token,
                expires_at=session.expires_at,
            )

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"RADIUS authentication failed: {e}")
            raise AuthenticationError(f"RADIUS authentication failed: {str(e)}") from e

    # Session Management

    async def _create_session(
        self,
        portal: CaptivePortalConfig,
        auth_method: AuthMethodType,
        user_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        client_mac: Optional[str] = None,
        user_agent: Optional[str] = None,
        auth_data: Optional[dict] = None,
        duration_override: Optional[int] = None,
    ) -> CaptivePortalSession:
        """Create a new captive portal session."""
        try:
            # Generate unique session token
            session_token = self._generate_session_token()

            # Calculate expiration
            duration_minutes = duration_override or (portal.session_timeout // 60)
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=duration_minutes
            )

            session_data = {
                "id": str(uuid4()),
                "tenant_id": self.tenant_id,
                "session_token": session_token,
                "portal_id": portal.id,
                "user_id": user_id,
                "customer_id": customer_id or portal.customer_id,
                "client_ip": client_ip,
                "client_mac": client_mac,
                "user_agent": user_agent,
                "auth_method_used": auth_method,
                "auth_data": auth_data or {},
                "expires_at": expires_at,
                "session_status": SessionStatus.ACTIVE,
            }

            session = CaptivePortalSession(**session_data)
            created_session = self.session_repo.create(session)

            logger.info(f"Created session {created_session.id} for portal {portal.id}")
            return created_session

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise ServiceError(f"Failed to create session: {str(e)}") from e

    async def validate_session(self, session_token: str) -> Optional[SessionResponse]:
        """Validate a session token and return session info if valid."""
        try:
            session = self.session_repo.find_active_session(session_token=session_token)
            if not session:
                return None

            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            self.session_repo.update(
                session.id, {"last_activity": session.last_activity}
            )

            return SessionResponse.model_validate(session)

        except Exception as e:
            logger.error(f"Error validating session: {e}")
            raise ServiceError(f"Failed to validate session: {str(e)}") from e

    async def terminate_session(
        self, session_id: str, request: SessionTerminateRequest
    ) -> bool:
        """Terminate a user session."""
        try:
            session = self.session_repo.get_by_id(session_id)
            if not session:
                raise EntityNotFoundError(f"Session {session_id} not found")

            # Update session status
            update_data = {
                "session_status": SessionStatus.TERMINATED,
                "end_time": datetime.now(timezone.utc),
                "termination_reason": request.reason,
            }

            self.session_repo.update(session_id, update_data)

            logger.info(f"Terminated session {session_id}: {request.reason}")
            return True

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            raise ServiceError(f"Failed to terminate session: {str(e)}") from e

    async def get_active_sessions(
        self, portal_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> list[SessionResponse]:
        """Get active sessions with optional filtering."""
        try:
            if portal_id:
                sessions, _ = self.session_repo.list_sessions_for_portal(
                    portal_id, status=SessionStatus.ACTIVE
                )
            else:
                # Get all active sessions for tenant
                sessions = self.session_repo.find_by_filters(
                    {"session_status": SessionStatus.ACTIVE}
                )

            if user_id:
                sessions = [s for s in sessions if s.user_id == user_id]

            return [SessionResponse.model_validate(session) for session in sessions]

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            raise ServiceError(f"Failed to get active sessions: {str(e)}") from e

    async def update_session_usage(
        self, session_id: str, bytes_downloaded: int, bytes_uploaded: int
    ) -> bool:
        """Update session usage statistics."""
        try:
            success = self.session_repo.update_session_usage(
                session_id, bytes_downloaded, bytes_uploaded
            )

            if success:
                logger.debug(f"Updated usage for session {session_id}")

            return success

        except Exception as e:
            logger.error(f"Error updating session usage: {e}")
            raise ServiceError(f"Failed to update session usage: {str(e)}") from e

    # Voucher Management

    async def create_vouchers(
        self, voucher_request: VoucherCreateRequest
    ) -> list[VoucherResponse]:
        """Create vouchers for portal access."""
        try:
            portal = self.portal_repo.get_by_id(voucher_request.portal_id)
            if not portal:
                raise EntityNotFoundError(
                    f"Portal {voucher_request.portal_id} not found"
                )

            vouchers = []
            for _i in range(voucher_request.quantity):
                voucher_data = voucher_request.model_dump(
                    exclude={"portal_id", "quantity", "batch_name"}
                )
                voucher_data.update(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self.tenant_id,
                        "portal_id": voucher_request.portal_id,
                        "code": self._generate_voucher_code(),
                        "voucher_status": VoucherStatus.ACTIVE,
                    }
                )

                voucher = Voucher(**voucher_data)
                created_voucher = self.voucher_repo.create(voucher)
                vouchers.append(VoucherResponse.model_validate(created_voucher))

            logger.info(
                f"Created {len(vouchers)} vouchers for portal {voucher_request.portal_id}"
            )
            return vouchers

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error creating vouchers: {e}")
            raise ServiceError(f"Failed to create vouchers: {str(e)}") from e

    async def redeem_voucher(
        self, voucher_code: str, portal_id: str, user_id: str
    ) -> bool:
        """Redeem a voucher for access."""
        try:
            success = self.voucher_repo.redeem_voucher(
                voucher_code.replace("-", ""), user_id
            )  # Remove dashes for lookup

            if success:
                logger.info(f"Redeemed voucher {voucher_code} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error redeeming voucher: {e}")
            raise ServiceError(f"Failed to redeem voucher: {str(e)}") from e

    # Analytics and Statistics

    async def get_portal_stats(
        self,
        portal_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Get portal usage statistics."""
        try:
            portal = self.portal_repo.get_by_id(portal_id)
            if not portal:
                raise EntityNotFoundError(f"Portal {portal_id} not found")

            # Default to last 30 days if no dates provided
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
            if not end_date:
                end_date = datetime.now(timezone.utc)

            # Get aggregated stats
            stats = self.stats_repo.aggregate_session_stats(portal_id, start_date)

            # Get current active sessions
            active_sessions = self.session_repo.get_active_session_count(portal_id)

            return {
                "portal_id": portal_id,
                "portal_name": portal.name,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "current_active_sessions": active_sessions,
                "statistics": stats,
            }

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting portal stats: {e}")
            raise ServiceError(f"Failed to get portal stats: {str(e)}") from e

    # Maintenance

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            count = self.session_repo.terminate_expired_sessions()
            logger.info(
                f"Cleaned up {count} expired sessions for tenant {self.tenant_id}"
            )
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            raise ServiceError(f"Failed to cleanup expired sessions: {str(e)}") from e

    # Private Helper Methods

    async def _create_default_auth_methods(self, portal_id: str) -> None:
        """Create default authentication methods for a portal."""
        try:
            default_methods = [
                {
                    "method_type": AuthMethodType.SOCIAL,
                    "name": "Social Login",
                    "config": {"providers": ["google", "facebook"]},
                    "is_default": True,
                    "display_order": 1,
                },
                {
                    "method_type": AuthMethodType.EMAIL,
                    "name": "Email Verification",
                    "config": {"require_verification": True},
                    "display_order": 2,
                },
            ]

            for method_data in default_methods:
                method_data.update(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self.tenant_id,
                        "portal_id": portal_id,
                    }
                )

                auth_method = AuthMethod(**method_data)
                self.auth_method_repo.create(auth_method)

        except Exception as e:
            logger.error(f"Error creating default auth methods: {e}")
            raise

    def _generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

    def _generate_voucher_code(self) -> str:
        """Generate a unique voucher code."""
        characters = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(characters) for _ in range(8))
        return f"{code[:4]}-{code[4:]}"  # Format as XXXX-XXXX
