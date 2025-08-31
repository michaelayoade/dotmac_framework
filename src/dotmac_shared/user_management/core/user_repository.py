"""
User Repository for Unified User Management.

Provides database operations for user lifecycle management across platforms.
Implements the repository pattern for clean separation of data access logic.
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    and_,
    asc,
    desc,
    func,
    or_,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship

from ..schemas.lifecycle_schemas import (
    UserActivation,
    UserDeactivation,
    UserDeletion,
    UserLifecycleEvent,
    UserRegistration,
)
from ..schemas.user_schemas import (
    UserCreate,
    UserProfile,
    UserResponse,
    UserSearchQuery,
    UserSearchResult,
    UserStatus,
    UserSummary,
    UserType,
    UserUpdate,
)

Base = declarative_base()


class UserModel(Base):
    """Database model for unified user management."""

    __tablename__ = "users"

    # Primary identification
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)

    # Basic information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    user_type = Column(SQLEnum(UserType), nullable=False, index=True)

    # Status and verification
    status = Column(
        SQLEnum(UserStatus), nullable=False, default=UserStatus.PENDING, index=True
    )
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Platform association
    tenant_id = Column(PostgresUUID(as_uuid=True), nullable=True, index=True)

    # Extended profile data (JSON)
    profile_data = Column(JSON, nullable=True)
    preferences = Column(JSON, nullable=True)

    # Platform-specific data
    platform_specific = Column(JSON, nullable=True)

    # Security information
    email_verified_at = Column(DateTime, nullable=True)
    phone_verified_at = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False)

    # Role and permission data
    roles = Column(JSON, nullable=True, default=list)
    permissions = Column(JSON, nullable=True, default=list)

    # Activity tracking
    login_count = Column(Integer, default=0)
    failed_login_count = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    last_failed_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # Registration information
    registration_source = Column(String(50), nullable=True)
    referral_code = Column(String(50), nullable=True)
    terms_accepted = Column(Boolean, default=False)
    privacy_policy_accepted = Column(Boolean, default=False)
    marketing_consent = Column(Boolean, default=False)

    # Approval workflow
    requires_approval = Column(Boolean, default=False)
    approval_level = Column(String(50), nullable=True)
    approved_by = Column(PostgresUUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime, nullable=True)

    # Lifecycle tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    deactivated_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    # Indexes for performance
    __table_args__ = (
        Index("idx_users_email_status", "email", "status"),
        Index("idx_users_username_status", "username", "status"),
        Index("idx_users_type_tenant", "user_type", "tenant_id"),
        Index("idx_users_status_active", "status", "is_active"),
        Index("idx_users_created_at", "created_at"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "user_type": self.user_type,
            "status": self.status,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "tenant_id": self.tenant_id,
            "profile": self.profile_data,
            "platform_specific": self.platform_specific or {},
            "email_verified_at": self.email_verified_at,
            "phone_verified_at": self.phone_verified_at,
            "mfa_enabled": self.mfa_enabled,
            "roles": self.roles or [],
            "permissions": self.permissions or [],
            "login_count": self.login_count,
            "failed_login_count": self.failed_login_count,
            "last_login": self.last_login,
            "last_failed_login": self.last_failed_login,
            "password_changed_at": self.password_changed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserLifecycleEventModel(Base):
    """Database model for user lifecycle events."""

    __tablename__ = "user_lifecycle_events"

    # Primary identification
    event_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    # Event information
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)

    # Event metadata
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source_platform = Column(String(50), nullable=False)
    triggered_by = Column(PostgresUUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Event outcome
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)

    # Related events
    parent_event_id = Column(PostgresUUID(as_uuid=True), nullable=True)
    correlation_id = Column(String(100), nullable=True, index=True)

    # Indexes
    __table_args__ = (
        Index("idx_lifecycle_user_type", "user_id", "event_type"),
        Index("idx_lifecycle_timestamp", "timestamp"),
        Index("idx_lifecycle_platform", "source_platform"),
    )


class UserPasswordModel(Base):
    """Database model for user password management."""

    __tablename__ = "user_passwords"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(255), nullable=True)
    algorithm = Column(String(50), default="bcrypt", nullable=False)

    # Password history for prevention of reuse
    previous_passwords = Column(JSON, nullable=True, default=list)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    expires_at = Column(DateTime, nullable=True)

    # Reset tokens
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    reset_attempts = Column(Integer, default=0)

    __table_args__ = (
        Index("idx_user_passwords_user_id", "user_id"),
        Index("idx_user_passwords_reset_token", "reset_token"),
    )


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize user repository."""
        self.db_session = db_session

    # User CRUD Operations
    async def create_user(self, user_registration: UserRegistration) -> UserResponse:
        """Create new user from registration data."""

        user_model = UserModel(
            username=user_registration.username,
            email=user_registration.email,
            first_name=user_registration.first_name,
            last_name=user_registration.last_name,
            user_type=user_registration.user_type,
            tenant_id=user_registration.tenant_id,
            registration_source=user_registration.registration_source.value,
            referral_code=user_registration.referral_code,
            terms_accepted=user_registration.terms_accepted,
            privacy_policy_accepted=user_registration.privacy_policy_accepted,
            marketing_consent=user_registration.marketing_consent,
            requires_approval=user_registration.requires_approval,
            approval_level=user_registration.approval_level,
            platform_specific=user_registration.platform_specific,
            preferences={
                "language": user_registration.language,
                "timezone": user_registration.timezone,
            },
        )

        self.db_session.add(user_model)
        await self.db_session.commit()
        await self.db_session.refresh(user_model)

        return self._model_to_response(user_model)

    async def get_user_by_id(self, user_id: UUID) -> Optional[UserResponse]:
        """Get user by ID."""

        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._model_to_response(user_model)
        return None

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email address."""

        query = select(UserModel).where(UserModel.email == email.lower())
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._model_to_response(user_model)
        return None

    async def get_user_by_username(self, username: str) -> Optional[UserResponse]:
        """Get user by username."""

        query = select(UserModel).where(UserModel.username == username.lower())
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._model_to_response(user_model)
        return None

    async def get_user_by_identifier(self, identifier: str) -> Optional[UserResponse]:
        """Get user by email or username."""

        query = select(UserModel).where(
            or_(
                UserModel.email == identifier.lower(),
                UserModel.username == identifier.lower(),
            )
        )
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if user_model:
            return self._model_to_response(user_model)
        return None

    async def update_user(
        self, user_id: UUID, update_data: UserUpdate
    ) -> Optional[UserResponse]:
        """Update user information."""

        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return None

        # Update basic fields
        if update_data.first_name is not None:
            user_model.first_name = update_data.first_name
        if update_data.last_name is not None:
            user_model.last_name = update_data.last_name
        if update_data.email is not None:
            user_model.email = update_data.email.lower()
        if update_data.phone is not None:
            user_model.phone = update_data.phone

        # Update status fields
        if update_data.is_active is not None:
            user_model.is_active = update_data.is_active
        if update_data.is_verified is not None:
            user_model.is_verified = update_data.is_verified
        if update_data.status is not None:
            user_model.status = update_data.status

        # Update profile data
        if update_data.profile is not None:
            user_model.profile_data = (
                update_data.profile.model_dump() if update_data.profile else None
            )

        # Update platform-specific data
        if update_data.platform_specific is not None:
            current_platform_data = user_model.platform_specific or {}
            current_platform_data.update(update_data.platform_specific)
            user_model.platform_specific = current_platform_data

        # Update roles and permissions
        if update_data.roles is not None:
            user_model.roles = update_data.roles
        if update_data.permissions is not None:
            user_model.permissions = update_data.permissions

        user_model.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(user_model)

        return self._model_to_response(user_model)

    async def delete_user(self, user_id: UUID, soft_delete: bool = True) -> bool:
        """Delete user (soft or hard delete)."""

        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return False

        if soft_delete:
            user_model.status = UserStatus.DELETED
            user_model.is_active = False
            user_model.deleted_at = datetime.utcnow()
            user_model.updated_at = datetime.utcnow()
            await self.db_session.commit()
        else:
            await self.db_session.delete(user_model)
            await self.db_session.commit()

        return True

    # User Search Operations
    async def search_users(self, search_query: UserSearchQuery) -> UserSearchResult:
        """Search users with filters and pagination."""

        query = select(UserModel)

        # Apply filters
        filters = []

        if search_query.query:
            search_term = f"%{search_query.query}%"
            filters.append(
                or_(
                    UserModel.username.ilike(search_term),
                    UserModel.email.ilike(search_term),
                    UserModel.first_name.ilike(search_term),
                    UserModel.last_name.ilike(search_term),
                    func.concat(UserModel.first_name, " ", UserModel.last_name).ilike(
                        search_term
                    ),
                )
            )

        if search_query.user_type:
            filters.append(UserModel.user_type == search_query.user_type)

        if search_query.status:
            filters.append(UserModel.status == search_query.status)

        if search_query.tenant_id:
            filters.append(UserModel.tenant_id == search_query.tenant_id)

        if search_query.is_active is not None:
            filters.append(UserModel.is_active == search_query.is_active)

        if search_query.is_verified is not None:
            filters.append(UserModel.is_verified == search_query.is_verified)

        if search_query.created_after:
            filters.append(UserModel.created_at >= search_query.created_after)

        if search_query.created_before:
            filters.append(UserModel.created_at <= search_query.created_before)

        if search_query.last_login_after:
            filters.append(UserModel.last_login >= search_query.last_login_after)

        if search_query.last_login_before:
            filters.append(UserModel.last_login <= search_query.last_login_before)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = (
            select(func.count(UserModel.id)).where(and_(*filters))
            if filters
            else select(func.count(UserModel.id))
        )
        count_result = await self.db_session.execute(count_query)
        total_count = count_result.scalar()

        # Apply sorting
        sort_column = getattr(UserModel, search_query.sort_by, UserModel.created_at)
        if search_query.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply pagination
        offset = (search_query.page - 1) * search_query.page_size
        query = query.offset(offset).limit(search_query.page_size)

        # Execute query
        result = await self.db_session.execute(query)
        user_models = result.scalars().all()

        # Convert to summaries
        users = [self._model_to_summary(user_model) for user_model in user_models]

        # Calculate pagination info
        total_pages = (
            total_count + search_query.page_size - 1
        ) // search_query.page_size

        return UserSearchResult(
            users=users,
            total_count=total_count,
            page=search_query.page,
            page_size=search_query.page_size,
            total_pages=total_pages,
        )

    # User Status Operations
    async def activate_user(
        self, user_id: UUID, verification_data: Dict[str, Any] = None
    ) -> bool:
        """Activate user account."""

        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return False

        user_model.status = UserStatus.ACTIVE
        user_model.is_active = True
        user_model.is_verified = True

        # Update verification timestamps
        if verification_data:
            if verification_data.get("email_verified"):
                user_model.email_verified_at = datetime.utcnow()
            if verification_data.get("phone_verified"):
                user_model.phone_verified_at = datetime.utcnow()

        user_model.updated_at = datetime.utcnow()

        await self.db_session.commit()
        return True

    async def deactivate_user(self, user_id: UUID, reason: str = None) -> bool:
        """Deactivate user account."""

        query = select(UserModel).where(UserModel.id == user_id)
        result = await self.db_session.execute(query)
        user_model = result.scalar_one_or_none()

        if not user_model:
            return False

        user_model.status = UserStatus.INACTIVE
        user_model.is_active = False
        user_model.deactivated_at = datetime.utcnow()
        user_model.updated_at = datetime.utcnow()

        await self.db_session.commit()
        return True

    # Lifecycle Event Operations
    async def create_lifecycle_event(self, event: UserLifecycleEvent) -> bool:
        """Create user lifecycle event record."""

        event_model = UserLifecycleEventModel(
            event_id=event.event_id,
            user_id=event.user_id,
            event_type=event.event_type,
            event_data=event.event_data,
            timestamp=event.timestamp,
            source_platform=event.source_platform,
            triggered_by=event.triggered_by,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            success=event.success,
            error_message=event.error_message,
            parent_event_id=event.parent_event_id,
            correlation_id=event.correlation_id,
        )

        self.db_session.add(event_model)
        await self.db_session.commit()
        return True

    async def get_user_lifecycle_events(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get user lifecycle events."""

        query = select(UserLifecycleEventModel).where(
            UserLifecycleEventModel.user_id == user_id
        )

        if start_date:
            query = query.where(UserLifecycleEventModel.timestamp >= start_date)

        if end_date:
            query = query.where(UserLifecycleEventModel.timestamp <= end_date)

        if event_types:
            query = query.where(UserLifecycleEventModel.event_type.in_(event_types))

        query = query.order_by(desc(UserLifecycleEventModel.timestamp)).limit(limit)

        result = await self.db_session.execute(query)
        event_models = result.scalars().all()

        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "event_data": event.event_data,
                "timestamp": event.timestamp,
                "source_platform": event.source_platform,
                "triggered_by": event.triggered_by,
                "success": event.success,
                "error_message": event.error_message,
            }
            for event in event_models
        ]

    # Password Operations
    async def store_user_password(
        self, user_id: UUID, password_hash: str, algorithm: str = "bcrypt"
    ) -> bool:
        """Store user password hash."""

        # Check if password record exists
        query = select(UserPasswordModel).where(UserPasswordModel.user_id == user_id)
        result = await self.db_session.execute(query)
        password_model = result.scalar_one_or_none()

        if password_model:
            # Update existing password
            # Store previous password in history
            previous = password_model.previous_passwords or []
            previous.append(
                {
                    "hash": password_model.password_hash,
                    "algorithm": password_model.algorithm,
                    "created_at": password_model.updated_at.isoformat(),
                }
            )
            # Keep only last 5 passwords
            previous = previous[-5:]

            password_model.password_hash = password_hash
            password_model.algorithm = algorithm
            password_model.previous_passwords = previous
            password_model.updated_at = datetime.utcnow()
        else:
            # Create new password record
            password_model = UserPasswordModel(
                user_id=user_id, password_hash=password_hash, algorithm=algorithm
            )
            self.db_session.add(password_model)

        await self.db_session.commit()
        return True

    async def get_user_password_hash(self, user_id: UUID) -> Optional[str]:
        """Get user password hash."""

        query = select(UserPasswordModel.password_hash).where(
            UserPasswordModel.user_id == user_id
        )
        result = await self.db_session.execute(query)
        password_hash = result.scalar_one_or_none()

        return password_hash

    # Helper Methods
    def _model_to_response(self, user_model: UserModel) -> UserResponse:
        """Convert UserModel to UserResponse."""

        user_dict = user_model.to_dict()
        return UserResponse(**user_dict)

    def _model_to_summary(self, user_model: UserModel) -> UserSummary:
        """Convert UserModel to UserSummary."""

        return UserSummary(
            id=user_model.id,
            username=user_model.username,
            email=user_model.email,
            first_name=user_model.first_name,
            last_name=user_model.last_name,
            user_type=user_model.user_type,
            status=user_model.status,
            is_active=user_model.is_active,
            created_at=user_model.created_at,
            last_login=user_model.last_login,
            avatar_url=(
                user_model.profile_data.get("avatar_url")
                if user_model.profile_data
                else None
            ),
        )
