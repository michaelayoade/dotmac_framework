"""
Unified Authentication API Endpoints

Single authentication API that serves all portals with proper
portal type detection and routing.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from dotmac_isp.shared.portal_auth import (
    PortalAuthManager,
    AuthenticationRequest,
    AuthenticationResponse,
    AuthenticationError,
    PortalType,
    AuthenticationMode,
    portal_auth_manager
)

router = APIRouter(prefix="/api/auth", tags=["unified-authentication"])


class PortalDetectionResponse(BaseModel):
    """Portal detection response."""
    detected_portal: Optional[str] = None
    available_portals: list[str]
    portal_urls: dict[str, str]
    auto_redirect: bool = False
    redirect_url: Optional[str] = None


class LoginRequest(BaseModel):
    """Simplified login request for frontend."""
    # Credentials
    username: Optional[str] = None
    email: Optional[str] = None
    portal_id: Optional[str] = None
    password: str
    
    # Options
    remember_device: bool = False
    portal_type: Optional[str] = None  # Override auto-detection


@router.get("/detect-portal", response_model=PortalDetectionResponse)
async def detect_portal_type(request: Request):
    """Detect appropriate portal based on request context."""
    try:
        detected_portal = portal_auth_manager.detect_portal_type_from_request(request)
        
        # Get all available portals and URLs
        available_portals = [portal.value for portal in PortalType]
        portal_urls = {
            portal.value: portal_auth_manager.get_portal_url(portal)
            for portal in PortalType
        }
        
        # Determine if we should auto-redirect
        auto_redirect = detected_portal is not None
        redirect_url = None
        if auto_redirect and detected_portal:
            redirect_url = portal_urls.get(detected_portal.value)
        
        return PortalDetectionResponse(
            detected_portal=detected_portal.value if detected_portal else None,
            available_portals=available_portals,
            portal_urls=portal_urls,
            auto_redirect=auto_redirect,
            redirect_url=redirect_url
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portal detection failed: {str(e)}"
        )


@router.post("/login", response_model=AuthenticationResponse)
async def unified_login(
    login_request: LoginRequest,
    request: Request,
    response: Response
):
    """Unified login endpoint for all portals."""
    try:
        # Detect portal type if not specified
        portal_type = None
        if login_request.portal_type:
            try:
                portal_type = PortalType(login_request.portal_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid portal type: {login_request.portal_type}"
                )
        else:
            portal_type = portal_auth_manager.detect_portal_type_from_request(request)
        
        if not portal_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portal type could not be determined. Please specify portal type or access from correct portal URL."
            )
        
        # Determine authentication mode based on provided credentials
        auth_mode = None
        if login_request.portal_id:
            auth_mode = AuthenticationMode.PORTAL_ID_PASSWORD
        elif login_request.email:
            auth_mode = AuthenticationMode.EMAIL_PASSWORD
        elif login_request.username:
            auth_mode = AuthenticationMode.USERNAME_PASSWORD
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide username, email, or portal_id"
            )
        
        # Create authentication request
        auth_request = AuthenticationRequest(
            portal_type=portal_type,
            auth_mode=auth_mode,
            username=login_request.username,
            email=login_request.email,
            portal_id=login_request.portal_id,
            password=login_request.password,
            remember_device=login_request.remember_device
        )
        
        # Authenticate
        auth_response = await portal_auth_manager.authenticate_user(auth_request)
        
        # Set secure cookies
        response.set_cookie(
            key="auth-token",
            value=auth_response.access_token,
            max_age=int((auth_response.expires_at - auth_response.expires_at.utcnow()).total_seconds()) if auth_response.expires_at else 28800,  # 8 hours default
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        response.set_cookie(
            key="portal-type", 
            value=auth_response.portal_type.value,
            max_age=86400,  # 24 hours
            httponly=False,  # Frontend needs to read this
            secure=True,
            samesite="strict"
        )
        
        response.set_cookie(
            key="refresh-token",
            value=auth_response.refresh_token,
            max_age=604800,  # 7 days
            httponly=True,
            secure=True,
            samesite="strict"
        )
        
        return auth_response
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}"
        )


@router.post("/logout")
async def unified_logout(response: Response):
    """Unified logout for all portals."""
    try:
        # Clear all auth cookies
        response.delete_cookie("auth-token", secure=True, samesite="strict")
        response.delete_cookie("portal-type", secure=True, samesite="strict") 
        response.delete_cookie("refresh-token", secure=True, samesite="strict")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh authentication token."""
    try:
        refresh_token = request.cookies.get("refresh-token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No refresh token provided"
            )
        
        # TODO: Implement token refresh logic
        # This would validate the refresh token and issue new access token
        
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Token refresh not yet implemented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.get("/portal-redirect")
async def portal_redirect(request: Request, portal: Optional[str] = None):
    """Redirect to appropriate portal based on detection or parameter."""
    try:
        target_portal = None
        
        if portal:
            try:
                target_portal = PortalType(portal)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid portal type: {portal}"
                )
        else:
            target_portal = portal_auth_manager.detect_portal_type_from_request(request)
        
        if not target_portal:
            # Redirect to portal discovery page
            return RedirectResponse(
                url="https://portal.dotmac-isp.local:3005",
                status_code=status.HTTP_302_FOUND
            )
        
        portal_url = portal_auth_manager.get_portal_url(target_portal)
        return RedirectResponse(
            url=portal_url,
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Portal redirect failed: {str(e)}"
        )


@router.get("/check-session")
async def check_session(request: Request):
    """Check current session status."""
    try:
        auth_token = request.cookies.get("auth-token")
        portal_type = request.cookies.get("portal-type")
        
        if not auth_token or not portal_type:
            return {
                "authenticated": False,
                "portal_type": None,
                "user_info": None
            }
        
        # TODO: Validate token and return user info
        # For now, return basic response
        
        return {
            "authenticated": True,
            "portal_type": portal_type,
            "user_info": {"token_present": True}
        }
        
    except Exception as e:
        return {
            "authenticated": False,
            "portal_type": None,
            "user_info": None,
            "error": str(e)
        }


# Export router
auth_router = router