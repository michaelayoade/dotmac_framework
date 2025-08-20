"""
DotMac Services - Main Application
Provides service provisioning, lifecycle management, and service catalog.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import config
from .core.exceptions import ServicesError

# Import SDKs
from .sdks import (
    ServiceCatalogSDK,
    ServiceOrderSDK,
    ServiceProvisioningSDK,
    ServiceActivationSDK,
    ServiceSuspensionSDK,
    ServiceTerminationSDK,
    ServiceMigrationSDK,
    ServiceUpgradeSDK,
    ServiceDowngradeSDK,
    ServiceBundleSDK,
    ServiceDependencySDK,
    ServiceQualificationSDK,
    ServiceAvailabilitySDK,
    ServiceFeasibilitySDK,
    ServiceResourceSDK,
    ServiceInventorySDK,
    ServiceConfigurationSDK,
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
        "name": "Catalog",
        "description": "Service catalog and product management",
    },
    {
        "name": "Orders",
        "description": "Service order management and tracking",
    },
    {
        "name": "Provisioning",
        "description": "Service provisioning and activation",
    },
    {
        "name": "Lifecycle",
        "description": "Service lifecycle management (suspend, terminate, migrate)",
    },
    {
        "name": "Bundles",
        "description": "Service bundle and package management",
    },
    {
        "name": "Qualification",
        "description": "Service qualification and feasibility checks",
    },
    {
        "name": "Inventory",
        "description": "Service inventory and resource management",
    },
    {
        "name": "Configuration",
        "description": "Service configuration and parameters",
    },
    {
        "name": "Dependencies",
        "description": "Service dependency management",
    },
    {
        "name": "Availability",
        "description": "Service availability and coverage checks",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting DotMac Services...")
    
    # Initialize service components
    logger.info(f"Service initialized with tenant: {config.tenant_id}")
    
    yield
    
    # Cleanup
    logger.info("Shutting down DotMac Services...")


# Create FastAPI application with comprehensive documentation
app = FastAPI(
    title="DotMac Services",
    description="""
    **Enterprise Service Management and Provisioning Platform**

    The DotMac Services platform provides comprehensive service lifecycle management for ISPs:

    ## 📦 Core Features

    ### Service Catalog
    - Product and service definitions
    - Service templates and variants
    - Pricing and billing rules
    - Service attributes and metadata
    - Version management
    - Category hierarchies

    ### Order Management
    - Service order creation
    - Order workflow orchestration
    - Order tracking and status
    - Bulk ordering
    - Order validation
    - SLA management

    ### Service Provisioning
    - Automated provisioning workflows
    - Network resource allocation
    - Equipment assignment
    - Configuration management
    - Activation scheduling
    - Rollback capabilities

    ### Lifecycle Management
    - Service activation
    - Suspension and resumption
    - Service termination
    - Service migrations
    - Upgrades and downgrades
    - Renewal processing

    ### Service Bundles
    - Bundle composition
    - Package deals
    - Cross-service dependencies
    - Bundle pricing
    - Promotional bundles
    - Custom packages

    ### Qualification & Feasibility
    - Service availability checks
    - Technical feasibility
    - Coverage verification
    - Resource availability
    - Prerequisite validation
    - Capacity planning

    ### Service Inventory
    - Active service tracking
    - Resource allocation
    - Service relationships
    - Asset management
    - Service history
    - Audit trails

    ### Configuration Management
    - Service parameters
    - Feature flags
    - Service limits
    - QoS settings
    - Custom attributes
    - Template management

    ## 🌐 Service Types

    ### Internet Services
    - Broadband (Fiber, DSL, Cable)
    - Static IP addresses
    - VPN services
    - Security services
    - DNS services
    - Email hosting

    ### Voice Services
    - VoIP
    - SIP trunking
    - Phone numbers
    - Call features
    - IVR services
    - Conference bridges

    ### TV & Entertainment
    - IPTV packages
    - Video on demand
    - Channel lineups
    - Set-top boxes
    - Streaming services
    - Content packages

    ### Business Services
    - Dedicated internet
    - MPLS networks
    - Cloud connectivity
    - Managed services
    - Colocation
    - Professional services

    ## 🚀 Integration

    - **Database**: PostgreSQL for service data
    - **Cache**: Redis for performance
    - **Events**: Event-driven provisioning
    - **Network**: Integration with network elements
    - **Billing**: Real-time billing integration
    - **CRM**: Customer data synchronization

    ## 📊 API Standards

    - RESTful API design
    - JSON request/response format
    - Async provisioning support
    - Webhook notifications
    - Batch operations
    - Comprehensive error handling

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
            "url": "https://services.dotmac.com",
            "description": "Production Services Platform"
        },
        {
            "url": "https://staging-services.dotmac.com",
            "description": "Staging Services Platform"
        }
    ],
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "DotMac Services Team",
        "email": "services-support@dotmac.com",
        "url": "https://docs.dotmac.com/services",
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
@app.exception_handler(ServicesError)
async def services_error_handler(request, exc: ServicesError):
    """Handle service-specific errors."""
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
                        "service": "dotmac_services",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "dependencies": {
                            "database": "healthy",
                            "redis": "healthy",
                            "provisioning_api": "healthy",
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service is unhealthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "service": "dotmac_services",
                        "version": "1.0.0",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "dependencies": {
                            "database": "healthy",
                            "redis": "healthy",
                            "provisioning_api": "unhealthy",
                        },
                        "error": "Provisioning API is not responding"
                    }
                }
            }
        }
    }
)
async def health_check() -> Dict[str, Any]:
    """Check service health status."""
    # In production, would check actual dependencies
    return {
        "status": "healthy",
        "service": "dotmac_services",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": {
            "database": "healthy",
            "redis": "healthy",
            "provisioning_api": "healthy",
        }
    }


# Service statistics endpoint
@app.get(
    "/stats",
    tags=["Health"],
    summary="Get service statistics",
    description="Get current service platform statistics and metrics",
    responses={
        200: {
            "description": "Service statistics",
            "content": {
                "application/json": {
                    "example": {
                        "active_services": 45230,
                        "pending_orders": 125,
                        "provisioning_queue": 48,
                        "services_activated_today": 320,
                        "services_terminated_today": 45,
                        "failed_provisions": 3,
                        "service_types": {
                            "broadband": 25000,
                            "voip": 15000,
                            "iptv": 5230,
                        }
                    }
                }
            }
        }
    }
)
async def get_stats() -> Dict[str, Any]:
    """Get service platform statistics."""
    # In production, would fetch actual statistics
    return {
        "active_services": 45230,
        "pending_orders": 125,
        "provisioning_queue": 48,
        "services_activated_today": 320,
        "services_terminated_today": 45,
        "failed_provisions": 3,
        "service_types": {
            "broadband": 25000,
            "voip": 15000,
            "iptv": 5230,
        }
    }


# API version endpoint
@app.get(
    "/version",
    tags=["Health"],
    summary="Get API version",
    description="Get the current API version and capability information",
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
                        "capabilities": {
                            "auto_provisioning": True,
                            "bulk_operations": True,
                            "async_processing": True,
                            "webhook_notifications": True,
                            "service_bundles": True,
                            "qualification_api": True,
                        }
                    }
                }
            }
        }
    }
)
async def get_version() -> Dict[str, Any]:
    """Get API version information."""
    return {
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2024-01-15",
        "git_commit": "abc123def",
        "capabilities": {
            "auto_provisioning": True,
            "bulk_operations": True,
            "async_processing": True,
            "webhook_notifications": True,
            "service_bundles": True,
            "qualification_api": True,
        }
    }


# Import and include API routers
# Note: These would be implemented in separate files
# from .api import catalog, orders, provisioning, lifecycle, bundles, inventory

# Example router includes (to be implemented):
# app.include_router(catalog.router, prefix="/api/v1/catalog", tags=["Catalog"])
# app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
# app.include_router(provisioning.router, prefix="/api/v1/provisioning", tags=["Provisioning"])
# app.include_router(lifecycle.router, prefix="/api/v1/lifecycle", tags=["Lifecycle"])
# app.include_router(bundles.router, prefix="/api/v1/bundles", tags=["Bundles"])
# app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "dotmac_services.main:app",
        host="0.0.0.0",
        port=8003,
        reload=config.debug,
        log_level="info" if not config.debug else "debug",
    )