"""Portal Management Router - API endpoints for Portal ID system."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.shared.schemas import PaginatedResponse
from .models import PortalAccountStatus
from .schemas import (
    PortalAccountCreate,
    PortalAccountUpdate,
    PortalAccountResponse,
    PortalAccountAdminCreate,
    PortalAccountAdminUpdate,
    PortalLoginRequest,
    PortalLoginResponse,
    PortalPasswordChangeRequest,
    PortalPasswordResetRequest,
    PortalPasswordResetConfirm,
    Portal2FASetupRequest,
    Portal2FASetupResponse,
    Portal2FAVerifyRequest,
    PortalSessionResponse,
    PortalBulkOperationRequest,
    PortalBulkOperationResponse,
    PortalAnalyticsResponse,
)
from .services import PortalAccountService, PortalAuthService
from datetime import timezone


router = APIRouter(prefix="/portal-management", tags=["Portal Management"])


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request."""
    return request.headers.get("User-Agent")


def get_current_tenant_id(request: Request) -> UUID:
    """Get current tenant ID from request context or JWT token."""
    # Try to extract from JWT token first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from dotmac_isp.shared.auth import verify_token

            payload = verify_token(token, "access")
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                return UUID(tenant_id)
        except Exception:
            pass

    # Try to extract from request headers (multi-tenant setup)
    tenant_header = request.headers.get("X-Tenant-ID")
    if tenant_header:
        try:
            return UUID(tenant_header)
        except ValueError:
            pass

    # Try to extract from subdomain (subdomain.domain.com -> tenant)
    host = request.headers.get("Host", "")
    if "." in host:
        subdomain = host.split(".")[0]
        # In production, you'd map subdomain to tenant_id via database lookup
        # For now, generate a deterministic UUID from subdomain
        import hashlib

        if subdomain and subdomain not in ["www", "api", "admin"]:
            # Create deterministic UUID from subdomain
            namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
            return UUID(bytes=hashlib.sha256(f"{namespace}{subdomain}".encode()).digest()[:16])

    # Fallback to default tenant for development
    return UUID("00000000-0000-0000-0000-000000000001")


def get_current_admin_id(request: Request) -> Optional[UUID]:
    """Get current admin user ID from JWT token."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from dotmac_isp.shared.auth import verify_token

            payload = verify_token(token, "access")
            user_id = payload.get("user_id")
            user_type = payload.get("user_type", "")

            # Only return user_id if it's an admin user
            if user_id and user_type in ["admin", "super_admin"]:
                return UUID(user_id)
        except Exception:
            pass

    return None


# Portal Account Management Endpoints


@router.post("/accounts", response_model=PortalAccountResponse)
async def create_portal_account(
    account_data: PortalAccountCreate, request: Request, db: Session = Depends(get_db)
):
    """Create a new Portal Account."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    try:
        account = service.create_portal_account(tenant_id, account_data, admin_id)
        return PortalAccountResponse.from_orm(account)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/admin", response_model=PortalAccountResponse)
async def create_portal_account_admin(
    account_data: PortalAccountAdminCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new Portal Account with admin privileges."""
    service = PortalAccountService(db)

    try:
        # Convert to base create schema and add admin fields
        create_data = PortalAccountCreate(**account_data.model_dump())
        account = service.create_portal_account(tenant_id, create_data, admin_id)

        # Apply admin-specific settings
        if account_data.status:
            account.status = account_data.status.value
        if account_data.email_verified is not None:
            account.email_verified = account_data.email_verified
        if account_data.phone_verified is not None:
            account.phone_verified = account_data.phone_verified
        if account_data.must_change_password is not None:
            account.must_change_password = account_data.must_change_password

        service.db.commit()
        service.db.refresh(account)

        return PortalAccountResponse.from_orm(account)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts", response_model=PaginatedResponse[PortalAccountResponse])
async def list_portal_accounts(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[PortalAccountStatus] = None,
    db: Session = Depends(get_db),
):
    """List Portal Accounts with pagination."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    accounts = service.list_portal_accounts(tenant_id, skip, limit, status)
    total = len(accounts)  # In production, implement proper count query

    return PaginatedResponse(
        items=[PortalAccountResponse.from_orm(account) for account in accounts],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/accounts/{account_id}", response_model=PortalAccountResponse)
async def get_portal_account(
    request: Request, account_id: UUID, db: Session = Depends(get_db)
):
    """Get Portal Account by ID."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    account = service.get_portal_account_by_id(tenant_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Portal account not found")

    return PortalAccountResponse.from_orm(account)


@router.put("/accounts/{account_id}", response_model=PortalAccountResponse)
async def update_portal_account(
    request: Request,
    account_id: UUID,
    update_data: PortalAccountUpdate,
    db: Session = Depends(get_db),
):
    """Update Portal Account."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    account = service.update_portal_account(
        tenant_id, account_id, update_data, admin_id
    )
    if not account:
        raise HTTPException(status_code=404, detail="Portal account not found")

    return PortalAccountResponse.from_orm(account)


@router.put("/accounts/{account_id}/admin", response_model=PortalAccountResponse)
async def update_portal_account_admin(
    request: Request,
    account_id: UUID,
    update_data: PortalAccountAdminUpdate,
    db: Session = Depends(get_db),
):
    """Update Portal Account with admin privileges."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    account = service.get_portal_account_by_id(tenant_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Portal account not found")

    # Apply admin updates
    for field, value in update_data.model_dump(exclude_unset=True).items():
        if hasattr(account, field):
            if field in ["status"] and value:
                setattr(
                    account, field, value.value if hasattr(value, "value") else value
                )
            else:
                setattr(account, field, value)

    account.last_modified_by_admin_id = admin_id

    service.db.commit()
    service.db.refresh(account)

    return PortalAccountResponse.from_orm(account)


@router.delete("/accounts/{account_id}")
async def delete_portal_account(
    request: Request, account_id: UUID, db: Session = Depends(get_db)
):
    """Soft delete Portal Account."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    account = service.get_portal_account_by_id(tenant_id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Portal account not found")

    account.soft_delete()
    account.last_modified_by_admin_id = admin_id

    service.db.commit()

    return {"message": "Portal account deleted successfully"}


# Authentication Endpoints


@router.post("/auth/login", response_model=PortalLoginResponse)
async def portal_login(
    login_request: PortalLoginRequest, request: Request, db: Session = Depends(get_db)
):
    """Portal login endpoint."""
    tenant_id = get_current_tenant_id(request)
    auth_service = PortalAuthService(db)

    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)

    return auth_service.authenticate_portal_login(
        tenant_id, login_request, ip_address, user_agent
    )


@router.post("/auth/refresh")
async def refresh_portal_token(
    request: Request, refresh_token: str, db: Session = Depends(get_db)
):
    """Refresh Portal access token."""
    tenant_id = get_current_tenant_id(request)
    auth_service = PortalAuthService(db)

    new_token = auth_service.refresh_token(tenant_id, refresh_token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    return {"access_token": new_token, "token_type": "bearer"}


@router.post("/auth/logout")
async def portal_logout(
    request: Request, session_token: str, db: Session = Depends(get_db)
):
    """Portal logout endpoint."""
    tenant_id = get_current_tenant_id(request)
    auth_service = PortalAuthService(db)

    success = auth_service.logout_session(tenant_id, session_token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid session token")

    return {"message": "Logged out successfully"}


# Password Management Endpoints


@router.post("/auth/change-password")
async def change_portal_password(
    request: Request,
    account_id: UUID,
    password_change: PortalPasswordChangeRequest,
    db: Session = Depends(get_db),
):
    """Change Portal Account password."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    try:
        success = service.change_password(tenant_id, account_id, password_change)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid current password")

        return {"message": "Password changed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/request-password-reset")
async def request_password_reset(
    request: Request,
    reset_request: PortalPasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request password reset for Portal Account."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    reset_token = service.initiate_password_reset(tenant_id, reset_request.portal_id)
    if reset_token:
        # In production, send reset token via email/SMS
        # For now, return success message without exposing token
        return {"message": "Password reset token sent"}
    else:
        # Don't reveal if portal ID exists for security
        return {"message": "If the Portal ID exists, a reset token has been sent"}


@router.post("/auth/confirm-password-reset")
async def confirm_password_reset(
    request: Request,
    reset_confirm: PortalPasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Confirm password reset with token."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    success = service.confirm_password_reset(
        tenant_id, reset_confirm.reset_token, reset_confirm.new_password
    )

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    return {"message": "Password reset successfully"}


# Two-Factor Authentication Endpoints


@router.post("/auth/2fa/setup", response_model=Portal2FASetupResponse)
async def setup_2fa(
    request: Request,
    account_id: UUID,
    setup_request: Portal2FASetupRequest,
    db: Session = Depends(get_db),
):
    """Setup two-factor authentication."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    try:
        return service.setup_2fa(tenant_id, account_id, setup_request.method)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/auth/2fa/verify")
async def verify_2fa_setup(
    request: Request,
    account_id: UUID,
    verify_request: Portal2FAVerifyRequest,
    db: Session = Depends(get_db),
):
    """Verify 2FA setup with TOTP code."""
    tenant_id = get_current_tenant_id(request)
    service = PortalAccountService(db)

    success = service.verify_2fa_setup(tenant_id, account_id, verify_request.code)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    return {"message": "Two-factor authentication enabled successfully"}


@router.delete("/auth/2fa/{account_id}")
async def disable_2fa(
    request: Request, account_id: UUID, db: Session = Depends(get_db)
):
    """Disable two-factor authentication."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    success = service.disable_2fa(tenant_id, account_id, admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Portal account not found")

    return {"message": "Two-factor authentication disabled"}


# Session Management Endpoints


@router.get(
    "/accounts/{account_id}/sessions", response_model=List[PortalSessionResponse]
)
async def get_portal_sessions(
    request: Request, account_id: UUID, db: Session = Depends(get_db)
):
    """Get all active sessions for Portal Account."""
    tenant_id = get_current_tenant_id(request)
    auth_service = PortalAuthService(db)

    sessions = auth_service.get_active_sessions(tenant_id, account_id)

    return [PortalSessionResponse.from_orm(session) for session in sessions]


@router.delete("/sessions/{session_id}")
async def terminate_portal_session(
    request: Request, session_id: UUID, db: Session = Depends(get_db)
):
    """Terminate a specific Portal session."""
    tenant_id = get_current_tenant_id(request)
    from .models import PortalSession
    from sqlalchemy import and_

    session = (
        db.query(PortalSession)
        .filter(
            and_(
                PortalSession.id == session_id,
                PortalSession.tenant_id == tenant_id,
                PortalSession.is_active == True,
            )
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.terminate_session("admin")
    db.commit()

    return {"message": "Session terminated successfully"}


# Bulk Operations


@router.post("/accounts/bulk-operations", response_model=PortalBulkOperationResponse)
async def bulk_portal_operations(
    request: Request,
    bulk_request: PortalBulkOperationRequest,
    db: Session = Depends(get_db),
):
    """Perform bulk operations on Portal Accounts."""
    tenant_id = get_current_tenant_id(request)
    admin_id = get_current_admin_id(request)
    service = PortalAccountService(db)

    successful = 0
    failed = 0
    errors = []
    processed_ids = []

    for account_id in bulk_request.portal_account_ids:
        try:
            account = service.get_portal_account_by_id(tenant_id, account_id)
            if not account:
                errors.append(f"Account {account_id} not found")
                failed += 1
                continue

            if bulk_request.operation == "activate":
                account.status = PortalAccountStatus.ACTIVE.value
            elif bulk_request.operation == "suspend":
                account.status = PortalAccountStatus.SUSPENDED.value
            elif bulk_request.operation == "lock":
                account.lock_account(reason=bulk_request.reason)
            elif bulk_request.operation == "unlock":
                account.unlock_account(admin_id)
            elif bulk_request.operation == "reset_2fa":
                account.two_factor_enabled = False
                account.two_factor_secret = None
                account.backup_codes = None

            account.last_modified_by_admin_id = admin_id
            if bulk_request.reason:
                account.security_notes = (
                    f"{bulk_request.reason}\n{account.security_notes or ''}"
                )

            successful += 1
            processed_ids.append(account_id)

        except Exception as e:
            errors.append(f"Account {account_id}: {str(e)}")
            failed += 1

    db.commit()

    return PortalBulkOperationResponse(
        total_requested=len(bulk_request.portal_account_ids),
        successful=successful,
        failed=failed,
        errors=errors,
        processed_ids=processed_ids,
    )


# Analytics and Reporting


@router.get("/analytics", response_model=PortalAnalyticsResponse)
async def get_portal_analytics(request: Request, db: Session = Depends(get_db)):
    """Get Portal Account analytics and statistics."""
    tenant_id = get_current_tenant_id(request)
    from .models import PortalAccount, PortalSession, PortalLoginAttempt
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta

    today = datetime.now(timezone.utc).date()

    # Account statistics
    total_accounts = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id, PortalAccount.is_deleted == False
            )
        )
        .scalar()
    )

    active_accounts = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.status == PortalAccountStatus.ACTIVE.value,
            )
        )
        .scalar()
    )

    suspended_accounts = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.status == PortalAccountStatus.SUSPENDED.value,
            )
        )
        .scalar()
    )

    locked_accounts = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.status == PortalAccountStatus.LOCKED.value,
            )
        )
        .scalar()
    )

    pending_accounts = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.status == PortalAccountStatus.PENDING_ACTIVATION.value,
            )
        )
        .scalar()
    )

    # Session statistics
    active_sessions = (
        db.query(func.count(PortalSession.id))
        .filter(
            and_(
                PortalSession.tenant_id == tenant_id,
                PortalSession.is_active == True,
                PortalSession.expires_at > datetime.now(timezone.utc),
            )
        )
        .scalar()
    )

    # Login statistics
    total_sessions_today = (
        db.query(func.count(PortalSession.id))
        .filter(
            and_(
                PortalSession.tenant_id == tenant_id,
                func.date(PortalSession.login_at) == today,
            )
        )
        .scalar()
    )

    failed_logins_today = (
        db.query(func.count(PortalLoginAttempt.id))
        .filter(
            and_(
                PortalLoginAttempt.tenant_id == tenant_id,
                PortalLoginAttempt.success == False,
                func.date(PortalLoginAttempt.created_at) == today,
            )
        )
        .scalar()
    )

    # Security statistics
    two_factor_enabled_count = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.two_factor_enabled == True,
            )
        )
        .scalar()
    )

    password_expires_soon = (
        db.query(func.count(PortalAccount.id))
        .filter(
            and_(
                PortalAccount.tenant_id == tenant_id,
                PortalAccount.is_deleted == False,
                PortalAccount.password_changed_at
                < datetime.now(timezone.utc) - timedelta(days=60),
            )
        )
        .scalar()
    )

    security_alerts_count = (
        db.query(func.count(PortalLoginAttempt.id))
        .filter(
            and_(
                PortalLoginAttempt.tenant_id == tenant_id,
                PortalLoginAttempt.flagged_as_suspicious == True,
                PortalLoginAttempt.created_at > datetime.now(timezone.utc) - timedelta(days=7),
            )
        )
        .scalar()
    )

    return PortalAnalyticsResponse(
        total_accounts=total_accounts or 0,
        active_accounts=active_accounts or 0,
        suspended_accounts=suspended_accounts or 0,
        locked_accounts=locked_accounts or 0,
        pending_accounts=pending_accounts or 0,
        total_sessions_today=total_sessions_today or 0,
        active_sessions=active_sessions or 0,
        failed_logins_today=failed_logins_today or 0,
        two_factor_enabled_count=two_factor_enabled_count or 0,
        password_expires_soon_count=password_expires_soon or 0,
        security_alerts_count=security_alerts_count or 0,
        top_locations=[],  # Would need geographic data for implementation
    )
