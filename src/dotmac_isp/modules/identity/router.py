"""
Identity module router for user, customer, and auth management.
Provides comprehensive identity operations with proper authentication.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.auth.dependencies import (
    get_current_user,
    get_permission_manager,
    require_permissions,
)
from dotmac_shared.core.pagination import PaginationParams, paginate
from dotmac_isp.shared.schemas import (
    CustomerCreateSchema,
    CustomerSchema,
    UserCreateSchema,
    UserSchema,
    AuthLoginSchema,
    AuthResponseSchema,
    PortalAccessSchema,
)

from .services import (
    AuthService,
    CustomerService,
    UserService,
    PortalService,
)

logger = logging.getLogger(__name__)

# Router instance
router = APIRouter(prefix="/identity", tags=["identity"])


# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str
    portal_type: Optional[str] = "admin"


class CustomerCreateRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    company_name: Optional[str] = None
    create_user_account: bool = False
    password_hash: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    service_address: Optional[Dict[str, Any]] = None


class UserCreateRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    portal_type: str = "admin"
    password_hash: str
    is_active: bool = True


class PortalAccessRequest(BaseModel):
    user_id: UUID
    portal_type: str
    access_level: str = "standard"
    is_enabled: bool = True
    allowed_features: List[str] = []
    denied_features: List[str] = []


# Authentication endpoints
@router.post("/auth/login", response_model=Dict[str, Any])
@standard_exception_handler
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(lambda: AuthService(None, "default"))
):
    """Authenticate user and return access token."""
    try:
        result = await auth_service.authenticate_user(
            username=request.username,
            password=request.password,
            portal_type=request.portal_type,
            user_agent="api-client",
            ip_address="127.0.0.1"
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/auth/logout")
@standard_exception_handler
async def logout(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
    auth_service: AuthService = Depends(lambda: AuthService(None, "default"))
):
    """Logout user and invalidate session."""
    try:
        success = await auth_service.logout_user(
            session_id=session_id,
            user_id=current_user["id"]
        )
        
        return {"success": success, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


# User management endpoints
@router.post("/users", response_model=Dict[str, Any])
@standard_exception_handler
async def create_user(
    request: UserCreateRequest,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["users.create"])),
    user_service: UserService = Depends(lambda: UserService(None, "default"))
):
    """Create new user."""
    try:
        user_data = request.model_dump()
        result = await user_service.create_user(
            user_data=user_data,
            created_by=current_user["id"]
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User creation failed"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User creation failed"
        )


@router.get("/users/{user_id}", response_model=Dict[str, Any])
@standard_exception_handler
async def get_user(
    user_id: UUID,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["users.read"])),
    user_service: UserService = Depends(lambda: UserService(None, "default"))
):
    """Get user by ID."""
    try:
        result = await user_service.get_user_by_id(user_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.get("/users", response_model=List[Dict[str, Any]])
@standard_exception_handler
async def list_users(
    portal_type: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["users.list"])),
    user_service: UserService = Depends(lambda: UserService(None, "default"))
):
    """List users with optional filtering."""
    try:
        filters = {}
        if portal_type:
            filters["portal_type"] = portal_type
        if status:
            filters["status"] = status
            
        result = await user_service.search_users(filters)
        return result
        
    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


# Customer management endpoints
@router.post("/customers", response_model=Dict[str, Any])
@standard_exception_handler
async def create_customer(
    request: CustomerCreateRequest,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["customers.create"])),
    customer_service: CustomerService = Depends(lambda: CustomerService(None, "default"))
):
    """Create new customer."""
    try:
        customer_data = request.model_dump()
        result = await customer_service.create_customer(
            customer_data=customer_data,
            created_by=current_user["id"]
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer creation failed"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Customer creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Customer creation failed"
        )


@router.get("/customers/{customer_id}", response_model=Dict[str, Any])
@standard_exception_handler
async def get_customer(
    customer_id: UUID,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["customers.read"])),
    customer_service: CustomerService = Depends(lambda: CustomerService(None, "default"))
):
    """Get customer by ID."""
    try:
        result = await customer_service.get_customer_by_id(customer_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get customer error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer"
        )


@router.get("/customers", response_model=List[Dict[str, Any]])
@standard_exception_handler
async def list_customers(
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["customers.list"])),
    customer_service: CustomerService = Depends(lambda: CustomerService(None, "default"))
):
    """List customers with optional filtering."""
    try:
        if search:
            result = await customer_service.search_customers(search)
        elif status:
            result = await customer_service.get_customers_by_status(status)
        else:
            # Default to active customers
            result = await customer_service.get_customers_by_status("active")
            
        return result
        
    except Exception as e:
        logger.error(f"List customers error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customers"
        )


# Portal access management endpoints
@router.post("/portal-access", response_model=Dict[str, Any])
@standard_exception_handler
async def create_portal_access(
    request: PortalAccessRequest,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["portal.manage"])),
    portal_service: PortalService = Depends(lambda: PortalService(None, "default"))
):
    """Create portal access for user."""
    try:
        access_data = {
            "access_level": request.access_level,
            "is_enabled": request.is_enabled,
            "allowed_features": request.allowed_features,
            "denied_features": request.denied_features
        }
        
        result = await portal_service.create_portal_access(
            user_id=request.user_id,
            portal_type=request.portal_type,
            access_data=access_data,
            created_by=current_user["id"]
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Portal access creation failed"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Portal access creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portal access creation failed"
        )


@router.get("/portal-access/{user_id}/{portal_type}", response_model=Dict[str, Any])
@standard_exception_handler
async def get_portal_access(
    user_id: UUID,
    portal_type: str,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["portal.read"])),
    portal_service: PortalService = Depends(lambda: PortalService(None, "default"))
):
    """Get user's portal access."""
    try:
        result = await portal_service.get_user_portal_access(user_id, portal_type)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portal access not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get portal access error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portal access"
        )


@router.get("/portal-users/{portal_type}", response_model=List[Dict[str, Any]])
@standard_exception_handler
async def list_portal_users(
    portal_type: str,
    current_user: Dict = Depends(get_current_user),
    _: None = Depends(require_permissions(["portal.list"])),
    portal_service: PortalService = Depends(lambda: PortalService(None, "default"))
):
    """List users with access to specific portal."""
    try:
        result = await portal_service.list_portal_users(portal_type)
        return result
        
    except Exception as e:
        logger.error(f"List portal users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve portal users"
        )


# Health check endpoint
@router.get("/health")
@standard_exception_handler
async def identity_health():
    """Identity module health check."""
    return {
        "status": "healthy",
        "module": "identity",
        "endpoints": 12,
        "features": ["authentication", "users", "customers", "portal_access"]
    }


# Export router
__all__ = ['router']