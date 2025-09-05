"""
Captive Portal Repository Layer

Provides data access layer for captive portal operations with DRY patterns
leveraging existing base repository classes and tenant isolation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from dotmac_isp.shared.base_repository import BaseTenantRepository
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import joinedload, selectinload

from .models import (
    AuthMethod,
    CaptivePortalConfig,
    CaptivePortalSession,
    PortalCustomization,
    PortalUsageStats,
    SessionStatus,
    Voucher,
    VoucherBatch,
    VoucherStatus,
)

logger = logging.getLogger(__name__)


class CaptivePortalConfigRepository(BaseTenantRepository[CaptivePortalConfig]):
    """Repository for captive portal configuration management."""

    model = CaptivePortalConfig

    def find_by_ssid(self, ssid: str) -> Optional[CaptivePortalConfig]:
        """Find portal configuration by SSID."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.ssid == ssid,
                        self.model.is_active is True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error finding portal by SSID {ssid}: {e}")
            raise

    def find_by_customer_id(
        self, customer_id: str, limit: Optional[int] = None
    ) -> list[CaptivePortalConfig]:
        """Find all portal configurations for a customer."""
        try:
            query = (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.customer_id == customer_id,
                        self.model.is_active is True,
                    )
                )
                .order_by(desc(self.model.created_at))
            )

            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            logger.error(f"Error finding portals for customer {customer_id}: {e}")
            raise

    def list_with_filters(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CaptivePortalConfig], int]:
        """List portal configurations with filtering and pagination."""
        try:
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == self.tenant_id, self.model.is_active is True
                )
            )

            # Apply filters
            if customer_id:
                query = query.filter(self.model.customer_id == customer_id)
            if status:
                query = query.filter(self.model.portal_status == status)
            if location:
                query = query.filter(self.model.location.ilike(f"%{location}%"))

            # Get total count
            total = query.count()

            # Apply pagination and get results
            portals = (
                query.order_by(desc(self.model.created_at))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return portals, total
        except Exception as e:
            logger.error(f"Error listing portals with filters: {e}")
            raise

    def check_ssid_availability(
        self, ssid: str, exclude_id: Optional[str] = None
    ) -> bool:
        """Check if SSID is available for use."""
        try:
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.ssid == ssid,
                    self.model.is_active is True,
                )
            )

            if exclude_id:
                query = query.filter(self.model.id != exclude_id)

            existing = query.first()
            return existing is None
        except Exception as e:
            logger.error(f"Error checking SSID availability: {e}")
            raise


class CaptivePortalSessionRepository(BaseTenantRepository[CaptivePortalSession]):
    """Repository for captive portal session management."""

    model = CaptivePortalSession

    def find_active_session(
        self,
        session_token: Optional[str] = None,
        client_mac: Optional[str] = None,
        portal_id: Optional[str] = None,
    ) -> Optional[CaptivePortalSession]:
        """Find active session by token, MAC address, or portal."""
        try:
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.session_status == SessionStatus.ACTIVE,
                    self.model.expires_at > datetime.now(timezone.utc),
                )
            )

            if session_token:
                query = query.filter(self.model.session_token == session_token)
            elif client_mac and portal_id:
                query = query.filter(
                    and_(
                        self.model.client_mac == client_mac,
                        self.model.portal_id == portal_id,
                    )
                )
            else:
                return None

            return query.first()
        except Exception as e:
            logger.error(f"Error finding active session: {e}")
            raise

    def list_sessions_for_portal(
        self,
        portal_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[CaptivePortalSession], int]:
        """List sessions for a specific portal."""
        try:
            query = self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == self.tenant_id,
                    self.model.portal_id == portal_id,
                )
            )

            if status:
                query = query.filter(self.model.session_status == status)

            total = query.count()

            sessions = (
                query.options(
                    joinedload(self.model.user), joinedload(self.model.customer)
                )
                .order_by(desc(self.model.start_time))
                .offset(offset)
                .limit(limit)
                .all()
            )

            return sessions, total
        except Exception as e:
            logger.error(f"Error listing sessions for portal {portal_id}: {e}")
            raise

    def get_active_session_count(self, portal_id: str) -> int:
        """Get count of active sessions for a portal."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                        self.model.session_status == SessionStatus.ACTIVE,
                        self.model.expires_at > datetime.now(timezone.utc),
                    )
                )
                .count()
            )
        except Exception as e:
            logger.error(f"Error counting active sessions: {e}")
            raise

    def terminate_expired_sessions(self) -> int:
        """Terminate all expired sessions."""
        try:
            now = datetime.now(timezone.utc)
            expired_count = (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.session_status == SessionStatus.ACTIVE,
                        self.model.expires_at <= now,
                    )
                )
                .update(
                    {
                        "session_status": SessionStatus.EXPIRED,
                        "end_time": now,
                        "termination_reason": "Session expired",
                    }
                )
            )

            self.db.commit()
            return expired_count
        except Exception as e:
            logger.error(f"Error terminating expired sessions: {e}")
            self.db.rollback()
            raise

    def update_session_usage(
        self,
        session_id: str,
        bytes_downloaded: int,
        bytes_uploaded: int,
        packets_received: int = 0,
        packets_sent: int = 0,
    ) -> bool:
        """Update session usage statistics."""
        try:
            updated = (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.id == session_id,
                    )
                )
                .update(
                    {
                        "bytes_downloaded": self.model.bytes_downloaded
                        + bytes_downloaded,
                        "bytes_uploaded": self.model.bytes_uploaded + bytes_uploaded,
                        "packets_received": self.model.packets_received
                        + packets_received,
                        "packets_sent": self.model.packets_sent + packets_sent,
                        "last_activity": datetime.now(timezone.utc),
                    }
                )
            )

            self.db.commit()
            return updated > 0
        except Exception as e:
            logger.error(f"Error updating session usage: {e}")
            self.db.rollback()
            raise


class AuthMethodRepository(BaseTenantRepository[AuthMethod]):
    """Repository for authentication method management."""

    model = AuthMethod

    def find_by_portal_id(self, portal_id: str) -> list[AuthMethod]:
        """Get all authentication methods for a portal."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                        self.model.is_enabled is True,
                    )
                )
                .order_by(self.model.display_order, self.model.name)
                .all()
            )
        except Exception as e:
            logger.error(f"Error finding auth methods for portal {portal_id}: {e}")
            raise

    def find_default_method(self, portal_id: str) -> Optional[AuthMethod]:
        """Find the default authentication method for a portal."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                        self.model.is_enabled is True,
                        self.model.is_default is True,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error finding default auth method: {e}")
            raise


class VoucherRepository(BaseTenantRepository[Voucher]):
    """Repository for voucher management."""

    model = Voucher

    def find_by_code(self, code: str, portal_id: str) -> Optional[Voucher]:
        """Find voucher by code and portal."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.code == code,
                        self.model.portal_id == portal_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error finding voucher by code {code}: {e}")
            raise

    def find_valid_vouchers(self, portal_id: str) -> list[Voucher]:
        """Find all valid vouchers for a portal."""
        try:
            now = datetime.now(timezone.utc)
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                        self.model.voucher_status == VoucherStatus.ACTIVE,
                        self.model.valid_from <= now,
                        or_(
                            self.model.valid_until.is_(None),
                            self.model.valid_until > now,
                        ),
                    )
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error finding valid vouchers: {e}")
            raise

    def redeem_voucher(self, voucher_id: str, user_id: str) -> bool:
        """Mark voucher as redeemed."""
        try:
            now = datetime.now(timezone.utc)
            updated = (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.id == voucher_id,
                    )
                )
                .update(
                    {
                        "redemption_count": self.model.redemption_count + 1,
                        "last_redeemed_at": now,
                        "redeemed_by_user_id": user_id,
                    }
                )
            )

            # Set first redemption time if this is the first use
            voucher = self.get_by_id(voucher_id)
            if voucher and not voucher.first_redeemed_at:
                voucher.first_redeemed_at = now

            self.db.commit()
            return updated > 0
        except Exception as e:
            logger.error(f"Error redeeming voucher: {e}")
            self.db.rollback()
            raise


class VoucherBatchRepository(BaseTenantRepository[VoucherBatch]):
    """Repository for voucher batch management."""

    model = VoucherBatch

    def find_with_vouchers(self, batch_id: str) -> Optional[VoucherBatch]:
        """Find batch with associated vouchers."""
        try:
            return (
                self.db.query(self.model)
                .options(selectinload(self.model.vouchers))
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.id == batch_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error finding batch with vouchers: {e}")
            raise


class PortalCustomizationRepository(BaseTenantRepository[PortalCustomization]):
    """Repository for portal customization management."""

    model = PortalCustomization

    def find_by_portal_id(self, portal_id: str) -> Optional[PortalCustomization]:
        """Find customization settings for a portal."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                    )
                )
                .first()
            )
        except Exception as e:
            logger.error(f"Error finding customization for portal {portal_id}: {e}")
            raise


class PortalUsageStatsRepository(BaseTenantRepository[PortalUsageStats]):
    """Repository for portal usage statistics."""

    model = PortalUsageStats

    def get_stats_for_period(
        self,
        portal_id: str,
        start_date: datetime,
        end_date: datetime,
        period_type: str = "day",
    ) -> list[PortalUsageStats]:
        """Get usage statistics for a time period."""
        try:
            return (
                self.db.query(self.model)
                .filter(
                    and_(
                        self.model.tenant_id == self.tenant_id,
                        self.model.portal_id == portal_id,
                        self.model.period_type == period_type,
                        self.model.stats_date >= start_date,
                        self.model.stats_date <= end_date,
                    )
                )
                .order_by(self.model.stats_date)
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise

    def aggregate_session_stats(
        self, portal_id: str, stats_date: datetime, period_type: str = "day"
    ) -> dict:
        """Aggregate session statistics for a specific period."""
        try:
            # This would typically aggregate from the sessions table
            # Implementation would depend on specific aggregation requirements
            CaptivePortalSessionRepository(self.db, self.tenant_id)

            # Calculate period boundaries
            if period_type == "day":
                start_time = stats_date.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                end_time = stats_date.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            else:
                # Add logic for other period types (hour, week, month)
                start_time = stats_date
                end_time = stats_date

            # Aggregate data from sessions
            sessions_query = self.db.query(CaptivePortalSession).filter(
                and_(
                    CaptivePortalSession.tenant_id == self.tenant_id,
                    CaptivePortalSession.portal_id == portal_id,
                    CaptivePortalSession.start_time >= start_time,
                    CaptivePortalSession.start_time <= end_time,
                )
            )

            sessions_query.count()

            # Calculate other aggregations
            usage_stats = sessions_query.with_entities(
                func.count(CaptivePortalSession.id).label("total_sessions"),
                func.count(CaptivePortalSession.user_id.distinct()).label(
                    "unique_users"
                ),
                func.avg(
                    func.extract(
                        "epoch",
                        CaptivePortalSession.end_time - CaptivePortalSession.start_time,
                    )
                    / 60
                ).label("avg_duration_minutes"),
                func.sum(CaptivePortalSession.bytes_downloaded).label(
                    "total_downloaded"
                ),
                func.sum(CaptivePortalSession.bytes_uploaded).label("total_uploaded"),
            ).first()

            return {
                "total_sessions": usage_stats.total_sessions or 0,
                "unique_users": usage_stats.unique_users or 0,
                "avg_session_duration": float(usage_stats.avg_duration_minutes or 0),
                "total_bytes_downloaded": usage_stats.total_downloaded or 0,
                "total_bytes_uploaded": usage_stats.total_uploaded or 0,
            }
        except Exception as e:
            logger.error(f"Error aggregating session stats: {e}")
            raise
