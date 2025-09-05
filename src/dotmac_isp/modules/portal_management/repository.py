"""Portal Management repository - Data access layer for portal accounts and sessions."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from dotmac.core import BaseRepository
from dotmac.core.exceptions import standard_exception_handler

from .models import (
    PortalAccount,
    PortalAccountStatus,
    PortalAccountType,
    PortalLoginAttempt,
    PortalPreferences,
    PortalSession,
)


class PortalAccountRepository(BaseRepository[PortalAccount]):
    """Repository for portal account operations."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, PortalAccount, tenant_id)

    @standard_exception_handler
    async def find_by_portal_id(self, portal_id: str) -> Optional[PortalAccount]:
        """Find portal account by portal ID."""
        query = (
            select(PortalAccount)
            .options(joinedload(PortalAccount.customer), joinedload(PortalAccount.user))
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.portal_id == portal_id,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def find_by_customer_id(self, customer_id: UUID) -> Optional[PortalAccount]:
        """Find portal account by customer ID."""
        query = (
            select(PortalAccount)
            .options(joinedload(PortalAccount.sessions))
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.customer_id == customer_id,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def find_by_user_id(self, user_id: UUID) -> Optional[PortalAccount]:
        """Find portal account by user ID."""
        query = select(PortalAccount).where(
            and_(
                PortalAccount.tenant_id == self.tenant_id,
                PortalAccount.user_id == user_id,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def find_by_account_type(
        self, account_type: PortalAccountType
    ) -> list[PortalAccount]:
        """Find portal accounts by type."""
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.account_type == account_type.value,
                )
            )
            .order_by(PortalAccount.created_at.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_by_status(self, status: PortalAccountStatus) -> list[PortalAccount]:
        """Find portal accounts by status."""
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.status == status.value,
                )
            )
            .order_by(PortalAccount.updated_at.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_locked_accounts(self) -> list[PortalAccount]:
        """Find currently locked accounts."""
        now = datetime.now(timezone.utc)
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.locked_until.isnot(None),
                    PortalAccount.locked_until > now,
                )
            )
            .order_by(PortalAccount.locked_until.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_accounts_needing_password_change(self) -> list[PortalAccount]:
        """Find accounts that must change their password."""
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.must_change_password is True,
                    PortalAccount.status == PortalAccountStatus.ACTIVE.value,
                )
            )
            .order_by(PortalAccount.created_at.asc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_accounts_with_expired_passwords(
        self, expiry_days: int = 90
    ) -> list[PortalAccount]:
        """Find accounts with expired passwords."""
        expiry_threshold = datetime.now(timezone.utc) - timedelta(days=expiry_days)

        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    or_(
                        PortalAccount.password_changed_at < expiry_threshold,
                        PortalAccount.password_changed_at.is_(None),
                    ),
                    PortalAccount.status == PortalAccountStatus.ACTIVE.value,
                )
            )
            .order_by(PortalAccount.password_changed_at.asc().nullsfirst())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_accounts_with_2fa_enabled(self) -> list[PortalAccount]:
        """Find accounts with two-factor authentication enabled."""
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.two_factor_enabled is True,
                )
            )
            .order_by(PortalAccount.portal_id)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_accounts_by_last_login(
        self, days_inactive: int = 30
    ) -> list[PortalAccount]:
        """Find accounts by last login activity."""
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days_inactive)

        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    or_(
                        PortalAccount.last_successful_login < threshold_date,
                        PortalAccount.last_successful_login.is_(None),
                    ),
                    PortalAccount.status == PortalAccountStatus.ACTIVE.value,
                )
            )
            .order_by(PortalAccount.last_successful_login.asc().nullsfirst())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_accounts_with_failed_attempts(
        self, min_attempts: int = 3
    ) -> list[PortalAccount]:
        """Find accounts with multiple failed login attempts."""
        query = (
            select(PortalAccount)
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.failed_login_attempts >= min_attempts,
                )
            )
            .order_by(PortalAccount.failed_login_attempts.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def search_accounts(self, search_term: str) -> list[PortalAccount]:
        """Search portal accounts by portal ID or customer info."""
        search_pattern = f"%{search_term}%"

        query = (
            select(PortalAccount)
            .options(joinedload(PortalAccount.customer))
            .where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.portal_id.ilike(search_pattern),
                )
            )
            .order_by(PortalAccount.portal_id)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def get_account_statistics(self) -> dict[str, Any]:
        """Get portal account statistics."""
        total_accounts = await self.session.execute(
            select(func.count(PortalAccount.id)).where(
                PortalAccount.tenant_id == self.tenant_id
            )
        )

        active_accounts = await self.session.execute(
            select(func.count(PortalAccount.id)).where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.status == PortalAccountStatus.ACTIVE.value,
                )
            )
        )

        locked_accounts = await self.session.execute(
            select(func.count(PortalAccount.id)).where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.locked_until.isnot(None),
                    PortalAccount.locked_until > datetime.now(timezone.utc),
                )
            )
        )

        accounts_with_2fa = await self.session.execute(
            select(func.count(PortalAccount.id)).where(
                and_(
                    PortalAccount.tenant_id == self.tenant_id,
                    PortalAccount.two_factor_enabled is True,
                )
            )
        )

        accounts_by_type = await self.session.execute(
            select(
                PortalAccount.account_type, func.count(PortalAccount.id).label("count")
            )
            .where(PortalAccount.tenant_id == self.tenant_id)
            .group_by(PortalAccount.account_type)
        )

        return {
            "total_accounts": total_accounts.scalar(),
            "active_accounts": active_accounts.scalar(),
            "locked_accounts": locked_accounts.scalar(),
            "accounts_with_2fa": accounts_with_2fa.scalar(),
            "accounts_by_type": {
                row.account_type: row.count for row in accounts_by_type
            },
        }


class PortalSessionRepository(BaseRepository[PortalSession]):
    """Repository for portal session operations."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, PortalSession, tenant_id)

    @standard_exception_handler
    async def find_by_session_token(
        self, session_token: str
    ) -> Optional[PortalSession]:
        """Find session by session token."""
        query = (
            select(PortalSession)
            .options(joinedload(PortalSession.portal_account))
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.session_token == session_token,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def find_active_sessions_by_account(
        self, portal_account_id: UUID
    ) -> list[PortalSession]:
        """Find active sessions for a portal account."""
        now = datetime.now(timezone.utc)
        query = (
            select(PortalSession)
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.portal_account_id == portal_account_id,
                    PortalSession.is_active is True,
                    PortalSession.expires_at > now,
                )
            )
            .order_by(PortalSession.last_activity.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_expired_sessions(self) -> list[PortalSession]:
        """Find expired sessions that need cleanup."""
        now = datetime.now(timezone.utc)
        query = (
            select(PortalSession)
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.is_active is True,
                    PortalSession.expires_at <= now,
                )
            )
            .order_by(PortalSession.expires_at.asc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_sessions_by_ip(
        self, ip_address: str, active_only: bool = True
    ) -> list[PortalSession]:
        """Find sessions by IP address."""
        query = (
            select(PortalSession)
            .options(joinedload(PortalSession.portal_account))
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.ip_address == ip_address,
                )
            )
        )

        if active_only:
            now = datetime.now(timezone.utc)
            query = query.where(
                and_(PortalSession.is_active is True, PortalSession.expires_at > now)
            )

        query = query.order_by(PortalSession.login_at.desc())

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_suspicious_sessions(self) -> list[PortalSession]:
        """Find sessions flagged as suspicious."""
        query = (
            select(PortalSession)
            .options(joinedload(PortalSession.portal_account))
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.suspicious_activity is True,
                    PortalSession.is_active is True,
                )
            )
            .order_by(PortalSession.last_activity.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_long_running_sessions(
        self, hours_threshold: int = 24
    ) -> list[PortalSession]:
        """Find long-running active sessions."""
        threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)

        query = (
            select(PortalSession)
            .options(joinedload(PortalSession.portal_account))
            .where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.is_active is True,
                    PortalSession.login_at <= threshold_time,
                )
            )
            .order_by(PortalSession.login_at.asc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def cleanup_expired_sessions(self) -> int:
        """Mark expired sessions as inactive and return count."""
        datetime.now(timezone.utc)

        # Get expired sessions
        expired_sessions = await self.find_expired_sessions()

        # Mark them as terminated
        for session in expired_sessions:
            session.terminate_session("expired")

        await self.session.flush()
        return len(expired_sessions)

    @standard_exception_handler
    async def terminate_all_sessions_for_account(
        self, portal_account_id: UUID, reason: str = "admin"
    ) -> int:
        """Terminate all active sessions for an account."""
        active_sessions = await self.find_active_sessions_by_account(portal_account_id)

        for session in active_sessions:
            session.terminate_session(reason)

        await self.session.flush()
        return len(active_sessions)

    @standard_exception_handler
    async def get_session_statistics(self, days_back: int = 30) -> dict[str, Any]:
        """Get session statistics."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        total_sessions = await self.session.execute(
            select(func.count(PortalSession.id)).where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.login_at >= start_date,
                )
            )
        )

        active_sessions = await self.session.execute(
            select(func.count(PortalSession.id)).where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.is_active is True,
                    PortalSession.expires_at > datetime.now(timezone.utc),
                )
            )
        )

        avg_duration = await self.session.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch", PortalSession.logout_at - PortalSession.login_at
                    )
                    / 60
                )
            ).where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.logout_at.isnot(None),
                    PortalSession.login_at >= start_date,
                )
            )
        )

        suspicious_sessions = await self.session.execute(
            select(func.count(PortalSession.id)).where(
                and_(
                    PortalSession.tenant_id == self.tenant_id,
                    PortalSession.suspicious_activity is True,
                    PortalSession.login_at >= start_date,
                )
            )
        )

        return {
            "total_sessions_period": total_sessions.scalar(),
            "active_sessions": active_sessions.scalar(),
            "avg_duration_minutes": avg_duration.scalar() or 0,
            "suspicious_sessions": suspicious_sessions.scalar(),
        }


class PortalLoginAttemptRepository(BaseRepository[PortalLoginAttempt]):
    """Repository for portal login attempt operations."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, PortalLoginAttempt, tenant_id)

    @standard_exception_handler
    async def find_by_portal_id(
        self, portal_id: str, limit: int = 100
    ) -> list[PortalLoginAttempt]:
        """Find login attempts for a portal ID."""
        query = (
            select(PortalLoginAttempt)
            .where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.portal_id_attempted == portal_id,
                )
            )
            .order_by(PortalLoginAttempt.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_by_ip_address(
        self, ip_address: str, hours_back: int = 24
    ) -> list[PortalLoginAttempt]:
        """Find login attempts from an IP address."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = (
            select(PortalLoginAttempt)
            .where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.ip_address == ip_address,
                    PortalLoginAttempt.created_at >= start_time,
                )
            )
            .order_by(PortalLoginAttempt.created_at.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_failed_attempts(
        self, hours_back: int = 24, min_attempts: int = 1
    ) -> list[PortalLoginAttempt]:
        """Find failed login attempts."""
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = (
            select(PortalLoginAttempt)
            .where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.success is False,
                    PortalLoginAttempt.created_at >= start_time,
                )
            )
            .order_by(PortalLoginAttempt.created_at.desc())
        )

        result = await self.session.execute(query)
        attempts = result.scalars().all()

        if min_attempts > 1:
            # Group by IP and filter by minimum attempts
            ip_counts = {}
            for attempt in attempts:
                ip_counts[attempt.ip_address] = ip_counts.get(attempt.ip_address, 0) + 1

            filtered_attempts = [
                attempt
                for attempt in attempts
                if ip_counts[attempt.ip_address] >= min_attempts
            ]
            return filtered_attempts

        return attempts

    @standard_exception_handler
    async def find_high_risk_attempts(
        self, risk_threshold: int = 75
    ) -> list[PortalLoginAttempt]:
        """Find high-risk login attempts."""
        query = (
            select(PortalLoginAttempt)
            .options(joinedload(PortalLoginAttempt.portal_account))
            .where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    or_(
                        PortalLoginAttempt.risk_score >= risk_threshold,
                        PortalLoginAttempt.flagged_as_suspicious is True,
                    ),
                )
            )
            .order_by(PortalLoginAttempt.created_at.desc())
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def get_attempt_statistics(self, days_back: int = 7) -> dict[str, Any]:
        """Get login attempt statistics."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days_back)

        total_attempts = await self.session.execute(
            select(func.count(PortalLoginAttempt.id)).where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.created_at >= start_date,
                )
            )
        )

        successful_attempts = await self.session.execute(
            select(func.count(PortalLoginAttempt.id)).where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.success is True,
                    PortalLoginAttempt.created_at >= start_date,
                )
            )
        )

        failed_attempts = await self.session.execute(
            select(func.count(PortalLoginAttempt.id)).where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.success is False,
                    PortalLoginAttempt.created_at >= start_date,
                )
            )
        )

        high_risk_attempts = await self.session.execute(
            select(func.count(PortalLoginAttempt.id)).where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.risk_score >= 75,
                    PortalLoginAttempt.created_at >= start_date,
                )
            )
        )

        unique_ips = await self.session.execute(
            select(func.count(func.distinct(PortalLoginAttempt.ip_address))).where(
                and_(
                    PortalLoginAttempt.tenant_id == self.tenant_id,
                    PortalLoginAttempt.created_at >= start_date,
                )
            )
        )

        return {
            "total_attempts": total_attempts.scalar(),
            "successful_attempts": successful_attempts.scalar(),
            "failed_attempts": failed_attempts.scalar(),
            "high_risk_attempts": high_risk_attempts.scalar(),
            "unique_ips": unique_ips.scalar(),
            "success_rate": (
                successful_attempts.scalar() / max(total_attempts.scalar(), 1)
            )
            * 100,
        }


class PortalPreferencesRepository(BaseRepository[PortalPreferences]):
    """Repository for portal preferences operations."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(session, PortalPreferences, tenant_id)

    @standard_exception_handler
    async def find_by_account_id(self, account_id: UUID) -> Optional[PortalPreferences]:
        """Find preferences by account ID."""
        query = select(PortalPreferences).where(
            and_(
                PortalPreferences.tenant_id == self.tenant_id,
                PortalPreferences.account_id == str(account_id),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    @standard_exception_handler
    async def find_by_theme(self, theme: str) -> list[PortalPreferences]:
        """Find preferences by theme."""
        query = (
            select(PortalPreferences)
            .options(joinedload(PortalPreferences.account))
            .where(
                and_(
                    PortalPreferences.tenant_id == self.tenant_id,
                    PortalPreferences.theme == theme,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def find_marketing_email_subscribers(self) -> list[PortalPreferences]:
        """Find accounts subscribed to marketing emails."""
        query = (
            select(PortalPreferences)
            .options(joinedload(PortalPreferences.account))
            .where(
                and_(
                    PortalPreferences.tenant_id == self.tenant_id,
                    PortalPreferences.marketing_emails is True,
                    PortalPreferences.email_notifications is True,
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    @standard_exception_handler
    async def get_preference_statistics(self) -> dict[str, Any]:
        """Get portal preference statistics."""
        theme_stats = await self.session.execute(
            select(
                PortalPreferences.theme, func.count(PortalPreferences.id).label("count")
            )
            .where(PortalPreferences.tenant_id == self.tenant_id)
            .group_by(PortalPreferences.theme)
        )

        notification_stats = await self.session.execute(
            select(
                func.count(PortalPreferences.id)
                .filter(PortalPreferences.email_notifications is True)
                .label("email_enabled"),
                func.count(PortalPreferences.id)
                .filter(PortalPreferences.sms_notifications is True)
                .label("sms_enabled"),
                func.count(PortalPreferences.id)
                .filter(PortalPreferences.marketing_emails is True)
                .label("marketing_subscribed"),
            ).where(PortalPreferences.tenant_id == self.tenant_id)
        )

        lang_stats = await self.session.execute(
            select(
                PortalPreferences.language,
                func.count(PortalPreferences.id).label("count"),
            )
            .where(PortalPreferences.tenant_id == self.tenant_id)
            .group_by(PortalPreferences.language)
        )

        notification_row = notification_stats.first()

        return {
            "themes": {row.theme: row.count for row in theme_stats},
            "languages": {row.language: row.count for row in lang_stats},
            "notifications": {
                "email_enabled": notification_row.email_enabled
                if notification_row
                else 0,
                "sms_enabled": notification_row.sms_enabled if notification_row else 0,
                "marketing_subscribed": notification_row.marketing_subscribed
                if notification_row
                else 0,
            },
        }
