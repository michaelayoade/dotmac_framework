"""
Production-ready user management schemas using Pydantic 2.
All schemas leverage DRY patterns from base_schemas.
"""

from .user_schemas import *
from .auth_schemas import *
from .profile_schemas import *
from .role_schemas import *

__all__ = [
    # User schemas
    "UserCreateSchema",
    "UserUpdateSchema", 
    "UserResponseSchema",
    "UserSummarySchema",
    "UserSearchSchema",
    "UserBulkOperationSchema",
    
    # Authentication schemas
    "LoginRequestSchema",
    "LoginResponseSchema",
    "TokenResponseSchema",
    "RefreshTokenSchema",
    "PasswordResetSchema",
    "ChangePasswordSchema",
    "MFASetupSchema",
    "MFAVerifySchema",
    
    # Profile schemas
    "UserProfileSchema",
    "ProfileUpdateSchema",
    "ContactInfoSchema",
    "PreferencesSchema",
    "NotificationSettingsSchema",
    
    # Role schemas
    "RoleSchema",
    "PermissionSchema",
    "RoleAssignmentSchema",
    "PermissionCheckSchema",
]