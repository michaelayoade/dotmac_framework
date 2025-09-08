"""
GIS Schemas following DotMac DRY patterns.
All schemas inherit from base classes to eliminate code duplication.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field, field_validator

from dotmac.core.schemas.base_schemas import (
    BaseCreateSchema,
    BaseResponseSchema,
    BaseUpdateSchema,
    CurrencyMixin,
    GeoLocationMixin,
)

from .models import NetworkNodeTypeEnum, ServiceTypeEnum

# ============================================================================
# SERVICE AREA SCHEMAS
# ============================================================================


class ServiceAreaCreate(BaseCreateSchema, GeoLocationMixin):
    """Create schema for service areas - inherits geo location fields."""

    name: str = Field(..., min_length=1, max_length=200, description="Service area name")
    description: Optional[str] = Field(None, max_length=1000)
    polygon_coordinates: list[dict[str, float]] = Field(..., description="Area boundary coordinates")
    service_types: list[ServiceTypeEnum] = Field(..., description="Available services")

    @field_validator("polygon_coordinates")
    @classmethod
    def validate_polygon(cls, v):
        """Validate polygon has minimum 3 points."""
        if len(v) < 3:
            raise ValueError("Polygon must have at least 3 coordinates")
        return v


class ServiceAreaUpdate(BaseUpdateSchema):
    """Update schema for service areas - all fields optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    polygon_coordinates: Optional[list[dict[str, float]]] = None
    service_types: Optional[list[ServiceTypeEnum]] = None
    is_active: Optional[bool] = None


class ServiceAreaResponse(BaseResponseSchema, GeoLocationMixin):
    """Response schema inheriting all standard fields."""

    polygon_coordinates: list[dict[str, float]]
    service_types: list[ServiceTypeEnum]
    population: int = 0
    households: int = 0
    businesses: int = 0
    coverage_percentage: float = 0.0
    last_analyzed_at: Optional[datetime] = None


# ============================================================================
# NETWORK NODE SCHEMAS
# ============================================================================


class NetworkNodeCreate(BaseCreateSchema, GeoLocationMixin):
    """Create network infrastructure node."""

    name: str = Field(..., min_length=1, max_length=200)
    node_type: NetworkNodeTypeEnum = Field(..., description="Node type")
    ip_address: Optional[str] = Field(None, description="IP address")
    mac_address: Optional[str] = Field(None, description="MAC address")
    bandwidth_mbps: Optional[int] = Field(None, ge=1, description="Bandwidth in Mbps")
    coverage_radius_km: Optional[float] = Field(None, ge=0, description="Coverage radius")
    service_area_id: Optional[UUID] = Field(None, description="Associated service area")


class NetworkNodeUpdate(BaseUpdateSchema):
    """Update network node - all optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    node_type: Optional[NetworkNodeTypeEnum] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    bandwidth_mbps: Optional[int] = Field(None, ge=1)
    coverage_radius_km: Optional[float] = Field(None, ge=0)
    operational_status: Optional[str] = None
    is_active: Optional[bool] = None


class NetworkNodeResponse(BaseResponseSchema, GeoLocationMixin):
    """Network node response with all details."""

    node_type: NetworkNodeTypeEnum
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    bandwidth_mbps: Optional[int] = None
    coverage_radius_km: Optional[float] = None
    operational_status: str = "active"
    last_seen_at: Optional[datetime] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    firmware_version: Optional[str] = None


# ============================================================================
# COVERAGE ANALYSIS SCHEMAS
# ============================================================================


class CoverageAnalysisRequest(BaseCreateSchema):
    """Request for coverage analysis."""

    service_area_id: UUID = Field(..., description="Service area to analyze")
    service_types: list[ServiceTypeEnum] = Field(..., description="Services to analyze")
    include_demographics: bool = Field(True, description="Include demographic data")
    include_competition: bool = Field(False, description="Include competitor analysis")
    analysis_parameters: Optional[dict[str, Any]] = Field({}, description="Custom parameters")


class CoverageGapSchema(BaseResponseSchema):
    """Coverage gap information."""

    gap_type: str
    severity: str
    polygon_coordinates: list[dict[str, float]]
    affected_customers: int = 0
    potential_revenue: float = 0.0
    buildout_cost: float = 0.0
    priority_score: float = 0.0
    recommendations: list[str] = []


class CoverageRecommendationSchema(BaseResponseSchema, CurrencyMixin):
    """Coverage improvement recommendation."""

    recommendation_type: str
    priority: str
    description: str
    timeframe: Optional[str] = None
    requirements: list[str] = []
    affected_areas: list[dict[str, Any]] = []


class CoverageAnalysisResponse(BaseResponseSchema):
    """Complete coverage analysis results."""

    service_area_id: UUID
    service_types: list[ServiceTypeEnum]
    coverage_percentage: float
    population: int = 0
    households: int = 0
    businesses: int = 0

    # Analysis results
    gaps: list[CoverageGapSchema] = []
    recommendations: list[CoverageRecommendationSchema] = []

    # Demographics (optional)
    demographics: Optional[dict[str, Any]] = None
    competitor_analysis: Optional[dict[str, Any]] = None


# ============================================================================
# TERRITORY MANAGEMENT SCHEMAS
# ============================================================================


class TerritoryCreate(BaseCreateSchema):
    """Create territory schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    boundary_coordinates: list[dict[str, float]] = Field(..., description="Territory boundary")
    territory_type: str = Field("sales", description="Territory type")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color")
    assigned_user_id: Optional[UUID] = None
    revenue_target: Optional[float] = Field(None, ge=0)

    @field_validator("boundary_coordinates")
    @classmethod
    def validate_boundary(cls, v):
        """Validate territory boundary."""
        if len(v) < 3:
            raise ValueError("Territory boundary must have at least 3 points")
        return v


class TerritoryUpdate(BaseUpdateSchema):
    """Update territory schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    boundary_coordinates: Optional[list[dict[str, float]]] = None
    territory_type: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    assigned_user_id: Optional[UUID] = None
    revenue_target: Optional[float] = Field(None, ge=0)
    is_active: Optional[bool] = None


class TerritoryResponse(BaseResponseSchema):
    """Territory response schema."""

    boundary_coordinates: list[dict[str, float]]
    territory_type: str
    color: Optional[str] = None
    assigned_user_id: Optional[UUID] = None
    assigned_team: Optional[str] = None
    customer_count: int = 0
    revenue_target: float = 0.0
    actual_revenue: float = 0.0
    competitor_analysis: dict[str, Any] = {}
    demographics: dict[str, Any] = {}


# ============================================================================
# ROUTE OPTIMIZATION SCHEMAS
# ============================================================================


class RouteOptimizationRequest(BaseCreateSchema):
    """Route optimization request."""

    start_coordinates: dict[str, float] = Field(..., description="Starting point")
    end_coordinates: Optional[dict[str, float]] = Field(None, description="End point")
    waypoints: list[dict[str, float]] = Field([], description="Intermediate points")
    optimization_type: str = Field("shortest", description="Optimization goal")
    vehicle_type: str = Field("truck", description="Vehicle type")
    constraints: dict[str, Any] = Field({}, description="Route constraints")

    @field_validator("start_coordinates")
    @classmethod
    def validate_start_coords(cls, v):
        """Validate start coordinates."""
        required_keys = ["latitude", "longitude"]
        if not all(key in v for key in required_keys):
            raise ValueError("Start coordinates must include latitude and longitude")
        return v


class RouteOptimizationResponse(BaseResponseSchema):
    """Route optimization results."""

    start_coordinates: dict[str, float]
    end_coordinates: Optional[dict[str, float]] = None
    waypoints: list[dict[str, float]] = []
    optimization_type: str
    vehicle_type: str

    # Results
    optimized_route: Optional[list[dict[str, float]]] = None
    total_distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[int] = None
    calculated_at: Optional[datetime] = None


# ============================================================================
# GEOCODING SCHEMAS
# ============================================================================


class GeocodingRequest(BaseCreateSchema):
    """Geocoding request schema."""

    address: str = Field(..., min_length=1, max_length=500, description="Address to geocode")
    country: Optional[str] = Field(None, description="Country filter")
    bounds: Optional[dict[str, float]] = Field(None, description="Bounding box for results")


class ReverseGeocodingRequest(BaseCreateSchema):
    """Reverse geocoding request."""

    latitude: float = Field(..., ge=-90, le=90, description="Latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude")


class GeocodingResponse(BaseResponseSchema):
    """Geocoding response."""

    address: str
    latitude: float
    longitude: float
    confidence: float = Field(..., ge=0, le=1, description="Result confidence score")
    components: dict[str, str] = Field({}, description="Address components")


# Export all schemas
__all__ = [
    # Service Areas
    "ServiceAreaCreate",
    "ServiceAreaUpdate",
    "ServiceAreaResponse",
    # Network Nodes
    "NetworkNodeCreate",
    "NetworkNodeUpdate",
    "NetworkNodeResponse",
    # Coverage Analysis
    "CoverageAnalysisRequest",
    "CoverageAnalysisResponse",
    "CoverageGapSchema",
    "CoverageRecommendationSchema",
    # Territories
    "TerritoryCreate",
    "TerritoryUpdate",
    "TerritoryResponse",
    # Route Optimization
    "RouteOptimizationRequest",
    "RouteOptimizationResponse",
    # Geocoding
    "GeocodingRequest",
    "ReverseGeocodingRequest",
    "GeocodingResponse",
]
