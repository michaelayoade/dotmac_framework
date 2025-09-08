"""
Core captive portal functionality and configuration.

Provides the main CaptivePortal class and configuration management
for unified captive portal operations.
"""

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .models import GuestUser, Portal, Session, SessionStatus

logger = structlog.get_logger(__name__)


@dataclass
class CaptivePortalConfig:
    """Configuration for captive portal operations."""

    # Database settings
    database_url: str = "postgresql://localhost/captive_portal"
    redis_url: str = "redis://localhost:6379"

    # Portal defaults
    default_session_timeout: int = 3600  # 1 hour
    default_idle_timeout: int = 1800  # 30 minutes
    default_data_limit_mb: int = 0  # unlimited
    default_bandwidth_down: int = 0  # unlimited
    default_bandwidth_up: int = 0  # unlimited

    # Authentication settings
    require_email_verification: bool = True
    verification_code_length: int = 6
    verification_expires_minutes: int = 15

    # Session management
    cleanup_expired_sessions: bool = True
    cleanup_interval_minutes: int = 15
    max_concurrent_sessions_per_user: int = 3

    # Security settings
    session_token_length: int = 32
    enable_captcha: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Portal customization
    default_theme: str = "default"
    allow_custom_css: bool = True
    allow_custom_html: bool = True
    max_logo_size_mb: int = 5

    # Billing integration
    billing_enabled: bool = False
    payment_providers: list[str] = field(default_factory=lambda: ["stripe", "paypal"])

    # Analytics and monitoring
    enable_usage_tracking: bool = True
    enable_analytics: bool = True
    analytics_retention_days: int = 90

    # Notification settings
    smtp_server: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    sms_provider: str | None = None  # twilio, nexmo

    # External integrations
    radius_server: str | None = None
    radius_secret: str | None = None
    social_auth_providers: dict[str, dict[str, str]] = field(default_factory=dict)


class CaptivePortalService:
    """Core service for captive portal operations."""

    def __init__(self, config: CaptivePortalConfig, db_session: AsyncSession):
        self.config = config
        self.db = db_session
        self._active_sessions: dict[str, Session] = {}
        self._login_attempts: dict[str, list[datetime]] = {}

    async def create_portal(
        self,
        tenant_id: str,
        name: str,
        ssid: str,
        location: str | None = None,
        **kwargs,
    ) -> Portal:
        """Create a new captive portal."""
        portal = Portal(
            tenant_id=uuid.UUID(tenant_id),
            name=name,
            ssid=ssid,
            location=location,
            portal_url=kwargs.get("portal_url", f"https://portal.guest/{uuid.uuid4().hex[:8]}"),
            auth_methods=kwargs.get("auth_methods", ["social", "voucher"]),
            session_timeout=kwargs.get("session_timeout", self.config.default_session_timeout),
            require_terms=kwargs.get("require_terms", True),
            require_email_verification=kwargs.get(
                "require_email_verification",
                self.config.require_email_verification,
            ),
            max_concurrent_sessions=kwargs.get("max_concurrent_sessions", 100),
            data_limit_mb=kwargs.get("data_limit_mb", self.config.default_data_limit_mb),
            bandwidth_limit_down=kwargs.get(
                "bandwidth_limit_down",
                self.config.default_bandwidth_down,
            ),
            bandwidth_limit_up=kwargs.get("bandwidth_limit_up", self.config.default_bandwidth_up),
            billing_enabled=kwargs.get("billing_enabled", self.config.billing_enabled),
            theme_config=kwargs.get("theme_config", {"theme": self.config.default_theme}),
            **kwargs,
        )

        self.db.add(portal)
        await self.db.commit()
        await self.db.refresh(portal)

        logger.info(
            "Portal created",
            portal_id=str(portal.id),
            name=name,
            ssid=ssid,
            tenant_id=tenant_id,
        )

        return portal

    async def get_portal(self, portal_id: str) -> Portal | None:
        """Get portal by ID."""
        return await self.db.get(Portal, uuid.UUID(portal_id))

    async def update_portal(
        self,
        portal_id: str,
        **updates,
    ) -> Portal | None:
        """Update portal configuration."""
        portal = await self.get_portal(portal_id)
        if not portal:
            return None

        for key, value in updates.items():
            if hasattr(portal, key):
                setattr(portal, key, value)

        await self.db.commit()
        await self.db.refresh(portal)

        logger.info("Portal updated", portal_id=portal_id, updates=list(updates.keys()))

        return portal

    async def delete_portal(self, portal_id: str) -> bool:
        """Delete portal and associated data."""
        portal = await self.get_portal(portal_id)
        if not portal:
            return False

        # Terminate all active sessions
        active_sessions = await self.get_active_sessions(portal_id)
        for session in active_sessions:
            await self.terminate_session(str(session.id), "Portal deleted")

        await self.db.delete(portal)
        await self.db.commit()

        logger.info("Portal deleted", portal_id=portal_id)
        return True

    async def register_guest_user(
        self,
        portal_id: str,
        auth_method: str,
        email: str | None = None,
        phone_number: str | None = None,
        **user_data,
    ) -> GuestUser:
        """Register a new guest user."""
        portal = await self.get_portal(portal_id)
        if not portal:
            msg = f"Portal not found: {portal_id}"
            raise ValueError(msg)

        # Generate verification code if needed
        verification_code = None
        verification_expires = None
        is_verified = False

        # Email/SMS verification no longer supported - all methods are verified by default
        is_verified = True

        user = GuestUser(
            portal_id=uuid.UUID(portal_id),
            tenant_id=portal.tenant_id,
            email=email,
            phone_number=phone_number,
            auth_method=auth_method,
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            company=user_data.get("company"),
            is_verified=is_verified,
            verification_code=verification_code,
            verification_expires=verification_expires,
            data_limit_mb=user_data.get("data_limit_mb", portal.data_limit_mb),
            **user_data,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            "Guest user registered",
            user_id=str(user.id),
            portal_id=portal_id,
            auth_method=auth_method,
            email=email,
            phone_number=phone_number,
        )

        # Send verification if needed
        if verification_code:
            await self._send_verification(user, verification_code)

        return user

    async def authenticate_user(
        self,
        portal_id: str,
        identifier: str,  # email, phone, or username
        password: str | None = None,
        verification_code: str | None = None,
        client_ip: str | None = None,
        client_mac: str | None = None,
        **session_data,
    ) -> dict[str, Any]:
        """Authenticate user and create session."""
        # Check rate limiting
        if not await self._check_rate_limit(identifier, client_ip):
            msg = "Too many authentication attempts. Please try again later."
            raise ValueError(msg)

        # Find user
        user = await self._find_user(portal_id, identifier)
        if not user:
            await self._record_failed_attempt(identifier, client_ip)
            msg = "Invalid credentials"
            raise ValueError(msg)

        # Validate authentication
        if not await self._validate_authentication(user, password, verification_code):
            await self._record_failed_attempt(identifier, client_ip)
            msg = "Invalid credentials"
            raise ValueError(msg)

        # Check user status and limits
        if not user.is_active:
            msg = "User account is suspended"
            raise ValueError(msg)

        if user.valid_until and datetime.now(UTC) > user.valid_until:
            msg = "User account has expired"
            raise ValueError(msg)

        # Check concurrent session limits
        active_user_sessions = await self._get_user_active_sessions(str(user.id))
        if len(active_user_sessions) >= self.config.max_concurrent_sessions_per_user:
            msg = "Maximum concurrent sessions reached"
            raise ValueError(msg)

        # Create session
        session = await self._create_session(
            user,
            client_ip,
            client_mac,
            **session_data,
        )

        # Update user login tracking
        user.last_login = datetime.now(UTC)
        user.login_count += 1
        await self.db.commit()

        # Clear failed attempts
        self._clear_failed_attempts(identifier, client_ip)

        logger.info(
            "User authenticated",
            user_id=str(user.id),
            session_id=str(session.id),
            portal_id=portal_id,
            client_ip=client_ip,
        )

        return {
            "user_id": str(user.id),
            "session_id": str(session.id),
            "session_token": session.session_token,
            "expires_at": session.expires_at.isoformat(),
            "data_limit_mb": user.data_limit_mb,
            "time_limit_minutes": user.time_limit_minutes,
            "authenticated": True,
        }

    async def _create_session(
        self,
        user: GuestUser,
        client_ip: str | None,
        client_mac: str | None,
        **session_data,
    ) -> Session:
        """Create user session."""
        portal = await self.get_portal(str(user.portal_id))

        session_token = secrets.token_urlsafe(self.config.session_token_length)
        expires_at = datetime.now(UTC) + timedelta(seconds=portal.session_timeout)

        session = Session(
            portal_id=user.portal_id,
            guest_user_id=user.id,
            tenant_id=user.tenant_id,
            session_token=session_token,
            client_ip=client_ip,
            client_mac=client_mac,
            expires_at=expires_at,
            user_agent=session_data.get("user_agent"),
            device_type=session_data.get("device_type"),
            browser=session_data.get("browser"),
            os=session_data.get("os"),
            access_point_mac=session_data.get("access_point_mac"),
            access_point_name=session_data.get("access_point_name"),
            location_coordinates=session_data.get("location_coordinates"),
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        # Cache active session
        self._active_sessions[session.session_token] = session

        return session

    async def terminate_session(
        self,
        session_id: str,
        reason: str = "User logout",
    ) -> dict[str, Any]:
        """Terminate user session."""
        session = await self.db.get(Session, uuid.UUID(session_id))
        if not session:
            msg = f"Session not found: {session_id}"
            raise ValueError(msg)

        session.status = SessionStatus.TERMINATED
        session.end_time = datetime.now(UTC)
        session.termination_reason = reason

        await self.db.commit()

        # Remove from active sessions cache
        if session.session_token in self._active_sessions:
            del self._active_sessions[session.session_token]

        logger.info(
            "Session terminated",
            session_id=session_id,
            reason=reason,
            duration=session.duration_minutes,
        )

        return {
            "session_id": session_id,
            "terminated": True,
            "reason": reason,
            "duration_minutes": session.duration_minutes,
        }

    async def get_active_sessions(
        self,
        portal_id: str | None = None,
        user_id: str | None = None,
    ) -> list[Session]:
        """Get active sessions with optional filtering."""
        query = self.db.query(Session).filter(Session.status == SessionStatus.ACTIVE)

        if portal_id:
            query = query.filter(Session.portal_id == uuid.UUID(portal_id))

        if user_id:
            query = query.filter(Session.guest_user_id == uuid.UUID(user_id))

        return await query.all()

    async def validate_session(self, session_token: str) -> Session | None:
        """Validate session token and return session if valid."""
        # Check cache first
        if session_token in self._active_sessions:
            session = self._active_sessions[session_token]
            if datetime.now(UTC) < session.expires_at:
                return session
            # Session expired, remove from cache
            del self._active_sessions[session_token]

        # Query database
        query = self.db.query(Session).filter(
            Session.session_token == session_token,
            Session.status == SessionStatus.ACTIVE,
        )
        session = await query.first()

        if session and datetime.now(UTC) < session.expires_at:
            # Update last activity
            session.last_activity = datetime.now(UTC)
            await self.db.commit()

            # Cache for next time
            self._active_sessions[session_token] = session
            return session

        return None

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        if not self.config.cleanup_expired_sessions:
            return 0

        cutoff_time = datetime.now(UTC)

        # Update expired active sessions
        expired_sessions = (
            await self.db.query(Session)
            .filter(
                Session.status == SessionStatus.ACTIVE,
                Session.expires_at < cutoff_time,
            )
            .all()
        )

        count = 0
        for session in expired_sessions:
            session.status = SessionStatus.EXPIRED
            session.end_time = cutoff_time
            session.termination_reason = "Session timeout"
            count += 1

        await self.db.commit()

        # Clear from cache
        expired_tokens = [
            token for token, session in self._active_sessions.items() if datetime.now(UTC) >= session.expires_at
        ]
        for token in expired_tokens:
            del self._active_sessions[token]

        if count > 0:
            logger.info("Cleaned up expired sessions", count=count)

        return count

    def _generate_verification_code(self) -> str:
        """Generate numeric verification code."""
        return "".join(secrets.choice("0123456789") for _ in range(self.config.verification_code_length))

    async def _find_user(self, portal_id: str, identifier: str) -> GuestUser | None:
        """Find user by email, phone, or username."""
        query = self.db.query(GuestUser).filter(
            GuestUser.portal_id == uuid.UUID(portal_id),
            GuestUser.is_active is True,
        )

        # Check if identifier is email, phone, or username
        if "@" in identifier:
            query = query.filter(GuestUser.email == identifier)
        elif identifier.startswith("+") or identifier.isdigit():
            query = query.filter(GuestUser.phone_number == identifier)
        else:
            query = query.filter(GuestUser.username == identifier)

        return await query.first()

    async def _validate_authentication(
        self,
        user: GuestUser,
        password: str | None,
        verification_code: str | None,
    ) -> bool:
        """Validate user authentication credentials."""
        # Email/SMS verification no longer supported - skip verification check
        if False:  # Disabled email/sms verification
            # Check verification code
            if not verification_code or not user.verification_code:
                return False

            if user.verification_expires and datetime.now(UTC) > user.verification_expires:
                return False

            if verification_code != user.verification_code:
                return False

            # Mark as verified
            user.is_verified = True
            user.verification_code = None
            user.verification_expires = None

        # Check password if required
        if user.password_hash and password:
            # In a real implementation, use proper password hashing
            return user.password_hash == password

        return True

    async def _check_rate_limit(self, identifier: str, client_ip: str | None) -> bool:
        """Check authentication rate limits."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(minutes=60)  # 1 hour window

        # Check by identifier
        if identifier in self._login_attempts:
            attempts = [attempt for attempt in self._login_attempts[identifier] if attempt > cutoff]
            self._login_attempts[identifier] = attempts

            if len(attempts) >= self.config.max_login_attempts:
                return False

        # Check by IP if available
        if client_ip and client_ip in self._login_attempts:
            attempts = [attempt for attempt in self._login_attempts[client_ip] if attempt > cutoff]
            self._login_attempts[client_ip] = attempts

            if len(attempts) >= self.config.max_login_attempts * 3:  # More lenient for IP
                return False

        return True

    async def _record_failed_attempt(self, identifier: str, client_ip: str | None):
        """Record failed authentication attempt."""
        now = datetime.now(UTC)

        if identifier not in self._login_attempts:
            self._login_attempts[identifier] = []
        self._login_attempts[identifier].append(now)

        if client_ip:
            if client_ip not in self._login_attempts:
                self._login_attempts[client_ip] = []
            self._login_attempts[client_ip].append(now)

    def _clear_failed_attempts(self, identifier: str, client_ip: str | None):
        """Clear failed authentication attempts."""
        if identifier in self._login_attempts:
            del self._login_attempts[identifier]

        if client_ip and client_ip in self._login_attempts:
            del self._login_attempts[client_ip]

    async def _get_user_active_sessions(self, user_id: str) -> list[Session]:
        """Get active sessions for a user."""
        return await self.get_active_sessions(user_id=user_id)

    async def _send_verification(self, user: GuestUser, code: str):
        """Send verification code to user."""
        # In a real implementation, integrate with notification providers
        logger.info(
            "Verification code sent",
            user_id=str(user.id),
            method=user.auth_method.value,
            code=code,
        )


class CaptivePortal:
    """Main captive portal management class."""

    def __init__(self, config: CaptivePortalConfig):
        self.config = config
        self._service: CaptivePortalService | None = None

    def set_database_session(self, db_session: AsyncSession):
        """Set database session for the service."""
        self._service = CaptivePortalService(self.config, db_session)

    @property
    def service(self) -> CaptivePortalService:
        """Get the captive portal service."""
        if not self._service:
            msg = "Database session not configured"
            raise RuntimeError(msg)
        return self._service

    async def create_portal(self, tenant_id: str, name: str, ssid: str, **kwargs) -> Portal:
        """Create a new captive portal."""
        return await self.service.create_portal(tenant_id, name, ssid, **kwargs)

    async def authenticate_user(self, portal_id: str, identifier: str, **kwargs) -> dict[str, Any]:
        """Authenticate user and create session."""
        return await self.service.authenticate_user(portal_id, identifier, **kwargs)

    async def terminate_session(self, session_id: str, reason: str = "User logout") -> dict[str, Any]:
        """Terminate user session."""
        return await self.service.terminate_session(session_id, reason)

    async def validate_session(self, session_token: str) -> Session | None:
        """Validate session token."""
        return await self.service.validate_session(session_token)

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        return await self.service.cleanup_expired_sessions()
