"""Repository pattern for portal management database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func, desc

from .models import (
    PortalAccount,
    PortalSession,
    PortalLoginAttempt,
    PortalPreferences,
    PortalAccountStatus,
    PortalAccountType,
    SessionStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class PortalAccountRepository:
    """Repository for portal account database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, account_data: Dict[str, Any]) -> PortalAccount:
        """Create a new portal account."""
        try:
            account = PortalAccount(
                id=str(uuid4()), tenant_id=str(self.tenant_id), **account_data
            )

            self.db.add(account)
            self.db.commit()
            self.db.refresh(account)
            return account

        except IntegrityError as e:
            self.db.rollback()
            if "portal_id" in str(e):
                raise ConflictError(
                    f"Portal ID {account_data.get('portal_id')} already exists"
                )
            elif "email" in str(e):
                raise ConflictError(f"Email {account_data.get('email')} already exists")
            raise ConflictError("Portal account creation failed due to data conflict")

    def get_by_id(self, account_id: str) -> Optional[PortalAccount]:
        """Get portal account by ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.id == account_id,
                    PortalAccount.tenant_id == str(self.tenant_id),
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_portal_id(self, portal_id: str) -> Optional[PortalAccount]:
        """Get portal account by portal ID."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.portal_id == portal_id,
                    PortalAccount.tenant_id == str(self.tenant_id),
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_email(self, email: str) -> Optional[PortalAccount]:
        """Get portal account by email."""
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.email == email,
                    PortalAccount.tenant_id == str(self.tenant_id),
                    PortalAccount.is_deleted == False,
                )
            )
            .first()
        )

    def list_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        account_type: Optional[PortalAccountType] = None,
        status: Optional[PortalAccountStatus] = None,
        search_term: Optional[str] = None,
    ) -> List[PortalAccount]:
        """List portal accounts with filtering."""
        query = self.db.query(PortalAccount).filter(
            and_(
                PortalAccount.tenant_id == str(self.tenant_id),
                PortalAccount.is_deleted == False,
            )
        )

        if account_type:
            query = query.filter(PortalAccount.account_type == account_type)
        if status:
            query = query.filter(PortalAccount.account_status == status)
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                or_(
                    PortalAccount.portal_id.ilike(search_pattern),
                    PortalAccount.email.ilike(search_pattern),
                    PortalAccount.first_name.ilike(search_pattern),
                    PortalAccount.last_name.ilike(search_pattern),
                )
            )

        return (
            query.order_by(desc(PortalAccount.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update(
        self, account_id: str, update_data: Dict[str, Any]
    ) -> Optional[PortalAccount]:
        """Update portal account."""
        account = self.get_by_id(account_id)
        if not account:
            return None

        for key, value in update_data.items():
            if hasattr(account, key):
                setattr(account, key, value)

        account.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account_id: str) -> bool:
        """Soft delete portal account."""
        account = self.get_by_id(account_id)
        if not account:
            return False

        account.soft_delete()
        self.db.commit()
        return True

    def count_by_type(self) -> List[Dict[str, Any]]:
        """Count accounts by type."""
        result = (
            self.db.query(
                PortalAccount.account_type, func.count(PortalAccount.id).label("count")
            )
            .filter(
                and_(
                    PortalAccount.tenant_id == str(self.tenant_id),
                    PortalAccount.is_deleted == False,
                )
            )
            .group_by(PortalAccount.account_type)
            .all()
        )

        return [
            {"account_type": row.account_type, "count": row.count} for row in result
        ]

    def get_recently_created(self, days: int = 30) -> List[PortalAccount]:
        """Get recently created accounts."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(PortalAccount)
            .filter(
                and_(
                    PortalAccount.tenant_id == str(self.tenant_id),
                    PortalAccount.is_deleted == False,
                    PortalAccount.created_at >= cutoff_date,
                )
            )
            .order_by(desc(PortalAccount.created_at))
            .all()
        )


class PortalSessionRepository:
    """Repository for portal session database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, session_data: Dict[str, Any]) -> PortalSession:
        """Create a new portal session."""
        session = PortalSession(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **session_data
        )

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: str) -> Optional[PortalSession]:
        """Get portal session by ID."""
        return (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.id == session_id,
                    PortalSession.tenant_id == str(self.tenant_id),
                    PortalSession.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_session_token(self, session_token: str) -> Optional[PortalSession]:
        """Get portal session by session token."""
        return (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.session_token == session_token,
                    PortalSession.tenant_id == str(self.tenant_id),
                    PortalSession.is_deleted == False,
                )
            )
            .first()
        )

    def get_active_sessions(self, account_id: str) -> List[PortalSession]:
        """Get active sessions for an account."""
        return (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.account_id == account_id,
                    PortalSession.tenant_id == str(self.tenant_id),
                    PortalSession.is_deleted == False,
                    PortalSession.session_status == SessionStatus.ACTIVE,
                    PortalSession.expires_at > datetime.utcnow(),
                )
            )
            .order_by(desc(PortalSession.created_at))
            .all()
        )

    def update(
        self, session_id: str, update_data: Dict[str, Any]
    ) -> Optional[PortalSession]:
        """Update portal session."""
        session = self.get_by_id(session_id)
        if not session:
            return None

        for key, value in update_data.items():
            if hasattr(session, key):
                setattr(session, key, value)

        session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(session)
        return session

    def expire_session(self, session_id: str) -> bool:
        """Expire a portal session."""
        session = self.get_by_id(session_id)
        if not session:
            return False

        session.session_status = SessionStatus.EXPIRED
        session.ended_at = datetime.utcnow()
        session.updated_at = datetime.utcnow()
        self.db.commit()
        return True

    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_count = (
            self.db.query(PortalSession)
            .filter(
                and_(
                    PortalSession.tenant_id == str(self.tenant_id),
                    PortalSession.expires_at < datetime.utcnow(),
                    PortalSession.session_status == SessionStatus.ACTIVE,
                )
            )
            .update(
                {
                    PortalSession.session_status: SessionStatus.EXPIRED,
                    PortalSession.ended_at: datetime.utcnow(),
                    PortalSession.updated_at: datetime.utcnow(),
                }
            )
        )

        self.db.commit()
        return expired_count


class PortalLoginAttemptRepository:
    """Repository for portal login attempt database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, attempt_data: Dict[str, Any]) -> PortalLoginAttempt:
        """Create a new login attempt record."""
        attempt = PortalLoginAttempt(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **attempt_data
        )

        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_recent_attempts(
        self, identifier: str, minutes: int = 15
    ) -> List[PortalLoginAttempt]:
        """Get recent login attempts for an identifier (email/portal_id)."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(PortalLoginAttempt)
            .filter(
                and_(
                    PortalLoginAttempt.tenant_id == str(self.tenant_id),
                    PortalLoginAttempt.login_identifier == identifier,
                    PortalLoginAttempt.attempt_time >= cutoff_time,
                )
            )
            .order_by(desc(PortalLoginAttempt.attempt_time))
            .all()
        )

    def count_failed_attempts(self, identifier: str, minutes: int = 15) -> int:
        """Count failed login attempts for an identifier in time window."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(PortalLoginAttempt)
            .filter(
                and_(
                    PortalLoginAttempt.tenant_id == str(self.tenant_id),
                    PortalLoginAttempt.login_identifier == identifier,
                    PortalLoginAttempt.attempt_time >= cutoff_time,
                    PortalLoginAttempt.success == False,
                )
            )
            .count()
        )

    def get_attempts_by_ip(
        self, ip_address: str, minutes: int = 15
    ) -> List[PortalLoginAttempt]:
        """Get login attempts by IP address."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(PortalLoginAttempt)
            .filter(
                and_(
                    PortalLoginAttempt.tenant_id == str(self.tenant_id),
                    PortalLoginAttempt.ip_address == ip_address,
                    PortalLoginAttempt.attempt_time >= cutoff_time,
                )
            )
            .order_by(desc(PortalLoginAttempt.attempt_time))
            .all()
        )


class PortalPreferencesRepository:
    """Repository for portal preferences database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    def create(self, preferences_data: Dict[str, Any]) -> PortalPreferences:
        """Create portal preferences."""
        preferences = PortalPreferences(
            id=str(uuid4()), tenant_id=str(self.tenant_id), **preferences_data
        )

        self.db.add(preferences)
        self.db.commit()
        self.db.refresh(preferences)
        return preferences

    def get_by_account_id(self, account_id: str) -> Optional[PortalPreferences]:
        """Get preferences by account ID."""
        return (
            self.db.query(PortalPreferences)
            .filter(
                and_(
                    PortalPreferences.account_id == account_id,
                    PortalPreferences.tenant_id == str(self.tenant_id),
                    PortalPreferences.is_deleted == False,
                )
            )
            .first()
        )

    def update(
        self, account_id: str, update_data: Dict[str, Any]
    ) -> Optional[PortalPreferences]:
        """Update portal preferences."""
        preferences = self.get_by_account_id(account_id)
        if not preferences:
            # Create preferences if they don't exist
            create_data = {"account_id": account_id, **update_data}
            return self.create(create_data)

        for key, value in update_data.items():
            if hasattr(preferences, key):
                setattr(preferences, key, value)

        preferences.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(preferences)
        return preferences

    def get_or_create_preferences(self, account_id: str) -> PortalPreferences:
        """Get preferences or create default ones."""
        preferences = self.get_by_account_id(account_id)
        if not preferences:
            default_data = {
                "account_id": account_id,
                "theme": "light",
                "language": "en",
                "timezone": "UTC",
                "email_notifications": True,
                "sms_notifications": False,
                "marketing_emails": False,
                "security_alerts": True,
            }
            preferences = self.create(default_data)

        return preferences
