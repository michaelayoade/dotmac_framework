"""
Production-ready unified user management system.

This module provides comprehensive user management functionality
leveraging existing DRY patterns, Pydantic 2, and production best practices.

Key Features:
- Unified user models across ISP and Management platforms
- Comprehensive authentication and authorization
- Multi-tenant support with proper isolation
- Complete audit trail and lifecycle management
- Role-based access control (RBAC)
- Password policy enforcement
- Account lifecycle management
- Session management
- Multi-factor authentication support
"""

from .models import *
from .schemas import *
from .services import *
from .repositories import *
from .auth import *

__version__ = "2.0.0"
__all__ = [
    # Models
    "UserModel",
    "UserRoleModel", 
    "UserSessionModel",
    "UserInvitationModel",
    "UserAuditModel",
    "UserProfileModel",
    
    # Schemas
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserResponseSchema",
    "UserProfileSchema",
    "UserAuthSchema",
    "UserSearchSchema",
    
    # Services
    "UserService",
    "AuthService",
    "UserLifecycleService",
    "UserProfileService",
    
    # Repositories
    "UserRepository",
    "UserRoleRepository",
    "UserSessionRepository",
    "UserAuditRepository",
    
    # Auth
    "UserAuthenticator",
    "PermissionChecker",
    "RoleManager",
]