"""
Authentication router for tenant provisioning.
Handles admin user creation during tenant bootstrap.
"""

import logging
from typing import Dict, Any
from pydantic import BaseModel, EmailStr
import secrets
from datetime import datetime

from fastapi import HTTPException, status
from dotmac_shared.api.router_factory import RouterFactory
from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.auth.models import User
from dotmac_management.user_management.adapters.isp_user_adapter import ISPUserAdapter
from dotmac_shared.core.logging import get_logger

logger = get_logger(__name__)

# Create auth router
auth_router = RouterFactory.create_standard_router(
    prefix="/auth", 
    tags=["authentication", "provisioning"]
)


class AdminCreateRequest(BaseModel):
    """Request model for creating tenant admin during provisioning"""
    email: EmailStr
    name: str
    company: str
    temp_password: str


class AdminCreateResponse(BaseModel):
    """Response model for admin creation"""
    success: bool
    admin_id: str
    message: str
    login_instructions: str


@auth_router.post("/create-admin", response_model=AdminCreateResponse)
@standard_exception_handler
async def create_tenant_admin(request: AdminCreateRequest) -> AdminCreateResponse:
    """
    Create tenant admin user during provisioning.
    
    This endpoint is called by the tenant provisioning service
    to create the initial admin user for a newly provisioned tenant.
    
    ⚠️  SECURITY NOTE: This endpoint is only accessible during initial
    tenant provisioning and should be disabled after the first admin login.
    """
    
    try:
        logger.info(f"Creating tenant admin user: {request.email}")
        
        # Initialize user adapter
        user_adapter = ISPUserAdapter()
        
        # Check if admin already exists
        existing_user = await user_adapter.get_user_by_email(request.email)
        if existing_user:
            logger.warning(f"Admin user already exists: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admin user already exists for this tenant"
            )
        
        # Create admin user
        admin_data = {
            "email": request.email,
            "name": request.name,
            "password": request.temp_password,  # Will be hashed by adapter
            "is_active": True,
            "is_superuser": True,  # Tenant admin has full permissions
            "is_verified": True,   # Auto-verify during provisioning
            "company": request.company,
            "role": "admin",
            "portal_access": ["admin", "customer", "technician"],  # Full access
            "created_at": datetime.now(timezone.utc),
            "metadata": {
                "created_during_provisioning": True,
                "requires_password_change": True,
                "provisioning_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        # Create the admin user
        admin_user = await user_adapter.create_user(admin_data)
        
        if not admin_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create admin user"
            )
        
        logger.info(f"✅ Tenant admin created successfully: {admin_user.id}")
        
        # Return success response with login instructions
        return AdminCreateResponse(
            success=True,
            admin_id=str(admin_user.id),
            message=f"Admin user created successfully for {request.company}",
            login_instructions=(
                f"Your tenant is ready! Login with:\n"
                f"Email: {request.email}\n"
                f"Password: {request.temp_password}\n"
                f"⚠️  Please change your password after first login."
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create tenant admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin creation failed: {str(e)}"
        )


@auth_router.get("/admin-status")
@standard_exception_handler 
async def get_admin_status() -> Dict[str, Any]:
    """
    Check if tenant admin has been created and configured.
    Used for provisioning status checks.
    """
    
    try:
        user_adapter = ISPUserAdapter()
        
        # Count admin users
        admin_count = await user_adapter.count_admin_users()
        
        return {
            "tenant_configured": admin_count > 0,
            "admin_count": admin_count,
            "status": "configured" if admin_count > 0 else "pending_admin_creation",
            "message": "Tenant has admin users" if admin_count > 0 else "Tenant needs admin user creation"
        }
        
    except Exception as e:
        logger.error(f"Failed to check admin status: {e}")
        return {
            "tenant_configured": False,
            "admin_count": 0,
            "status": "error",
            "message": f"Status check failed: {str(e)}"
        }


# Export router
router = auth_router
__all__ = ["router", "auth_router"]