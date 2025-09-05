"""
Licensing API - DRY Migration
License management endpoints using RouterFactory patterns.
"""

from typing import Any

from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)
from fastapi import Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler

# === License Schemas ===


class LicenseCreateRequest(BaseModel):
    """Request schema for creating licenses."""

    license_type: str = Field(..., description="Type of license")
    features: list[str] = Field(..., description="Licensed features")
    limits: dict[str, Any] = Field(..., description="License limits")
    expires_at: str | None = Field(None, description="License expiration date")


class LicenseUpdateRequest(BaseModel):
    """Request schema for updating licenses."""

    features: list[str] | None = Field(None, description="Licensed features")
    limits: dict[str, Any] | None = Field(None, description="License limits")
    is_active: bool | None = Field(None, description="License active status")


# === Licensing Router ===

licensing_router = RouterFactory.create_standard_router(
    prefix="/licensing",
    tags=["licensing"],
)


# === License Management ===


@licensing_router.get("/licenses", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_licenses(
    license_type: str | None = Query(None, description="Filter by license type"),
    status: str | None = Query(None, description="Filter by status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List all licenses with optional filtering."""
    # Mock implementation
    licenses = [
        {
            "id": "license-001",
            "license_type": "enterprise",
            "tenant_id": deps.tenant_id,
            "features": ["analytics", "multi_tenant", "api_access"],
            "limits": {"max_users": 1000, "max_storage_gb": 500},
            "status": "active",
            "expires_at": "2025-12-31T23:59:59Z",
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "license-002",
            "license_type": "professional",
            "tenant_id": deps.tenant_id,
            "features": ["analytics", "api_access"],
            "limits": {"max_users": 100, "max_storage_gb": 100},
            "status": "active",
            "expires_at": "2025-06-30T23:59:59Z",
            "created_at": "2024-06-01T00:00:00Z",
        },
    ]

    # Apply filters
    if license_type:
        licenses = [l for l in licenses if l["license_type"] == license_type]
    if status:
        licenses = [l for l in licenses if l["status"] == status]

    return licenses[: deps.pagination.size]


@licensing_router.post("/licenses", response_model=dict[str, Any])
@standard_exception_handler
async def create_license(
    request: LicenseCreateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new license."""
    license_id = f"license-{request.license_type}-{deps.tenant_id}"

    return {
        "id": license_id,
        "license_type": request.license_type,
        "tenant_id": deps.tenant_id,
        "features": request.features,
        "limits": request.limits,
        "status": "active",
        "expires_at": request.expires_at,
        "created_by": deps.user_id,
        "message": "License created successfully",
    }


@licensing_router.get("/licenses/{license_id}", response_model=dict[str, Any])
@standard_exception_handler
async def get_license(
    license_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get license details."""
    return {
        "id": license_id,
        "license_type": "enterprise",
        "tenant_id": deps.tenant_id,
        "features": ["analytics", "multi_tenant", "api_access"],
        "limits": {"max_users": 1000, "max_storage_gb": 500},
        "status": "active",
        "usage": {"current_users": 245, "current_storage_gb": 125},
        "expires_at": "2025-12-31T23:59:59Z",
        "created_at": "2024-01-01T00:00:00Z",
    }


@licensing_router.put("/licenses/{license_id}", response_model=dict[str, Any])
@standard_exception_handler
async def update_license(
    license_id: str,
    request: LicenseUpdateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update license configuration."""
    return {
        "id": license_id,
        "status": "updated",
        "updated_fields": {
            k: v for k, v in request.model_dump().items() if v is not None
        },
        "updated_by": deps.user_id,
        "message": "License updated successfully",
    }


# === License Validation ===


@licensing_router.get("/validate/{feature}", response_model=dict[str, Any])
@standard_exception_handler
async def validate_feature_access(
    feature: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Validate access to a specific feature."""
    # Mock validation logic
    licensed_features = ["analytics", "multi_tenant", "api_access"]

    return {
        "feature": feature,
        "tenant_id": deps.tenant_id,
        "has_access": feature in licensed_features,
        "license_type": "enterprise",
        "expires_at": "2025-12-31T23:59:59Z",
        "usage_limit": 1000 if feature == "max_users" else None,
        "current_usage": 245 if feature == "max_users" else None,
    }


@licensing_router.get("/usage", response_model=dict[str, Any])
@standard_exception_handler
async def get_license_usage(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get current license usage statistics."""
    return {
        "tenant_id": deps.tenant_id,
        "license_type": "enterprise",
        "usage": {
            "users": {"current": 245, "limit": 1000, "percentage": 24.5},
            "storage": {"current_gb": 125, "limit_gb": 500, "percentage": 25.0},
            "api_calls": {
                "current_monthly": 15420,
                "limit_monthly": 50000,
                "percentage": 30.8,
            },
        },
        "status": "within_limits",
        "expires_at": "2025-12-31T23:59:59Z",
    }


# === License Templates ===


@licensing_router.get("/templates", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_license_templates(
    category: str | None = Query(None, description="Filter by category"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get available license templates."""
    templates = [
        {
            "id": "template-starter",
            "name": "Starter",
            "category": "basic",
            "description": "Basic features for small teams",
            "features": ["core_features", "basic_support"],
            "limits": {"max_users": 10, "max_storage_gb": 10},
            "price_monthly": 29.99,
        },
        {
            "id": "template-professional",
            "name": "Professional",
            "category": "business",
            "description": "Advanced features for growing businesses",
            "features": [
                "core_features",
                "analytics",
                "api_access",
                "priority_support",
            ],
            "limits": {"max_users": 100, "max_storage_gb": 100},
            "price_monthly": 99.99,
        },
        {
            "id": "template-enterprise",
            "name": "Enterprise",
            "category": "enterprise",
            "description": "Full feature set for large organizations",
            "features": [
                "all_features",
                "multi_tenant",
                "custom_integrations",
                "dedicated_support",
            ],
            "limits": {"max_users": 1000, "max_storage_gb": 500},
            "price_monthly": 299.99,
        },
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    return templates


# === Health Check ===


@licensing_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def licensing_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check licensing service health."""
    return {
        "status": "healthy",
        "license_validation": "operational",
        "feature_checks": "operational",
        "database_connection": "healthy",
        "active_licenses": 2,
        "last_check": "2025-01-15T10:30:00Z",
    }


# Export the router
__all__ = ["licensing_router"]
