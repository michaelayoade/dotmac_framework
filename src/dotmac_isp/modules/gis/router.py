"""
GIS Router using DotMac RouterFactory patterns.
Enforces DRY principles with zero manual router creation.
"""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import \1, Dependsndsses import JSONResponse

from dotmac_shared.api.dependencies import (
    StandardDependencies,
    PaginatedDependencies,
    SearchParams,
    get_standard_deps,
    get_paginated_deps,
    get_admin_deps

from dotmac_shared.api.exception_handlers import standard_exception_handler
from dotmac_shared.api.rate_limiting_decorators import rate_limit
from dotmac_shared.api.router_factory import RouterFactory

from .models import NetworkNode, RouteOptimization, ServiceArea, Territory
from .schemas import (  # Service Areas; Network Nodes; Coverage Analysis; Territory Management; Route Optimization; Geocoding
    CoverageAnalysisRequest,
    CoverageAnalysisResponse,
    GeocodingRequest,
    GeocodingResponse,
    NetworkNodeCreate,
    NetworkNodeResponse,
    NetworkNodeUpdate,
    ReverseGeocodingRequest,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    ServiceAreaCreate,
    ServiceAreaResponse,
    ServiceAreaUpdate,
    TerritoryCreate,
    TerritoryResponse,
    TerritoryUpdate,
)
from .services import (
    GeocodingService,
    RouteOptimizationService,
    ServiceCoverageService,
    TerritoryManagementService,
)

# ============================================================================
# MAIN GIS ROUTER - Aggregates all GIS endpoints
# ============================================================================

gis_router = APIRouter(prefix="/gis", tags=["GIS", "Mapping"])


# ============================================================================
# SERVICE AREA CRUD ROUTER - Uses DotMac RouterFactory
# ============================================================================

service_areas_router = RouterFactory.create_crud_router(
    service_class=ServiceCoverageService,
    create_schema=ServiceAreaCreate,
    update_schema=ServiceAreaUpdate,
    response_schema=ServiceAreaResponse,
    prefix="/service-areas",
    tags=["GIS", "Service Areas"],
    enable_search=True,
    enable_bulk_operations=False,  # Disable bulk for geographic data
)


# Add service area specific endpoints to the CRUD router
@service_areas_router.post("/{area_id}/analyze-coverage")
@rate_limit(max_requests=10, time_window_seconds=60)
@standard_exception_handler
async def analyze_service_area_coverage(
    area_id: UUID = Path(..., description="Service area ID"),
    analysis_request: CoverageAnalysisRequest = Body(...),
    deps: StandardDependencies = Depends(get_standard_deps) = None,
) -> CoverageAnalysisResponse:
    """Analyze coverage for a specific service area."""
    service = ServiceCoverageService(deps.db, deps.tenant_id)

    # Override the service area ID from path parameter
    analysis_request.service_area_id = area_id

    result = await service.analyze_coverage(analysis_request, deps.user_id)
    return CoverageAnalysisResponse(**result)


@service_areas_router.get("/{area_id}/network-nodes")
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def get_service_area_nodes(
    area_id: UUID = Path(..., description="Service area ID"), deps: PaginatedDependencies = Depends(get_paginated_deps) = None
) -> List[NetworkNodeResponse]:
    """Get all network nodes in a service area."""
    from sqlalchemy import select

    # Query network nodes for the service area
    query = (
        select(NetworkNode)
        .where(
            NetworkNode.service_area_id == area_id,
            NetworkNode.tenant_id == deps.tenant_id,
            NetworkNode.is_active == True,
        )
        .offset(deps.pagination.offset)
        .limit(deps.pagination.size)
    )

    result = await deps.db.execute(query)
    nodes = result.scalars().all()

    return [NetworkNodeResponse.model_validate(node) for node in nodes]


# ============================================================================
# NETWORK NODES CRUD ROUTER
# ============================================================================

network_nodes_router = RouterFactory.create_crud_router(
    service_class=None,  # Will implement custom service class
    create_schema=NetworkNodeCreate,
    update_schema=NetworkNodeUpdate,
    response_schema=NetworkNodeResponse,
    prefix="/network-nodes",
    tags=["GIS", "Network Infrastructure"],
    enable_search=True,
    enable_bulk_operations=True,  # Allow bulk operations for network nodes
)


# Custom network node endpoints
@network_nodes_router.get("/by-location")
@rate_limit(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def find_nodes_by_location(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_km: float = Query(1.0, ge=0.1, le=50, description="Search radius in km"),
    deps: StandardDependencies = Depends(get_standard_deps) = None,
) -> List[NetworkNodeResponse]:
    """Find network nodes within radius of coordinates."""
    from sqlalchemy import func, select

    import math

    # Get all nodes (in production, use spatial database query)
    query = select(NetworkNode).where(
        NetworkNode.tenant_id == deps.tenant_id,
        NetworkNode.is_active == True,
        NetworkNode.latitude.isnot(None),
        NetworkNode.longitude.isnot(None),
    )

    result = await deps.db.execute(query)
    all_nodes = result.scalars().all()

    # Filter by distance using haversine formula
    def haversine_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points using haversine formula."""
        R = 6371  # Earth's radius in kilometers
        lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
        lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c

    nearby_nodes = []
    for node in all_nodes:
        distance = haversine_distance(
            latitude, longitude, float(node.latitude), float(node.longitude)
        )
        if distance <= radius_km:
            nearby_nodes.append(node)

    return [NetworkNodeResponse.model_validate(node) for node in nearby_nodes]


# ============================================================================
# TERRITORY MANAGEMENT ROUTER
# ============================================================================

territories_router = RouterFactory.create_crud_router(
    service_class=TerritoryManagementService,
    create_schema=TerritoryCreate,
    update_schema=TerritoryUpdate,
    response_schema=TerritoryResponse,
    prefix="/territories",
    tags=["GIS", "Territory Management"],
    enable_search=True,
    enable_bulk_operations=False,
)


@territories_router.get("/containing-point")
@rate_limit(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def find_territories_containing_point(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    deps: StandardDependencies = Depends(get_standard_deps) = None,
) -> List[TerritoryResponse]:
    """Find territories containing a geographic point."""
    service = TerritoryManagementService(deps.db, deps.tenant_id)
    territories = await service.find_territories_containing_point(
        latitude, longitude, deps.user_id
    )
    return [TerritoryResponse.model_validate(t) for t in territories]


@territories_router.get("/{territory_id}/metrics")
@rate_limit(max_requests=30, time_window_seconds=60)
@standard_exception_handler
async def get_territory_metrics(
    territory_id: UUID = Path(..., description="Territory ID"),
    deps: StandardDependencies = Depends(get_standard_deps) = None,
) -> Dict[str, Any]:
    """Get territory performance metrics."""
    service = TerritoryManagementService(deps.db, deps.tenant_id)
    return await service.calculate_territory_metrics(territory_id, deps.user_id)


# ============================================================================
# ROUTE OPTIMIZATION ENDPOINTS
# ============================================================================


@gis_router.post("/route-optimization", response_model=RouteOptimizationResponse)
@rate_limit(max_requests=20, time_window_seconds=60)
@standard_exception_handler
async def optimize_route(
    request: RouteOptimizationRequest = Body(...), deps: StandardDependencies = Depends(get_standard_deps) = None
) -> RouteOptimizationResponse:
    """Optimize route for field operations."""
    service = RouteOptimizationService(deps.db, deps.tenant_id)
    result = await service.optimize_route(request, deps.user_id)
    return RouteOptimizationResponse(**result)


@gis_router.get("/route-optimizations")
@rate_limit(max_requests=50, time_window_seconds=60)
@standard_exception_handler
async def list_route_optimizations(
    deps: PaginatedDependencies = Depends(get_paginated_deps) = None,
) -> List[RouteOptimizationResponse]:
    """List previous route optimizations."""
    from sqlalchemy import desc, select

    query = (
        select(RouteOptimization)
        .where(RouteOptimization.tenant_id == deps.tenant_id)
        .order_by(desc(RouteOptimization.calculated_at))
        .offset(deps.pagination.offset)
        .limit(deps.pagination.size)
    )

    result = await deps.db.execute(query)
    optimizations = result.scalars().all()

    return [RouteOptimizationResponse.model_validate(opt) for opt in optimizations]


# ============================================================================
# GEOCODING ENDPOINTS
# ============================================================================


@gis_router.post("/geocoding", response_model=GeocodingResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def geocode_address(
    request: GeocodingRequest = Body(...), deps: StandardDependencies = Depends(get_standard_deps) = None
) -> GeocodingResponse:
    """Convert address to coordinates."""
    service = GeocodingService(deps.tenant_id)
    result = await service.geocode_address(request)
    return GeocodingResponse(**result)


@gis_router.post("/reverse-geocoding", response_model=GeocodingResponse)
@rate_limit(max_requests=100, time_window_seconds=60)
@standard_exception_handler
async def reverse_geocode(
    request: ReverseGeocodingRequest = Body(...), deps: StandardDependencies = Depends(get_standard_deps) = None
) -> GeocodingResponse:
    """Convert coordinates to address."""
    service = GeocodingService(deps.tenant_id)
    result = await service.reverse_geocode(request)
    return GeocodingResponse(**result)


# ============================================================================
# COMPREHENSIVE COVERAGE ANALYSIS ENDPOINT
# ============================================================================


@gis_router.post("/coverage-analysis", response_model=CoverageAnalysisResponse)
@rate_limit(
    max_requests=5, time_window_seconds=60
)  # Strict limit for intensive analysis
@standard_exception_handler
async def comprehensive_coverage_analysis(
    request: CoverageAnalysisRequest = Body(...), deps: StandardDependencies = Depends(get_standard_deps) = None
) -> CoverageAnalysisResponse:
    """Perform comprehensive coverage analysis."""
    service = ServiceCoverageService(deps.db, deps.tenant_id)
    result = await service.analyze_coverage(request, deps.user_id)
    return CoverageAnalysisResponse(**result)


# ============================================================================
# REGISTER ALL SUB-ROUTERS WITH MAIN GIS ROUTER
# ============================================================================

# Include all sub-routers in the main GIS router
gis_router.include_router(service_areas_router)
gis_router.include_router(network_nodes_router)
gis_router.include_router(territories_router)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================


@gis_router.get("/health")
@rate_limit(max_requests=100, time_window_seconds=60)
async def gis_health_check() -> JSONResponse:
    """GIS module health check."""
    return JSONResponse(
        {
            "status": "healthy",
            "module": "gis",
            "features": [
                "service_area_management",
                "coverage_analysis",
                "network_node_tracking",
                "territory_management",
                "route_optimization",
                "geocoding",
            ],
            "integrations": [
                "dotmac_shared_patterns",
                "multi_tenant_isolation",
                "haversine_distance_calculation",
            ],
        }
    )


# Export router for inclusion in main app
__all__ = ["gis_router"]
