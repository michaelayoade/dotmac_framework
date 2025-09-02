"""Captive Portal API router for WiFi hotspot authentication and session management."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import \1, Dependsnds

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from dotmac_isp.shared.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    EntityNotFoundError,
    ServiceError,
    ValidationError,
)
from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import (
    Body,
    Depends,
    HTTPException,
    Query,
    standard_exception_handler,
    status,
)
from dotmac_shared.api.router_factory import RouterFactory

from .schemas import (
    AuthenticationRequest,
    AuthenticationResponse,
    CaptivePortalConfigCreate,
    CaptivePortalConfigResponse,
    CaptivePortalConfigUpdate,
    EmailAuthRequest,
    ErrorResponse,
    PaginationParams,
    PortalCustomizationResponse,
    PortalCustomizationUpdate,
    RadiusAuthRequest,
    SessionListResponse,
    SessionResponse,
    SessionTerminateRequest,
    SocialAuthRequest,
    UsageStatsRequest,
    UsageStatsResponse,
    VoucherAuthRequest,
    VoucherBatchCreateRequest,
    VoucherBatchResponse,
    VoucherCreateRequest,
    VoucherResponse,
)
from .service import CaptivePortalService

# REPLACED: Direct APIRouter with RouterFactory
router = RouterFactory.create_crud_router(
    service_class=CaptivePortalService,
    create_schema=CaptivePortalConfigCreate,
    update_schema=CaptivePortalConfigUpdate,
    response_schema=CaptivePortalConfigResponse,
    prefix="/captive-portal",
    tags=["captive-portal"],
    enable_search=True,
    enable_bulk_operations=True,
)
# Portal Configuration Endpoints


@router.post("/portals", response_model=CaptivePortalConfigResponse)
async def create_portal(
    deps: StandardDependencies = Depends(get_standard_deps),
    portal_data: CaptivePortalConfigCreate,
):
    """Create a new captive portal configuration."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.create_portal(portal_data)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/portals", response_model=List[CaptivePortalConfigResponse])
async def list_portals(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by portal status"),
):
    """List captive portal configurations with optional filtering."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        # This method needs to be implemented in the service
        portals = service.portal_repo.list_portals(
            customer_id=customer_id,
            status=status,
            offset=deps.pagination.offset,
            limit=deps.pagination.size,
        )
        return [
            CaptivePortalConfigResponse.model_validate(portal) for portal in portals
        ]
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/portals/{portal_id}", response_model=CaptivePortalConfigResponse)
async def get_portal(
    deps: StandardDependencies = Depends(get_standard_deps),
    portal_id: str,
):
    """Get captive portal configuration by ID."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        portal = await service.get_portal(portal_id)
        if not portal:
            raise HTTPException(status_code=404, detail="Portal not found")
        return portal
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Portal not found")
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.put("/portals/{portal_id}", response_model=CaptivePortalConfigResponse)
async def update_portal(
    deps: StandardDependencies = Depends(get_standard_deps),
    portal_id: str,
    portal_updates: CaptivePortalConfigUpdate,
):
    """Update captive portal configuration."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        portal = await service.update_portal(portal_id, portal_updates)
        if not portal:
            raise HTTPException(status_code=404, detail="Portal not found")
        return portal
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Portal not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.delete("/portals/{portal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portal(
    deps: StandardDependencies = Depends(get_standard_deps),
    portal_id: str,
):
    """Delete a captive portal configuration."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        success = await service.delete_portal(portal_id)
        if not success:
            raise HTTPException(status_code=404, detail="Portal not found")
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Portal not found")
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Authentication Endpoints


@router.post("/auth/email", response_model=AuthenticationResponse)
async def authenticate_email(
    deps: StandardDependencies = Depends(get_standard_deps),
    auth_request: EmailAuthRequest,
):
    """Authenticate user via email verification."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.authenticate_user(auth_request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/auth/social", response_model=AuthenticationResponse)
async def authenticate_social(
    deps: StandardDependencies = Depends(get_standard_deps),
    auth_request: SocialAuthRequest,
):
    """Authenticate user via social media provider."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.authenticate_user(auth_request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/auth/voucher", response_model=AuthenticationResponse)
async def authenticate_voucher(
    deps: StandardDependencies = Depends(get_standard_deps),
    auth_request: VoucherAuthRequest,
):
    """Authenticate user via access voucher."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.authenticate_user(auth_request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/auth/radius", response_model=AuthenticationResponse)
async def authenticate_radius(
    deps: StandardDependencies = Depends(get_standard_deps),
    auth_request: RadiusAuthRequest,
):
    """Authenticate user via RADIUS server."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.authenticate_user(auth_request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Session Management Endpoints


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    portal_id: Optional[str] = Query(None, description="Filter by portal ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    active_only: bool = Query(True, description="Show only active sessions"),
):
    """List user sessions with optional filtering."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        if active_only:
            sessions = await service.get_active_sessions(
                portal_id=portal_id, user_id=deps.deps.user_id
            )
        else:
            # This would need to be implemented in the service
            sessions = await service.get_active_sessions(
                portal_id=portal_id, user_id=deps.deps.user_id
            )

        return SessionListResponse(
            sessions=sessions,
            total=len(sessions),
            active=len([s for s in sessions if s.session_status.value == "active"]),
        )
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    deps: StandardDependencies = Depends(get_standard_deps),
    session_id: str,
):
    """Get session information by ID."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        session = service.session_repo.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionResponse.model_validate(session)
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/sessions/validate", response_model=Optional[SessionResponse])
async def validate_session(
    deps: StandardDependencies = Depends(get_standard_deps),
    session_token: str = Body(..., embed=True),
):
    """Validate a session token and return session info if valid."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        session = await service.validate_session(session_token)
        return session
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/sessions/{session_id}/terminate", status_code=status.HTTP_204_NO_CONTENT)
async def terminate_session(
    deps: StandardDependencies = Depends(get_standard_deps),
    session_id: str,
    request: SessionTerminateRequest,
):
    """Terminate a user session."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        success = await service.terminate_session(session_id, request)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/sessions/{session_id}/usage")
async def update_session_usage(
    deps: StandardDependencies = Depends(get_standard_deps),
    session_id: str,
    bytes_downloaded: int = Body(..., description="Bytes downloaded"),
    bytes_uploaded: int = Body(..., description="Bytes uploaded"),
):
    """Update session usage statistics."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        success = await service.update_session_usage(
            session_id=session_id,
            bytes_downloaded=bytes_downloaded,
            bytes_uploaded=bytes_uploaded,
        )
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "success", "message": "Usage updated"}
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Voucher Management Endpoints


@router.post("/vouchers", response_model=List[VoucherResponse])
async def create_vouchers(
    deps: StandardDependencies = Depends(get_standard_deps),
    voucher_request: VoucherCreateRequest,
):
    """Create vouchers for portal access."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        return await service.create_vouchers(voucher_request)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/vouchers/{voucher_code}/redeem")
async def redeem_voucher(
    deps: StandardDependencies = Depends(get_standard_deps),
    voucher_code: str,
    portal_id: str = Body(..., description="Portal ID"),
    user_id: str = Body(..., description="User ID"),
):
    """Redeem a voucher for access."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        success = await service.redeem_voucher(
            voucher_code, portal_id, deps.deps.user_id
        )
        if not success:
            raise HTTPException(status_code=400, detail="Voucher redemption failed")
        return {"status": "success", "message": "Voucher redeemed successfully"}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except BusinessRuleError as e:
        raise HTTPException(status_code=422, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Analytics Endpoints


@router.get("/portals/{portal_id}/stats", response_model=Dict[str, Any])
async def get_portal_stats(
    deps: PaginatedDependencies = Depends(get_paginated_deps),
    portal_id: str,
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
):
    """Get portal usage statistics."""
    try:
        from datetime import datetime, timezone

        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)

        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            parsed_start_date = datetime.fromisoformat(
                start_date.replace("Z", "+00:00")
            )
        if end_date:
            parsed_end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        return await service.get_portal_stats(
            portal_id=portal_id, start_date=parsed_start_date, end_date=parsed_end_date
        )
    except EntityNotFoundError:
        raise HTTPException(status_code=404, detail="Portal not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Maintenance Endpoints


@router.post("/maintenance/cleanup-sessions")
async def cleanup_expired_sessions(
    deps: StandardDependencies = Depends(get_standard_deps),
):
    """Clean up expired sessions."""
    try:
        service = CaptivePortalService(deps.deps.db, deps.deps.tenant_id)
        count = await service.cleanup_expired_sessions()
        return {"status": "success", "cleaned_sessions": count}
    except ServiceError as e:
        raise HTTPException(status_code=500, detail=e.message)


# Health Check Endpoint


@router.get("/health")
async def health_check():
    """Health check endpoint for captive portal service."""
    return {"status": "healthy", "service": "captive_portal"}
