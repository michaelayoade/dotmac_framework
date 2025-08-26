"""
User management schemas for validation and serialization.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator

from schemas.common import BaseSchema


class UserCreate(BaseModel):
    """User creation schema."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User full name")
    password: Optional[str] = Field(None, min_length=8, description="User password")
    role: str = Field(..., description="User role")
    is_active: bool = Field(default=True, description="Whether user is active")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = [
            'super_admin', 'platform_admin', 'tenant_admin', 
            'tenant_user', 'support', 'readonly', 'api_user'
        ]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: Optional[str] = Field(None, description="Updated full name")
    role: Optional[str] = Field(None, description="Updated role")
    is_active: Optional[bool] = Field(None, description="Updated active status")
    permissions: Optional[List[str]] = Field(None, description="Custom permissions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Updated metadata")
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = [
                'super_admin', 'platform_admin', 'tenant_admin', 
                'tenant_user', 'support', 'readonly', 'api_user'
            ]
            if v not in valid_roles:
                raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UserInvite(BaseModel):
    """User invitation schema."""
    email: EmailStr = Field(..., description="Email address to invite")
    full_name: Optional[str] = Field(None, description="Full name of invitee")
    role: str = Field(..., description="Role to assign")
    custom_message: Optional[str] = Field(None, description="Custom invitation message")
    expires_in_days: int = Field(default=7, ge=1, le=30, description="Invitation expiry in days")
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = [
            'super_admin', 'platform_admin', 'tenant_admin', 
            'tenant_user', 'support', 'readonly', 'api_user'
        ]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UserInviteResponse(BaseModel):
    """User invitation response schema."""
    user_id: UUID = Field(..., description="Created user identifier")
    email: str = Field(..., description="Invited email address")
    invitation_token: str = Field(..., description="Invitation token")
    expires_at: datetime = Field(..., description="Invitation expiry")
    invited_at: datetime = Field(..., description="Invitation timestamp")
    status: str = Field(..., description="Invitation status")


class AcceptInvitation(BaseModel):
    """Accept invitation schema."""
    invitation_token: str = Field(..., description="Invitation token")
    password: str = Field(..., min_length=8, description="User password")
    full_name: Optional[str] = Field(None, description="User full name")


class PasswordReset(BaseModel):
    """Password reset schema."""
    email: EmailStr = Field(..., description="User email address")
    new_password: Optional[str] = Field(None, min_length=8, description="New password")


class PasswordChange(BaseModel):
    """Password change schema."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class UserStatus(BaseModel):
    """User status schema."""
    user_id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    is_active: bool = Field(..., description="Whether user is active")
    status: str = Field(..., description="User status")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserProfile(BaseModel):
    """User profile schema."""
    user_id: UUID = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="User role")
    tenant_id: Optional[UUID] = Field(None, description="Associated tenant")
    is_active: bool = Field(..., description="Whether user is active")
    permissions: List[str] = Field(..., description="User permissions")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RoleDefinition(BaseModel):
    """Role definition schema."""
    role: str = Field(..., description="Role name")
    display_name: str = Field(..., description="Human-readable role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="Role permissions")
    is_system_role: bool = Field(..., description="Whether this is a system role")


class PermissionDefinition(BaseModel):
    """Permission definition schema."""
    permission: str = Field(..., description="Permission name")
    category: str = Field(..., description="Permission category")
    display_name: str = Field(..., description="Human-readable permission name")
    description: str = Field(..., description="Permission description")
    is_dangerous: bool = Field(default=False, description="Whether this is a dangerous permission")


class PermissionAssignment(BaseModel):
    """Permission assignment schema."""
    user_id: UUID = Field(..., description="User identifier")
    permissions: List[str] = Field(..., description="Permissions to assign")
    reason: Optional[str] = Field(None, description="Reason for assignment")


class PermissionRevocation(BaseModel):
    """Permission revocation schema."""
    user_id: UUID = Field(..., description="User identifier")
    permissions: List[str] = Field(..., description="Permissions to revoke")
    reason: Optional[str] = Field(None, description="Reason for revocation")


class RoleCreate(BaseModel):
    """Role creation schema (for custom roles)."""
    name: str = Field(..., min_length=3, max_length=50, description="Role name")
    display_name: str = Field(..., description="Human-readable role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="Role permissions")
    tenant_id: Optional[UUID] = Field(None, description="Tenant ID for tenant-specific roles")


class RoleUpdate(BaseModel):
    """Role update schema."""
    display_name: Optional[str] = Field(None, description="Updated display name")
    description: Optional[str] = Field(None, description="Updated description")
    permissions: Optional[List[str]] = Field(None, description="Updated permissions")
    is_active: Optional[bool] = Field(None, description="Whether role is active")


class UserSession(BaseModel):
    """User session schema."""
    session_id: str = Field(..., description="Session identifier")
    user_id: UUID = Field(..., description="User identifier")
    ip_address: str = Field(..., description="IP address")
    user_agent: str = Field(..., description="User agent")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    is_active: bool = Field(..., description="Whether session is active")


class UserActivity(BaseModel):
    """User activity schema."""
    activity_id: UUID = Field(..., description="Activity identifier")
    user_id: UUID = Field(..., description="User identifier")
    activity_type: str = Field(..., description="Type of activity")
    resource: Optional[str] = Field(None, description="Resource affected")
    details: Dict[str, Any] = Field(..., description="Activity details")
    ip_address: Optional[str] = Field(None, description="IP address")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Activity timestamp")


class UserLoginAttempt(BaseModel):
    """User login attempt schema."""
    attempt_id: UUID = Field(..., description="Attempt identifier")
    email: str = Field(..., description="Email used in attempt")
    success: bool = Field(..., description="Whether attempt was successful")
    ip_address: str = Field(..., description="IP address")
    user_agent: str = Field(..., description="User agent")
    failure_reason: Optional[str] = Field(None, description="Reason for failure")
    timestamp: datetime = Field(..., description="Attempt timestamp")


class UserAuditLog(BaseModel):
    """User audit log schema."""
    log_id: UUID = Field(..., description="Log identifier")
    user_id: UUID = Field(..., description="User identifier")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: Optional[str] = Field(None, description="Resource identifier")
    old_values: Optional[Dict[str, Any]] = Field(None, description="Previous values")
    new_values: Optional[Dict[str, Any]] = Field(None, description="New values")
    performed_by: UUID = Field(..., description="User who performed the action")
    ip_address: Optional[str] = Field(None, description="IP address")
    timestamp: datetime = Field(..., description="Action timestamp")


class UserSecuritySettings(BaseModel):
    """User security settings schema."""
    user_id: UUID = Field(..., description="User identifier")
    two_factor_enabled: bool = Field(default=False, description="Two-factor authentication enabled")
    password_expires_at: Optional[datetime] = Field(None, description="Password expiration")
    account_locked: bool = Field(default=False, description="Whether account is locked")
    failed_login_attempts: int = Field(default=0, description="Number of failed login attempts")
    last_password_change: Optional[datetime] = Field(None, description="Last password change")
    security_questions_set: bool = Field(default=False, description="Security questions configured")


class TwoFactorSetup(BaseModel):
    """Two-factor authentication setup schema."""
    user_id: UUID = Field(..., description="User identifier")
    method: str = Field(..., description="2FA method (totp, sms, email)")
    phone_number: Optional[str] = Field(None, description="Phone number for SMS")
    backup_codes: Optional[List[str]] = Field(None, description="Backup codes")


class TwoFactorVerification(BaseModel):
    """Two-factor authentication verification schema."""
    user_id: UUID = Field(..., description="User identifier")
    code: str = Field(..., description="Verification code")
    method: str = Field(..., description="2FA method used")


class ApiKeyCreate(BaseModel):
    """API key creation schema."""
    name: str = Field(..., min_length=3, max_length=100, description="API key name")
    permissions: List[str] = Field(..., description="API key permissions")
    expires_in_days: Optional[int] = Field(None, gt=0, le=365, description="Expiration in days")
    description: Optional[str] = Field(None, description="API key description")


class ApiKey(BaseModel):
    """API key schema."""
    key_id: UUID = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    key_prefix: str = Field(..., description="Key prefix (first 8 characters)")
    permissions: List[str] = Field(..., description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last used timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    created_at: datetime = Field(..., description="Creation timestamp")


class ApiKeyResponse(BaseModel):
    """API key creation response schema."""
    key_id: UUID = Field(..., description="API key identifier")
    name: str = Field(..., description="API key name")
    api_key: str = Field(..., description="Full API key (shown only once)")
    permissions: List[str] = Field(..., description="API key permissions")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class UserBulkOperation(BaseModel):
    """Bulk user operation schema."""
    user_ids: List[UUID] = Field(..., min_items=1, description="List of user IDs")
    operation: str = Field(..., description="Operation to perform")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class UserBulkOperationResult(BaseModel):
    """Bulk user operation result schema."""
    operation: str = Field(..., description="Operation performed")
    total_users: int = Field(..., description="Total users processed")
    successful: int = Field(..., description="Successful operations")
    failed: int = Field(..., description="Failed operations")
    errors: List[Dict[str, Any]] = Field(..., description="List of errors")
    results: List[Dict[str, Any]] = Field(..., description="Operation results")


class UserImport(BaseModel):
    """User import schema."""
    users: List[UserCreate] = Field(..., min_items=1, description="Users to import")
    tenant_id: Optional[UUID] = Field(None, description="Target tenant ID")
    send_invitations: bool = Field(default=True, description="Send invitation emails")
    skip_existing: bool = Field(default=True, description="Skip users that already exist")


class UserImportResult(BaseModel):
    """User import result schema."""
    total_users: int = Field(..., description="Total users in import")
    imported: int = Field(..., description="Successfully imported users")
    skipped: int = Field(..., description="Skipped users")
    failed: int = Field(..., description="Failed imports")
    errors: List[Dict[str, Any]] = Field(..., description="Import errors")
    imported_users: List[Dict[str, Any]] = Field(..., description="Successfully imported users")


class UserExport(BaseModel):
    """User export schema."""
    tenant_id: Optional[UUID] = Field(None, description="Tenant to export users from")
    include_inactive: bool = Field(default=False, description="Include inactive users")
    format: str = Field(default="json", description="Export format (json, csv)")
    fields: Optional[List[str]] = Field(None, description="Fields to include in export")


class UserStatistics(BaseModel):
    """User statistics schema."""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    inactive_users: int = Field(..., description="Number of inactive users")
    users_by_role: Dict[str, int] = Field(..., description="User count by role")
    users_by_tenant: Dict[str, int] = Field(..., description="User count by tenant")
    recent_logins: int = Field(..., description="Users with recent logins (last 7 days)")
    pending_invitations: int = Field(..., description="Pending invitations")
    locked_accounts: int = Field(..., description="Locked accounts")
    last_updated: datetime = Field(..., description="Statistics update timestamp")