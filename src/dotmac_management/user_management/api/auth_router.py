"""
Authentication API router for user management v2 system.
Provides comprehensive authentication endpoints using RouterFactory patterns.
"""
from typing import Optional
from uuid import UUID

from dotmac_shared.api.dependencies import get_current_tenant_id, get_current_user
from dotmac_shared.auth.services import AuthService
from dotmac_shared.common.exceptions import standard_exception_handler
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.application import RouterFactory
from dotmac.database.session import get_db_session
from dotmac.platform.observability.logging import get_logger

from ..schemas.auth_schemas import (
    ApiKeyCreateSchema,
    ApiKeySchema,
    ChangePasswordSchema,
    LoginRequestSchema,
    LoginResponseSchema,
    MFASetupResponseSchema,
    MFASetupSchema,
    MFAVerifySchema,
    SessionInfoSchema,
)
from ..schemas.user_schemas import UserResponseSchema

logger = get_logger(__name__)
security = HTTPBearer()


def create_auth_router() -> APIRouter:
    """Create authentication router with all endpoints."""
    router = APIRouter(prefix="/auth", tags=["authentication"])

    @router.post("/login", response_model=LoginResponseSchema)
    @standard_exception_handler
    async def login(
        request: LoginRequestSchema,
        http_request: Request,
        db: AsyncSession = Depends(get_db_session),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> LoginResponseSchema:
        """
        Authenticate user and create session.

        Returns access token and session information on successful authentication.
        If MFA is required, returns temporary token for MFA verification.
        """
        auth_service = AuthService(db, tenant_id)

        # Extract client information
        client_ip = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("User-Agent")
        device_fingerprint = http_request.headers.get("X-Device-Fingerprint")

        result = await auth_service.authenticate_user(
            username=request.username,
            password=request.password,
            client_ip=client_ip,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
        )

        if not result.success:
            if result.error_code == "ACCOUNT_LOCKED":
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED, detail=result.message
                )
            elif result.error_code == "ACCOUNT_INACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message
                )

        response_data = {
            "success": result.success,
            "message": result.message,
            "requires_mfa": result.requires_mfa or False,
        }

        if result.requires_mfa:
            response_data.update(
                {"temp_token": result.temp_token, "user_id": result.user_id}
            )
        else:
            response_data.update(
                {
                    "access_token": result.access_token,
                    "refresh_token": result.refresh_token,
                    "token_type": "bearer",
                    "expires_at": result.expires_at,
                    "user_id": result.user_id,
                    "session_id": result.session_id,
                }
            )

        return LoginResponseSchema(**response_data)

    @router.post("/mfa/verify", response_model=LoginResponseSchema)
    @standard_exception_handler
    async def verify_mfa(
        request: MFAVerifySchema,
        http_request: Request,
        db: AsyncSession = Depends(get_db_session),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> LoginResponseSchema:
        """
        Verify MFA code and complete login process.

        Uses temporary token from initial authentication to verify MFA code
        and complete the login process with full access tokens.
        """
        auth_service = AuthService(db, tenant_id)

        client_ip = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("User-Agent")
        device_fingerprint = http_request.headers.get("X-Device-Fingerprint")

        result = await auth_service.verify_mfa_and_complete_login(
            temp_token=request.temp_token,
            mfa_code=request.mfa_code,
            client_ip=client_ip,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint,
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=result.message
            )

        return LoginResponseSchema(
            success=True,
            message=result.message,
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            token_type="bearer",  # noqa: S106 - token type label, not a secret
            expires_at=result.expires_at,
            user_id=result.user_id,
            session_id=result.session_id,
            requires_mfa=False,
        )

    @router.post("/logout")
    @standard_exception_handler
    async def logout(
        http_request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """
        Logout current user and invalidate session.

        Requires valid access token. Invalidates the current session.
        """
        auth_service = AuthService(db, tenant_id)

        # Extract session ID from request context (set by auth middleware)
        session_id = getattr(http_request.state, "session_id", None)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found",
            )

        client_ip = http_request.client.host if http_request.client else None
        success = await auth_service.logout_user(session_id, client_ip)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to logout"
            )

        return {"message": "Logout successful"}

    @router.post("/refresh", response_model=dict)
    @standard_exception_handler
    async def refresh_token(
        refresh_token: str,
        db: AsyncSession = Depends(get_db_session),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """
        Refresh access token using refresh token.

        Provides new access and refresh tokens for continued authentication.
        """
        auth_service = AuthService(db, tenant_id)

        tokens = await auth_service.refresh_token(refresh_token)
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        access_token, new_refresh_token = tokens

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }

    @router.post("/password/change")
    @standard_exception_handler
    async def change_password(
        request: ChangePasswordSchema,
        http_request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """
        Change user password.

        Requires current password verification. Optionally keeps current session active.
        """
        auth_service = AuthService(db, tenant_id)

        # Set current session ID if keeping session active
        if request.keep_current_session:
            request.current_session_id = getattr(http_request.state, "session_id", None)

        client_ip = http_request.client.host if http_request.client else None
        success = await auth_service.change_password(
            user_id=current_user.id, request=request, client_ip=client_ip
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to change password. Current password may be incorrect.",
            )

        return {"message": "Password changed successfully"}

    @router.post("/mfa/setup", response_model=MFASetupResponseSchema)
    @standard_exception_handler
    async def setup_mfa(
        request: MFASetupSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> MFASetupResponseSchema:
        """
        Setup Multi-Factor Authentication for user account.

        Generates TOTP secret, QR code, and backup codes for MFA setup.
        MFA is not enabled until verified with /mfa/verify-setup.
        """
        auth_service = AuthService(db, tenant_id)

        setup_response = await auth_service.setup_mfa(
            user_id=current_user.id, request=request
        )

        return setup_response

    @router.post("/mfa/verify-setup")
    @standard_exception_handler
    async def verify_mfa_setup(
        mfa_code: str,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """
        Verify MFA setup and enable MFA for account.

        Verifies the MFA code from authenticator app and enables MFA for the user.
        """
        auth_service = AuthService(db, tenant_id)

        success = await auth_service.verify_mfa_setup(
            user_id=current_user.id, mfa_code=mfa_code
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MFA code. Please try again.",
            )

        return {"message": "MFA setup completed successfully"}

    @router.post("/api-keys", response_model=ApiKeySchema)
    @standard_exception_handler
    async def create_api_key(
        request: ApiKeyCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> ApiKeySchema:
        """
        Create API key for programmatic access.

        Generates secure API key with optional expiry and permissions.
        API key is only returned once and must be stored securely.
        """
        auth_service = AuthService(db, tenant_id)

        api_key_response = await auth_service.create_api_key(
            user_id=current_user.id, request=request
        )

        return api_key_response

    @router.get("/me", response_model=UserResponseSchema)
    @standard_exception_handler
    async def get_current_user_info(
        current_user: UserResponseSchema = Depends(get_current_user),
    ) -> UserResponseSchema:
        """
        Get current authenticated user information.

        Returns detailed user profile information for the authenticated user.
        """
        return current_user

    @router.get("/session", response_model=SessionInfoSchema)
    @standard_exception_handler
    async def get_current_session(
        http_request: Request,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> SessionInfoSchema:
        """
        Get current session information.

        Returns details about the current authentication session.
        """
        session_id = getattr(http_request.state, "session_id", None)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found",
            )

        auth_service = AuthService(db, tenant_id)
        session = await auth_service.session_repo.get_by_id(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        return SessionInfoSchema.model_validate(session)

    return router


def create_rbac_router() -> APIRouter:
    """Create RBAC (Role-Based Access Control) router."""
    from ..schemas.rbac_schemas import (
        BulkRoleAssignmentSchema,
        PermissionCheckRequestSchema,
        PermissionCheckResponseSchema,
        PermissionCreateSchema,
        PermissionResponseSchema,
        PermissionSearchSchema,
        RoleCreateSchema,
        RoleResponseSchema,
        RoleSearchSchema,
        RoleUpdateSchema,
        UserPermissionSummarySchema,
        UserRoleCreateSchema,
    )
    from ..services.rbac_service import RBACService

    router = APIRouter(prefix="/rbac", tags=["rbac", "roles", "permissions"])

    # Role management endpoints
    role_router = RouterFactory.create_crud_router(
        service_class=RBACService,
        prefix="/roles",
        tags=["roles"],
        create_schema=RoleCreateSchema,
        update_schema=RoleUpdateSchema,
        response_schema=RoleResponseSchema,
        search_schema=RoleSearchSchema,
        require_admin=True,
        enable_search=True,
        enable_bulk_operations=True,
    )

    # Permission management endpoints
    permission_router = RouterFactory.create_crud_router(
        service_class=RBACService,
        prefix="/permissions",
        tags=["permissions"],
        create_schema=PermissionCreateSchema,
        response_schema=PermissionResponseSchema,
        search_schema=PermissionSearchSchema,
        require_admin=True,
        enable_search=True,
        enable_create_only=True,  # Permissions typically not updated after creation
    )

    @router.post("/users/{user_id}/roles", response_model=dict)
    @standard_exception_handler
    async def assign_role_to_user(
        user_id: UUID,
        request: UserRoleCreateSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """Assign role to user."""
        rbac_service = RBACService(db, tenant_id)

        success = await rbac_service.assign_role_to_user(
            user_id=user_id,
            role_id=request.role_id,
            assigned_by=current_user.id,
            assignment_reason=request.assignment_reason,
            expires_at=request.expires_at,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to assign role to user",
            )

        return {"message": "Role assigned successfully"}

    @router.delete("/users/{user_id}/roles/{role_id}")
    @standard_exception_handler
    async def revoke_role_from_user(
        user_id: UUID,
        role_id: UUID,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """Revoke role from user."""
        rbac_service = RBACService(db, tenant_id)

        success = await rbac_service.revoke_role_from_user(user_id, role_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke role from user",
            )

        return {"message": "Role revoked successfully"}

    @router.post("/users/bulk-assign-roles", response_model=dict)
    @standard_exception_handler
    async def bulk_assign_roles(
        request: BulkRoleAssignmentSchema,
        db: AsyncSession = Depends(get_db_session),
        current_user: UserResponseSchema = Depends(get_current_user),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> dict:
        """Bulk assign roles to multiple users."""
        rbac_service = RBACService(db, tenant_id)

        assignments = await rbac_service.bulk_assign_roles(
            user_ids=request.user_ids,
            role_ids=request.role_ids,
            assigned_by=current_user.id,
            assignment_reason=request.assignment_reason,
            expires_at=request.expires_at,
        )

        return {
            "message": f"Successfully assigned {len(assignments)} role assignments",
            "assignments_created": len(assignments),
        }

    @router.post("/check-permission", response_model=PermissionCheckResponseSchema)
    @standard_exception_handler
    async def check_permission(
        request: PermissionCheckRequestSchema,
        db: AsyncSession = Depends(get_db_session),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> PermissionCheckResponseSchema:
        """Check if user has specific permission."""
        rbac_service = RBACService(db, tenant_id)

        result = await rbac_service.check_user_permission(
            user_id=request.user_id,
            permission_name=request.permission_name,
            resource_id=request.resource_id,
            context=request.context,
        )

        return result

    @router.get(
        "/users/{user_id}/permissions", response_model=UserPermissionSummarySchema
    )
    @standard_exception_handler
    async def get_user_permissions(
        user_id: UUID,
        db: AsyncSession = Depends(get_db_session),
        tenant_id: Optional[UUID] = Depends(get_current_tenant_id),
    ) -> UserPermissionSummarySchema:
        """Get comprehensive permission summary for user."""
        rbac_service = RBACService(db, tenant_id)

        summary = await rbac_service.get_user_permission_summary(user_id)

        return summary

    # Include sub-routers
    router.include_router(role_router)
    router.include_router(permission_router)

    return router


# Create router instances
auth_router = create_auth_router()
rbac_router = create_rbac_router()
