"""
User management service for identity operations.
Handles user lifecycle and management operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from dotmac_isp.shared.base_service import BaseService
from ..models import User, Role
from ..repository import UserRepository, RoleRepository

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """User management service."""
    
    def __init__(self, db_session, tenant_id: str):
        super().__init__(db_session, tenant_id)
        self.user_repo = UserRepository(db_session, tenant_id)
        self.role_repo = RoleRepository(db_session, tenant_id)

    async def create_user(self, user_data: Dict[str, Any], created_by: str) -> Optional[Dict[str, Any]]:
        """Create new user."""
        try:
            # Check if email already exists
            existing_user = await self.user_repo.get_by_email(user_data["email"])
            if existing_user:
                logger.warning(f"User creation failed: email {user_data['email']} already exists")
                return None

            # Create user entity
            user = User(
                tenant_id=self.tenant_id,
                username=user_data["username"],
                email=user_data["email"],
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                portal_type=user_data.get("portal_type", "customer"),
                is_active=user_data.get("is_active", True),
                password_hash=user_data.get("password_hash")  # Should be hashed
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Created user {user.id} by {created_by}")
            
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "portal_type": user.portal_type,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "tenant_id": user.tenant_id
            }
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await self.db.rollback()
            return None

    async def get_user_by_id(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return None
                
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "portal_type": user.portal_type,
                "is_active": user.is_active,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "created_at": user.created_at.isoformat(),
                "tenant_id": user.tenant_id
            }
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def update_user(
        self, 
        user_id: UUID, 
        user_data: Dict[str, Any], 
        updated_by: str
    ) -> Optional[Dict[str, Any]]:
        """Update user information."""
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return None
            
            # Update allowed fields
            if "first_name" in user_data:
                user.first_name = user_data["first_name"]
            if "last_name" in user_data:
                user.last_name = user_data["last_name"]
            if "is_active" in user_data:
                user.is_active = user_data["is_active"]
            if "portal_type" in user_data:
                user.portal_type = user_data["portal_type"]
            
            user.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"Updated user {user_id} by {updated_by}")
            
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "portal_type": user.portal_type,
                "is_active": user.is_active,
                "updated_at": user.updated_at.isoformat(),
                "tenant_id": user.tenant_id
            }
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            await self.db.rollback()
            return None

    async def list_users(
        self, 
        portal_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List users with optional filtering."""
        try:
            if portal_type:
                users = await self.user_repo.get_by_portal_type(portal_type)
            else:
                users = await self.user_repo.list_all(limit=limit, offset=offset)
            
            return [
                {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "portal_type": user.portal_type,
                    "is_active": user.is_active,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "created_at": user.created_at.isoformat(),
                    "tenant_id": user.tenant_id
                }
                for user in users
            ]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []

    async def assign_role(
        self, 
        user_id: UUID, 
        role: Role, 
        assigned_by: UUID,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """Assign role to user."""
        try:
            user_role = await self.role_repo.assign_role(
                user_id=user_id,
                role=role,
                assigned_by=assigned_by,
                expires_at=expires_at
            )
            
            if user_role:
                logger.info(f"Assigned role {role} to user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error assigning role {role} to user {user_id}: {e}")
            return False

    async def revoke_role(self, user_id: UUID, role: Role) -> bool:
        """Revoke role from user."""
        try:
            success = await self.role_repo.revoke_role(user_id, role)
            if success:
                logger.info(f"Revoked role {role} from user {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error revoking role {role} from user {user_id}: {e}")
            return False

    async def get_user_roles(self, user_id: UUID) -> List[str]:
        """Get user's roles."""
        try:
            user_roles = await self.role_repo.get_user_roles(user_id)
            return [role.role.value for role in user_roles if role.is_active]
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}")
            return []


# Export service
__all__ = ['UserService']