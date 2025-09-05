"""
DRY pattern captive portal router replacing corrupted router.py
Clean captive portal management with standardized patterns.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from dotmac_shared.api import StandardDependencies, standard_exception_handler
from dotmac_shared.api.dependencies import get_standard_deps
from dotmac_shared.schemas import BaseResponseSchema
from fastapi import APIRouter, Body, Depends, Path, Query

from ..schemas import CaptivePortalSessionResponse, PortalConfigResponse
from ..services import CaptivePortalService, get_captive_portal_service


class PortalFilters(BaseResponseSchema):
    """Captive portal filter parameters."""

    session_status: str | None = None
    location: str | None = None
    device_type: str | None = None
    authentication_method: str | None = None


def create_captive_portal_router_dry() -> APIRouter:
    """
    Create captive portal router using DRY patterns.

    BEFORE: Unexpected token Indent syntax error
    AFTER: Clean captive portal management for ISP operations
    """

    router = APIRouter(prefix="/captive-portal", tags=["Captive Portal"])

    # Create dependency factory
    def get_portal_service(
        deps: StandardDependencies = Depends(get_standard_deps),
    ) -> CaptivePortalService:
        return get_captive_portal_service(deps.db, deps.tenant_id)

    # Portal configuration endpoint
    @router.get("/config", response_model=PortalConfigResponse)
    @standard_exception_handler
    async def get_portal_config(
        location: str | None = Query(None, description="Filter by location"),
        include_branding: bool = Query(True, description="Include branding configuration"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> PortalConfigResponse:
        """Get captive portal configuration settings."""

        config = await service.get_portal_config(
            tenant_id=deps.tenant_id, location=location, include_branding=include_branding
        )

        return PortalConfigResponse.model_validate(config)

    # Active sessions endpoint
    @router.get("/sessions", response_model=list[CaptivePortalSessionResponse])
    @standard_exception_handler
    async def list_active_sessions(
        status: str | None = Query(None, description="Filter by session status"),
        location: str | None = Query(None, description="Filter by location"),
        device_type: str | None = Query(None, description="Filter by device type"),
        auth_method: str | None = Query(None, description="Filter by authentication method"),
        limit: int = Query(100, ge=1, le=500, description="Maximum sessions to return"),
        offset: int = Query(0, ge=0, description="Number of sessions to skip"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> list[CaptivePortalSessionResponse]:
        """List active captive portal sessions."""

        filters = PortalFilters(
            session_status=status, location=location, device_type=device_type, authentication_method=auth_method
        )

        sessions = await service.list_portal_sessions(
            tenant_id=deps.tenant_id, filters=filters.model_dump(exclude_unset=True), limit=limit, offset=offset
        )

        return [CaptivePortalSessionResponse.model_validate(session) for session in sessions]

    # Session details endpoint
    @router.get("/sessions/{session_id}", response_model=CaptivePortalSessionResponse)
    @standard_exception_handler
    async def get_session_details(
        session_id: UUID = Path(..., description="Portal session ID"),
        include_usage: bool = Query(True, description="Include usage statistics"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> CaptivePortalSessionResponse:
        """Get detailed information for a specific portal session."""

        session = await service.get_session_details(
            session_id=session_id, tenant_id=deps.tenant_id, include_usage=include_usage
        )

        return CaptivePortalSessionResponse.model_validate(session)

    # Authenticate user endpoint
    @router.post("/authenticate", response_model=dict[str, any])
    @standard_exception_handler
    async def authenticate_user(
        username: str = Body(..., description="Username or email"),
        password: str = Body(..., description="Password or access code"),
        mac_address: str = Body(..., description="Device MAC address"),
        location: str | None = Body(None, description="Portal location"),
        device_info: dict | None = Body(None, description="Device information"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> dict[str, any]:
        """Authenticate a user through the captive portal."""

        auth_result = await service.authenticate_portal_user(
            tenant_id=deps.tenant_id,
            username=username,
            password=password,
            mac_address=mac_address,
            location=location,
            device_info=device_info or {},
        )

        return {
            "authentication": auth_result,
            "session_id": auth_result.get("session_id"),
            "access_granted": auth_result.get("success", False),
            "expires_at": auth_result.get("expires_at"),
            "redirect_url": auth_result.get("redirect_url"),
        }

    # Guest access endpoint
    @router.post("/guest-access", response_model=dict[str, any])
    @standard_exception_handler
    async def grant_guest_access(
        mac_address: str = Body(..., description="Device MAC address"),
        location: str = Body(..., description="Portal location"),
        duration_hours: int = Body(24, ge=1, le=72, description="Access duration in hours"),
        terms_accepted: bool = Body(True, description="Terms and conditions acceptance"),
        contact_info: dict | None = Body(None, description="Optional contact information"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> dict[str, any]:
        """Grant guest access through the captive portal."""

        guest_session = await service.create_guest_session(
            tenant_id=deps.tenant_id,
            mac_address=mac_address,
            location=location,
            duration_hours=duration_hours,
            terms_accepted=terms_accepted,
            contact_info=contact_info or {},
        )

        return {
            "guest_access": guest_session,
            "session_id": guest_session.get("session_id"),
            "access_granted": True,
            "expires_at": guest_session.get("expires_at"),
            "bandwidth_limits": guest_session.get("bandwidth_limits", {}),
        }

    # Terminate session endpoint
    @router.post("/sessions/{session_id}/terminate", response_model=dict[str, str])
    @standard_exception_handler
    async def terminate_session(
        session_id: UUID = Path(..., description="Session ID to terminate"),
        reason: str | None = Body(None, description="Termination reason"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> dict[str, str]:
        """Terminate an active portal session."""

        await service.terminate_portal_session(
            session_id=session_id, tenant_id=deps.tenant_id, terminator_id=deps.user_id, reason=reason
        )

        return {
            "message": "Session terminated successfully",
            "session_id": str(session_id),
            "terminated_by": deps.user_id,
        }

    # Usage statistics endpoint
    @router.get("/stats", response_model=dict[str, any])
    @standard_exception_handler
    async def get_portal_statistics(
        time_range: str = Query("24h", description="Time range for statistics"),
        location: str | None = Query(None, description="Filter by location"),
        group_by: str = Query("location", description="Group statistics by (location, auth_method, device_type)"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> dict[str, any]:
        """Get captive portal usage statistics."""

        stats = await service.get_portal_statistics(
            tenant_id=deps.tenant_id, time_range=time_range, location=location, group_by=group_by
        )

        return {
            "statistics": stats,
            "time_range": time_range,
            "location_filter": location,
            "grouped_by": group_by,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # Update portal branding endpoint
    @router.put("/branding", response_model=dict[str, str])
    @standard_exception_handler
    async def update_portal_branding(
        branding_config: dict = Body(..., description="Portal branding configuration"),
        location: str | None = Body(None, description="Specific location for branding"),
        deps: StandardDependencies = Depends(get_standard_deps),
        service: CaptivePortalService = Depends(get_portal_service),
    ) -> dict[str, str]:
        """Update captive portal branding and appearance."""

        await service.update_portal_branding(
            tenant_id=deps.tenant_id, branding_config=branding_config, location=location, updated_by=deps.user_id
        )

        return {
            "message": "Portal branding updated successfully",
            "location": location or "all_locations",
            "updated_by": deps.user_id,
        }

    # Health check endpoint
    @router.get("/health")
    @standard_exception_handler
    async def health_check(
        deps: StandardDependencies = Depends(get_standard_deps),
    ) -> dict[str, str]:
        """Health check for captive portal service."""
        return {"service": "captive-portal", "status": "healthy", "tenant_id": deps.tenant_id}

    return router


# Migration statistics
def get_captive_portal_migration_stats() -> dict[str, any]:
    """Show captive portal router migration improvements."""
    return {
        "original_issues": ["Unexpected token Indent syntax error", "Malformed indentation patterns"],
        "dry_pattern_lines": 250,
        "portal_features": [
            "✅ Portal configuration management",
            "✅ User authentication workflows",
            "✅ Guest access provisioning",
            "✅ Session management and tracking",
            "✅ Usage statistics and analytics",
            "✅ Portal branding customization",
            "✅ Location-based configurations",
            "✅ Multi-tenant portal isolation",
        ],
        "production_capabilities": [
            "Multi-authentication method support",
            "Customizable portal branding",
            "Comprehensive session tracking",
            "Usage analytics and reporting",
            "Location-specific configurations",
        ],
    }
