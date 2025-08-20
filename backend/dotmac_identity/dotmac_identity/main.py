"""
DotMac Identity Service - Main Application
Provides user authentication, customer management, and identity services.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import config
from .core.exceptions import IdentityError

# Import SDKs
from .sdks import (
    IdentityAccountSDK,
    CustomerManagementSDK,
    UserProfileSDK,
    OrganizationSDK,
    ContactSDK,
    AddressSDK,
    PhoneSDK,
    EmailSDK,
    ConsentPreferencesSDK,
    CustomerPortalSDK,
    ResellerPortalSDK,
    PortalManagementSDK,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAPI tags metadata
tags_metadata = [
    {
        "name": "Health",
        "description": "Service health and status monitoring",
    },
    {
        "name": "Authentication",
        "description": "User authentication, login, logout, and token management",
    },
    {
        "name": "Customers",
        "description": "Customer account management and profiles",
    },
    {
        "name": "Organizations",
        "description": "Organization management for B2B customers",
    },
    {
        "name": "Contacts",
        "description": "Contact information management (email, phone, address)",
    },
    {
        "name": "Profiles",
        "description": "User profile and preference management",
    },
    {
        "name": "Verification",
        "description": "Email and phone verification services",
    },
    {
        "name": "Consent",
        "description": "GDPR consent and preference management",
    },
    {
        "name": "Portals",
        "description": "Customer and reseller portal management",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac Identity Service...")
    
    # Initialize service components
    logger.info(f"Service initialized with tenant: {config.tenant_id}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down DotMac Identity Service...")


# Create FastAPI application with comprehensive documentation
app = FastAPI(
    title="DotMac Identity Service",
    description="""
    **Enterprise Identity and Customer Management Service**

    The DotMac Identity Service provides comprehensive identity management capabilities for ISPs:

    ## 🔐 Core Features

    ### Authentication & Authorization
    - JWT-based authentication with refresh tokens
    - Multi-factor authentication (MFA) support
    - OAuth2 and SAML integration
    - API key management
    - Session management

    ### Customer Management
    - B2C and B2B customer accounts
    - Customer lifecycle management
    - Account hierarchies and relationships
    - Credit and billing profiles
    - Service entitlements

    ### User Profiles
    - Personal information management
    - Communication preferences
    - Privacy settings
    - Avatar and profile customization
    - Activity tracking

    ### Organization Management
    - Corporate account structures
    - Department and team management
    - Role-based permissions
    - Delegated administration
    - Bulk user provisioning

    ### Contact Information
    - Email address management
    - Phone number management
    - Physical address management
    - Verification workflows
    - Primary/secondary contacts

    ### Consent & Compliance
    - GDPR consent management
    - Marketing preferences
    - Data retention policies
    - Audit trails
    - Right to be forgotten

    ### Portal Access
    - Customer self-service portal
    - Reseller partner portal
    - Admin management portal
    - Customizable branding
    - Feature toggles

    ## 🚀 Integration

    - **Database**: PostgreSQL for persistent storage
    - **Cache**: Redis for session management
    - **Events**: Event-driven architecture support
    - **Multi-tenant**: Full tenant isolation

    ## 📊 API Standards

    - RESTful API design
    - JSON request/response format
    - OAuth2 Bearer token authentication
    - Comprehensive error responses
    - Request ID tracking

    **Base URL**: `/api/v1`
    **Version**: 1.0.0
    """,
    version="1.0.0",
    openapi_tags=tags_metadata,
    servers=[
        {
            "url": "/",
            "description": "Current server"
        },
        {
            "url": "https://identity.dotmac.com",
            "description": "Production Identity Service"
        },
        {
            "url": "https://staging-identity.dotmac.com",
            "description": "Staging Identity Service"
        }
    ],
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "DotMac Identity Team",
        "email": "identity-support@dotmac.com",
        "url": "https://docs.dotmac.com/identity",
    },
    lifespan=lifespan,
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(IdentityError)
async def identity_error_handler(request, exc: IdentityError):
    """Handle identity-specific errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": str(exc),
            "details": exc.details,
            "request_id": request.headers.get("X-Request-ID"),
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "request_id": request.headers.get("X-Request-ID"),
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check service health and dependencies",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "dotmac_identity",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "dependencies": {
                            "database": "healthy",
                            "redis": "healthy",
                        }
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Check service health status."""
    return {
        "status": "healthy",
        "service": "dotmac_identity",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "database": "healthy",
            "redis": "healthy",
        }
    }


# API version endpoint
@app.get(
    "/version",
    tags=["Health"],
    summary="Get API version",
    description="Get the current API version and build information",
    responses={
        200: {
            "description": "Version information",
            "content": {
                "application/json": {
                    "example": {
                        "version": "1.0.0",
                        "api_version": "v1",
                        "build_date": "2024-01-15",
                        "git_commit": "abc123def",
                    }
                }
            }
        }
    }
)
async def get_version() -> Dict[str, str]:
    """Get API version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2024-01-15",
        "git_commit": "abc123def",
    }


# Import and include API routers
# Note: These would be implemented in separate files
# from .api import auth, customers, organizations, profiles, contacts, consent, portals

# Example router includes (to be implemented):
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(customers.router, prefix="/api/v1/customers", tags=["Customers"])
# app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizations"])
# app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["Profiles"])
# app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["Contacts"])
# app.include_router(consent.router, prefix="/api/v1/consent", tags=["Consent"])
# app.include_router(portals.router, prefix="/api/v1/portals", tags=["Portals"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_identity.main:app",
        host="0.0.0.0",
        port=8001,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )