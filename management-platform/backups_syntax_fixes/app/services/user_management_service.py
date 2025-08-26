"""
User management and RBAC service.
Provides comprehensive user lifecycle management, role-based access control,
and permission management across the platform.
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from passlib.context import CryptContext

from core.exceptions import ValidationError, AuthenticationError, AuthorizationError
from core.logging import get_logger
from models.user import User
from models.tenant import Tenant
from schemas.user_management import ()
    UserCreate,
    UserUpdate,
    RoleCreate,
    PermissionAssignment,
    UserInvite,
    PasswordReset,
    UserStatus
, timezone)

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """System-wide user roles."""
    SUPER_ADMIN = "super_admin"
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    SUPPORT = "support"
    READONLY = "readonly"
    API_USER = "api_user"


class Permission(str, Enum):
    """System permissions."""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_INVITE = "user:invite"
    USER_SUSPEND = "user:suspend"
    USER_IMPERSONATE = "user:impersonate"
    
    # Tenant management
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_SUSPEND = "tenant:suspend"
    
    # Billing
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_PROCESS = "billing:process"
    BILLING_REFUND = "billing:refund"
    
    # Infrastructure
    INFRA_READ = "infrastructure:read"
    INFRA_WRITE = "infrastructure:write"
    INFRA_PROVISION = "infrastructure:provision"
    INFRA_DEPROVISION = "infrastructure:deprovision"
    INFRA_SCALE = "infrastructure:scale"
    
    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_BACKUP = "system:backup"
    
    # Security
    SECURITY_READ = "security:read"
    SECURITY_WRITE = "security:write"
    SECURITY_AUDIT = "security:audit"
    
    # API access
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"


# Role to permissions mapping
ROLE_PERMISSIONS = {
    UserRole.SUPER_ADMIN: [p for p in Permission],  # All permissions
    UserRole.PLATFORM_ADMIN: [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_DELETE, Permission.USER_INVITE, Permission.USER_SUSPEND,
        Permission.TENANT_CREATE, Permission.TENANT_READ, Permission.TENANT_UPDATE, Permission.TENANT_SUSPEND,
        Permission.BILLING_READ, Permission.BILLING_WRITE, Permission.BILLING_PROCESS,
        Permission.INFRA_READ, Permission.INFRA_WRITE, Permission.INFRA_PROVISION, Permission.INFRA_DEPROVISION, Permission.INFRA_SCALE,
        Permission.SYSTEM_METRICS, Permission.SYSTEM_LOGS,
        Permission.SECURITY_READ, Permission.SECURITY_AUDIT,
        Permission.API_READ, Permission.API_WRITE
    ],
    UserRole.TENANT_ADMIN: [
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_INVITE,
        Permission.TENANT_READ, Permission.TENANT_UPDATE,
        Permission.BILLING_READ,
        Permission.INFRA_READ, Permission.INFRA_WRITE,
        Permission.API_READ
    ],
    UserRole.TENANT_USER: [
        Permission.USER_READ,
        Permission.TENANT_READ,
        Permission.BILLING_READ,
        Permission.INFRA_READ,
        Permission.API_READ
    ],
    UserRole.SUPPORT: [
        Permission.USER_READ,
        Permission.TENANT_READ,
        Permission.BILLING_READ,
        Permission.INFRA_READ,
        Permission.SYSTEM_LOGS,
        Permission.SECURITY_READ
    ],
    UserRole.READONLY: [
        Permission.USER_READ,
        Permission.TENANT_READ,
        Permission.BILLING_READ,
        Permission.INFRA_READ,
        Permission.SYSTEM_METRICS
    ],
    UserRole.API_USER: [
        Permission.API_READ,
        Permission.API_WRITE
    ]
}


class UserManagementService:
    """Service for managing users, roles, and permissions."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_user():
        self,
        user_data: UserCreate,
        created_by: str,
        tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create a new user with role and permissions.
        
        Args:
            user_data: User creation data
            created_by: User ID of the creator
            tenant_id: Optional tenant ID for tenant-scoped users
            
        Returns:
            Dict containing user details and credentials
        """
        try:
            logger.info(f"Creating user {user_data.email}")
            
            # Check if user already exists
            existing_user_result = await self.db.execute()
                select(User).where(User.email == user_data.email)
            )
            existing_user = existing_user_result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError(f"User with email {user_data.email} already exists")
            
            # Validate role
            if user_data.role not in [role.value for role in UserRole]:
                raise ValidationError(f"Invalid role: {user_data.role}")
            
            # Generate password if not provided
            if not user_data.password:
                password = self._generate_secure_password()
            else:
                password = user_data.password
            
            # Hash password
            hashed_password = pwd_context.hash(password)
            
            # Create user
            user = User()
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                role=user_data.role,
                tenant_id=tenant_id,
                is_active=user_data.is_active,
                permissions=ROLE_PERMISSIONS.get(UserRole(user_data.role), []),
                metadata={
                    "created_by": created_by,
                    "password_generated": not bool(user_data.password),
                    "must_change_password": not bool(user_data.password)
                }
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User {user.email} created successfully with ID {user.id}")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "is_active": user.is_active,
                "permissions": user.permissions,
                "created_at": user.created_at.isoformat(),
                "temporary_password": password if not user_data.password else None
            }
            
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            raise ValidationError(f"User creation failed: {e}")
    
    async def update_user():
        self,
        user_id: UUID,
        user_update: UserUpdate,
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update user information and permissions.
        
        Args:
            user_id: User identifier
            user_update: Updated user data
            updated_by: User ID of the updater
            
        Returns:
            Dict containing updated user details
        """
        try:
            logger.info(f"Updating user {user_id}")
            
            # Get existing user
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            # Update fields
            if user_update.full_name is not None:
                user.full_name = user_update.full_name
            
            if user_update.role is not None:
                if user_update.role not in [role.value for role in UserRole]:
                    raise ValidationError(f"Invalid role: {user_update.role}")
                user.role = user_update.role
                # Update permissions based on new role
                user.permissions = ROLE_PERMISSIONS.get(UserRole(user_update.role), [])
            
            if user_update.is_active is not None:
                user.is_active = user_update.is_active
            
            if user_update.permissions is not None:
                # Validate permissions
                valid_permissions = [p.value for p in Permission]
                invalid_perms = [p for p in user_update.permissions if p not in valid_permissions]
                if invalid_perms:
                    raise ValidationError(f"Invalid permissions: {invalid_perms}")
                user.permissions = user_update.permissions
            
            if user_update.metadata:
                user.metadata = user.metadata or {}
                user.metadata.update(user_update.metadata)
            
            # Update metadata
            user.metadata = user.metadata or {}
            user.metadata.update({)
                "updated_by": updated_by,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            
            user.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User {user_id} updated successfully")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "is_active": user.is_active,
                "permissions": user.permissions,
                "updated_at": user.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"User update failed: {e}")
            raise ValidationError(f"User update failed: {e}")
    
    async def delete_user():
        self,
        user_id: UUID,
        deleted_by: str,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """
        Delete or deactivate a user.
        
        Args:
            user_id: User identifier
            deleted_by: User ID of the deleter
            soft_delete: Whether to soft delete (deactivate) or hard delete
            
        Returns:
            Dict containing deletion status
        """
        try:
            logger.info(f"Deleting user {user_id} (soft_delete={soft_delete})")
            
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            if soft_delete:
                # Deactivate user
                user.is_active = False
                user.metadata = user.metadata or {}
                user.metadata.update({)
                    "deactivated_by": deleted_by,
                    "deactivated_at": datetime.now(timezone.utc).isoformat()
                })
                user.updated_at = datetime.now(timezone.utc)
                await self.db.commit()
                
                return {
                    "user_id": str(user_id),
                    "status": "deactivated",
                    "deactivated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                # Hard delete user
                await self.db.execute(delete(User).where(User.id == user_id)
                await self.db.commit()
                
                return {
                    "user_id": str(user_id),
                    "status": "deleted",
                    "deleted_at": datetime.now(timezone.utc).isoformat()
                }
            
        except Exception as e:
            logger.error(f"User deletion failed: {e}")
            raise ValidationError(f"User deletion failed: {e}")
    
    async def invite_user():
        self,
        invitation: UserInvite,
        invited_by: str,
        tenant_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Invite a user to join the platform or tenant.
        
        Args:
            invitation: User invitation data
            invited_by: User ID of the inviter
            tenant_id: Optional tenant ID for tenant invitations
            
        Returns:
            Dict containing invitation details
        """
        try:
            logger.info(f"Inviting user {invitation.email}")
            
            # Check if user already exists
            existing_user_result = await self.db.execute()
                select(User).where(User.email == invitation.email)
            )
            existing_user = existing_user_result.scalar_one_or_none()
            
            if existing_user:
                raise ValidationError(f"User with email {invitation.email} already exists")
            
            # Generate invitation token
            invitation_token = self._generate_invitation_token(invitation.email, invited_by)
            
            # Create user record in pending state
            user = User()
                email=invitation.email,
                full_name=invitation.full_name,
                role=invitation.role,
                tenant_id=tenant_id,
                is_active=False,  # Will be activated when invitation is accepted
                permissions=ROLE_PERMISSIONS.get(UserRole(invitation.role), []),
                metadata={
                    "status": "invited",
                    "invitation_token": invitation_token,
                    "invited_by": invited_by,
                    "invited_at": datetime.now(timezone.utc).isoformat(),
                    "invitation_expires_at": (datetime.now(timezone.utc) + timedelta(days=7).isoformat())
                    "custom_message": invitation.custom_message
                }
            )
            
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            # TODO: Send invitation email via notification service
            
            logger.info(f"User invitation created for {invitation.email}")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "invitation_token": invitation_token,
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7).isoformat())
                "invited_at": datetime.now(timezone.utc).isoformat(),
                "status": "invitation_sent"
            }
            
        except Exception as e:
            logger.error(f"User invitation failed: {e}")
            raise ValidationError(f"User invitation failed: {e}")
    
    async def accept_invitation():
        self,
        invitation_token: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Accept a user invitation and complete registration.
        
        Args:
            invitation_token: Invitation token
            password: User password
            
        Returns:
            Dict containing activation status
        """
        try:
            logger.info(f"Processing invitation acceptance")
            
            # Find user by invitation token
            result = await self.db.execute()
                select(User).where()
                    User.metadata.contains({"invitation_token": invitation_token})
                )
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError("Invalid invitation token")
            
            # Check if invitation has expired
            metadata = user.metadata or {}
            expires_at_str = metadata.get("invitation_expires_at")
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00')
                if datetime.now(timezone.utc) > expires_at:
                    raise ValidationError("Invitation has expired")
            
            # Check if already activated
            if user.is_active:
                raise ValidationError("Invitation has already been accepted")
            
            # Set password and activate user
            user.hashed_password = pwd_context.hash(password)
            user.is_active = True
            
            # Update metadata
            user.metadata.update({)
                "status": "active",
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "invitation_accepted": True
            })
            
            user.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            
            logger.info(f"User {user.email} activated successfully")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "status": "activated",
                "activated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Invitation acceptance failed: {e}")
            raise ValidationError(f"Invitation acceptance failed: {e}")
    
    async def reset_password():
        self,
        email: str,
        new_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reset user password.
        
        Args:
            email: User email
            new_password: New password (if None, generates temporary password)
            
        Returns:
            Dict containing reset status and temporary password if generated
        """
        try:
            logger.info(f"Resetting password for {email}")
            
            result = await self.db.execute()
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User with email {email} not found")
            
            # Generate password if not provided
            if not new_password:
                new_password = self._generate_secure_password()
                password_generated = True
            else:
                password_generated = False
            
            # Update password
            user.hashed_password = pwd_context.hash(new_password)
            user.metadata = user.metadata or {}
            user.metadata.update({)
                "password_reset_at": datetime.now(timezone.utc).isoformat(),
                "must_change_password": password_generated
            })
            user.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(f"Password reset for {email}")
            
            return {
                "user_id": str(user.id),
                "email": user.email,
                "status": "password_reset",
                "temporary_password": new_password if password_generated else None,
                "must_change_password": password_generated,
                "reset_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            raise ValidationError(f"Password reset failed: {e}")
    
    async def change_password():
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Change user password with current password verification.
        
        Args:
            user_id: User identifier
            current_password: Current password
            new_password: New password
            
        Returns:
            Dict containing change status
        """
        try:
            logger.info(f"Changing password for user {user_id}")
            
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            # Verify current password
            if not pwd_context.verify(current_password, user.hashed_password):
                raise AuthenticationError("Current password is incorrect")
            
            # Update password
            user.hashed_password = pwd_context.hash(new_password)
            user.metadata = user.metadata or {}
            user.metadata.update({)
                "password_changed_at": datetime.now(timezone.utc).isoformat(),
                "must_change_password": False
            })
            user.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(f"Password changed for user {user_id}")
            
            return {
                "user_id": str(user_id),
                "status": "password_changed",
                "changed_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            raise ValidationError(f"Password change failed: {e}")
    
    async def get_user_permissions():
        self,
        user_id: UUID,
        include_role_permissions: bool = True
    ) -> Dict[str, Any]:
        """
        Get user permissions including role-based and custom permissions.
        
        Args:
            user_id: User identifier
            include_role_permissions: Whether to include role-based permissions
            
        Returns:
            Dict containing user permissions
        """
        try:
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            permissions = set(user.permissions or [])
            
            if include_role_permissions:
                role_permissions = ROLE_PERMISSIONS.get(UserRole(user.role), [])
                permissions.update(role_permissions)
            
            return {
                "user_id": str(user_id),
                "role": user.role,
                "permissions": list(permissions),
                "role_permissions": ROLE_PERMISSIONS.get(UserRole(user.role), []) if include_role_permissions else [],
                "custom_permissions": user.permissions or []
            }
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            raise ValidationError(f"Failed to get user permissions: {e}")
    
    async def assign_permissions():
        self,
        user_id: UUID,
        permissions: List[str],
        assigned_by: str
    ) -> Dict[str, Any]:
        """
        Assign custom permissions to a user.
        
        Args:
            user_id: User identifier
            permissions: List of permissions to assign
            assigned_by: User ID of the assigner
            
        Returns:
            Dict containing assignment status
        """
        try:
            logger.info(f"Assigning permissions to user {user_id}")
            
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            # Validate permissions
            valid_permissions = [p.value for p in Permission]
            invalid_perms = [p for p in permissions if p not in valid_permissions]
            if invalid_perms:
                raise ValidationError(f"Invalid permissions: {invalid_perms}")
            
            # Assign permissions
            current_permissions = set(user.permissions or [])
            current_permissions.update(permissions)
            user.permissions = list(current_permissions)
            
            # Update metadata
            user.metadata = user.metadata or {}
            user.metadata.update({)
                "permissions_assigned_by": assigned_by,
                "permissions_assigned_at": datetime.now(timezone.utc).isoformat()
            })
            user.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(f"Permissions assigned to user {user_id}")
            
            return {
                "user_id": str(user_id),
                "permissions": user.permissions,
                "assigned_at": datetime.now(timezone.utc).isoformat(),
                "assigned_by": assigned_by
            }
            
        except Exception as e:
            logger.error(f"Permission assignment failed: {e}")
            raise ValidationError(f"Permission assignment failed: {e}")
    
    async def revoke_permissions():
        self,
        user_id: UUID,
        permissions: List[str],
        revoked_by: str
    ) -> Dict[str, Any]:
        """
        Revoke permissions from a user.
        
        Args:
            user_id: User identifier
            permissions: List of permissions to revoke
            revoked_by: User ID of the revoker
            
        Returns:
            Dict containing revocation status
        """
        try:
            logger.info(f"Revoking permissions from user {user_id}")
            
            result = await self.db.execute()
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError(f"User {user_id} not found")
            
            # Revoke permissions
            current_permissions = set(user.permissions or [])
            current_permissions.difference_update(permissions)
            user.permissions = list(current_permissions)
            
            # Update metadata
            user.metadata = user.metadata or {}
            user.metadata.update({)
                "permissions_revoked_by": revoked_by,
                "permissions_revoked_at": datetime.now(timezone.utc).isoformat()
            })
            user.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(f"Permissions revoked from user {user_id}")
            
            return {
                "user_id": str(user_id),
                "permissions": user.permissions,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "revoked_by": revoked_by
            }
            
        except Exception as e:
            logger.error(f"Permission revocation failed: {e}")
            raise ValidationError(f"Permission revocation failed: {e}")
    
    async def get_users_by_tenant():
        self,
        tenant_id: UUID,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get all users for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            include_inactive: Whether to include inactive users
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            Dict containing tenant users
        """
        try:
            # Build query
            query = select(User).where(User.tenant_id == tenant_id)
            
            if not include_inactive:
                query = query.where(User.is_active == True)
            
            query = query.order_by(User.created_at.desc().limit(limit).offset(offset)
            
            # Get users
            result = await self.db.execute(query)
            users = result.scalars().all()
            
            # Get total count
            count_query = select(func.count(User.id).where(User.tenant_id == tenant_id)
            if not include_inactive:
                count_query = count_query.where(User.is_active == True)
            
            count_result = await self.db.execute(count_query)
            total_count = count_result.scalar()
            
            user_list = []
            for user in users:
                user_list.append({)
                    "user_id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "is_active": user.is_active,
                    "permissions": user.permissions,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "created_at": user.created_at.isoformat(),
                    "metadata": user.metadata
                })
            
            return {
                "tenant_id": str(tenant_id),
                "users": user_list,
                "total_count": total_count,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get tenant users: {e}")
            raise ValidationError(f"Failed to get tenant users: {e}")
    
    # Private helper methods
    
    def _generate_secure_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        import string
        import random
        
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(characters) for _ in range(length)
        return password
    
    def _generate_invitation_token(self, email: str, invited_by: str) -> str:
        """Generate a unique invitation token."""
        timestamp = str(int(datetime.now(timezone.utc).timestamp()
        data = f"{email}:{invited_by}:{timestamp}:{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode().hexdigest()
    
    def _validate_permission(self, permission: str) -> bool:
        """Validate if permission exists."""
        return permission in [p.value for p in Permission]