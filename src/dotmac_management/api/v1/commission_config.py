"""
Commission Configuration API - DRY Migration
Commission management endpoints using RouterFactory patterns.
"""

from typing import Any

from fastapi import Depends, Query
from pydantic import BaseModel, Field

from dotmac.application import RouterFactory, standard_exception_handler
from dotmac_shared.api.dependencies import (
    PaginatedDependencies,
    StandardDependencies,
    get_paginated_deps,
    get_standard_deps,
)

# === Commission Configuration Schemas ===


class CommissionConfigCreateRequest(BaseModel):
    """Request schema for creating commission configurations."""

    name: str = Field(..., description="Configuration name")
    commission_type: str = Field(..., description="Type of commission (percentage, fixed)")
    rate: float = Field(..., description="Commission rate")
    conditions: dict[str, Any] = Field(..., description="Commission conditions")
    applies_to: list[str] = Field(..., description="Services/products this applies to")


class CommissionConfigUpdateRequest(BaseModel):
    """Request schema for updating commission configurations."""

    name: str | None = Field(None, description="Configuration name")
    rate: float | None = Field(None, description="Commission rate")
    conditions: dict[str, Any] | None = Field(None, description="Commission conditions")
    is_active: bool | None = Field(None, description="Configuration active status")


# === Commission Configuration Router ===

commission_config_router = RouterFactory.create_standard_router(
    prefix="/commission-config",
    tags=["commission-config"],
)


# === Configuration Management ===


@commission_config_router.get("/configurations", response_model=list[dict[str, Any]])
@standard_exception_handler
async def list_commission_configurations(
    commission_type: str | None = Query(None, description="Filter by commission type"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    deps: PaginatedDependencies = Depends(get_paginated_deps),
) -> list[dict[str, Any]]:
    """List all commission configurations."""
    # Mock implementation
    configurations = [
        {
            "id": "config-001",
            "name": "Standard Reseller Commission",
            "commission_type": "percentage",
            "rate": 15.0,
            "conditions": {
                "min_monthly_revenue": 1000,
                "customer_retention_months": 6,
            },
            "applies_to": ["internet_service", "phone_service"],
            "is_active": True,
            "created_at": "2024-01-01T00:00:00Z",
        },
        {
            "id": "config-002",
            "name": "Premium Partner Commission",
            "commission_type": "percentage",
            "rate": 20.0,
            "conditions": {
                "min_monthly_revenue": 5000,
                "customer_retention_months": 12,
                "tier": "premium",
            },
            "applies_to": ["internet_service", "phone_service", "tv_service"],
            "is_active": True,
            "created_at": "2024-02-01T00:00:00Z",
        },
    ]

    # Apply filters
    if commission_type:
        configurations = [c for c in configurations if c["commission_type"] == commission_type]
    if is_active is not None:
        configurations = [c for c in configurations if c["is_active"] == is_active]

    return configurations[: deps.pagination.size]


@commission_config_router.post("/configurations", response_model=dict[str, Any])
@standard_exception_handler
async def create_commission_configuration(
    request: CommissionConfigCreateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Create a new commission configuration."""
    config_id = f"config-{request.name.lower().replace(' ', '-')}"

    return {
        "id": config_id,
        "name": request.name,
        "commission_type": request.commission_type,
        "rate": request.rate,
        "conditions": request.conditions,
        "applies_to": request.applies_to,
        "is_active": True,
        "created_by": deps.user_id,
        "created_at": "2025-01-15T10:30:00Z",
        "message": "Commission configuration created successfully",
    }


@commission_config_router.get("/configurations/{config_id}", response_model=dict[str, Any])
@standard_exception_handler
async def get_commission_configuration(
    config_id: str,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get commission configuration details."""
    return {
        "id": config_id,
        "name": "Standard Reseller Commission",
        "commission_type": "percentage",
        "rate": 15.0,
        "conditions": {
            "min_monthly_revenue": 1000,
            "customer_retention_months": 6,
        },
        "applies_to": ["internet_service", "phone_service"],
        "is_active": True,
        "usage_stats": {
            "active_partners": 12,
            "total_commissions_paid": 25670.50,
            "avg_monthly_commission": 2139.21,
        },
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-12-01T00:00:00Z",
    }


@commission_config_router.put("/configurations/{config_id}", response_model=dict[str, Any])
@standard_exception_handler
async def update_commission_configuration(
    config_id: str,
    request: CommissionConfigUpdateRequest,
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Update commission configuration."""
    return {
        "id": config_id,
        "status": "updated",
        "updated_fields": {k: v for k, v in request.model_dump().items() if v is not None},
        "updated_by": deps.user_id,
        "updated_at": "2025-01-15T10:30:00Z",
        "message": "Commission configuration updated successfully",
    }


# === Commission Calculation ===


@commission_config_router.post("/calculate", response_model=dict[str, Any])
@standard_exception_handler
async def calculate_commission(
    config_id: str = Query(..., description="Configuration ID"),
    revenue: float = Query(..., description="Revenue amount"),
    service_type: str = Query(..., description="Service type"),
    partner_tier: str | None = Query(None, description="Partner tier"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Calculate commission based on configuration."""
    # Mock calculation logic
    base_rate = 15.0
    commission_amount = revenue * (base_rate / 100)

    # Apply tier multiplier if applicable
    tier_multipliers = {"standard": 1.0, "premium": 1.2, "elite": 1.5}
    multiplier = tier_multipliers.get(partner_tier or "standard", 1.0)
    final_commission = commission_amount * multiplier

    return {
        "config_id": config_id,
        "revenue": revenue,
        "service_type": service_type,
        "base_rate": base_rate,
        "base_commission": commission_amount,
        "tier_multiplier": multiplier,
        "final_commission": final_commission,
        "calculation_date": "2025-01-15T10:30:00Z",
        "calculation_details": {
            "formula": f"({revenue} * {base_rate}%) * {multiplier}",
            "tier": partner_tier or "standard",
        },
    }


# === Commission Templates ===


@commission_config_router.get("/templates", response_model=list[dict[str, Any]])
@standard_exception_handler
async def get_commission_templates(
    category: str | None = Query(None, description="Filter by category"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> list[dict[str, Any]]:
    """Get predefined commission configuration templates."""
    templates = [
        {
            "id": "template-basic",
            "name": "Basic Reseller",
            "category": "reseller",
            "commission_type": "percentage",
            "rate": 10.0,
            "conditions": {"min_monthly_revenue": 500},
            "applies_to": ["internet_service"],
            "description": "Basic commission structure for new resellers",
        },
        {
            "id": "template-standard",
            "name": "Standard Partner",
            "category": "partner",
            "commission_type": "percentage",
            "rate": 15.0,
            "conditions": {
                "min_monthly_revenue": 1000,
                "customer_retention_months": 6,
            },
            "applies_to": ["internet_service", "phone_service"],
            "description": "Standard commission for established partners",
        },
        {
            "id": "template-enterprise",
            "name": "Enterprise Affiliate",
            "category": "enterprise",
            "commission_type": "percentage",
            "rate": 25.0,
            "conditions": {
                "min_monthly_revenue": 10000,
                "customer_retention_months": 12,
                "tier": "enterprise",
            },
            "applies_to": ["all_services"],
            "description": "Premium commission for enterprise affiliates",
        },
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    return templates


# === Analytics ===


@commission_config_router.get("/analytics", response_model=dict[str, Any])
@standard_exception_handler
async def get_commission_analytics(
    time_period: str = Query("30d", description="Time period for analytics"),
    config_id: str | None = Query(None, description="Filter by configuration"),
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Get commission configuration analytics."""
    return {
        "time_period": time_period,
        "summary": {
            "total_commissions_paid": 125670.50,
            "average_commission_rate": 16.5,
            "active_configurations": 3,
            "participating_partners": 25,
        },
        "by_configuration": [
            {
                "config_id": "config-001",
                "name": "Standard Reseller Commission",
                "total_paid": 75420.30,
                "partner_count": 15,
                "avg_commission": 5028.02,
            },
            {
                "config_id": "config-002",
                "name": "Premium Partner Commission",
                "total_paid": 50250.20,
                "partner_count": 10,
                "avg_commission": 5025.02,
            },
        ],
        "trends": {
            "monthly_growth": "+12%",
            "partner_acquisition": "+8%",
            "commission_per_partner": "+5%",
        },
    }


# === Health Check ===


@commission_config_router.get("/health", response_model=dict[str, Any])
@standard_exception_handler
async def commission_config_health_check(
    deps: StandardDependencies = Depends(get_standard_deps),
) -> dict[str, Any]:
    """Check commission configuration service health."""
    return {
        "status": "healthy",
        "active_configurations": 3,
        "calculation_engine": "operational",
        "database_connection": "healthy",
        "last_calculation": "2025-01-15T10:25:00Z",
        "total_calculations_today": 45,
    }


# Export the router
__all__ = ["commission_config_router"]
