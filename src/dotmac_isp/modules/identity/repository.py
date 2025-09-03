"""
Identity management repositories.
Data access layer for users, customers, and authentication entities.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from dotmac_isp.shared.base_repository import BaseTenantRepository as BaseRepository
from .models import (
    User, Customer, PortalAccess, UserSession, 
    AuthenticationLog, PasswordResetToken, AuthToken,
    LoginAttempt, UserRole, AccountStatus, CustomerType, Role
)

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for user management operations."""
    
    def __init__(self, db_session: AsyncSession, tenant_id: str):
        super().__init__(db_session, User, tenant_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        try:
            stmt = select(User).where(
                and_(
                    User.tenant_id == self.tenant_id,
                    User.email == email,
                    User.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            stmt = select(User).where(
                and_(
                    User.tenant_id == self.tenant_id,
                    User.username == username,
                    User.is_active == True
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    async def get_by_portal_type(self, portal_type: str) -> List[User]:
        """Get users by portal type."""
        try:
            stmt = select(User).where(
                and_(
                    User.tenant_id == self.tenant_id,
                    User.portal_type == portal_type,
                    User.is_active == True
                )
            ).order_by(desc(User.created_at))
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting users by portal type {portal_type}: {e}")
            return []

    async def update_last_login(self, user_id: UUID) -> bool:
        """Update user's last login timestamp."""
        try:
            user = await self.get_by_id(user_id)
            if user:
                user.last_login = datetime.now(timezone.utc)
                user.failed_login_attempts = 0
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    async def increment_failed_login(self, user_id: UUID) -> bool:
        """Increment failed login attempts."""
        try:
            user = await self.get_by_id(user_id)
            if user:
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error incrementing failed login for user {user_id}: {e}")
            return False


class CustomerRepository(BaseRepository[Customer]):
    """Repository for customer management operations."""
    
    def __init__(self, db_session: AsyncSession, tenant_id: str):
        super().__init__(db_session, Customer, tenant_id)

    async def get_by_customer_number(self, customer_number: str) -> Optional[Customer]:
        """Get customer by customer number."""
        try:
            stmt = select(Customer).where(
                and_(
                    Customer.tenant_id == self.tenant_id,
                    Customer.customer_number == customer_number
                )
            ).options(selectinload(Customer.user))
            
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting customer by number {customer_number}: {e}")
            return None

    async def get_by_email(self, email: str) -> Optional[Customer]:
        """Get customer by email address."""
        try:
            stmt = select(Customer).where(
                and_(
                    Customer.tenant_id == self.tenant_id,
                    Customer.email == email
                )
            ).options(selectinload(Customer.user))
            
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting customer by email {email}: {e}")
            return None

    async def get_by_status(self, status: str) -> List[Customer]:
        """Get customers by status."""
        try:
            stmt = select(Customer).where(
                and_(
                    Customer.tenant_id == self.tenant_id,
                    Customer.status == status
                )
            ).order_by(desc(Customer.created_at))
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting customers by status {status}: {e}")
            return []

    async def search_customers(
        self, 
        search_term: str, 
        limit: int = 50
    ) -> List[Customer]:
        """Search customers by name, email, or customer number."""
        try:
            stmt = select(Customer).where(
                and_(
                    Customer.tenant_id == self.tenant_id,
                    or_(
                        Customer.first_name.ilike(f"%{search_term}%"),
                        Customer.last_name.ilike(f"%{search_term}%"),
                        Customer.email.ilike(f"%{search_term}%"),
                        Customer.customer_number.ilike(f"%{search_term}%"),
                        Customer.company_name.ilike(f"%{search_term}%")
                    )
                )
            ).limit(limit).order_by(desc(Customer.created_at))
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error searching customers with term {search_term}: {e}")
            return []


class RoleRepository(BaseRepository[UserRole]):
    """Repository for role management operations."""
    
    def __init__(self, db_session: AsyncSession, tenant_id: str):
        super().__init__(db_session, UserRole, tenant_id)

    async def get_user_roles(self, user_id: UUID) -> List[UserRole]:
        """Get all roles for a user."""
        try:
            stmt = select(UserRole).where(
                and_(
                    UserRole.tenant_id == self.tenant_id,
                    UserRole.user_id == user_id,
                    UserRole.is_active == True
                )
            ).options(selectinload(UserRole.user))
            
            result = await self.db.execute(stmt)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}")
            return []

    async def assign_role(
        self, 
        user_id: UUID, 
        role: Role, 
        assigned_by: UUID,
        expires_at: Optional[datetime] = None
    ) -> Optional[UserRole]:
        """Assign role to user."""
        try:
            user_role = UserRole(
                tenant_id=self.tenant_id,
                user_id=user_id,
                role=role,
                assigned_by=assigned_by,
                expires_at=expires_at
            )
            
            self.db.add(user_role)
            await self.db.commit()
            await self.db.refresh(user_role)
            return user_role
        except Exception as e:
            logger.error(f"Error assigning role {role} to user {user_id}: {e}")
            return None

    async def revoke_role(self, user_id: UUID, role: Role) -> bool:
        """Revoke role from user."""
        try:
            stmt = select(UserRole).where(
                and_(
                    UserRole.tenant_id == self.tenant_id,
                    UserRole.user_id == user_id,
                    UserRole.role == role,
                    UserRole.is_active == True
                )
            )
            
            result = await self.db.execute(stmt)
            user_role = result.scalar_one_or_none()
            
            if user_role:
                user_role.is_active = False
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error revoking role {role} from user {user_id}: {e}")
            return False


class AuthenticationRepository:
    """Repository for authentication-related operations (global scope)."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def log_authentication_attempt(
        self,
        email: Optional[str] = None,
        username: Optional[str] = None,
        tenant_id: Optional[str] = None,
        success: bool = False,
        failure_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        portal_type: Optional[str] = None
    ) -> Optional[AuthenticationLog]:
        """Log authentication attempt."""
        try:
            log_entry = AuthenticationLog(
                email=email,
                username=username,
                tenant_id=tenant_id,
                attempt_type="login",
                success=success,
                failure_reason=failure_reason,
                ip_address=ip_address,
                user_agent=user_agent,
                portal_type=portal_type
            )
            
            self.db.add(log_entry)
            await self.db.commit()
            await self.db.refresh(log_entry)
            return log_entry
        except Exception as e:
            logger.error(f"Error logging authentication attempt: {e}")
            return None

    async def create_session(
        self,
        session_id: str,
        user_id: UUID,
        tenant_id: str,
        portal_type: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[UserSession]:
        """Create user session."""
        try:
            session = UserSession(
                id=session_id,
                user_id=user_id,
                tenant_id=tenant_id,
                portal_type=portal_type,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
            return session
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return None

    async def get_active_session(self, session_id: str) -> Optional[UserSession]:
        """Get active session by ID."""
        try:
            stmt = select(UserSession).where(
                and_(
                    UserSession.id == session_id,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            )
            
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session."""
        try:
            session = await self.get_active_session(session_id)
            if session:
                session.is_active = False
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error invalidating session {session_id}: {e}")
            return False


# Export all repositories
__all__ = [
    'UserRepository',
    'CustomerRepository', 
    'RoleRepository',
    'AuthenticationRepository'
]